"""
Tests for the Delivery Service.
"""
import os
import sys
import tempfile
import pytest
import pytest_asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../services/delivery-service"))

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
    assert resp.json()["status"] == "healthy"
    assert resp.json()["service"] == "delivery-service"


@pytest.mark.asyncio
async def test_assign_delivery(client):
    payload = {
        "order_id": 1001,
        "pickup_address": "The Golden Spice, 245 Curry Lane, Manhattan, NY",
        "delivery_address": "42 Customer Road, Brooklyn, NY 11201",
    }
    resp = await client.post("/delivery", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["order_id"] == 1001
    assert data["agent_name"] is not None
    assert data["status"] == "assigned"
    assert data["estimated_minutes"] > 0


@pytest.mark.asyncio
async def test_assign_delivery_duplicate(client):
    payload = {
        "order_id": 2002,
        "pickup_address": "Restaurant Row, Manhattan",
        "delivery_address": "22 Client Street, Queens",
    }
    await client.post("/delivery", json=payload)

    resp = await client.post("/delivery", json=payload)
    assert resp.status_code == 400
    assert "already assigned" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_get_delivery_status(client):
    payload = {
        "order_id": 3003,
        "pickup_address": "Mama Rosa's, 88 Pasta Blvd, Brooklyn",
        "delivery_address": "99 Hungry Lane, Bronx, NY 10451",
    }
    await client.post("/delivery", json=payload)

    resp = await client.get("/delivery/3003")
    assert resp.status_code == 200
    assert resp.json()["order_id"] == 3003


@pytest.mark.asyncio
async def test_get_delivery_not_found(client):
    resp = await client.get("/delivery/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_delivery_status(client):
    payload = {
        "order_id": 4004,
        "pickup_address": "Dragon Palace, Queens",
        "delivery_address": "55 Destination Ave, Manhattan",
    }
    await client.post("/delivery", json=payload)

    update_resp = await client.patch("/delivery/4004", json={
        "status": "picked_up",
        "current_location": "Dragon Palace Restaurant",
        "estimated_minutes": 25,
    })
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "picked_up"
    assert update_resp.json()["current_location"] == "Dragon Palace Restaurant"
    assert update_resp.json()["estimated_minutes"] == 25


@pytest.mark.asyncio
async def test_update_invalid_delivery_status(client):
    payload = {
        "order_id": 5005,
        "pickup_address": "El Taco Loco, Bronx",
        "delivery_address": "77 Final Ave, Brooklyn",
    }
    await client.post("/delivery", json=payload)

    resp = await client.patch("/delivery/5005", json={"status": "teleporting"})
    assert resp.status_code == 400
