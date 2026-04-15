from contextlib import asynccontextmanager
from typing import Optional

import aiosqlite
from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, EmailStr

from auth import (
    create_access_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from database import DATABASE_URL, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="User Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)

security = HTTPBearer()


class UserRegister(BaseModel):
    name: str
    email: str
    password: str
    phone: Optional[str] = None
    address: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str]
    address: Optional[str]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "user-service", "version": "1.0.0"}


@app.post("/users/register", response_model=TokenResponse, status_code=201)
async def register(user: UserRegister):
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT id FROM users WHERE email = ?", (user.email,))
        existing = await cursor.fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed = get_password_hash(user.password)
        cursor = await db.execute(
            "INSERT INTO users (name, email, hashed_password, phone, address) VALUES (?, ?, ?, ?, ?)",
            (user.name, user.email, hashed, user.phone, user.address),
        )
        await db.commit()
        user_id = cursor.lastrowid

        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()

    token = create_access_token({"sub": str(row["id"]), "email": row["email"]})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            phone=row["phone"],
            address=row["address"],
        ),
    )


@app.post("/users/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE email = ?", (credentials.email,))
        row = await cursor.fetchone()

    if not row or not verify_password(credentials.password, row["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": str(row["id"]), "email": row["email"]})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            phone=row["phone"],
            address=row["address"],
        ),
    )


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, current_user: dict = Depends(get_current_user)):
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        id=row["id"],
        name=row["name"],
        email=row["email"],
        phone=row["phone"],
        address=row["address"],
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False)
