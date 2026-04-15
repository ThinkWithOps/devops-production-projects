"""
Tests for the Order Service.
"""
import os
import sys
import tempfile
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../services/order-service"))

os.environ.setdefault("DATABASE_URL", tempfile.mktemp(suffix=".db"))
os.environ.setdefault("RESTAURANT_SERVICE_URL", "http://mock-restaurant:8002")
os.environ.setdefault("ORDER_SERVICE_FAILURE_MODE", "false")

from httpx import AsyncClient, ASGITransport
from main import app

MOCK_RESTAURANT = {
    "id": 1,
    "name": "The Golden Spice",
    "cuisine_type": "Indian",
    "address": "245 Curry Lane",
    "rating": 4.7,
    "delivery_time_min": 35,
    "min_order_amount": 15.0,
    "is_open": True,
    "menu": [
        {"id": 1, "restaurant_id": 1, "name": "Butter Chicken", "price": 16.99, "category": "Main", "is_available": True, "description": "Tender chicken"},
        {"id": 2, "restaurant_id": 1, "name": "Garlic Naan", "price": 3.99, "category": "Bread", "is_available": True, "description": "Soft bread"},
    ],
}


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"
    assert resp.json()["service"] == "order-service"


@pytest.mark.asyncio
async def test_create_order(client):
    with patch("main.httpx.AsyncClient") as mock_httpx:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_RESTAURANT
        mock_response.raise_for_status = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

        payload = {
            "user_id": 1,
            "restaurant_id": 1,
            "items": [
                {"menu_item_id": 1, "name": "Butter Chicken", "quantity": 2, "unit_price": 16.99},
                {"menu_item_id": 2, "name": "Garlic Naan", "quantity": 3, "unit_price": 3.99},
            ],
            "delivery_address": "42 Delivery Street, Brooklyn, NY 11201",
        }
        resp = await client.post("/orders", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"
        assert data["user_id"] == 1
        assert data["restaurant_id"] == 1
        assert abs(data["total_amount"] - (2 * 16.99 + 3 * 3.99)) < 0.01


@pytest.mark.asyncio
async def test_get_order_not_found(client):
    resp = await client.get("/orders/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_order_status(client):
    with patch("main.httpx.AsyncClient") as mock_httpx:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_RESTAURANT
        mock_response.raise_for_status = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

        payload = {
            "user_id": 1,
            "restaurant_id": 1,
            "items": [{"menu_item_id": 1, "name": "Butter Chicken", "quantity": 1, "unit_price": 16.99}],
            "delivery_address": "Status Test Ave, NY",
        }
        create_resp = await client.post("/orders", json=payload)
        order_id = create_resp.json()["id"]

    update_resp = await client.patch(f"/orders/{order_id}", json={"status": "confirmed"})
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "confirmed"


@pytest.mark.asyncio
async def test_update_invalid_status(client):
    with patch("main.httpx.AsyncClient") as mock_httpx:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_RESTAURANT
        mock_response.raise_for_status = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

        create_resp = await client.post("/orders", json={
            "user_id": 1,
            "restaurant_id": 1,
            "items": [{"menu_item_id": 1, "name": "Butter Chicken", "quantity": 1, "unit_price": 16.99}],
            "delivery_address": "Invalid Status Test",
        })
        order_id = create_resp.json()["id"]

    resp = await client.patch(f"/orders/{order_id}", json={"status": "flying"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_user_orders(client):
    resp = await client.get("/orders/user/1")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
