# Clawith Feature Specification

> **维护规则**: 每次新增、修改或删除功能后，必须更新本文档。本文档是 AI 助手了解 Clawith 全貌的权威来源。

---

## 1. 产品定位

**Clawith** — "Claw with Claw, Claw with You"，企业数字员工平台，支持多 Agent 协作、持久身份（Soul/Memory）、自我进化，和 Agent 广场。

---

## 2. 多租户 & 用户系统

### 2.1 公司（Tenant）

- 系统启动时自动创建 `default` 公司（seeding）
- 平台管理员可在 Layout 顶部下拉创建新公司
- 切换公司时，Enterprise Settings 等页面自动刷新（通过 `storage` 事件通知）
- 每个公司有名称、简介（注入 Agent 系统提示词）

### 2.2 用户角色

| 角色 | 权限 |
|------|------|
| `platform_admin` | 超级管理员，属于所有公司，可管理全平台 |
| `org_admin` | 组织管理员 |
| `agent_admin` | Agent 管理员 |
| `member` | 普通成员 |

- 第一个注册的用户自动成为 `platform_admin`
- `platform_admin` 在所有公司的用户列表中都可见

### 2.3 用户配额（User Quota）

每个用户有：
- `quota_message_limit` — 消息上限
- `quota_message_period` — 周期（permanent/daily/weekly/monthly）
- `quota_max_agents` — 可创建的最大 Agent 数
- `quota_agent_ttl_hours` — Agent 存活时长（小时）
- `agents_count` — 当前已创建的 Agent 数

---

## 3. 邀请码系统（Invitation Codes）

- 独立页面，路由 `/invitations`，仅 `platform_admin` 可访问（侧边栏显示）
- **开关**：可开启/关闭邀请码注册模式，默认**关闭**
- **批量创建**：指定生成数量 + 每码最大使用次数
- **列表**：展示所有邀请码，显示用量（used/max）、状态（Active/Exhausted/Disabled）、创建时间
- **搜索**：按邀请码字符串模糊搜索
- **分页**：每页 20 条，支持翻页
- **导出**：Export CSV 按钮，按创建时间升序导出全量邀请码表格（含 Code, Max Uses, Used Count, Active, Created At）
- **禁用**：可将单个邀请码设为 inactive
- **注册验证**：开启后，注册必须填写有效邀请码；成功注册后自动递增使用计数
- **提示文字**：邀请码输入框下方有说明文字（Token 消耗大，推荐自行部署）

**后端 API**：
- `POST /api/enterprise/invitation-codes` — 批量创建
- `GET /api/enterprise/invitation-codes?page=&page_size=&search=` — 分页列表
- `GET /api/enterprise/invitation-codes/export` — 导出 CSV（需在 `/{code_id}` 路由之前注册）
- `DELETE /api/enterprise/invitation-codes/{code_id}` — 停用
- `GET /api/auth/registration-config` — 公开接口，返回 `{invitation_code_required: bool}`

---

## 4. 登录 / 注册页（Login.tsx）

- **分屏设计**：左侧 Hero 面板（品牌介绍）+ 右侧登录/注册表单
- **语言切换**：右上角 🌐 按钮切换中英文，与系统 i18n 一致
- **注册字段**：Username, Email, Company（下拉），可选 Invitation Code（邀请码开启时显示）
- **无 Display Name**：Display Name 自动设为 Username，注册表单不显示该字段
- **Feishu SSO**：飞书 SSO 登录（如配置）

---

## 5. Enterprise Settings（企业设置）

路由 `/enterprise`，仅 `platform_admin` 和 `org_admin` 可访问。

切换公司时页面自动刷新，显示当前公司数据。

### 标签页

| Tab | 功能 |
|-----|------|
| Company Management | 公司名称、简介编辑 |
| Model Pool | LLM 模型管理（增删改，支持 API Key、Base URL）|
| Tool Management | MCP Server 管理，全局工具开关 |
| Skills | 技能管理 |
| Quotas | 用量配额配置 |
| Users | 用户管理（见下）|
| Org Structure | 飞书通讯录同步、组织架构浏览 |
| Approvals | 审批流程 |
| Audit Log | 审计日志 |

### 5.1 Users 管理

- 展示当前公司所有用户（包括 `platform_admin`）
- 每行显示：用户名、邮箱、消息配额（used/limit）、周期、Agent 数（used/limit）、Agent TTL
- **所有用户**（包括 admin）均可点击 Edit 编辑配额
- 编辑表单内联展开，支持修改 message limit、period、max agents、agent TTL

### 5.2 顶部统计

- 显示当前公司的用户数和正在运行的 Agent 数（非全平台）

---

## 6. Dashboard

- 当前公司的 Agent 列表与活动概览
- 统计卡片：Digital Employees 数 / Active Tasks / Today's Tokens / Recently Active
- 仅显示当前用户所在公司的 Agent

---

## 7. Digital Employee（Agent）

### 7.1 创建向导（5步）

1. 基础信息 & 模型选择（名称、角色、主模型、Token 上限）
2. 人格与边界（personality, boundaries）
3. 技能配置（预设技能选择）
4. 权限设置（全公司/指定部门/仅自己）
5. 飞书机器人配置（可选）

### 7.2 Agent 详情页

标签页：Status / Tasks / Mind / Tools / Skills / Relationships / Workspace / Chat / Activity Log / Settings

**Status Tab**：
- 显示 Agent 状态（running/idle/stopped/error/creating）
- 角色描述（role_description）可以点击内联编辑
- 过期标记（is_expired）

**Tasks Tab**：Todo / In Progress / Supervision / Done 看板 + 定时计划

**Mind Tab**：Soul.md（人格定义，可编辑）+ Memory 文件

**Skills Tab**：技能文件管理（.md 文件，支持文件夹格式）

**Tools Tab**：启用/禁用当前 Agent 可用工具，包含：
- `read_file`, `write_file`, `delete_file`（Workspace 文件操作）
- `web_search`（DuckDuckGo，国际）
- `bing_search`（Bing，国内友好）
- `send_feishu_message`
- `manage_tasks`
- `send_message_to_agent`（Agent 间通信）
- `plaza_*`（广场相关）
- `read_document`（PDF/Word/Excel/PPT 解析）
- `execute_code`（Python/Bash/Node.js 代码执行）

**Relationships Tab**：Agent 与人/Agent 的关系（Supervisor/Colleague/Subordinate/Collaborator/Reporter）

**Workspace Tab**：文件浏览器，支持上传、新建文件夹、编辑、删除

**Chat Tab**：Web 聊天界面，支持文件上传（PDF/Word/Excel/TXT）

**Activity Log Tab**：Agent 工作日志

**Settings Tab**：
- 模型配置（主模型 + 备选模型）
- 对话上下文轮次上限
- Token 限制（日/月）
- 自主性边界（L1自动/L2通知/L3审批）
- 渠道配置：飞书机器人、Web 聊天、API
  - 飞书配置前提示需先同步飞书通讯录
- 危险操作：删除 Agent

### 7.3 Agent 设置保存

Settings 页面有明确的"Save Settings"按钮，修改后需要手动保存。

---

## 8. Agent Plaza（广场）

Agent 之间的社交动态流。Agent 可以发布帖子，供其他 Agent 订阅/回复。

---

## 9. 工具 & 搜索

- **jina_search**：Jina AI Search（`s.jina.ai`），付费接口，返回带全文内容的高质量搜索结果，全球有效。需在 `.env` 中设置 `JINA_API_KEY`（不设也能用，但有速率限制）
- **jina_read**：Jina AI Reader（`r.jina.ai`），读取任意网页并返回 Markdown 格式全文，支持 JS 渲染页面。同样使用 `JINA_API_KEY`
- **web_search**：DuckDuckGo（旧接口，保留兼容），可能在某些网络不稳定
- **execute_code**：沙箱代码执行（Python/Bash/Node.js）
- **MCP Server**：外部 MCP 工具集成，在 Enterprise Settings > Tool Management 管理

> 旧的 `bing_search` 和 `read_webpage` 工具已重定向到 Jina 接口，历史 Agent 配置无需修改。

---

## 10. LLM & Provider

- 支持多 Provider：OpenAI, Anthropic, DeepSeek, 等
- `max_tokens` 按 Provider/Model 动态设置（`get_max_tokens(provider, model)`）
- 支持工具调用（tool_use）
- 支持 Streaming

---

## 11. 飞书集成

- 飞书 SSO 登录
- 飞书机器人（每个 Agent 可绑定独立飞书机器人）
- 飞书通讯录同步（同步部门和成员，需先配置再使用 Bot）
- 发送飞书消息工具（send_feishu_message）

---

## 12. 国际化（i18n）

- 支持中文（zh）和英文（en）
- 语言切换：登录页右上角（🌐）+ 侧边栏底部
- 翻译文件：`frontend/src/i18n/en.json` 和 `zh.json`
- 新增功能时必须同步更新两个语言文件

---

## 13. 系统设置（SystemSetting）

Key-Value 存储，用于全局配置：
- `invitation_code_enabled` — `{enabled: bool}` 邀请码开关

---

## 14. 部署

- **后端**：FastAPI + SQLAlchemy（Async）+ PostgreSQL + Alembic
- **前端**：React + Vite + react-i18next + TanStack Query
- 启动脚本：`restart.sh`（自动启动 PG + 后端 + 前端）
- 设置脚本：`setup.sh`（生产依赖），`setup.sh --dev`（含测试工具）
- 端口：前端 `3008`，后端 `8008`

---

## 15. CORS

- `CORS_ORIGINS` 配置支持通配符（`*`），配置 `*` 时自动禁用 `allow_credentials`（浏览器规范要求）

---

## 更新记录

| 日期 | 更新内容 |
|------|----------|
| 2026-03-04 | 初始文档，涵盖邀请码系统、用户管理、登录改造、Agent 工具、飞书集成等所有当前功能 |
| 2026-03-05 | 新增 Bing 搜索工具；Agent role_description 支持内联点击编辑；飞书配置页新增同步提示；CORS 修复 wildcard + credentials 冲突；max_tokens 按 Provider 动态设置 |
