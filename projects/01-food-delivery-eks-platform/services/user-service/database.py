import aiosqlite
import os
from passlib.context import CryptContext

DATABASE_URL = os.getenv("DATABASE_URL", "users.db")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def get_db():
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def init_db():
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                phone TEXT,
                address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

        cursor = await db.execute("SELECT COUNT(*) FROM users")
        count = (await cursor.fetchone())[0]
        if count == 0:
            seed_users = [
                (
                    "Marcus Johnson",
                    "marcus.johnson@gmail.com",
                    pwd_context.hash("SecurePass123!"),
                    "+1-555-234-5678",
                    "142 Maple Street, Brooklyn, NY 11201",
                ),
                (
                    "Priya Sharma",
                    "priya.sharma@outlook.com",
                    pwd_context.hash("MySecret456@"),
                    "+1-555-876-5432",
                    "88 Oak Avenue, Queens, NY 11374",
                ),
                (
                    "Carlos Rivera",
                    "carlos.rivera@yahoo.com",
                    pwd_context.hash("Rivera789#"),
                    "+1-555-321-9876",
                    "37 Elm Court, Manhattan, NY 10001",
                ),
            ]
            await db.executemany(
                "INSERT INTO users (name, email, hashed_password, phone, address) VALUES (?, ?, ?, ?, ?)",
                seed_users,
            )
            await db.commit()
