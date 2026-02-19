import aiosqlite
import asyncio
import os

DB_PATH = "data/simulator.db"

async def test_persistence():
    print(f"Testing persistence on {DB_PATH}")
    uuid = "test-persist-1"
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM devices WHERE uuid=?", (uuid,))
        await db.commit()
    
    print("Deleted old test device")
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO devices (uuid, name, status, mode, publish_topic, interval_ms)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (uuid, "Persist Test", "STOPPED", "RANDOM", "test/persist", 1000))
        await db.commit()
    
    print("Inserted device. Status: STOPPED")
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE devices SET status='RUNNING' WHERE uuid=?", (uuid,))
        await db.commit()
    
    print("Updated status to RUNNING")
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT status FROM devices WHERE uuid=?", (uuid,))
        row = await cursor.fetchone()
        print(f"Read status: {row['status']}")
        assert row['status'] == 'RUNNING'

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_persistence())
