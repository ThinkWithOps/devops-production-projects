import random
from contextlib import asynccontextmanager
from typing import List, Optional

import aiosqlite
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel

from database import DATABASE_URL, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Delivery Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)


class DeliveryCreate(BaseModel):
    order_id: int
    pickup_address: str
    delivery_address: str
    notes: Optional[str] = None


class DeliveryUpdate(BaseModel):
    current_location: Optional[str] = None
    status: Optional[str] = None
    estimated_minutes: Optional[int] = None


class DeliveryResponse(BaseModel):
    id: int
    order_id: int
    agent_id: Optional[int]
    agent_name: Optional[str]
    status: str
    pickup_address: str
    delivery_address: str
    current_location: Optional[str]
    estimated_minutes: int
    notes: Optional[str]
    created_at: str
    updated_at: str


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "delivery-service", "version": "1.0.0"}


@app.post("/delivery", response_model=DeliveryResponse, status_code=201)
async def assign_delivery(delivery: DeliveryCreate):
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute("SELECT id FROM deliveries WHERE order_id = ?", (delivery.order_id,))
        existing = await cursor.fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="Delivery already assigned for this order")

        cursor = await db.execute("SELECT * FROM delivery_agents WHERE is_available = 1 ORDER BY rating DESC")
        agents = await cursor.fetchall()

        if not agents:
            raise HTTPException(status_code=503, detail="No delivery agents available at this time")

        agent = random.choice(agents)
        estimated_minutes = random.randint(20, 45)

        cursor = await db.execute(
            """INSERT INTO deliveries (order_id, agent_id, agent_name, status, pickup_address,
               delivery_address, current_location, estimated_minutes, notes)
               VALUES (?, ?, ?, 'assigned', ?, ?, ?, ?, ?)""",
            (
                delivery.order_id,
                agent["id"],
                agent["name"],
                delivery.pickup_address,
                delivery.delivery_address,
                agent["current_location"],
                estimated_minutes,
                delivery.notes,
            ),
        )
        await db.execute(
            "UPDATE delivery_agents SET is_available = 0 WHERE id = ?", (agent["id"],)
        )
        await db.commit()
        delivery_id = cursor.lastrowid

        cursor = await db.execute("SELECT * FROM deliveries WHERE id = ?", (delivery_id,))
        row = await cursor.fetchone()

    return DeliveryResponse(
        id=row["id"],
        order_id=row["order_id"],
        agent_id=row["agent_id"],
        agent_name=row["agent_name"],
        status=row["status"],
        pickup_address=row["pickup_address"],
        delivery_address=row["delivery_address"],
        current_location=row["current_location"],
        estimated_minutes=row["estimated_minutes"],
        notes=row["notes"],
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


@app.get("/delivery/{order_id}", response_model=DeliveryResponse)
async def get_delivery_status(order_id: int):
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM deliveries WHERE order_id = ?", (order_id,))
        row = await cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Delivery not found for this order")

    return DeliveryResponse(
        id=row["id"],
        order_id=row["order_id"],
        agent_id=row["agent_id"],
        agent_name=row["agent_name"],
        status=row["status"],
        pickup_address=row["pickup_address"],
        delivery_address=row["delivery_address"],
        current_location=row["current_location"],
        estimated_minutes=row["estimated_minutes"],
        notes=row["notes"],
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


@app.patch("/delivery/{order_id}", response_model=DeliveryResponse)
async def update_delivery(order_id: int, update: DeliveryUpdate):
    valid_statuses = ["assigned", "picked_up", "in_transit", "arrived", "delivered"]
    if update.status and update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM deliveries WHERE order_id = ?", (order_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Delivery not found for this order")

        new_location = update.current_location or row["current_location"]
        new_status = update.status or row["status"]
        new_eta = update.estimated_minutes if update.estimated_minutes is not None else row["estimated_minutes"]

        await db.execute(
            """UPDATE deliveries SET current_location = ?, status = ?, estimated_minutes = ?,
               updated_at = CURRENT_TIMESTAMP WHERE order_id = ?""",
            (new_location, new_status, new_eta, order_id),
        )

        if new_status == "delivered":
            await db.execute(
                "UPDATE delivery_agents SET is_available = 1, current_location = 'Base Station' WHERE id = ?",
                (row["agent_id"],),
            )

        await db.commit()

        cursor = await db.execute("SELECT * FROM deliveries WHERE order_id = ?", (order_id,))
        row = await cursor.fetchone()

    return DeliveryResponse(
        id=row["id"],
        order_id=row["order_id"],
        agent_id=row["agent_id"],
        agent_name=row["agent_name"],
        status=row["status"],
        pickup_address=row["pickup_address"],
        delivery_address=row["delivery_address"],
        current_location=row["current_location"],
        estimated_minutes=row["estimated_minutes"],
        notes=row["notes"],
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8004, reload=False)
