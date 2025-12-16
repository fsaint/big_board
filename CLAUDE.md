# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Big Board is a family dashboard for displaying time-sensitive information on an always-on monitor. Content is managed via MCP (Model Context Protocol) server that AI agents can interact with.

## Architecture

```
frontend/ (SvelteKit)  <--WebSocket-->  backend/ (FastAPI + MCP Server)
                                              |
                                           SQLite
```

- **Frontend**: SvelteKit app with real-time WebSocket updates
- **Backend**: FastAPI server with WebSocket support + MCP server for AI agent integration
- **Database**: SQLite (file: `backend/big_board.db`)

## Development Commands

### Backend
```bash
cd backend
pip install -r requirements.txt
python main.py                    # Run FastAPI server on :8000
python mcp_server.py              # Run MCP server (stdio mode for AI agents)
```

### Frontend
```bash
cd frontend
npm install
npm run dev                       # Dev server on :5173 (proxies to backend)
npm run build                     # Production build to build/
```

### Run Both (Development)
Terminal 1: `cd backend && python main.py`
Terminal 2: `cd frontend && npm run dev`

## MCP Server Configuration

Add to your AI agent's MCP config:
```json
{
  "mcpServers": {
    "big-board": {
      "command": "python",
      "args": ["/path/to/big_board/backend/mcp_server.py"]
    }
  }
}
```

## Key Files

- `backend/database.py` - SQLite operations, item/family member models
- `backend/main.py` - FastAPI app, WebSocket handler, REST API
- `backend/mcp_server.py` - MCP server with tools for AI agents
- `frontend/src/lib/stores/items.ts` - WebSocket client, Svelte stores
- `frontend/src/lib/components/ItemCard.svelte` - Item display component

## Display Behavior

- Before 7 PM: Shows today's items
- After 7 PM: Shows tomorrow's items
- Handled items reset at midnight
- Cards scale to fit screen (no pagination)
