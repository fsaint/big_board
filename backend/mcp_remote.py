#!/usr/bin/env python3
"""
Remote MCP Client for Big Board

This MCP server connects to a remote Big Board backend via HTTP.
Use this when the backend is running on a different machine.

Usage:
  python mcp_remote.py --url http://remote-host:8000

Configure in your MCP client:
{
  "mcpServers": {
    "big-board": {
      "command": "python",
      "args": ["/path/to/mcp_remote.py", "--url", "http://remote-host:8000"]
    }
  }
}
"""

import argparse
import asyncio
import httpx
from datetime import datetime

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Parse command line args before anything else
parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://localhost:8000", help="Backend URL")
args, _ = parser.parse_known_args()

BACKEND_URL = args.url.rstrip("/")

server = Server("big-board-remote")


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
- "weekly": same day each week
- "monthly": same date each month""",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Brief description of the item"
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
                        "description": "Optional date in YYYY-MM-DD format"
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
                    "recurrence": {"type": "string"}
                },
                "required": ["item_id"]
            }
        ),
        Tool(
            name="list_family_members",
            description="List all family members and their assigned colors.",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="list_categories",
            description="List all available categories.",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="add_category",
            description="Add a new category to the dashboard.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name of the new category"}
                },
                "required": ["name"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls by forwarding to the REST API."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if name == "add_item":
                resp = await client.post(f"{BACKEND_URL}/api/items", json=arguments)
                data = resp.json()
                if "item" in data:
                    item = data["item"]
                    return [TextContent(
                        type="text",
                        text=f"Added item #{item['id']}: '{item['title']}' for {item['family_member']} on {item['date']}"
                    )]
                return [TextContent(type="text", text=f"Error: {data}")]

            elif name == "list_items":
                params = {}
                if arguments.get("date"):
                    params["date_from"] = arguments["date"]
                resp = await client.get(f"{BACKEND_URL}/api/items", params=params)
                data = resp.json()
                items = data.get("items", [])

                if not items:
                    return [TextContent(type="text", text="No items found")]

                lines = ["Items:"]
                for item in items:
                    time_str = f" at {item['time']}" if item.get('time') else ""
                    recur_str = f" ({item['recurrence']})" if item.get('recurrence') else ""
                    handled_str = " [HANDLED]" if item.get('handled') else ""
                    lines.append(
                        f"  #{item['id']}: [{item['category']}] {item['family_member']} - "
                        f"{item['title']}{time_str}{recur_str}{handled_str} (date: {item['date']})"
                    )
                return [TextContent(type="text", text="\n".join(lines))]

            elif name == "remove_item":
                item_id = arguments["item_id"]
                resp = await client.delete(f"{BACKEND_URL}/api/items/{item_id}")
                if resp.status_code == 200:
                    return [TextContent(type="text", text=f"Removed item #{item_id}")]
                return [TextContent(type="text", text=f"Item #{item_id} not found")]

            elif name == "update_item":
                item_id = arguments.pop("item_id")
                resp = await client.put(f"{BACKEND_URL}/api/items/{item_id}", json=arguments)
                data = resp.json()
                if "item" in data:
                    return [TextContent(type="text", text=f"Updated item #{item_id}")]
                return [TextContent(type="text", text=f"Item #{item_id} not found")]

            elif name == "list_family_members":
                resp = await client.get(f"{BACKEND_URL}/api/family-members")
                data = resp.json()
                members = data.get("family_members", [])
                if not members:
                    return [TextContent(type="text", text="No family members yet")]
                lines = ["Family members:"]
                for m in members:
                    lines.append(f"  {m['name']}: {m['color']}")
                return [TextContent(type="text", text="\n".join(lines))]

            elif name == "list_categories":
                resp = await client.get(f"{BACKEND_URL}/api/categories")
                data = resp.json()
                cats = data.get("categories", [])
                return [TextContent(type="text", text="Categories: " + ", ".join(cats))]

            elif name == "add_category":
                resp = await client.post(f"{BACKEND_URL}/api/categories", params={"name": arguments["name"]})
                return [TextContent(type="text", text=f"Added category: {arguments['name']}")]

            return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except httpx.ConnectError:
            return [TextContent(type="text", text=f"Error: Cannot connect to backend at {BACKEND_URL}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
