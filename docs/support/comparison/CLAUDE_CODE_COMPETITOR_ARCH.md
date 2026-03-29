# AI Coding Assistant 产品设计与架构文档

> 对标 Claude Code 的竞品分析与技术规格

---

## 目录

1. [产品概述](#1-产品概述)
2. [核心功能规格](#2-核心功能规格)
3. [系统架构设计](#3-系统架构设计)
4. [模块详细设计](#4-模块详细设计)
5. [CLI 设计规范](#5-cli-设计规范)
6. [Agent 系统设计](#6-agent-系统设计)
7. [扩展协议 (MCP)](#7-扩展协议-mcp)
8. [权限与安全模型](#8-权限与安全模型)
9. [数据与记忆系统](#9-数据与记忆系统)
10. [插件系统](#10-插件系统)
11. [多端支持架构](#11-多端支持架构)
12. [实现技术选型](#12-实现技术选型)

---

## 1. 产品概述

### 1.1 产品定位

AI Coding Assistant 是一款终端编程助手，通过自然语言接口帮助开发者：

- 理解和探索代码库
- 自动执行编程任务
- 集成开发工具链
- 协调多 Agent 并行工作

### 1.2 核心价值

| 价值主张 | 描述 |
|---------|------|
| **自然语言驱动** | 用日常语言控制开发任务，无需学习复杂命令 |
| **上下文感知** | 理解整个代码库，保持项目级上下文 |
| **工具集成** | 通过开放协议连接 IDE、Git、CI/CD 等工具 |
| **自动化工作流** | 封装可复用的技能和工作流 |
| **安全可控** | 细粒度权限控制，清晰的操作边界 |

### 1.3 目标用户

- 个人开发者
- 软件团队
- DevOps 工程师
- 技术管理者

---

## 2. 核心功能规格

### 2.1 会话管理

| 功能 | 规格 |
|------|------|
| 交互模式 | 终端内实时对话，支持多轮迭代 |
| 非交互模式 | `-p/--print` 执行单次查询并输出结果 |
| 管道输入 | 支持 `cat file \| ai -p "query"` |
| 会话恢复 | `-c/--continue` 继续最近会话 |
| 命名会话 | `-n/--name` 为会话命名，支持 `ai -r <name>` 恢复 |
| 会话持久化 | 自动保存到 `~/.ai/projects/{project}/{session}/` |
| 上下文压缩 | 95% 容量时自动压缩历史 |

### 2.2 代码库交互

| 功能 | 规格 |
|------|------|
| 文件读取 | Read 工具读取任意文件 |
| 文件编辑 | Edit 工具支持精确替换 |
| 文件写入 | Write 工具创建/覆盖文件 |
| 模式搜索 | Glob 按通配符匹配文件 |
| 内容搜索 | Grep 支持正则表达式 |
| 命令执行 | Bash 执行 Shell 命令 |
| 网页获取 | WebFetch 抓取 URL 内容 |

### 2.3 Git 工作流

```bash
ai "commit my changes with a descriptive message"
ai "create a new branch for feature-x"
ai "review PR #456 and suggest improvements"
```

支持：
- 阶段变更 (stage)
- 提交消息生成
- 分支创建/切换
- PR 创建和审查

### 2.4 MCP 集成

通过 Model Context Protocol 连接外部工具：

```bash
ai mcp add github --transport http https://api.githubcopilot.com/mcp/
ai mcp add db --transport stdio -- npx -y @bytebase/dbhub
ai mcp list
ai mcp remove github
```

### 2.5 定时任务

| 类型 | 说明 |
|------|------|
| 云端定时 | 托管在服务器，设备关闭时仍可运行 |
| 本地定时 | 桌面客户端，支持定时触发 |
| 轮询模式 | CLI 内 `/loop` 重复执行提示 |

---

## 3. 系统架构设计

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        客户端层                              │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │ Terminal│  │  VS Code│  │ JetBrains│  │ Desktop │        │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘        │
└───────┼────────────┼───────────┼───────────┼──────────────┘
        │            │           │           │
        └────────────┴───────────┴───────────┘
                          │
                    ┌─────▼─────┐
                    │  CLI SDK   │
                    └─────┬─────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
   ┌────▼────┐      ┌─────▼────┐      ┌─────▼────┐
   │ Agent   │      │ Session   │      │  Plugin  │
   │ Engine  │◄────►│ Manager   │◄────►│ System   │
   └────┬────┘      └───────────┘      └──────────┘
        │
   ┌────▼────┐      ┌───────────┐      ┌───────────┐
   │  Tool   │◄────►│   MCP     │◄────►│   Hook    │
   │Registry │      │  Client   │      │  System   │
   └────┬────┘      └───────────┘      └───────────┘
        │
   ┌────▼────┐
   │ LLM API │
   │ (OpenAI/│
   │Anthropic│
   │ /Local) │
   └─────────┘
```

### 3.2 核心组件职责

| 组件 | 职责 |
|------|------|
| **CLI SDK** | 命令行解析、用户交互、输出格式化 |
| **Agent Engine** | 任务规划、步骤分解、工具调度 |
| **Session Manager** | 会话状态、上下文管理、持久化 |
| **Tool Registry** | 工具注册、权限控制、执行调度 |
| **MCP Client** | MCP 协议通信、服务器管理 |
| **Hook System** | 生命周期事件、预处理/后处理 |
| **Plugin System** | 插件加载、生命周期管理 |

### 3.3 数据流

```
用户输入 → CLI SDK → 会话管理器 → Agent Engine
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
              Tool Registry    MCP Client      Hook System
                    │               │               │
                    ▼               ▼               ▼
              内部工具执行    外部工具调用    事件回调
                    │               │               │
                    └───────────────┼───────────────┘
                                    ▼
                              结果聚合
                                    │
                                    ▼
                          Session Manager (更新上下文)
                                    │
                                    ▼
                              LLM 下一轮
```

---

## 4. 模块详细设计

### 4.1 Agent Engine

```python
class AgentEngine:
    """核心 Agent 引擎"""

    def __init__(self, config: EngineConfig):
        self.planner = Planner()
        self.executor = ToolExecutor()
        self.memory = WorkingMemory()

    def run(self, task: str, context: SessionContext) -> AgentResult:
        """执行单一任务"""
        plan = self.planner.create_plan(task, context)
        for step in plan.steps:
            result = self.executor.execute(step, context)
            context.update(result)
            if result.requires_approval:
                yield ApprovalRequest(result)
        return AgentResult(status="completed", context=context)

    def delegate(self, agent: AgentSpec, task: str) -> DelegateResult:
        """委托给子 Agent"""
        sub_context = context.fork()
        sub_result = self.run(task, sub_context)
        return DelegateResult(
            summary=sub_result.summary,
            artifacts=sub_result.artifacts
        )

    def spawn(self, agent: AgentSpec, task: str, background: bool) -> AgentHandle:
        """启动 Agent（前台或后台）"""
        handle = AgentHandle(id=uuid4(), agent=agent)
        if background:
            handle.start_async(task)
        else:
            handle.start_sync(task)
        return handle
```

### 4.2 Session Manager

```python
class SessionManager:
    """会话管理器"""

    def __init__(self, storage: StorageBackend):
        self.storage = storage
        self.active_sessions: Dict[str, Session] = {}

    def create_session(self, project_path: str, name: str = None) -> Session:
        """创建新会话"""
        session_id = str(uuid4())
        session = Session(
            id=session_id,
            project=project_path,
            name=name,
            created_at=now()
        )
        self.active_sessions[session_id] = session
        self.storage.save(session)
        return session

    def resume(self, session_id: str) -> Session:
        """恢复会话"""
        return self.storage.load(session_id)

    def compact(self, session: Session) -> Session:
        """压缩会话上下文"""
        compacted = self.summarize_old_messages(session)
        return session.with_messages(compacted)
```

### 4.3 Tool Registry

```python
class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._permissions: Dict[str, Permission] = {}
        self.register_builtin_tools()

    def register(self, tool: Tool, allowed: bool = True):
        """注册工具"""
        self._tools[tool.name] = tool
        self._permissions[tool.name] = Permission(allowed=allowed)

    def check_permission(self, tool_name: str, user: str) -> bool:
        """检查权限"""
        return self._permissions.get(tool_name, Permission()).allowed

    def execute(self, name: str, args: dict, context: Context) -> ToolResult:
        """执行工具"""
        if not self.check_permission(name, context.user):
            raise PermissionDenied(name)
        tool = self._tools[name]
        return tool.execute(args, context)

    def list_tools(self) -> List[ToolMetadata]:
        """列出可用工具"""
        return [t.metadata() for t in self._tools.values()]
```

### 4.4 MCP Client

```python
class MCPClient:
    """MCP 协议客户端"""

    def __init__(self, transport: Transport):
        self.transport = transport
        self.servers: Dict[str, MCPServer] = {}

    def connect(self, name: str, config: MCPConfig):
        """连接 MCP 服务器"""
        server = MCPServer(name=name, config=config)
        await server.connect()
        self.servers[name] = server

    async def call_tool(self, server: str, tool: str, args: dict) -> Any:
        """调用 MCP 工具"""
        return await self.servers[server].call_tool(tool, args)

    async def list_tools(self, server: str) -> List[Tool]:
        """列出服务器工具"""
        return await self.servers[server].list_tools()

    async def list_resources(self, server: str) -> List[Resource]:
        """列出服务器资源"""
        return await self.servers[server].list_resources()
```

---

## 5. CLI 设计规范

### 5.1 命令结构

```
ai [command] [options] [--] [args...]

# 主要命令
ai                          # 启动交互会话
ai "task description"       # 带初始提示的交互会话
ai -p "query"               # 非交互模式 (print mode)
ai -c                        # 继续最近会话
ai -r <session> "task"      # 恢复指定会话
ai -n <name> "task"         # 命名会话

# 子命令
ai auth login|logout|status
ai mcp add|list|get|remove
ai agents list|create|delete
ai plugin install|list|remove
```

### 5.2 全局 Flag

| Flag | 缩写 | 说明 | 示例 |
|------|------|------|------|
| `--print` | `-p` | 非交互模式 | `ai -p "query"` |
| `--continue` | `-c` | 继续会话 | `ai -c` |
| `--resume` | `-r` | 恢复会话 | `ai -r session-id` |
| `--name` | `-n` | 会话名称 | `ai -n my-session` |
| `--agent` | | 指定 Agent | `ai --agent reviewer` |
| `--tools` | | 限制工具 | `ai --tools "Read,Bash"` |
| `--permission-mode` | | 权限模式 | `ai --permission-mode plan` |
| `--mcp-config` | | MCP 配置 | `ai --mcp-config ./mcp.json` |
| `--bare` | | 最小模式 | `ai --bare -p "query"` |
| `--system-prompt` | | 自定义提示 | `ai --system-prompt "You are..."` |
| `--debug` | | 调试模式 | `ai --debug "api,mcp"` |
| `--version` | `-v` | 版本号 | `ai -v` |

### 5.3 输出格式

| Flag | 格式 |
|------|------|
| `--output-format text` | 纯文本 (默认) |
| `--output-format json` | 结构化 JSON |
| `--output-format stream-json` | 流式 JSON |

### 5.4 退出码

| 退出码 | 含义 |
|--------|------|
| 0 | 成功 |
| 1 | 执行失败 |
| 2 | 权限被拒绝 |
| 130 | Ctrl+C 中断 |

---

## 6. Agent 系统设计

### 6.1 内置 Agent

| Agent | 模型 | 工具 | 用途 |
|-------|------|------|------|
| **Explore** | Haiku | Read, Grep, Glob | 快速代码探索 |
| **Plan** | 继承 | Read, Grep, Glob | 规划模式研究 |
| **General** | 继承 | 全部 | 复杂多步骤任务 |

### 6.2 Agent 定义格式

Agent 使用 Markdown + YAML 定义：

```markdown
---
name: code-reviewer
description: 代码审查专家，在代码变更后主动使用
tools:
  - Read
  - Grep
  - Glob
  - Bash
model: sonnet
permissionMode: acceptEdits
memory: user
skills:
  - coding-standards
  - security-best-practices
maxTurns: 50
---

You are a senior code reviewer. Focus on:
- Code quality and readability
- Security vulnerabilities
- Performance issues
- Test coverage

When invoked:
1. Run `git diff` to see changes
2. Review each modified file
3. Provide actionable feedback
```

### 6.3 Agent 调用方式

```text
# 自然语言委托
Use the code-reviewer agent to review my changes

# @ 提及
@code-reviewer look at the auth module

# 整个会话使用指定 Agent
ai --agent reviewer

# 后台运行
Use the code-reviewer agent in the background
```

### 6.4 内存持久化

| 作用域 | 路径 | 用途 |
|--------|------|------|
| `user` | `~/.ai/agent-memory/{agent}/` | 跨项目记忆 |
| `project` | `.ai/agent-memory/{agent}/` | 项目共享记忆 |
| `local` | `.ai/agent-memory-local/{agent}/` | 本地私有记忆 |

---

## 7. 扩展协议 (MCP)

### 7.1 协议概述

Model Context Protocol 是开放的 AI-工具集成标准，支持：

- 工具调用 (tools/call)
- 资源访问 (resources/read)
- 提示模板 (prompts/list)
- 动态更新 (notifications/list_changed)

### 7.2 传输类型

| 传输 | 适用场景 | 配置示例 |
|------|---------|---------|
| **stdio** | 本地进程 | `{ "type": "stdio", "command": "npx", "args": [...] }` |
| **HTTP** | 远程服务 | `{ "type": "http", "url": "https://api.example.com/mcp" }` |
| **SSE** | 实时推送 | `{ "type": "sse", "url": "https://api.example.com/sse" }` |

### 7.3 MCP 配置结构

```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": {
        "Authorization": "Bearer ${GITHUB_TOKEN}"
      }
    },
    "filesystem": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "./workspace"]
    },
    "db": {
      "type": "stdio",
      "command": "python",
      "args": ["/usr/local/bin/db-server.py"],
      "env": {
        "DB_URL": "${DB_URL}"
      }
    }
  }
}
```

### 7.4 配置作用域

| 作用域 | 位置 | 共享范围 |
|--------|------|---------|
| `local` | `~/.ai.json` (项目路径下) | 仅当前用户当前项目 |
| `project` | `.mcp.json` | 团队共享，可提交到 Git |
| `user` | `~/.ai.json` | 仅当前用户所有项目 |
| `managed` | 系统目录 | 管理员部署，不可修改 |

### 7.5 Tool Search 优化

```bash
# 工具延迟加载，不预先塞入 context
ai  # 启动时只加载工具名称

# 阈值模式
ENABLE_TOOL_SEARCH=auto:10 ai  # 工具描述超 10% context 时延迟加载
```

---

## 8. 权限与安全模型

### 8.1 权限模式

| 模式 | 行为 | 适用场景 |
|------|------|---------|
| `default` | 操作前确认 | 日常开发 |
| `acceptEdits` | 自动接受文件编辑 | 批量修改 |
| `dontAsk` | 自动拒绝需确认的操作 | 安全审查 |
| `bypassPermissions` | 跳过所有确认 | CI/CD |
| `plan` | 只读探索模式 | 代码分析 |

### 8.2 权限规则

```json
{
  "permissions": {
    "allow": [
      "Read",
      "Bash(git *)",
      "Bash(npm test)"
    ],
    "deny": [
      "Bash(rm -rf /)",
      "Edit(/etc/**)"
    ]
  }
}
```

### 8.3 Hook 权限验证

```yaml
# Agent 定义中的 Hook
name: db-reader
tools: Bash
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate-readonly.sh"
```

### 8.4 MCP 服务器管控

```json
{
  "allowedMcpServers": [
    { "serverName": "github" },
    { "serverUrl": "https://mcp.company.com/*" }
  ],
  "deniedMcpServers": [
    { "serverName": "untrusted-tool" }
  ]
}
```

---

## 9. 数据与记忆系统

### 9.1 项目级文件

| 文件/目录 | 用途 |
|----------|------|
| `CLAUDE.md` | 项目级指令和约定 |
| `MEMORY.md` | 自动维护的项目记忆 |
| `.mcp.json` | MCP 服务器配置 |
| `.ai/commands/` | 自定义命令 |
| `.ai/agents/` | 项目级 Agent 定义 |
| `.ai/skills/` | 项目级 Skills |

### 9.2 CLAUDE.md 示例

```markdown
# 项目指南

## 技术栈
- Python 3.11+
- FastAPI
- PostgreSQL

## 代码规范
- 使用 Black 格式化
- 类型注解必须完整
- 单文件不超过 300 行

## 构建命令
- 开发: `npm run dev`
- 测试: `pytest tests/`
- 部署: `docker build`

## 注意事项
- 不要直接修改数据库
- 所有 API 必须有文档字符串
```

### 9.3 用户级配置

| 路径 | 用途 |
|------|------|
| `~/.ai.json` | 用户全局配置和 MCP |
| `~/.ai/agents/` | 用户级 Agent 定义 |
| `~/.ai/skills/` | 用户级 Skills |
| `~/.ai/agent-memory/` | 用户级 Agent 记忆 |

### 9.4 会话存储

```
~/.ai/projects/
└── {project-id}/
    └── {session-id}/
        ├── conversation.jsonl   # 对话历史
        ├── metadata.json       # 会话元数据
        └── subagents/          # 子 Agent 记录
            └── {agent-id}.jsonl
```

---

## 10. 插件系统

### 10.1 插件结构

```
my-plugin/
├── plugin.json           # 插件元数据
├── agents/               # 插件 Agent
│   └── reviewer.md
├── skills/               # 插件 Skills
│   └── security-check.md
├── commands/             # 插件命令
│   └── deploy.sh
├── mcp-servers/          # 插件 MCP 服务器
│   └── custom-tool.py
└── hooks/                # 插件 Hooks
    └── pre-commit.sh
```

### 10.2 plugin.json

```json
{
  "name": "code-review",
  "version": "1.0.0",
  "description": "Automated code review plugin",
  "agents": [
    "agents/reviewer.md"
  ],
  "skills": [
    "skills/security-check.md"
  ],
  "commands": [
    {
      "name": "/review-pr",
      "script": "commands/review.sh"
    }
  ],
  "mcpServers": {
    "review-tools": {
      "type": "stdio",
      "command": "${CLAUDE_PLUGIN_ROOT}/servers/review",
      "env": {}
    }
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit",
        "hooks": [
          { "type": "command", "command": "echo 'Edited!'" }
        ]
      }
    ]
  }
}
```

### 10.3 插件安装

```bash
ai plugin install code-review@https://github.com/org/plugin
ai plugin list
ai plugin remove code-review
ai plugin update
```

---

## 11. 多端支持架构

### 11.1 终端 (Terminal)

```
┌─────────────────────────────────┐
│          ai CLI                 │
│  ┌───────────────────────────┐  │
│  │   Readline Input          │  │
│  │   ANSI Colors             │  │
│  │   Terminal Detection      │  │
│  └───────────────────────────┘  │
│              │                  │
│         ┌────▼────┐             │
│         │  CLI    │             │
│         │  SDK    │             │
│         └────┬────┘             │
└──────────────┼──────────────────┘
               │ IPC / HTTP
               ▼
         ┌─────────┐
         │ Backend │
         │ Service │
         └─────────┘
```

### 11.2 VS Code 扩展

```typescript
// VS Code 扩展能力
interface VSCodeExtension {
  // 内联差异显示
  showInlineDiff(uri: string, edits: Edit[]): void

  // @ 文件提及
  registerFileMention(handler: MentionHandler): void

  // 计划审查
  showPlanReview(plan: Plan): Promise<Approved>

  // 对话历史
  showChatHistory(): void

  // 终端集成
  integrateTerminal(): Terminal
}
```

### 11.3 远程控制

```bash
# 启动远程控制服务器
ai remote-control --name "my-session"

# 从 Web 控制
# https://ai.example.com/remote/{session-id}
```

---

## 12. 实现技术选型

### 12.1 推荐技术栈

| 组件 | 推荐技术 | 备选 |
|------|---------|------|
| **CLI 核心** | Python (click) | Go (cobra) |
| **LLM 集成** | Anthropic SDK / OpenAI SDK | LiteLLM |
| **MCP 协议** | mcp Python SDK | TypeScript SDK |
| **配置存储** | JSON + Pydantic | YAML |
| **会话存储** | JSON Lines | SQLite |
| **IDE 扩展** | VS Code API | Language Server Protocol |
| **跨平台打包** | PyInstaller / Nuitka | Go binary |

### 12.2 项目结构

```
ai-coding-assistant/
├── src/
│   ├── cli/
│   │   ├── __main__.py
│   │   ├── commands/
│   │   ├── main.py
│   │   └── formatter.py
│   ├── core/
│   │   ├── agent/
│   │   │   ├── engine.py
│   │   │   ├── planner.py
│   │   │   └── executor.py
│   │   ├── session/
│   │   │   ├── manager.py
│   │   │   └── storage.py
│   │   └── tool/
│   │       ├── registry.py
│   │       └── builtin.py
│   ├── mcp/
│   │   ├── client.py
│   │   ├── protocol.py
│   │   └── transport/
│   ├── plugin/
│   │   ├── loader.py
│   │   └── lifecycle.py
│   ├── hook/
│   │   └── manager.py
│   └── llm/
│       ├── anthropic.py
│       └── openai.py
├── plugins/
│   └── builtins/
├── tests/
├── docs/
├── pyproject.toml
└── README.md
```

### 12.3 核心接口定义

```python
# === Agent 接口 ===
class Agent(ABC):
    @abstractmethod
    async def run(self, task: str, context: Context) -> AgentResult:
        pass

# === 工具接口 ===
class Tool(ABC):
    @property
    def name(self) -> str: pass

    @property
    def description(self) -> str: pass

    @abstractmethod
    async def execute(self, args: dict, context: Context) -> ToolResult:
        pass

# === MCP 接口 ===
class MCPClient(ABC):
    @abstractmethod
    async def connect(self, config: MCPConfig) -> None: pass

    @abstractmethod
    async def call_tool(self, name: str, args: dict) -> Any: pass

    @abstractmethod
    async def list_tools(self) -> List[Tool]: pass

# === 会话接口 ===
class Session(ABC):
    @property
    def id(self) -> str: pass

    @abstractmethod
    async def add_message(self, message: Message) -> None: pass

    @abstractmethod
    async def compact(self) -> None: pass

    @abstractmethod
    async def save(self) -> None: pass
```

### 12.4 环境变量

| 变量 | 用途 | 示例 |
|------|------|------|
| `AI_API_KEY` | LLM API 密钥 | `sk-...` |
| `AI_BASE_URL` | API 端点 | `https://api.anthropic.com` |
| `AI_MODEL` | 默认模型 | `claude-sonnet-4-6` |
| `AI_PROJECT_DIR` | 项目根目录 | `/path/to/project` |
| `ENABLE_TOOL_SEARCH` | 工具搜索模式 | `auto`, `true`, `false` |
| `MAX_MCP_OUTPUT_TOKENS` | MCP 输出限制 | `25000` |

---

## 附录 A: 功能优先级

### P0 - 核心功能

- [ ] 终端交互会话
- [ ] 文件读取/编辑/写入
- [ ] Bash 命令执行
- [ ] 基本 Agent 委托
- [ ] 会话持久化

### P1 - 重要功能

- [ ] MCP 集成
- [ ] Git 工作流
- [ ] 权限控制
- [ ] 自定义 Agent
- [ ] 管道输入/输出

### P2 - 增强功能

- [ ] VS Code 扩展
- [ ] 插件系统
- [ ] Skills 系统
- [ ] 定时任务
- [ ] 远程控制

### P3 - 高级功能

- [ ] 远程 Web 会话
- [ ] JetBrains 集成
- [ ] 桌面客户端
- [ ] 团队协作
- [ ] Agent 团队

---

## 附录 B: 竞品功能对照

| 功能 | Claude Code | Cursor | GitHub Copilot | 本产品 |
|------|-------------|--------|----------------|--------|
| 终端 CLI | ✅ | ❌ | ❌ | ✅ |
| VS Code 集成 | ✅ | ✅ | ✅ | ✅ |
| MCP 支持 | ✅ | 部分 | ❌ | ✅ |
| 子 Agent | ✅ | ❌ | ❌ | ✅ |
| 自定义 Skills | ✅ | ❌ | ❌ | ✅ |
| 插件系统 | ✅ | ❌ | ❌ | ✅ |
| 会话持久化 | ✅ | ✅ | ❌ | ✅ |
| 定时任务 | ✅ | ❌ | ❌ | ✅ |
| 远程控制 | ✅ | ❌ | ❌ | ✅ |
| Hooks | ✅ | ❌ | ❌ | ✅ |

---

*文档版本: 1.0.0*
*生成日期: 2026-03-28*
