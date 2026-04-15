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


app = FastAPI(title="Restaurant Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)


class MenuItem(BaseModel):
    id: int
    restaurant_id: int
    name: str
    description: Optional[str]
    price: float
    category: str
    is_available: bool


class RestaurantSummary(BaseModel):
    id: int
    name: str
    cuisine_type: str
    address: str
    rating: float
    delivery_time_min: int
    min_order_amount: float
    is_open: bool


class RestaurantDetail(RestaurantSummary):
    menu: List[MenuItem]


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "restaurant-service", "version": "1.0.0"}


@app.get("/restaurants", response_model=List[RestaurantSummary])
async def list_restaurants():
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM restaurants ORDER BY rating DESC")
        rows = await cursor.fetchall()
    return [
        RestaurantSummary(
            id=r["id"],
            name=r["name"],
            cuisine_type=r["cuisine_type"],
            address=r["address"],
            rating=r["rating"],
            delivery_time_min=r["delivery_time_min"],
            min_order_amount=r["min_order_amount"],
            is_open=bool(r["is_open"]),
        )
        for r in rows
    ]


@app.get("/restaurants/{restaurant_id}", response_model=RestaurantDetail)
async def get_restaurant(restaurant_id: int):
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM restaurants WHERE id = ?", (restaurant_id,))
        restaurant = await cursor.fetchone()
        if not restaurant:
            raise HTTPException(status_code=404, detail="Restaurant not found")

        cursor = await db.execute(
            "SELECT * FROM menu_items WHERE restaurant_id = ? AND is_available = 1 ORDER BY category",
            (restaurant_id,),
        )
        items = await cursor.fetchall()

    menu = [
        MenuItem(
            id=item["id"],
            restaurant_id=item["restaurant_id"],
            name=item["name"],
            description=item["description"],
            price=item["price"],
            category=item["category"],
            is_available=bool(item["is_available"]),
        )
        for item in items
    ]

    return RestaurantDetail(
        id=restaurant["id"],
        name=restaurant["name"],
        cuisine_type=restaurant["cuisine_type"],
        address=restaurant["address"],
        rating=restaurant["rating"],
        delivery_time_min=restaurant["delivery_time_min"],
        min_order_amount=restaurant["min_order_amount"],
        is_open=bool(restaurant["is_open"]),
        menu=menu,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=False)
