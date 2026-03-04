"""Seed builtin tools into the database on startup."""

from sqlalchemy import select
from app.database import async_session
from app.models.tool import Tool

# Builtin tool definitions — these map to the hardcoded AGENT_TOOLS
BUILTIN_TOOLS = [
    {
        "name": "list_files",
        "display_name": "List Files",
        "description": "List files and folders in a directory within the workspace. Can also list enterprise_info/ for shared company information.",
        "category": "file",
        "icon": "📁",
        "is_default": True,
        "parameters_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path to list, defaults to root (empty string)"}
            },
        },
        "config": {},
        "config_schema": {},
    },
    {
        "name": "read_file",
        "display_name": "Read File",
        "description": "Read file contents from the workspace. Can read tasks.json, soul.md, memory/memory.md, skills/, and enterprise_info/.",
        "category": "file",
        "icon": "📄",
        "is_default": True,
        "parameters_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path, e.g.: tasks.json, soul.md, memory/memory.md"}
            },
            "required": ["path"],
        },
        "config": {"max_file_size_kb": 500},
        "config_schema": {
            "fields": [
                {"key": "max_file_size_kb", "label": "Max file size (KB)", "type": "number", "default": 500},
            ]
        },
    },
    {
        "name": "write_file",
        "display_name": "Write File",
        "description": "Write or update a file in the workspace. Can update memory/memory.md, create documents in workspace/, create skills in skills/.",
        "category": "file",
        "icon": "✏️",
        "is_default": True,
        "parameters_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path, e.g.: memory/memory.md, workspace/report.md"},
                "content": {"type": "string", "description": "File content to write"},
            },
            "required": ["path", "content"],
        },
        "config": {},
        "config_schema": {},
    },
    {
        "name": "delete_file",
        "display_name": "Delete File",
        "description": "Delete a file from the workspace. Cannot delete soul.md or tasks.json.",
        "category": "file",
        "icon": "🗑️",
        "is_default": True,
        "parameters_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to delete"}
            },
            "required": ["path"],
        },
        "config": {},
        "config_schema": {},
    },
    {
        "name": "read_document",
        "display_name": "Read Document",
        "description": "Read office document contents (PDF, Word, Excel, PPT) and extract text.",
        "category": "file",
        "icon": "📑",
        "is_default": True,
        "parameters_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Document file path, e.g.: workspace/report.pdf"}
            },
            "required": ["path"],
        },
        "config": {},
        "config_schema": {},
    },
    {
        "name": "manage_tasks",
        "display_name": "Task Manager",
        "description": "Manage tasks (create, update status, delete). Changes sync to the database and task board.",
        "category": "task",
        "icon": "📋",
        "is_default": True,
        "parameters_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["create", "update_status", "delete"], "description": "Action type"},
                "title": {"type": "string", "description": "Task title"},
                "description": {"type": "string", "description": "Task description (optional)"},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"], "description": "Priority level"},
                "status": {"type": "string", "enum": ["pending", "doing", "done"], "description": "New status (for update_status)"},
            },
            "required": ["action", "title"],
        },
        "config": {},
        "config_schema": {},
    },
    {
        "name": "send_feishu_message",
        "display_name": "Feishu Message",
        "description": "Send a message to a human colleague via Feishu. Can only message people in your relationships.",
        "category": "communication",
        "icon": "💬",
        "is_default": True,
        "parameters_schema": {
            "type": "object",
            "properties": {
                "member_name": {"type": "string", "description": "Recipient name"},
                "message": {"type": "string", "description": "Message content"},
            },
            "required": ["member_name", "message"],
        },
        "config": {},
        "config_schema": {},
    },
    {
        "name": "send_message_to_agent",
        "display_name": "Agent Message",
        "description": "Send a message to a digital employee colleague and receive a reply. Suitable for questions, delegation, or collaboration.",
        "category": "communication",
        "icon": "🤖",
        "is_default": True,
        "parameters_schema": {
            "type": "object",
            "properties": {
                "agent_name": {"type": "string", "description": "Target agent name"},
                "message": {"type": "string", "description": "Message content"},
                "msg_type": {"type": "string", "enum": ["chat", "task_request", "info_share"], "description": "Message type"},
            },
            "required": ["agent_name", "message"],
        },
        "config": {},
        "config_schema": {},
    },
    {
        "name": "web_search",
        "display_name": "DuckDuckGo Search",
        "description": "Search the internet via DuckDuckGo. May be unavailable on some networks. Use Bing Search as an alternative.",
        "category": "search",
        "icon": "🦆",
        "is_default": True,
        "parameters_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keywords"},
                "max_results": {"type": "integer", "description": "Number of results to return"},
            },
            "required": ["query"],
        },
        "config": {
            "search_engine": "duckduckgo",
            "max_results": 5,
            "language": "en",
            "api_key": "",
        },
        "config_schema": {
            "fields": [
                {
                    "key": "search_engine",
                    "label": "Search Engine",
                    "type": "select",
                    "options": [
                        {"value": "duckduckgo", "label": "DuckDuckGo (free, no API key)"},
                        {"value": "tavily", "label": "Tavily (AI search, needs API key)"},
                        {"value": "google", "label": "Google Custom Search (needs API key)"},
                        {"value": "bing", "label": "Bing Search API (needs API key)"},
                    ],
                    "default": "duckduckgo",
                },
                {
                    "key": "api_key",
                    "label": "API Key",
                    "type": "password",
                    "default": "",
                    "placeholder": "Required for engines that need an API key",
                    "depends_on": {"search_engine": ["tavily", "google", "bing"]},
                },
                {
                    "key": "max_results",
                    "label": "Default results count",
                    "type": "number",
                    "default": 5,
                    "min": 1,
                    "max": 20,
                },
                {
                    "key": "language",
                    "label": "Search language",
                    "type": "select",
                    "options": [
                        {"value": "en", "label": "English"},
                        {"value": "zh-CN", "label": "中文"},
                        {"value": "ja", "label": "日本語"},
                    ],
                    "default": "en",
                },
            ]
        },
    },
    {
        "name": "bing_search",
        "display_name": "Bing Search",
        "description": "Search the internet via Bing. Works reliably in China and worldwide. No API key required.",
        "category": "search",
        "icon": "🔍",
        "is_default": True,
        "parameters_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keywords"},
                "max_results": {"type": "integer", "description": "Number of results to return (default 5, max 10)"},
            },
            "required": ["query"],
        },
        "config": {},
        "config_schema": {},
    },
    {
        "name": "plaza_get_new_posts",
        "display_name": "Plaza: Browse",
        "description": "Get recent posts from the Agent Plaza (shared social feed). Returns posts and comments since a given timestamp.",
        "category": "social",
        "icon": "🏛️",
        "is_default": True,
        "parameters_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max number of posts to return (default 10)", "default": 10},
            },
        },
        "config": {},
        "config_schema": {},
    },
    {
        "name": "plaza_create_post",
        "display_name": "Plaza: Post",
        "description": "Publish a new post to the Agent Plaza. Share work insights, tips, or interesting discoveries. Do NOT share private information.",
        "category": "social",
        "icon": "📝",
        "is_default": True,
        "parameters_schema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Post content (max 500 chars). Must be public-safe."},
            },
            "required": ["content"],
        },
        "config": {},
        "config_schema": {},
    },
    {
        "name": "plaza_add_comment",
        "display_name": "Plaza: Comment",
        "description": "Add a comment to an existing plaza post. Engage with colleagues' posts.",
        "category": "social",
        "icon": "💬",
        "is_default": True,
        "parameters_schema": {
            "type": "object",
            "properties": {
                "post_id": {"type": "string", "description": "The UUID of the post to comment on"},
                "content": {"type": "string", "description": "Comment content (max 300 chars)"},
            },
            "required": ["post_id", "content"],
        },
        "config": {},
        "config_schema": {},
    },
    {
        "name": "execute_code",
        "display_name": "Code Executor",
        "description": "Execute code (Python, Bash, Node.js) in a sandboxed environment within the agent's workspace. Useful for data processing, calculations, file transformations, and automation.",
        "category": "code",
        "icon": "💻",
        "is_default": True,
        "parameters_schema": {
            "type": "object",
            "properties": {
                "language": {"type": "string", "enum": ["python", "bash", "node"], "description": "Programming language"},
                "code": {"type": "string", "description": "Code to execute"},
                "timeout": {"type": "integer", "description": "Max execution time in seconds (default 30, max 60)"},
            },
            "required": ["language", "code"],
        },
        "config": {"default_timeout": 30, "max_timeout": 60},
        "config_schema": {
            "fields": [
                {"key": "default_timeout", "label": "Default Timeout (seconds)", "type": "number", "default": 30, "min": 5, "max": 120},
                {"key": "max_timeout", "label": "Max Timeout (seconds)", "type": "number", "default": 60, "min": 10, "max": 120},
            ]
        },
    },
    {
        "name": "discover_resources",
        "display_name": "Resource Discovery",
        "description": "Search public MCP registries (Smithery + ModelScope) for tools and capabilities that can extend your abilities. Use this when you encounter a task you cannot handle with your current tools.",
        "category": "discovery",
        "icon": "🔎",
        "is_default": True,
        "parameters_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Semantic description of the capability needed, e.g. 'send email', 'query SQL database', 'generate images'"},
                "max_results": {"type": "integer", "description": "Max results to return (default 5, max 10)"},
            },
            "required": ["query"],
        },
        "config": {"smithery_api_key": "", "modelscope_api_token": ""},
        "config_schema": {
            "fields": [
                {
                    "key": "smithery_api_key",
                    "label": "Smithery API Key",
                    "type": "password",
                    "default": "",
                    "placeholder": "Get your key at smithery.ai/account/api-keys",
                },
                {
                    "key": "modelscope_api_token",
                    "label": "ModelScope API Token",
                    "type": "password",
                    "default": "",
                    "placeholder": "Get your token at modelscope.cn → Home → Access Tokens",
                },
            ]
        },
    },
    {
        "name": "import_mcp_server",
        "display_name": "Import MCP Server",
        "description": "Import an MCP server from Smithery registry into the platform. The server's tools become available for use. Use discover_resources first to find the server ID.",
        "category": "discovery",
        "icon": "📥",
        "is_default": True,
        "parameters_schema": {
            "type": "object",
            "properties": {
                "server_id": {"type": "string", "description": "Smithery server ID, e.g. '@anthropic/brave-search' or '@anthropic/fetch'"},
                "config": {"type": "object", "description": "Optional server configuration (e.g. API keys required by the server)"},
            },
            "required": ["server_id"],
        },
        "config": {"smithery_api_key": "", "modelscope_api_token": ""},
        "config_schema": {
            "fields": [
                {
                    "key": "smithery_api_key",
                    "label": "Smithery API Key",
                    "type": "password",
                    "default": "",
                    "placeholder": "Get your key at smithery.ai/account/api-keys",
                },
                {
                    "key": "modelscope_api_token",
                    "label": "ModelScope API Token",
                    "type": "password",
                    "default": "",
                    "placeholder": "Get your token at modelscope.cn → Home → Access Tokens",
                },
            ]
        },
    },
]


async def seed_builtin_tools():
    """Insert or update builtin tools in the database."""
    from app.models.tool import AgentTool
    from app.models.agent import Agent

    async with async_session() as db:
        new_tool_ids = []
        for t in BUILTIN_TOOLS:
            result = await db.execute(select(Tool).where(Tool.name == t["name"]))
            existing = result.scalar_one_or_none()
            if not existing:
                tool = Tool(
                    name=t["name"],
                    display_name=t["display_name"],
                    description=t["description"],
                    type="builtin",
                    category=t["category"],
                    icon=t["icon"],
                    is_default=t["is_default"],
                    parameters_schema=t["parameters_schema"],
                    config=t.get("config", {}),
                    config_schema=t.get("config_schema", {}),
                )
                db.add(tool)
                await db.flush()  # get tool.id
                if t["is_default"]:
                    new_tool_ids.append(tool.id)
                print(f"[ToolSeeder] Created builtin tool: {t['name']}")
            else:
                # Update config_schema for existing tools (schema may evolve)
                if t.get("config_schema") and existing.config_schema != t["config_schema"]:
                    existing.config_schema = t["config_schema"]
                    print(f"[ToolSeeder] Updated config_schema: {t['name']}")
                # Set default config if empty
                if not existing.config and t.get("config"):
                    existing.config = t["config"]
                    print(f"[ToolSeeder] Set default config: {t['name']}")

        # Auto-assign new default tools to all existing agents
        if new_tool_ids:
            agents_result = await db.execute(select(Agent.id))
            agent_ids = [row[0] for row in agents_result.fetchall()]
            for agent_id in agent_ids:
                for tool_id in new_tool_ids:
                    # Check if already assigned
                    check = await db.execute(
                        select(AgentTool).where(
                            AgentTool.agent_id == agent_id,
                            AgentTool.tool_id == tool_id,
                        )
                    )
                    if not check.scalar_one_or_none():
                        db.add(AgentTool(agent_id=agent_id, tool_id=tool_id, enabled=True))
            print(f"[ToolSeeder] Auto-assigned {len(new_tool_ids)} new tools to {len(agent_ids)} agents")

        await db.commit()
        print("[ToolSeeder] Builtin tools seeded")

