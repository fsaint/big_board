#!/usr/bin/env python3
"""
MCP Server for Big Board - Family Dashboard

This server exposes tools for AI agents to manage family dashboard items.
Configure this in your AI agent's MCP settings to enable adding/managing
items via natural language.
"""

import asyncio
import os
from datetime import date, datetime
from typing import Optional

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

import database as db

server = Server("big-board")

# Backend API URL - write operations go through here to trigger WebSocket broadcasts
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools for managing the family dashboard."""
    return [
        Tool(
            name="add_item",
            description="""Add a new item to the family dashboard.

Use this to add meetings, reminders, school events, tasks, or activities.
Items will appear on the dashboard for the specified date.

Recurrence options:
- null: one-time item
- "daily": every day
- "weekdays": Monday through Friday
- "weekly": same day each week (use recurrence_day to specify which day)
- "monthly": same date each month (use recurrence_day to specify which day)

For weekly recurrence on a specific day, set recurrence="weekly" and recurrence_day to:
0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday, 5=Saturday, 6=Sunday

Example: "Every Monday" = recurrence="weekly", recurrence_day=0

Stay Until Done:
Set stay_until_done=true for items that should remain on the dashboard until
marked as done, regardless of date. After 24 hours these items will blink as alerts.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Brief description of the item (e.g., 'Math homework due', 'Team standup')"
                    },
                    "family_member": {
                        "type": "string",
                        "description": "Who this is for (e.g., 'Dad', 'Emma', 'Everyone')"
                    },
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format"
                    },
                    "time": {
                        "type": "string",
                        "description": "Optional time in HH:MM format (24-hour)"
                    },
                    "category": {
                        "type": "string",
                        "description": "Category: Meeting, School, Reminder, Task, or Activity"
                    },
                    "recurrence": {
                        "type": "string",
                        "enum": ["daily", "weekdays", "weekly", "monthly"],
                        "description": "Optional recurrence pattern"
                    },
                    "recurrence_day": {
                        "type": "integer",
                        "description": "For weekly: day of week (0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun). For monthly: day of month (1-31)."
                    },
                    "stay_until_done": {
                        "type": "boolean",
                        "description": "If true, item stays on dashboard until marked done (ignores date). Blinks after 24 hours."
                    }
                },
                "required": ["title", "family_member", "date", "category"]
            }
        ),
        Tool(
            name="list_items",
            description="List items on the family dashboard for a specific date or all items.",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Optional date in YYYY-MM-DD format. If not provided, lists all items."
                    }
                }
            }
        ),
        Tool(
            name="remove_item",
            description="Remove an item from the dashboard by its ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "integer",
                        "description": "The ID of the item to remove"
                    }
                },
                "required": ["item_id"]
            }
        ),
        Tool(
            name="update_item",
            description="Update an existing item on the dashboard.",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "integer",
                        "description": "The ID of the item to update"
                    },
                    "title": {"type": "string"},
                    "family_member": {"type": "string"},
                    "date": {"type": "string"},
                    "time": {"type": "string"},
                    "category": {"type": "string"},
                    "recurrence": {"type": "string"},
                    "recurrence_day": {"type": "integer", "description": "For weekly: 0-6 (Mon-Sun). For monthly: 1-31."},
                    "stay_until_done": {"type": "boolean", "description": "If true, item stays until marked done."}
                },
                "required": ["item_id"]
            }
        ),
        Tool(
            name="list_family_members",
            description="List all family members and their assigned colors.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="list_categories",
            description="List all available categories.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="add_category",
            description="Add a new category to the dashboard.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the new category"
                    }
                },
                "required": ["name"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    await db.init_db()

    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=10.0) as client:
        if name == "add_item":
            # Use REST API to trigger WebSocket broadcast
            payload = {
                "title": arguments["title"],
                "family_member": arguments["family_member"],
                "date": arguments["date"],
                "time": arguments.get("time"),
                "category": arguments["category"],
                "recurrence": arguments.get("recurrence"),
                "recurrence_day": arguments.get("recurrence_day"),
                "stay_until_done": arguments.get("stay_until_done", False),
            }
            resp = await client.post("/api/items", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                item = data.get("item", {})
                return [TextContent(
                    type="text",
                    text=f"Added item #{item.get('id')}: '{item.get('title')}' for {item.get('family_member')} on {item.get('date')}"
                )]
            return [TextContent(type="text", text=f"Failed to add item: {resp.text}")]

        elif name == "list_items":
            # Read operations can use direct DB access
            date_str = arguments.get("date")
            if date_str:
                target = datetime.strptime(date_str, "%Y-%m-%d").date()
                items = await db.get_items_for_date(target)
                header = f"Items for {date_str}:"
            else:
                items = await db.get_all_items()
                header = "All items:"

            if not items:
                return [TextContent(type="text", text=f"{header}\n(none)")]

            lines = [header]
            for item in items:
                time_str = f" at {item.time}" if item.time else ""
                recur_str = f" ({item.recurrence})" if item.recurrence else ""
                handled_str = " [HANDLED]" if item.handled else ""
                lines.append(
                    f"  #{item.id}: [{item.category}] {item.family_member} - {item.title}"
                    f"{time_str}{recur_str}{handled_str}"
                )
            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "remove_item":
            # Use REST API to trigger WebSocket broadcast
            item_id = arguments["item_id"]
            resp = await client.delete(f"/api/items/{item_id}")
            if resp.status_code == 200:
                return [TextContent(type="text", text=f"Removed item #{item_id}")]
            return [TextContent(type="text", text=f"Item #{item_id} not found")]

        elif name == "update_item":
            # Use REST API to trigger WebSocket broadcast
            item_id = arguments["item_id"]
            updates = {k: v for k, v in arguments.items() if k != "item_id" and v is not None}
            resp = await client.put(f"/api/items/{item_id}", json=updates)
            if resp.status_code == 200:
                data = resp.json()
                item = data.get("item", {})
                return [TextContent(type="text", text=f"Updated item #{item_id}: {item.get('title')}")]
            return [TextContent(type="text", text=f"Item #{item_id} not found")]

        elif name == "list_family_members":
            members = await db.get_family_members()
            if not members:
                return [TextContent(type="text", text="No family members yet (they are created when items are added)")]
            lines = ["Family members:"]
            for m in members:
                lines.append(f"  {m.name}: {m.color}")
            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "list_categories":
            categories = await db.get_categories()
            return [TextContent(type="text", text="Categories: " + ", ".join(c.name for c in categories))]

        elif name == "add_category":
            # Use REST API to trigger WebSocket broadcast
            resp = await client.post(f"/api/categories?name={arguments['name']}")
            if resp.status_code == 200:
                return [TextContent(type="text", text=f"Added category: {arguments['name']}")]
            return [TextContent(type="text", text=f"Failed to add category: {resp.text}")]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    """Run the MCP server."""
    await db.init_db()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
