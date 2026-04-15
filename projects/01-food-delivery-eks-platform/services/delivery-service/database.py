import aiosqlite
import os

DATABASE_URL = os.getenv("DATABASE_URL", "delivery.db")


async def get_db():
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def init_db():
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS delivery_agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                vehicle_type TEXT NOT NULL,
                license_plate TEXT NOT NULL,
                is_available INTEGER DEFAULT 1,
                current_location TEXT DEFAULT 'Base Station',
                rating REAL DEFAULT 4.5
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS deliveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER UNIQUE NOT NULL,
                agent_id INTEGER,
                agent_name TEXT,
                status TEXT DEFAULT 'assigned',
                pickup_address TEXT NOT NULL,
                delivery_address TEXT NOT NULL,
                current_location TEXT,
                estimated_minutes INTEGER DEFAULT 30,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES delivery_agents(id)
            )
        """)
        await db.commit()

        cursor = await db.execute("SELECT COUNT(*) FROM delivery_agents")
        count = (await cursor.fetchone())[0]
        if count == 0:
            agents = [
                ("DeShawn Williams", "+1-555-401-7823", "Motorcycle", "NYC-4521-M", 4.8),
                ("Aisha Patel", "+1-555-302-9145", "Bicycle", "NYC-BIKE-009", 4.9),
                ("Roberto Mendez", "+1-555-503-6287", "Car", "NYC-7834-C", 4.6),
                ("Yuki Tanaka", "+1-555-204-8563", "Motorcycle", "NYC-6102-M", 4.7),
                ("Fatima Al-Hassan", "+1-555-605-3741", "Bicycle", "NYC-BIKE-022", 4.5),
            ]
            await db.executemany(
                "INSERT INTO delivery_agents (name, phone, vehicle_type, license_plate, rating) VALUES (?, ?, ?, ?, ?)",
                agents,
            )
            await db.commit()
