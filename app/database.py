import aiosqlite
import os

DB_PATH = "data/simulator.db"

async def get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db

async def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                uuid TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT DEFAULT 'STOPPED',
                mode TEXT DEFAULT 'RANDOM',
                publish_topic TEXT NOT NULL,
                subscribe_topic TEXT,
                interval_ms INTEGER DEFAULT 1000,
                qos INTEGER DEFAULT 0,
                retain INTEGER DEFAULT 0,
                csv_file_path TEXT,
                csv_loop INTEGER DEFAULT 1
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS device_params (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_uuid TEXT NOT NULL,
                param_name TEXT NOT NULL,
                type TEXT NOT NULL,
                min_val REAL,
                max_val REAL,
                precision INTEGER,
                string_value TEXT,
                FOREIGN KEY(device_uuid) REFERENCES devices(uuid) ON DELETE CASCADE
            )
        """)
        await db.commit()
