import json
import os
import random
import time
from contextlib import asynccontextmanager
from typing import List, Optional

import aiosqlite
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel

from database import DATABASE_URL, init_db

RESTAURANT_SERVICE_URL = os.getenv("RESTAURANT_SERVICE_URL", "http://localhost:8002")
ORDER_SERVICE_FAILURE_MODE = os.getenv("ORDER_SERVICE_FAILURE_MODE", "false").lower() == "true"

orders_total = Counter("orders_total", "Total number of orders placed", ["status"])
order_processing_seconds = Histogram(
    "order_processing_seconds",
    "Time spent processing orders",
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)
failed_orders_total = Counter("failed_orders_total", "Total number of failed orders")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Order Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)


class OrderItem(BaseModel):
    menu_item_id: int
    name: str
    quantity: int
    unit_price: float


class OrderCreate(BaseModel):
    user_id: int
    restaurant_id: int
    items: List[OrderItem]
    delivery_address: str
    notes: Optional[str] = None


class OrderStatusUpdate(BaseModel):
    status: str


class OrderResponse(BaseModel):
    id: int
    user_id: int
    restaurant_id: int
    restaurant_name: str
    items: List[OrderItem]
    total_amount: float
    status: str
    delivery_address: str
    notes: Optional[str]
    created_at: str
    updated_at: str


def parse_order_row(row) -> OrderResponse:
    items = json.loads(row["items"])
    return OrderResponse(
        id=row["id"],
        user_id=row["user_id"],
        restaurant_id=row["restaurant_id"],
        restaurant_name=row["restaurant_name"],
        items=[OrderItem(**i) for i in items],
        total_amount=row["total_amount"],
        status=row["status"],
        delivery_address=row["delivery_address"],
        notes=row["notes"],
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "order-service", "version": "1.0.0"}


@app.post("/orders", response_model=OrderResponse, status_code=201)
async def create_order(order: OrderCreate):
    start_time = time.time()

    if ORDER_SERVICE_FAILURE_MODE and random.random() < 0.5:
        failed_orders_total.inc()
        orders_total.labels(status="failed").inc()
        raise HTTPException(status_code=500, detail="Order service is experiencing issues. Please try again.")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{RESTAURANT_SERVICE_URL}/restaurants/{order.restaurant_id}")
            if resp.status_code == 404:
                raise HTTPException(status_code=404, detail="Restaurant not found")
            resp.raise_for_status()
            restaurant_data = resp.json()
    except httpx.TimeoutException:
        failed_orders_total.inc()
        orders_total.labels(status="failed").inc()
        raise HTTPException(status_code=503, detail="Restaurant service timeout. Please try again.")
    except httpx.RequestError as e:
        failed_orders_total.inc()
        orders_total.labels(status="failed").inc()
        raise HTTPException(status_code=503, detail=f"Cannot reach restaurant service: {str(e)}")

    menu_map = {item["id"]: item for item in restaurant_data.get("menu", [])}
    for order_item in order.items:
        if order_item.menu_item_id not in menu_map:
            raise HTTPException(
                status_code=400,
                detail=f"Menu item {order_item.menu_item_id} not found in restaurant menu",
            )

    total_amount = sum(item.quantity * item.unit_price for item in order.items)
    items_json = json.dumps([i.model_dump() for i in order.items])

    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """INSERT INTO orders (user_id, restaurant_id, restaurant_name, items, total_amount,
               status, delivery_address, notes) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)""",
            (
                order.user_id,
                order.restaurant_id,
                restaurant_data["name"],
                items_json,
                total_amount,
                order.delivery_address,
                order.notes,
            ),
        )
        await db.commit()
        order_id = cursor.lastrowid

        cursor = await db.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = await cursor.fetchone()

    elapsed = time.time() - start_time
    order_processing_seconds.observe(elapsed)
    orders_total.labels(status="success").inc()

    return parse_order_row(row)


@app.get("/orders/user/{user_id}", response_model=List[OrderResponse])
async def get_user_orders(user_id: int):
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
        )
        rows = await cursor.fetchall()
    return [parse_order_row(r) for r in rows]


@app.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: int):
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
    return parse_order_row(row)


@app.patch("/orders/{order_id}", response_model=OrderResponse)
async def update_order_status(order_id: int, update: OrderStatusUpdate):
    valid_statuses = ["pending", "confirmed", "preparing", "out_for_delivery", "delivered", "cancelled"]
    if update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT id FROM orders WHERE id = ?", (order_id,))
        existing = await cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Order not found")

        await db.execute(
            "UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (update.status, order_id),
        )
        await db.commit()

        cursor = await db.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = await cursor.fetchone()

    return parse_order_row(row)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=False)
