#!/usr/bin/env python3
"""Clear the Big Board database for development purposes."""

import asyncio
from pathlib import Path

DATABASE_PATH = Path(__file__).parent / "big_board.db"

async def clear_database():
    """Clear all data from the database and re-initialize with defaults."""
    import aiosqlite
    from database import init_db

    if not DATABASE_PATH.exists():
        print("Database does not exist. Creating fresh database...")
        await init_db()
        print("Done.")
        return

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM items")
        await db.execute("DELETE FROM family_members")
        await db.execute("DELETE FROM categories")
        await db.commit()

    # Re-initialize with default categories
    await init_db()
    print("Database cleared and re-initialized with defaults.")

if __name__ == "__main__":
    asyncio.run(clear_database())
