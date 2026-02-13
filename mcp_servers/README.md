# MCP Servers for AI Employee System

Two MCP servers that give Claude Desktop/Code direct access to the AI Employee system.

## Servers

### 1. Email MCP (`email_mcp`)
Tools for email management via Gmail API:
- `send_email` - Send emails (respects DRY_RUN mode)
- `draft_email` - Create email drafts in vault
- `list_recent_emails` - List processed email tasks
- `search_emails` - Search email tasks by content

### 2. Vault Manager MCP (`browser_mcp`)
Tools for vault and task management:
- `list_tasks` - List tasks by folder/status
- `get_task` - Read a specific task
- `approve_task` - Move task to Approved
- `reject_task` - Reject with reason
- `create_task` - Create new tasks
- `get_dashboard` - Read system dashboard
- `get_system_status` - Full system status
- `force_briefing` - Generate CEO briefing
- `list_multistep_tasks` - View Ralph Loop tasks

## Setup

### For Claude Desktop

Add to `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ai-employee-email": {
      "command": "python",
      "args": ["-m", "mcp_servers.email_mcp.server"],
      "cwd": "D:\\Hackathon-0"
    },
    "ai-employee-vault": {
      "command": "python",
      "args": ["-m", "mcp_servers.browser_mcp.server"],
      "cwd": "D:\\Hackathon-0"
    }
  }
}
```

### For Claude Code

Add to `.claude/settings.json`:

```json
{
  "mcpServers": {
    "ai-employee-email": {
      "command": "python",
      "args": ["-m", "mcp_servers.email_mcp.server"]
    },
    "ai-employee-vault": {
      "command": "python",
      "args": ["-m", "mcp_servers.browser_mcp.server"]
    }
  }
}
```

## Testing

```bash
# Test Email MCP server starts
python -m mcp_servers.email_mcp.server

# Test Vault MCP server starts
python -m mcp_servers.browser_mcp.server
```

## Requirements

- Python 3.11+
- `mcp>=1.0.0` (MCP Python SDK)
- Gmail credentials for email server (optional)
