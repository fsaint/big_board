import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, date, timedelta
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import database as db


class ConnectionManager:
    """Manages WebSocket connections and broadcasts updates."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.active_connections.discard(conn)


manager = ConnectionManager()


def get_display_date() -> date:
    """Get the date to display based on current time (today before 7PM, tomorrow after)."""
    now = datetime.now()
    if now.hour >= 19:  # 7 PM or later
        return (now + timedelta(days=1)).date()
    return now.date()


async def broadcast_items():
    """Broadcast current items to all clients."""
    display_date = get_display_date()
    items = await db.get_items_for_date(display_date)
    family_members = await db.get_family_members()
    categories = await db.get_categories()

    await manager.broadcast({
        "type": "update",
        "display_date": display_date.isoformat(),
        "is_tomorrow": display_date != date.today(),
        "items": [item.model_dump() for item in items],
        "family_members": {fm.name: fm.color for fm in family_members},
        "categories": [c.name for c in categories],
    })


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await db.init_db()
    yield


app = FastAPI(title="Big Board", lifespan=lifespan)

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send initial data
        display_date = get_display_date()
        items = await db.get_items_for_date(display_date)
        family_members = await db.get_family_members()
        categories = await db.get_categories()

        await websocket.send_json({
            "type": "init",
            "display_date": display_date.isoformat(),
            "is_tomorrow": display_date != date.today(),
            "items": [item.model_dump() for item in items],
            "family_members": {fm.name: fm.color for fm in family_members},
            "categories": [c.name for c in categories],
        })

        # Listen for messages from client
        while True:
            data = await websocket.receive_json()
            await handle_client_message(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def handle_client_message(data: dict):
    """Handle messages from WebSocket clients."""
    msg_type = data.get("type")

    if msg_type == "mark_handled":
        item_id = data.get("item_id")
        handled = data.get("handled", True)
        await db.mark_item_handled(item_id, handled)
        await broadcast_items()

    elif msg_type == "refresh":
        await broadcast_items()


# REST API endpoints (for MCP server to call)

class ItemCreate(BaseModel):
    title: str
    family_member: str
    date: str
    time: str | None = None
    category: str
    recurrence: str | None = None
    recurrence_day: int | None = None


class ItemUpdate(BaseModel):
    title: str | None = None
    family_member: str | None = None
    date: str | None = None
    time: str | None = None
    category: str | None = None
    recurrence: str | None = None
    recurrence_day: int | None = None


@app.post("/api/items")
async def create_item(item: ItemCreate):
    new_item = await db.add_item(db.Item(**item.model_dump()))
    await broadcast_items()
    return {"status": "ok", "item": new_item.model_dump()}


@app.get("/api/items")
async def list_items(date_from: str | None = None, date_to: str | None = None):
    if date_from:
        target = datetime.strptime(date_from, "%Y-%m-%d").date()
        items = await db.get_items_for_date(target)
    else:
        items = await db.get_all_items()
    return {"items": [item.model_dump() for item in items]}


@app.get("/api/items/{item_id}")
async def get_item(item_id: int):
    items = await db.get_all_items()
    for item in items:
        if item.id == item_id:
            return {"item": item.model_dump()}
    return {"error": "Item not found"}, 404


@app.put("/api/items/{item_id}")
async def update_item(item_id: int, updates: ItemUpdate):
    update_dict = {k: v for k, v in updates.model_dump().items() if v is not None}
    item = await db.update_item(item_id, update_dict)
    if item:
        await broadcast_items()
        return {"status": "ok", "item": item.model_dump()}
    return {"error": "Item not found"}, 404


@app.delete("/api/items/{item_id}")
async def delete_item(item_id: int):
    success = await db.delete_item(item_id)
    if success:
        await broadcast_items()
        return {"status": "ok"}
    return {"error": "Item not found"}, 404


@app.post("/api/items/{item_id}/handle")
async def mark_handled(item_id: int, handled: bool = True):
    item = await db.mark_item_handled(item_id, handled)
    if item:
        await broadcast_items()
        return {"status": "ok", "item": item.model_dump()}
    return {"error": "Item not found"}, 404


@app.get("/api/family-members")
async def list_family_members():
    members = await db.get_family_members()
    return {"family_members": [m.model_dump() for m in members]}


@app.put("/api/family-members/{name}/color")
async def update_member_color(name: str, color: str):
    member = await db.update_family_member_color(name, color)
    await broadcast_items()
    return {"status": "ok", "family_member": member.model_dump()}


@app.get("/api/categories")
async def list_categories():
    categories = await db.get_categories()
    return {"categories": [c.name for c in categories]}


@app.post("/api/categories")
async def create_category(name: str):
    category = await db.add_category(name)
    await broadcast_items()
    return {"status": "ok", "category": category.model_dump()}


@app.delete("/api/categories/{name}")
async def remove_category(name: str):
    success = await db.delete_category(name)
    if success:
        await broadcast_items()
        return {"status": "ok"}
    return {"error": "Category not found"}, 404


if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("BACKEND_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
