# Big Board - Family Dashboard Specification

## Overview

A real-time family information dashboard designed for always-on display (e.g., a wall-mounted monitor). Shows time-sensitive information like meetings, school reminders, and family tasks. Content is managed via an MCP (Model Context Protocol) server that AI agents can interact with.

## Core Features

### Display Modes
- **Before 7 PM**: Shows today's items
- **After 7 PM**: Shows tomorrow's items (so the family can prepare for the next day)

### Item Types
Each item has:
- **Title**: Brief description
- **Family member(s)**: Who this is relevant to (e.g., "Dad", "Emma", "Everyone")
- **Time** (optional): When this is happening
- **Category**: Meeting, School, Reminder, Task, etc. (editable/configurable)
- **Date**: Which day this applies to
- **Recurrence** (optional): Support for recurring items (e.g., "Every Tuesday", "Weekdays")

### Interactions
- **Click to minimize**: Items can be dismissed/minimized when handled
- Minimized items move to a collapsed section or fade out
- **Handled state resets at midnight** - all items reappear fresh each day

### Family Member Colors
Each family member gets a bright, distinctive color for quick visual identification:
- Configurable per family member
- Default palette: `#FF6B6B` (coral red), `#4ECDC4` (teal), `#FFE66D` (yellow), `#95E1D3` (mint), `#F38181` (salmon), `#AA96DA` (lavender), `#6C5CE7` (purple), `#00B894` (green)
- Colors appear as card border/accent

## Architecture

```
┌─────────────────┐     WebSocket     ┌─────────────────┐
│   Svelte UI     │◄──────────────────►│  Python Backend │
│   (Browser)     │                    │   (FastAPI)     │
└─────────────────┘                    └────────┬────────┘
                                                │
                                       ┌────────▼────────┐
                                       │   MCP Server    │
                                       │   (Tool API)    │
                                       └────────┬────────┘
                                                │
                                       ┌────────▼────────┐
                                       │   AI Agents     │
                                       │ (Claude, etc.)  │
                                       └─────────────────┘
```

## MCP Server Tools

The MCP server exposes these tools for AI agents:

### `add_item`
```json
{
  "title": "Soccer practice",
  "family_member": "Emma",
  "date": "2024-12-15",
  "time": "16:00",
  "category": "activity"
}
```

### `list_items`
Returns all items for a given date range.

### `remove_item`
Remove an item by ID.

### `update_item`
Modify an existing item.

## Tech Stack

- **Frontend**: Svelte (SvelteKit for build tooling)
- **Backend**: Python with FastAPI
- **Real-time**: WebSockets
- **MCP**: Python MCP SDK
- **Data storage**: SQLite (simple, file-based, sufficient for family use)

## UI Layout

```
┌──────────────────────────────────────────────────────┐
│  📅 Today: Sunday, December 15         🕐 10:30 AM  │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ┌─────────────────────────────────────────────┐    │
│  │ 🏫 Emma - Math homework due                 │    │
│  │    School • Today                           │    │
│  └─────────────────────────────────────────────┘    │
│                                                      │
│  ┌─────────────────────────────────────────────┐    │
│  │ 📅 Dad - Team standup                       │    │
│  │    Meeting • 10:00 AM                       │    │
│  └─────────────────────────────────────────────┘    │
│                                                      │
│  ┌─────────────────────────────────────────────┐    │
│  │ 🏃 Everyone - Soccer practice pickup        │    │
│  │    Activity • 4:00 PM                       │    │
│  └─────────────────────────────────────────────┘    │
│                                                      │
│  ─────────── Handled (2) ───────────                │
│                                                      │
└──────────────────────────────────────────────────────┘
```

## File Structure

```
big_board/
├── backend/
│   ├── main.py           # FastAPI app + WebSocket
│   ├── mcp_server.py     # MCP server implementation
│   ├── database.py       # SQLite operations
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── routes/
│   │   │   └── +page.svelte
│   │   ├── lib/
│   │   │   ├── components/
│   │   │   │   ├── ItemCard.svelte
│   │   │   │   └── Header.svelte
│   │   │   └── stores/
│   │   │       └── items.ts
│   │   └── app.html
│   ├── package.json
│   └── svelte.config.js
├── CLAUDE.md
└── SPEC.md
```

## Design Principles

- **Everything visible**: No filtering, no pagination. All items for the day must fit on screen.
- **Raw and evident**: Nothing hidden. You shouldn't miss anything at a glance.
- **Cards scale**: If there are many items, cards shrink to fit. Few items = larger cards.

---

*Spec finalized. Ready for implementation.*
