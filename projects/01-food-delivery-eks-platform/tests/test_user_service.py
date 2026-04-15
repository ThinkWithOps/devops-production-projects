"""
Tests for the User Service.
Run against a live docker-compose stack or directly against the app.
"""
import os
import sys
import pytest
import pytest_asyncio
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../services/user-service"))

import tempfile
from httpx import AsyncClient, ASGITransport

os.environ.setdefault("DATABASE_URL", tempfile.mktemp(suffix=".db"))
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")

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
    assert data["service"] == "user-service"
    assert data["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_register_user(client):
    payload = {
        "name": "Alex Thompson",
        "email": "alex.thompson@test.com",
        "password": "StrongPass123!",
        "phone": "+1-555-100-2000",
        "address": "10 Test Street, Manhattan, NY 10001",
    }
    resp = await client.post("/users/register", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == payload["email"]
    assert data["user"]["name"] == payload["name"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    payload = {
        "name": "Duplicate User",
        "email": "duplicate@test.com",
        "password": "Pass123!",
    }
    resp1 = await client.post("/users/register", json=payload)
    assert resp1.status_code == 201

    resp2 = await client.post("/users/register", json=payload)
    assert resp2.status_code == 400
    assert "already registered" in resp2.json()["detail"]


@pytest.mark.asyncio
async def test_login_valid(client):
    email = "logintest@test.com"
    password = "LoginPass456!"
    await client.post("/users/register", json={"name": "Login Tester", "email": email, "password": password})

    resp = await client.post("/users/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == email


@pytest.mark.asyncio
async def test_login_invalid_password(client):
    email = "wrongpass@test.com"
    await client.post("/users/register", json={"name": "WP User", "email": email, "password": "RealPass789!"})

    resp = await client.post("/users/login", json={"email": email, "password": "WrongPassword"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_user_with_token(client):
    reg = await client.post("/users/register", json={
        "name": "Profile User",
        "email": "profile@test.com",
        "password": "ProfilePass!"
    })
    token = reg.json()["access_token"]
    user_id = reg.json()["user"]["id"]

    resp = await client.get(f"/users/{user_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["id"] == user_id


@pytest.mark.asyncio
async def test_get_user_without_token(client):
    resp = await client.get("/users/1")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_nonexistent_user(client):
    reg = await client.post("/users/register", json={
        "name": "Auth User",
        "email": "auth.user@test.com",
        "password": "AuthPass!"
    })
    token = reg.json()["access_token"]

    resp = await client.get("/users/99999", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404
