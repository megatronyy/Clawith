# MCP Tool Installer

## When to Use This Skill
Use this skill when a user wants to add a new tool or integration (e.g., Gmail, Notion, Brave Search, GitHub, Slack, etc.) that isn't currently available but can be imported from the MCP registry.

---

## Step-by-Step Protocol

### Step 1 — Search first
```
discover_resources(query="<what the user wants>", max_results=5)
```
Show the results and let the user pick. Note the `ID` field (e.g. `github`).

### Step 2 — Check Smithery API Key
Before importing, check if you have a Smithery API Key configured. If not, guide the user:
> "要导入 MCP 工具，需要一个 Smithery API Key。请按以下步骤操作：
> 1. 注册/登录 https://smithery.ai
> 2. 前往 https://smithery.ai/account/api-keys 创建 Key
> 3. 将 Key 提供给我"

**Important:** Only the Smithery API Key is needed. Do NOT ask users for individual tool tokens (e.g. GitHub PAT, Brave API key). Smithery handles tool authentication via OAuth.

### Step 3 — Import the tool
Once you have the Smithery API Key (or it's already configured):
```
import_mcp_server(
  server_id="<qualified_name>",
  config={"smithery_api_key": "<the key they provided>"}
)
```
- On the **first import**, include `smithery_api_key` in config
- On **subsequent imports** (key already stored), just pass `server_id`:
```
import_mcp_server(server_id="<qualified_name>")
```

### Step 4 — Handle OAuth Authorization (if needed)
Some tools (like GitHub) require OAuth authorization. The import will return an authorization URL:
> 🔐 **OAuth 授权需要**: 请在浏览器中访问以下链接完成授权：
> https://api.smithery.ai/connect/...

Tell the user to visit the link and authorize. Once done, the tools are ready.

### Step 5 — Confirm and demonstrate
After successful import (and OAuth if applicable):
> "✅ GitHub 工具已安装。需要我帮你试一下吗？"

---

## Authentication Flow Summary

| Step | What Happens |
|------|-------------|
| 1. Smithery Key | User provides once, stored per-agent |
| 2. Import | System auto-creates Smithery namespace + connection |
| 3. OAuth | Some tools return auth URL — user visits to authorize |
| 4. Ready | Tools work via Smithery Connect, no individual tokens needed |

> **Key principle:** Only ONE key (Smithery API Key) is needed. Individual tool tokens (GitHub PAT, Brave API key, etc.) are NOT required — OAuth handles this automatically through Smithery Connect.

---

## Handling Config for Non-OAuth Tools
Some tools use API keys directly (passed as headers through Smithery Connect). For these, import with both the Smithery key and the tool-specific key:
```
import_mcp_server(
  server_id="anthropic/brave-search",
  config={"smithery_api_key": "<smithery key>", "BRAVE_API_KEY": "<brave key>"}
)
```
The tool description will indicate if a specific API key is required.

---

## What NOT to Do
- ❌ Don't ask users for GitHub PAT, Notion API key, etc. — Smithery OAuth handles these
- ❌ Don't tell users to go to the Tools settings page — do it here in chat
- ❌ Don't echo API keys back in your response
- ❌ Don't skip the search step — always verify the server exists before importing
- ❌ Don't import local-only tools (without remote support) — inform users instead
