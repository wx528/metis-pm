# Metis PM

> [中文文档](README_zh.md)

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=flat&logo=react&logoColor=black" alt="React">
  <img src="https://img.shields.io/badge/TypeScript-5-3178C6?style=flat&logo=typescript&logoColor=white" alt="TypeScript">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white" alt="FastAPI">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow?style=flat" alt="License"></a>
  <a href="https://github.com/wx528/metis-pm/actions/workflows/test.yml"><img src="https://github.com/wx528/metis-pm/actions/workflows/test.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/wx528/metis-pm/actions/workflows/build.yml"><img src="https://img.shields.io/badge/Docker-ready-2496ED?style=flat&logo=docker&logoColor=white" alt="Docker"></a>
  <br>
  <img src="https://img.shields.io/badge/AI-pm--copilot--engine-722ED1?style=flat&logo=openai&logoColor=white" alt="AI Engine">
  <img src="https://img.shields.io/badge/MCP-Streamable%20HTTP-0078D4?style=flat" alt="MCP">
</p>

A human-AI collaborative project management system — designed for **you + AI Coding Agents** to manage projects together.

## Philosophy

This system is not for teams. It's for **you and an AI Coding Agent**:
- Both you and the Agent can create issues, set plans, and mark priorities
- Say "not now" and the Agent defers the issue to a later milestone
- The Agent can auto-create issues and tag them as `ai_agent`
- Both of you can comment on the same issue, building a shared discussion history

## Quick Start

### 1. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set the required variables:

```env
SECRET_KEY=your-random-secret-key-here-min-32-chars
ADMIN_PASSWORD=your-secure-password
```

### 2. Start Backend

```bash
cd backend
uv sync
uv run python main.py
# API: http://localhost:8000
# Swagger: http://localhost:8000/docs
```

### 3. Start Frontend

```bash
cd frontend
npm install
npm run dev
# Frontend: http://localhost:5173
# API requests are proxied to localhost:8000
```

### Docker One-Command

```bash
docker compose up -d
# Frontend: http://localhost:8080
# API:     http://localhost:8000
```

## Architecture

```
┌──────────────┐     HTTP API      ┌───────────────┐     SQLite
│  React Frontend │ ◄──────────────► │ FastAPI Backend │ ◄────────►
│  (for humans)   │                   │                │  metis_pm.db
└──────────────┘                   └───────┬────────┘
                                          │
                                     MCP Server (Streamable HTTP)
                                     ┌──────┴───────┐
                                     │ Unified Entry │ :9000
                                     │ Auto-detect   │ ← X-PM-Password
                                     └──────┬───────┘
                                  ┌─────────┼─────────┐
                                  │         │         │
                             ┌────┴───┐ ┌───┴────┐ ┌─┴──────┐
                             │ Agent  │ │  Mate  │ │ Tester │
                             │ (trae) │ │ (cline)│ │  (qa)  │
                             └────────┘ └────────┘ └────────┘
```

### MCP Transport (Streamable HTTP Recommended)

| Mode | Endpoint | Notes |
|------|----------|-------|
| **Streamable HTTP** | `http://host:9000/mcp` | **Recommended** — LAN/remote, no local scripts |
| SSE | `http://host:9000/sse` | Legacy client compatibility |

IDE MCP configuration:

```json
{
  "mcpServers": {
    "pm-agent": {
      "url": "http://192.168.1.100:9000/mcp",
      "headers": { "X-PM-Password": "CHANGE-ME" }
    },
    "pm-mate": {
      "url": "http://192.168.1.100:9001/mcp",
      "headers": { "X-PM-Password": "CHANGE-ME" }
    }
  }
}
```

### Multi-Identity Authentication

Each Agent has a unique password. Activity logs track exactly who did what:

```env
AGENT_PASSWORDS=agent-a:CHANGE-ME:agent,mate:CHANGE-ME:mate
```

### AI Copilot (Optional)

Metis PM can be enhanced with an AI Copilot powered by [pm-copilot-engine](https://pypi.org/project/pm-copilot-engine/):

```env
PM_COPILOT_ENABLED=true
PM_API_BASE_URL=https://api.openai.com/v1
PM_API_KEY=sk-...
PM_MODEL=gpt-4o
```

When enabled, the Copilot can:
- Run autonomous project health scans
- Answer questions about project status
- Auto-create risk alerts
- Generate daily/weekly reports

When disabled (`PM_COPILOT_ENABLED=false`), the system runs as a complete standalone PM tool — no AI dependency.

## MCP Tools

Agents interact with the system via MCP protocol. Core tools:

| Tool | Description |
|------|-------------|
| `get_context` | **Recommended entry point** — project overview, alerts, pending plans, recent activity |
| `create_issue` | Create an Issue |
| `list_issues` | Query Issues (with filters) |
| `update_issue_status` | Update Issue status |
| `update_issue_priority` | Update Issue priority |
| `defer_issue` | Defer an Issue to a later milestone |
| `undefer_issue` | Restore a deferred Issue to open |
| `add_issue_comment` | Add a comment |
| `list_comments` | View Issue comments |
| `propose_plan` | Propose a Plan |
| `list_plans` | Query Plans |
| `update_plan_progress` | Update Plan progress |
| `check_notifications` | Check notifications |
| `mark_notification_read` | Mark notification as read |
| `list_milestones` | List milestones |
| `create_milestone` | Create a milestone |
| `list_servers` | List servers |
| `get_server_credentials` | Get server credentials (admin only) |
| `list_workflows` | List workflows |
| `create_workflow` | Create a workflow |
| `trigger_workflow` | Trigger a workflow |
| `list_workflow_runs` | List workflow runs |

## Data Models

### Issue

| Field | Description |
|-------|-------------|
| `title` | Title |
| `description` | Detailed description |
| `issue_type` | bug / feature / task / improvement / documentation |
| `status` | open / in_progress / review / **deferred** / closed / cancelled |
| `priority` | **P0** / **P1** / **P2** / **P3** |
| `source` | **user** / **ai_agent** / **collaborative** |
| `milestone_id` | Associated milestone |
| `deferred_to_milestone_id` | Deferred to which milestone |
| `deferred_reason` | Deferral reason |

### Milestone

| Field | Description |
|-------|-------------|
| `title` | Milestone name |
| `phase` | Phase identifier (e.g. `phase-1`, `MVP`) |
| `status` | open / closed |

### Plan (with Approval Flow)

| Field | Description |
|-------|-------------|
| `title` | Plan name |
| `status` | draft / **pending_approval** / active / completed / abandoned |
| `proposed_by` | Who proposed: user / ai_agent |
| `approved_by` | Who approved |
| `reject_reason` | Rejection reason |

```
Agent proposes → pending_approval → You approve → active → Agent updates progress
                      ↓
                You reject → abandoned (with reason)
```

### Server

| Field | Description |
|-------|-------------|
| `name` | Server name |
| `ip_address` | IP address |
| `username` | Username |
| `has_password` / `has_ssh_key` | Credential flags (actual values never exposed) |
| `status` | active / maintenance / offline / decommissioned |
| `environment` | production / staging / development |

### Risk Alert

| Field | Description |
|-------|-------------|
| `title` | Alert title |
| `level` | critical / high / medium / low |
| `source` | manual / copilot / system |
| `status` | open / acknowledged / resolved / dismissed |
| `suggested_action` | Suggested remediation |

## Frontend Pages

| Page | Features |
|------|----------|
| Dashboard | P0/P1 issues, pending approvals, server status, activity timeline |
| Issues | List (filter + sort + paginate), create, detail (with comments), defer |
| Graph View | Force-directed graph of project structure (like Obsidian) |
| Milestones | Phase cards, issue statistics |
| Plans | Plan list (with progress bars), approval actions, checklist detail |
| Servers | Server list, add, view credentials |
| Risk Alerts | Alert list, create, resolve, filter by level/status |

## API Reference

> All endpoints require JWT authentication (`Authorization: Bearer <token>`)

### Auth
```
POST /api/v1/auth/login
GET  /api/v1/auth/me
```

### Issues
```
GET    /api/v1/issues
POST   /api/v1/issues
GET    /api/v1/issues/{id}
PUT    /api/v1/issues/{id}
DELETE /api/v1/issues/{id}
POST   /api/v1/issues/{id}/defer
POST   /api/v1/issues/{id}/comments
```

### Milestones
```
GET    /api/v1/milestones
POST   /api/v1/milestones
GET    /api/v1/milestones/{id}
PUT    /api/v1/milestones/{id}
DELETE /api/v1/milestones/{id}
```

### Plans
```
GET    /api/v1/plans
POST   /api/v1/plans
GET    /api/v1/plans/{id}
PUT    /api/v1/plans/{id}
POST   /api/v1/plans/{id}/approve
POST   /api/v1/plans/{id}/reject
DELETE /api/v1/plans/{id}
GET    /api/v1/plans/{id}/items
POST   /api/v1/plans/{id}/items
PUT    /api/v1/plans/{id}/items/{item_id}
DELETE /api/v1/plans/{id}/items/{item_id}
```

### Risk Alerts
```
GET    /api/v1/risk-alerts
POST   /api/v1/risk-alerts
GET    /api/v1/risk-alerts/{id}
PUT    /api/v1/risk-alerts/{id}
POST   /api/v1/risk-alerts/{id}/resolve
DELETE /api/v1/risk-alerts/{id}
```

### Copilot
```
POST   /api/v1/copilot/chat
POST   /api/v1/copilot/scan
GET    /api/v1/copilot/status
```

## Security

| Measure | Description |
|---------|-------------|
| JWT Auth | All API endpoints require Bearer Token |
| Credential Isolation | Server passwords/SSH keys served via separate endpoint only |
| CORS Restriction | Configurable via `CORS_ORIGINS` env var |
| Secret Enforcement | `SECRET_KEY` and `ADMIN_PASSWORD` must be set in `.env` |
| MCP Multi-Identity | Each Agent authenticates via unique password (`X-PM-Password` header) |
| MCP Token Cache | JWT cached per password, auto-cleared on 401 |
| LIKE Escaping | Search endpoints escape `%`, `_`, `\` to prevent wildcard injection |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0 (async), SQLite, JWT |
| Frontend | React 19, TypeScript, Ant Design 6, Vite, React Router 7 |
| MCP | FastMCP, httpx |
| AI Engine | pm-copilot-engine (optional) |
| Deployment | Docker, Docker Compose, Nginx, Helm |

## License

MIT
