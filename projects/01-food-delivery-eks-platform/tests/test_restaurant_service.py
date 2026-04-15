"""
Tests for the Restaurant Service.
"""
import os
import sys
import tempfile
import pytest
import pytest_asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../services/restaurant-service"))

os.environ.setdefault("DATABASE_URL", tempfile.mktemp(suffix=".db"))

from httpx import AsyncClient, ASGITransport
from main import app


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "restaurant-service"


@pytest.mark.asyncio
async def test_list_restaurants(client):
    resp = await client.get("/restaurants")
    assert resp.status_code == 200
    restaurants = resp.json()
    assert isinstance(restaurants, list)
    assert len(restaurants) >= 5


@pytest.mark.asyncio
async def test_restaurant_has_required_fields(client):
    resp = await client.get("/restaurants")
    restaurants = resp.json()
    for r in restaurants:
        assert "id" in r
        assert "name" in r
        assert "cuisine_type" in r
        assert "rating" in r
        assert "delivery_time_min" in r
        assert "min_order_amount" in r


@pytest.mark.asyncio
async def test_get_restaurant_by_id(client):
    list_resp = await client.get("/restaurants")
    first_id = list_resp.json()[0]["id"]

    resp = await client.get(f"/restaurants/{first_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == first_id
    assert "menu" in data
    assert isinstance(data["menu"], list)
    assert len(data["menu"]) >= 10


@pytest.mark.asyncio
async def test_menu_item_has_required_fields(client):
    resp = await client.get("/restaurants/1")
    assert resp.status_code == 200
    for item in resp.json()["menu"]:
        assert "id" in item
        assert "name" in item
        assert "price" in item
        assert item["price"] > 0
        assert "category" in item


@pytest.mark.asyncio
async def test_restaurant_not_found(client):
    resp = await client.get("/restaurants/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_restaurants_ordered_by_rating(client):
    resp = await client.get("/restaurants")
    restaurants = resp.json()
    ratings = [r["rating"] for r in restaurants]
    assert ratings == sorted(ratings, reverse=True)
