import aiosqlite
import json
from datetime import datetime, date
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

DATABASE_PATH = Path(__file__).parent / "big_board.db"

# Default bright colors for family members
DEFAULT_COLORS = [
    "#FF6B6B",  # coral red
    "#4ECDC4",  # teal
    "#FFE66D",  # yellow
    "#95E1D3",  # mint
    "#F38181",  # salmon
    "#AA96DA",  # lavender
    "#6C5CE7",  # purple
    "#00B894",  # green
]

DEFAULT_CATEGORIES = ["Meeting", "School", "Reminder", "Task", "Activity"]


class Item(BaseModel):
    id: Optional[int] = None
    title: str
    family_member: str
    date: str  # YYYY-MM-DD
    time: Optional[str] = None  # HH:MM
    category: str
    recurrence: Optional[str] = None  # null, "daily", "weekdays", "weekly", "monthly"
    recurrence_day: Optional[int] = None  # for weekly (0-6) or monthly (1-31)
    handled: bool = False
    handled_date: Optional[str] = None  # track when it was handled for midnight reset
    stay_until_done: bool = False  # if True, stays on dashboard until marked done
    created_at: Optional[str] = None


class FamilyMember(BaseModel):
    id: Optional[int] = None
    name: str
    color: str


class Category(BaseModel):
    id: Optional[int] = None
    name: str


async def init_db():
    """Initialize the database with required tables."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                family_member TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT,
                category TEXT NOT NULL,
                recurrence TEXT,
                recurrence_day INTEGER,
                handled INTEGER DEFAULT 0,
                handled_date TEXT,
                stay_until_done INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Migration: add stay_until_done column if it doesn't exist
        try:
            await db.execute("ALTER TABLE items ADD COLUMN stay_until_done INTEGER DEFAULT 0")
        except Exception:
            pass  # Column already exists

        await db.execute("""
            CREATE TABLE IF NOT EXISTS family_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                color TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)

        # Insert default categories if empty
        cursor = await db.execute("SELECT COUNT(*) FROM categories")
        count = (await cursor.fetchone())[0]
        if count == 0:
            for cat in DEFAULT_CATEGORIES:
                await db.execute("INSERT INTO categories (name) VALUES (?)", (cat,))

        await db.commit()


async def get_or_create_family_member(name: str) -> FamilyMember:
    """Get a family member by name, creating with a color if they don't exist."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM family_members WHERE name = ?", (name,)
        )
        row = await cursor.fetchone()

        if row:
            return FamilyMember(id=row["id"], name=row["name"], color=row["color"])

        # Assign next available color
        cursor = await db.execute("SELECT COUNT(*) FROM family_members")
        count = (await cursor.fetchone())[0]
        color = DEFAULT_COLORS[count % len(DEFAULT_COLORS)]

        cursor = await db.execute(
            "INSERT INTO family_members (name, color) VALUES (?, ?)",
            (name, color)
        )
        await db.commit()

        return FamilyMember(id=cursor.lastrowid, name=name, color=color)


async def get_family_members() -> list[FamilyMember]:
    """Get all family members."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM family_members ORDER BY name")
        rows = await cursor.fetchall()
        return [FamilyMember(id=r["id"], name=r["name"], color=r["color"]) for r in rows]


async def update_family_member_color(name: str, color: str) -> FamilyMember:
    """Update a family member's color."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE family_members SET color = ? WHERE name = ?",
            (color, name)
        )
        await db.commit()
        return await get_or_create_family_member(name)


async def get_categories() -> list[Category]:
    """Get all categories."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM categories ORDER BY name")
        rows = await cursor.fetchall()
        return [Category(id=r["id"], name=r["name"]) for r in rows]


async def add_category(name: str) -> Category:
    """Add a new category."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "INSERT OR IGNORE INTO categories (name) VALUES (?)", (name,)
        )
        await db.commit()

        cursor = await db.execute("SELECT * FROM categories WHERE name = ?", (name,))
        row = await cursor.fetchone()
        return Category(id=row[0], name=row[1])


async def delete_category(name: str) -> bool:
    """Delete a category."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("DELETE FROM categories WHERE name = ?", (name,))
        await db.commit()
        return cursor.rowcount > 0


def _row_to_item(row) -> Item:
    return Item(
        id=row["id"],
        title=row["title"],
        family_member=row["family_member"],
        date=row["date"],
        time=row["time"],
        category=row["category"],
        recurrence=row["recurrence"],
        recurrence_day=row["recurrence_day"],
        handled=bool(row["handled"]),
        handled_date=row["handled_date"],
        stay_until_done=bool(row["stay_until_done"]) if row["stay_until_done"] is not None else False,
        created_at=row["created_at"],
    )


def _matches_recurrence(item_date: str, item_recurrence: str, item_recurrence_day: Optional[int], target_date: date) -> bool:
    """Check if a recurring item matches the target date."""
    if not item_recurrence:
        return False

    item_date_obj = datetime.strptime(item_date, "%Y-%m-%d").date()

    # Don't show before the original date
    if target_date < item_date_obj:
        return False

    if item_recurrence == "daily":
        return True
    elif item_recurrence == "weekdays":
        return target_date.weekday() < 5  # Mon-Fri
    elif item_recurrence == "weekly":
        if item_recurrence_day is not None:
            return target_date.weekday() == item_recurrence_day
        return target_date.weekday() == item_date_obj.weekday()
    elif item_recurrence == "monthly":
        if item_recurrence_day is not None:
            return target_date.day == item_recurrence_day
        return target_date.day == item_date_obj.day

    return False


async def add_item(item: Item) -> Item:
    """Add a new item."""
    # Ensure family member exists
    await get_or_create_family_member(item.family_member)

    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO items (title, family_member, date, time, category, recurrence, recurrence_day, stay_until_done)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (item.title, item.family_member, item.date, item.time, item.category,
             item.recurrence, item.recurrence_day, 1 if item.stay_until_done else 0)
        )
        await db.commit()
        item.id = cursor.lastrowid
        return item


async def get_items_for_date(target_date: date) -> list[Item]:
    """Get all items for a specific date, including recurring items and stay_until_done items."""
    target_str = target_date.strftime("%Y-%m-%d")

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Get exact date matches (excluding stay_until_done which we handle separately)
        cursor = await db.execute(
            "SELECT * FROM items WHERE date = ? AND (stay_until_done = 0 OR stay_until_done IS NULL) ORDER BY time, title",
            (target_str,)
        )
        exact_rows = await cursor.fetchall()

        # Get recurring items (excluding stay_until_done)
        cursor = await db.execute(
            "SELECT * FROM items WHERE recurrence IS NOT NULL AND (stay_until_done = 0 OR stay_until_done IS NULL)"
        )
        recurring_rows = await cursor.fetchall()

        # Get all unhandled stay_until_done items (regardless of date)
        cursor = await db.execute(
            "SELECT * FROM items WHERE stay_until_done = 1 AND handled = 0"
        )
        stay_until_done_rows = await cursor.fetchall()

        items = []

        for row in exact_rows:
            item = _row_to_item(row)
            # Reset handled if it was handled on a different day than the target date
            if item.handled and item.handled_date != target_str:
                item.handled = False
            items.append(item)

        for row in recurring_rows:
            if row["date"] == target_str:
                continue  # Already included above

            if _matches_recurrence(row["date"], row["recurrence"], row["recurrence_day"], target_date):
                item = _row_to_item(row)
                # For recurring items, check if handled on the target date
                if item.handled and item.handled_date != target_str:
                    item.handled = False
                items.append(item)

        # Add stay_until_done items (they persist until handled)
        for row in stay_until_done_rows:
            item = _row_to_item(row)
            items.append(item)

        # Sort by time, then title
        items.sort(key=lambda x: (x.time or "99:99", x.title))
        return items


async def get_all_items() -> list[Item]:
    """Get all items."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM items ORDER BY date, time, title")
        rows = await cursor.fetchall()
        return [_row_to_item(r) for r in rows]


async def update_item(item_id: int, updates: dict) -> Optional[Item]:
    """Update an existing item."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Build update query
        set_clauses = []
        values = []
        for key, value in updates.items():
            if key in ["title", "family_member", "date", "time", "category",
                       "recurrence", "recurrence_day", "handled", "handled_date", "stay_until_done"]:
                set_clauses.append(f"{key} = ?")
                values.append(value)

        if not set_clauses:
            return None

        values.append(item_id)
        await db.execute(
            f"UPDATE items SET {', '.join(set_clauses)} WHERE id = ?",
            values
        )
        await db.commit()

        cursor = await db.execute("SELECT * FROM items WHERE id = ?", (item_id,))
        row = await cursor.fetchone()
        return _row_to_item(row) if row else None


async def mark_item_handled(item_id: int, handled: bool = True) -> Optional[Item]:
    """Mark an item as handled/unhandled."""
    today_str = date.today().strftime("%Y-%m-%d")
    return await update_item(item_id, {
        "handled": 1 if handled else 0,
        "handled_date": today_str if handled else None
    })


async def delete_item(item_id: int) -> bool:
    """Delete an item."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("DELETE FROM items WHERE id = ?", (item_id,))
        await db.commit()
        return cursor.rowcount > 0
