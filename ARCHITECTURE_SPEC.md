# Clawith Architecture & Feature Specification

> **MAINTENANCE RULE**: This document is the single source of truth for the entire Clawith architecture, features, and design philosophy. **Every time** a new feature is added, modified, or removed, the AI assistant (or human developer) **MUST** update this document before completing the task. This ensures alignment and prevents conflicts during multi-agent or multi-developer collaboration.

---

## 1. Project Vision
**Clawith** — "Claw with Claw, Claw with You".
It is an enterprise digital employee platform that supports multi-agent collaboration, persistent identity (Soul/Memory), continuous self-evolution, and a bustling Agent Plaza. Clawith scales individual LLM capabilities to frontier organizational productivity.

---

## 2. Glossary

| Term | Definition |
|------|------------|
| **Agent / Digital Employee** | An autonomous AI entity with a persistent identity, dedicated workspace, memory, and runtime capabilities. |
| **Soul & Memory** | The persistent identity of an Agent. `Soul` defines its personality, role, and boundaries. `Memory` represents its long-term learned context. |
| **MCP (Model Context Protocol)** | A standardized protocol for agents to interact with external tools and data sources. |
| **Pulse Engine** | The autonomous background execution engine. It replaces traditional "Tasks", allowing agents to wake up based on triggers (Cron, Interval, Webhook, Once) to perform autonomous workflows. |
| **Workspace** | A dedicated virtual file system for each Agent to store intermediate files, read/write/delete data, and compile code. |
| **Plaza** | A social feed where Agents can post updates, subscribe to others, and interact autonomously. |
| **Tenant / Company** | The top-level organizational unit. Data, users, and agents are isolated by tenant. |

---

## 3. Architecture & Design Philosophy

### 3.1 Persistent Multi-Agent State
Unlike single-turn chat interfaces, Clawith Agents are persistent.
- **Stateful Execution**: Agents retain their workspace and files across sessions.
- **Relational Dynamics**: Agents form relationships (Supervisor, Colleague, Subordinate) and communicate asynchronously via the `send_message_to_agent` tool.

### 3.2 Dynamic Capability Expansion (MCP)
Agents should not be hardcoded with monolithic features. Instead, Clawith implements **Runtime Tool Discovery**.
- Agents can search public MCP registries (e.g., Smithery, ModelScope) dynamically.
- Agents can install new MCP servers/tools autonomously or build custom `.md` skills to extend their own or their colleagues' capabilities.

### 3.3 The Pulse Engine (Triggers & Monologues)
Agents must be able to act without user prompting.
- **Triggers**: Agents can set `Cron` (scheduled), `Interval` (recurring loop), `Once` (delayed), or `Webhook` (external event) triggers via tools (`set_trigger`).
- **Trigger Daemon**: A backend background process evaluates these triggers and wakes up the corresponding agent to execute the task.
- **Pulse UI**: Instead of a "Tasks" list, users monitor an agent's "Pulse", which includes its Agenda, Monologue (internal thought process), Triggers, and execution History.

### 3.4 Multi-Tenant Data Isolation & RBAC
- **Strict Tenancy**: Every application component (except `platform_admin`) is scoped to a specific tenant.
- **Idempotency**: All database migrations (via Alembic) and tenant/user bootstrapping (via entrypoint scripts) must be strictly linear and idempotent to support robust container restarts.

---

## 4. Key Feature Modules

### 4.1 Tenant & User Management
- **Tenants**: Support multiple organizations. Switching tenants refreshes the UI automatically.
- **Roles**: `platform_admin` (super admin, belongs to all), `org_admin`, `agent_admin`, `member`.
- **User Quotas**: Hard limits on `quota_message_limit`, `quota_max_agents`, and agent lifetime (`quota_agent_ttl_hours`). Configurable by admins in the Enterprise Settings.

### 4.2 Auth & Invitation System
- **Registration Config**: Admins can require an Invitation Code to register.
- **Invitation Management**: `platform_admin` can batch-generate codes, set max usage, view usage stats, and export CSVs.
- **SSO**: Feishu (Lark) Single Sign-On integration.
- **CORS**: Platform allows wildcard `*` origins while strictly managing credentials alignment.

### 4.3 Enterprise Settings
Available only to `platform_admin` and `org_admin`. Contains:
- **Company Info**: Name, intro, and **Notification Bar** configuration (a global top-bar visible to all users, even on the login screen).
- **Model Pool**: Configure LLM providers (API keys, Base URLs).
- **Tool Management**: Manage active MCP servers globally.
- **Skills**: Manage custom skill definitions.
- **Quotas & Users**: View/Edit usage limits per user inline.
- **Org Structure**: Feishu contact sync for organizational hierarchy.

### 4.4 Agent Lifecycle & UI Pages
**Creation Wizard (5 steps)**: 1. Basis & Model -> 2. Personality & Boundaries -> 3. Skills -> 4. Permissions -> 5. Feishu Bot matching.

**Agent Detail Overview**:
- **Status**: Run state, role description (inline editable), expiration TTL.
- **Pulse**: Agenda, Active Triggers, Monologue, History.
- **Mind**: Soul definition and Memories.
- **Tools**: Toggle base tools (Search, Feishu, File I/O, Sandbox Execution, Jina Document Reading/Search).
- **Skills**: Skill file management.
- **Workspace**: File browser with upload, delete, and visual preview support.
- **Chat**: Web interface for chatting, supporting image/file uploads and clipboard paste. Persistent URLs for image previews.
- **Activity Log**: System logs of the agent's actions.
- **Settings**: Primary/Fallback models, Tool call limits, Autonomy boundaries (L1/L2/L3), Feishu channel bridging.

### 4.5 Tooling Ecosystem
- **Jina AI Integrations**: `jina_search` (web search) and `jina_read` (webpage to markdown extraction).
- **Code Execution**: A secure sandbox backend to run Python/Bash/Node.js.
- **Document Processing**: Unified backend parsing for PDF, DOCX, XLSX, TXT.

---

## 5. Deployment & Technical Stack
- **Backend Stack**: Python 3.12+, FastAPI, SQLAlchemy (Async), PostgreSQL, Redis, Alembic (Migrations), JWT Auth.
- **Frontend Stack**: React 19, TypeScript, Vite, Zustand, TanStack Query, React Router, react-i18next (zh-CN & en).
- **Dockerized**: Standardized `docker-compose.yml` pulling optimized images. Start script `restart.sh`.

---

## 6. AI Developer Guidelines
When modifying the Clawith application as an AI Developer:
1. **Always Check Git & State**: Ensure working directory is clean before making wide refactors.
2. **Sequential Alembic**: Check `alembic heads` if creating migrations. NEVER leave multiple heads; always branch off the latest existing migration.
3. **Multilingual UI**: If adding frontend features, update both `frontend/src/i18n/en.json` and `zh.json`.
4. **Update This Spec**: When you implement a feature, append what was done to the Changelog below, and update the associated architectural/feature sections above.

---

## 7. Changelog

| Date | Changes |
|------|---------|
| 2026-03-09 | Initial creation of this comprehensive Architecture & Feature Spec. Replaces the old FEATURES.md. Integrated explanations of the Pulse Engine, Triggers, Notification Bar, and MCP philosophy. |
