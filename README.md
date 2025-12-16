# Big Board

A family dashboard for displaying time-sensitive information on an always-on monitor. Content is managed via MCP server that AI agents can interact with.

## Quick Start

### Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## MCP Configuration

### HTTP Transport (Recommended for Remote Access)

The backend includes a built-in MCP HTTP endpoint at `/mcp`. Configure your MCP client:

```json
{
  "mcpServers": {
    "big-board": {
      "type": "http",
      "url": "http://studio:8000/mcp"
    }
  }
}
```

Replace `studio` with your server's hostname or IP.

### Stdio Transport (Local Development)

For local development, you can use the stdio-based MCP server:

**Claude Code** (`~/.claude/settings.json`):
```json
{
  "mcpServers": {
    "big-board": {
      "command": "/path/to/big_board/backend/venv/bin/python",
      "args": ["/path/to/big_board/backend/mcp_server.py"]
    }
  }
}
```

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "big-board": {
      "command": "/path/to/big_board/backend/venv/bin/python",
      "args": ["/path/to/big_board/backend/mcp_server.py"]
    }
  }
}
```

**Note**: Use the full path to the venv Python interpreter to ensure dependencies are available.

## Development

### Clear Database
```bash
cd backend
source venv/bin/activate
python clear_db.py
```

This removes all items, family members, and categories, then re-initializes with default categories.

## Features

- Real-time updates via WebSocket
- Shows today's items before 7 PM, tomorrow's items after
- Click items to mark as handled (resets at midnight)
- Color-coded family members
- Recurring items (daily, weekly, monthly)
