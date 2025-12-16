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

Add to your Claude Desktop or Claude Code config:

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

For remote backend, use `mcp_remote.py --url http://host:8000` instead.

## Features

- Real-time updates via WebSocket
- Shows today's items before 7 PM, tomorrow's items after
- Click items to mark as handled (resets at midnight)
- Color-coded family members
- Recurring items (daily, weekly, monthly)
