import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, date, timedelta
from typing import Set, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import database as db


# MCP Protocol Constants
MCP_PROTOCOL_VERSION = "2025-03-26"
MCP_SERVER_NAME = "big-board"
MCP_SERVER_VERSION = "1.0.0"


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
    stay_until_done: bool = False


class ItemUpdate(BaseModel):
    title: str | None = None
    family_member: str | None = None
    date: str | None = None
    time: str | None = None
    category: str | None = None
    recurrence: str | None = None
    recurrence_day: int | None = None
    stay_until_done: bool | None = None


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


# ============================================================================
# MCP (Model Context Protocol) HTTP Endpoint
# ============================================================================

MCP_TOOLS = [
    {
        "name": "add_item",
        "description": """Add a new item to the family dashboard.

Use this to add meetings, reminders, school events, tasks, or activities.
Items will appear on the dashboard for the specified date.

Recurrence options:
- null: one-time item
- "daily": every day
- "weekdays": Monday through Friday
- "weekly": same day each week
- "monthly": same date each month

Stay Until Done:
Set stay_until_done=true for items that should remain on the dashboard until
marked as done, regardless of date. After 24 hours these items will blink as alerts.""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Brief description of the item"},
                "family_member": {"type": "string", "description": "Who this is for (e.g., 'Dad', 'Emma', 'Everyone')"},
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                "time": {"type": "string", "description": "Optional time in HH:MM format (24-hour)"},
                "category": {"type": "string", "description": "Category: Meeting, School, Reminder, Task, or Activity"},
                "recurrence": {"type": "string", "enum": ["daily", "weekdays", "weekly", "monthly"], "description": "Optional recurrence pattern"},
                "stay_until_done": {"type": "boolean", "description": "If true, item stays on dashboard until marked done. Blinks after 24 hours."}
            },
            "required": ["title", "family_member", "date", "category"]
        }
    },
    {
        "name": "list_items",
        "description": "List items on the family dashboard for a specific date or all items.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Optional date in YYYY-MM-DD format"}
            }
        }
    },
    {
        "name": "remove_item",
        "description": "Remove an item from the dashboard by its ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "item_id": {"type": "integer", "description": "The ID of the item to remove"}
            },
            "required": ["item_id"]
        }
    },
    {
        "name": "update_item",
        "description": "Update an existing item on the dashboard.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "item_id": {"type": "integer", "description": "The ID of the item to update"},
                "title": {"type": "string"},
                "family_member": {"type": "string"},
                "date": {"type": "string"},
                "time": {"type": "string"},
                "category": {"type": "string"},
                "recurrence": {"type": "string"},
                "stay_until_done": {"type": "boolean", "description": "If true, item stays until marked done."}
            },
            "required": ["item_id"]
        }
    },
    {
        "name": "list_family_members",
        "description": "List all family members and their assigned colors.",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "list_categories",
        "description": "List all available categories.",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "add_category",
        "description": "Add a new category to the dashboard.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the new category"}
            },
            "required": ["name"]
        }
    }
]


async def handle_mcp_tool_call(name: str, arguments: dict) -> str:
    """Execute an MCP tool and return the result as text."""
    if name == "add_item":
        item = db.Item(
            title=arguments["title"],
            family_member=arguments["family_member"],
            date=arguments["date"],
            time=arguments.get("time"),
            category=arguments["category"],
            recurrence=arguments.get("recurrence"),
            stay_until_done=arguments.get("stay_until_done", False),
        )
        created = await db.add_item(item)
        await broadcast_items()
        stay_str = " [STAY UNTIL DONE]" if created.stay_until_done else ""
        return f"Added item #{created.id}: '{created.title}' for {created.family_member} on {created.date}{stay_str}"

    elif name == "list_items":
        date_str = arguments.get("date")
        if date_str:
            target = datetime.strptime(date_str, "%Y-%m-%d").date()
            items = await db.get_items_for_date(target)
            header = f"Items for {date_str}:"
        else:
            items = await db.get_all_items()
            header = "All items:"

        if not items:
            return f"{header}\n(none)"

        lines = [header]
        for item in items:
            time_str = f" at {item.time}" if item.time else ""
            recur_str = f" ({item.recurrence})" if item.recurrence else ""
            handled_str = " [HANDLED]" if item.handled else ""
            stay_str = " [STAY]" if item.stay_until_done else ""
            lines.append(
                f"  #{item.id}: [{item.category}] {item.family_member} - {item.title}"
                f"{time_str}{recur_str}{stay_str}{handled_str}"
            )
        return "\n".join(lines)

    elif name == "remove_item":
        item_id = arguments["item_id"]
        success = await db.delete_item(item_id)
        if success:
            await broadcast_items()
            return f"Removed item #{item_id}"
        return f"Item #{item_id} not found"

    elif name == "update_item":
        item_id = arguments["item_id"]
        updates = {k: v for k, v in arguments.items() if k != "item_id" and v is not None}
        item = await db.update_item(item_id, updates)
        if item:
            await broadcast_items()
            return f"Updated item #{item_id}: {item.title}"
        return f"Item #{item_id} not found"

    elif name == "list_family_members":
        members = await db.get_family_members()
        if not members:
            return "No family members yet (they are created when items are added)"
        lines = ["Family members:"]
        for m in members:
            lines.append(f"  {m.name}: {m.color}")
        return "\n".join(lines)

    elif name == "list_categories":
        categories = await db.get_categories()
        return "Categories: " + ", ".join(c.name for c in categories)

    elif name == "add_category":
        category = await db.add_category(arguments["name"])
        await broadcast_items()
        return f"Added category: {category.name}"

    return f"Unknown tool: {name}"


def jsonrpc_response(id: Any, result: Any) -> dict:
    """Create a JSON-RPC 2.0 response."""
    return {"jsonrpc": "2.0", "id": id, "result": result}


def jsonrpc_error(id: Any, code: int, message: str) -> dict:
    """Create a JSON-RPC 2.0 error response."""
    return {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """MCP Streamable HTTP endpoint."""
    try:
        body = await request.json()
    except Exception:
        return Response(
            content=json.dumps(jsonrpc_error(None, -32700, "Parse error")),
            media_type="application/json",
            status_code=400
        )

    method = body.get("method")
    params = body.get("params", {})
    req_id = body.get("id")

    # Handle different MCP methods
    if method == "initialize":
        result = {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "serverInfo": {
                "name": MCP_SERVER_NAME,
                "version": MCP_SERVER_VERSION
            },
            "capabilities": {
                "tools": {}
            }
        }
        response = jsonrpc_response(req_id, result)
        resp = Response(
            content=json.dumps(response),
            media_type="application/json"
        )
        resp.headers["Mcp-Session-Id"] = str(uuid.uuid4())
        return resp

    elif method == "notifications/initialized":
        # Client acknowledgment - no response needed
        return Response(status_code=202)

    elif method == "tools/list":
        result = {"tools": MCP_TOOLS}
        return Response(
            content=json.dumps(jsonrpc_response(req_id, result)),
            media_type="application/json"
        )

    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        try:
            text_result = await handle_mcp_tool_call(tool_name, arguments)
            result = {
                "content": [{"type": "text", "text": text_result}]
            }
            return Response(
                content=json.dumps(jsonrpc_response(req_id, result)),
                media_type="application/json"
            )
        except Exception as e:
            return Response(
                content=json.dumps(jsonrpc_error(req_id, -32603, str(e))),
                media_type="application/json",
                status_code=500
            )

    elif method == "ping":
        return Response(
            content=json.dumps(jsonrpc_response(req_id, {})),
            media_type="application/json"
        )

    else:
        return Response(
            content=json.dumps(jsonrpc_error(req_id, -32601, f"Method not found: {method}")),
            media_type="application/json",
            status_code=404
        )


if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("BACKEND_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
