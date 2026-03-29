# Module Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split `2026-03-28_architecture_design.md` into 12 independent module documents plus a condensed overview document.

**Architecture:** This is a documentation task. Each module document follows a uniform template: module info, component list, core interfaces, data flow, and dependencies. The overview document retains the system-wide views and cross-module relationships.

**Tech Stack:** Markdown documents, following project's documentation rules.

---

## Source Document
- `docs/iteration/v1.0/design/2026-03-28_architecture_design.md`

## Target Documents
```
docs/iteration/v1.0/design/
├── 2026-03-28_architecture_design.md    # Condensed overview (保留)
├── 2026-03-28_ingress.md                  # NEW
├── 2026-03-28_orchestration.md            # NEW
├── 2026-03-28_agent.md                   # NEW
├── 2026-03-28_model.md                   # NEW
├── 2026-03-28_memory.md                  # NEW
├── 2026-03-28_context.md                  # NEW
├── 2026-03-28_tools.md                   # NEW
├── 2026-03-28_storage.md                 # NEW
├── 2026-03-28_security.md               # NEW
├── 2026-03-28_extensions.md              # NEW
├── 2026-03-28_task_planning.md           # NEW
└── 2026-03-28_config.md                  # NEW
```

---

## Task 1: Create Ingress Module Document

**File:** `docs/iteration/v1.0/design/2026-03-28_ingress.md`

**Source:** Section 2 of architecture_design.md

- [ ] **Step 1: Create document with content**

```markdown
# Ingress Module (接入层)

## 文档信息
| 字段 | 内容 |
|------|------|
| 模块名称 | Ingress |
| 职责 | 命令解析、用户交互 |
| 路径 | `mozi/ingress/` |
| 文档版本 | v1.0 |
| 状态 | 规划中 |

## 组件列表

| 组件 | 路径 | 职责 |
|------|------|------|
| CLI (Typer) | `mozi/ingress/cli/` | 命令行交互 |
| Web UI (FastAPI) | `mozi/ingress/web/` | REST API、WebSocket |
| IDE Extension | `mozi/ingress/ide/` | VSCode/JetBrains 集成 |

## CLI 命令

| 命令 | 说明 |
|------|------|
| `mozi` | 启动交互会话 |
| `mozi "task"` | 带初始提示的会话 |
| `mozi -p "query"` | 非交互模式 |
| `mozi -c` | 继续最近会话 |
| `mozi -r <session>` | 恢复指定会话 |

## 依赖关系
- 依赖：无
- 被依赖：Orchestration Layer

## 变更记录
| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-03-28 | 初始版本 |
```

---

## Task 2: Create Orchestration Module Document

**File:** `docs/iteration/v1.0/design/2026-03-28_orchestration.md`

**Source:** Section 3 of architecture_design.md

- [ ] **Step 1: Create document with IntentGate, RalphLoop, TodoEnforcer content**

## 组件列表

| 组件 | 职责 |
|------|------|
| **IntentGate** | 意图识别，路由到对应 Agent |
| **RalphLoop** | 自循环执行，确保任务 100% 完成 |
| **TodoEnforcer** | 监控空闲 Agent，重新激活 |

## 核心接口

### IntentGate

意图分析与路由，识别宽泛意图类别（EXPLORE/CODE/REVIEW/PLAN/RESEARCH）。

```python
class IntentGate:
    async def analyze(self, user_input: str, context: Context) -> IntentResult:
        # 1. 显式指令解析
        explicit = self.parse_explicit(user_input)

        # 2. 隐式意图推断
        implicit = await self.model.analyze(...)

        # 3. 冲突检测
        if self._has_conflict(explicit, implicit):
            return IntentResult(status="ambiguous", needs_clarification=True)

        return IntentResult(status="clear", routing=self._determine_routing(implicit))
```

### RalphLoop

自循环执行器，确保任务 100% 完成。

```python
class RalphLoop:
    async def execute(self, task: Task, executor: Agent) -> LoopResult:
        while not task.is_complete:
            result = await executor.execute(task)

            if result.progress >= 0.95:
                task.is_complete = True

            if self._is_stuck(results):
                await self.todo_enforcer.reenact(task)

        return LoopResult(state=TaskState.COMPLETED)
```

### TodoEnforcer

监控空闲 Agent，重新激活卡住的任务。

```python
class TodoEnforcer:
    async def reenact(self, task: Task):
        # 清空当前上下文，重新开始
        task.clear_context()
        task.set_state(INITIAL)
        # 从上一次的检查点恢复
        task.restore_checkpoint()
```

## 依赖关系
- 依赖：Agent Layer, Model Layer
- 被依赖：Ingress Layer

---

## Task 3: Create Agent Module Document

**File:** `docs/iteration/v1.0/design/2026-03-28_agent.md`

**Source:** Section 4 (excluding 4.4 task planning) of architecture_design.md

- [ ] **Step 1: Create document with Agent content**

## 组件

| Agent | 角色 | 工具 | 使用场景 |
|-------|------|------|----------|
| **Builder** | 代码执行 | 内置全部 | 直接修改代码 |
| **Reviewer** | 代码审查 | read/grep/glob | 审查代码质量 |
| **Explorer** | 代码探索 | read/grep/glob | 了解代码库 |
| **Planner** | 任务规划 | read/grep/glob | 复杂任务分解 |
| **Researcher** | 技术研究 | read/web_search | 技术调研 |

## 扩展 Agent

从 `~/.mozi/agents/` 目录加载的自定义 Agent。

```python
class AgentRegistry:
    def load_builtin_agents(self) -> List[BaseAgent]:
        return [Builder(), Reviewer(), Explorer(), Planner(), Researcher()]

    def load_external_agents(self) -> List[BaseAgent]:
        agents = []
        for path in Path("~/.mozi/agents/").glob("*.py"):
            agents.append(self._load_agent(path))
        return agents
```

## BaseAgent

```python
class BaseAgent(ABC):
    @property
    def name(self) -> str: ...

    @property
    def tools(self) -> List[Tool]: ...

    @abstractmethod
    async def think(self, task: Task, context: Context) -> Thought: ...

    @abstractmethod
    async def execute(self, thought: Thought) -> Result: ...
```

## 意图路由

```
EXPLORE  → Explorer Agent
CODE     → Builder Agent
REVIEW   → Reviewer Agent
PLAN     → Planner Agent
RESEARCH → Researcher Agent
```

## 依赖关系
- 依赖：Model Layer, Tools Layer, Memory Layer
- 被依赖：Orchestration Layer

---

## Task 4: Create Model Module Document

**File:** `docs/iteration/v1.0/design/2026-03-28_model.md`

**Source:** Section 5 of architecture_design.md

- [ ] **Step 1: Create document with Model Gateway content**

## 组件

| 组件 | 职责 |
|------|------|
| **ModelGateway** | 多模型统一接口，智能路由 |
| **AnthropicProvider** | Anthropic API 适配 |
| **OpenAIProvider** | OpenAI API 适配 |
| **OllamaProvider** | Ollama 本地模型适配 |

## 多模型路由

```python
class ModelGateway:
    PROVIDERS = {
        "anthropic": AnthropicProvider,
        "openai": OpenAIProvider,
        "ollama": OllamaProvider,
    }

    async def complete(self, messages: List[Message], model: str = None) -> Response:
        provider, model_name = self.router.resolve(model)
        return await self.providers[provider].complete(messages, model_name)
```

## Provider 接口

```python
class BaseProvider(ABC):
    @abstractmethod
    async def complete(self, messages: List[Message], model: str) -> Response: ...

    @abstractmethod
    async def embeddings(self, texts: List[str]) -> List[float]: ...
```

## 依赖关系
- 依赖：无
- 被依赖：Agent Layer, Orchestration Layer

---

## Task 5: Create Memory Module Document

**File:** `docs/iteration/v1.0/design/2026-03-28_memory.md`

**Source:** Section 7.4 Memory Store of architecture_design.md

- [ ] **Step 1: Create document with Memory content**

## 三层记忆系统

| 层级 | 存储 | 生命周期 | 用途 |
|------|------|----------|------|
| Working | 内存 | 会话内 | LLM Context 滑动窗口 |
| Short-term | Qdrant | 180 天 | 语义搜索、RAG |
| Long-term | SQLite | 永久 | 用户偏好、历史经验 |

## 依赖关系
- 依赖：Storage Layer
- 被依赖：Agent Layer, Context Module

---

## Task 6: Create Context Module Document

**File:** `docs/iteration/v1.0/design/2026-03-28_context.md`

**Source:** Section 7.2 ContextManager of architecture_design.md

- [ ] **Step 1: Create document with ContextManager content**

## 组件

| 组件 | 职责 |
|------|------|
| **ContextManager** | 上下文组装、Token 预算管理、记忆检索 |

## ContextManager

上下文组装器，管理 Prompt 组成和 Token 预算。

```python
class ContextManager:
    async def assemble(self, task: Task, memory: MemoryStore) -> AssembledContext:
        # 1. 获取系统 Prompt
        system = self.get_system_prompt()

        # 2. 获取 Working Memory（滑动窗口）
        working = await memory.get_working(task.session_id)

        # 3. RAG 检索 Short-term Memory
        short_term = await memory.search(task.query, limit=5)

        # 4. 获取 Long-term Memory（用户偏好）
        long_term = await memory.get_preferences(task.session_id)

        # 5. Token 预算检查
        context = ConcatPrompt(system, working, short_term, long_term)
        if context.token_count > self.max_tokens:
            context = self.compress(context)

        return AssembledContext(prompt=context, token_count=token_count)
```

## 依赖关系
- 依赖：Memory Module
- 被依赖：Agent Layer

---

## Task 7: Create Tools Module Document

**File:** `docs/iteration/v1.0/design/2026-03-28_tools.md`

**Source:** Section 6 of architecture_design.md

- [ ] **Step 1: Create document with Tools content**

## 组件

| 组件 | 职责 |
|------|------|
| **HashAnchorEdit** | 带哈希验证的安全编辑 |
| **BuiltinTools** | read/write/edit/glob/grep/bash |
| **LSPBridge** | LSP 工具封装 |
| **MCPClient** | MCP 协议客户端 |
| **SkillLoader** | Skill 按需加载（加载后为工具） |

## 工具接口

```python
class Tool(ABC):
    @property
    def name(self) -> str: ...

    @property
    def description(self) -> str: ...

    @abstractmethod
    async def execute(self, params: dict, context: Context) -> ToolResult: ...
```

## 内置工具

| 工具 | 说明 |
|------|------|
| `read` | 读取文件 |
| `write` | 写入文件 |
| `edit` | 带哈希锚定的编辑 |
| `bash` | 执行 shell 命令 |
| `grep` | 内容搜索 |
| `glob` | 文件模式匹配 |

## HashAnchorEdit

安全编辑，带内容哈希验证。

```python
class HashAnchorEdit:
    async def execute(self, params: dict, context: Context) -> ToolResult:
        file_path = params["path"]
        old_content = params["old"]
        new_content = params["new"]

        # 读取当前文件内容
        current = await self.read_file(file_path)

        # 验证哈希
        if self.hash(current) != self.hash(old_content):
            raise HashMismatchError()

        # 执行替换
        updated = current.replace(old_content, new_content)
        await self.write_file(file_path, updated)

        return ToolResult(success=True)
```

## 依赖关系
- 依赖：Security Layer
- 被依赖：Agent Layer

---

## Task 8: Create Storage Module Document

**File:** `docs/iteration/v1.0/design/2026-03-28_storage.md`

**Source:** Section 7.1, 7.3 (excluding Memory) of architecture_design.md

- [ ] **Step 1: Create document with Storage content**

## 组件

| 组件 | 职责 |
|------|------|
| **SessionStore** | 会话持久化 (SQLite) |
| **ConfigStore** | 配置存储 |
| **ArtifactStore** | 工件存储 |

## SessionStore

```python
class SessionStore:
    async def create(self, session: Session) -> Session: ...
    async def get(self, session_id: str) -> Session: ...
    async def update(self, session: Session) -> Session: ...
    async def list(self, limit: int = 10) -> List[Session]: ...
```

## 依赖关系
- 依赖：无
- 被依赖：所有模块

---

## Task 9: Create Security Module Document

**File:** `docs/iteration/v1.0/design/2026-03-28_security.md`

**Source:** Section 8 of architecture_design.md

- [ ] **Step 1: Create document with Security content**

## 组件

| 组件 | 职责 |
|------|------|
| **Permission** | 权限检查，支持通配符 |
| **Sandbox** | 沙箱隔离模式 |
| **HITL** | 人工介入确认 |
| **Audit** | 审计日志 |

## Permission

权限检查，支持通配符。

```python
class PermissionChecker:
    # 优先级: deny > ask > allow

    async def check(self, tool_name: str, params: dict) -> PermissionResult:
        # 1. 检查 deny 名单
        if self._matches_pattern(tool_name, params, "deny"):
            return PermissionResult(status="deny")

        # 2. 检查 ask 名单
        if self._matches_pattern(tool_name, params, "ask"):
            return PermissionResult(status="ask")

        # 3. 默认 allow
        return PermissionResult(status="allow")
```

## Sandbox

沙箱隔离模式。

| 模式 | 行为 |
|------|------|
| `off` | 无隔离 |
| `non-main` | 禁止访问 ~/ 和项目目录 |
| `all` | 禁止所有敏感路径 |

## HITL

人工介入确认。

```
工具调用 → Permission "ask" → HITL 暂停 → 用户确认/拒绝
```

## Audit

审计日志。

```sql
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    action TEXT NOT NULL,
    tool TEXT,
    params JSON,
    result TEXT,
    user_decision TEXT,
    created_at TIMESTAMP
);
```

## 依赖关系
- 依赖：无
- 被依赖：所有模块（跨切面）

---

## Task 10: Create Extensions Module Document

**File:** `docs/iteration/v1.0/design/2026-03-28_extensions.md`

**Source:** Section 9 of architecture_design.md

- [ ] **Step 1: Create document with Extensions content**

## 组件

| 组件 | 职责 |
|------|------|
| **SkillsEngine** | Skill 解析与执行 |
| **MCPClient** | MCP 协议客户端 |

## Skills Engine

Skill 文档结构：

```markdown
---
name: git-master
triggers:
  - "atomic commit"
  - "safe rebase"
---

# Git Master Skill

## 执行步骤
1. 检查 git 状态
2. 生成提交消息
3. 执行提交
```

## MCP Client

支持的传输：stdio / sse / http / websocket

## 依赖关系
- 依赖：Tools Layer
- 被依赖：Agent Layer

---

## Task 11: Create Task Planning Module Document

**File:** `docs/iteration/v1.0/design/2026-03-28_task_planning.md`

**Source:** Section 4.4, 10 of architecture_design.md

- [ ] **Step 1: Create document with Task Planning content**

## 组件

| 组件 | 职责 |
|------|------|
| **TaskManager** | 任务创建、分解、状态跟踪 |
| **TaskRunner** | 任务执行调度 |
| **CheckpointManager** | 检查点保存与恢复 |
| **ProgressTracker** | 进度跟踪 |

## 复杂度路由

### 评估维度

| 维度 | 权重 |
|------|------|
| 预估修改文件数 | 30% |
| 技术栈多样性 | 20% |
| 跨模块依赖深度 | 30% |
| 历史成功率 | 20% |

### 路由策略

| 复杂度 | 范围 | Agent 行为 |
|--------|------|----------|
| **SIMPLE** | ≤40 | Builder 直接执行 |
| **MEDIUM** | 41-70 | Builder + Reviewer |
| **COMPLEX** | >70 | Planner → Explorer → Builder → Reviewer |

## 依赖关系
- 依赖：Agent Layer, Storage Layer
- 被依赖：Orchestration Layer

---

## Task 12: Create Config Module Document

**File:** `docs/iteration/v1.0/design/2026-03-28_config.md`

**Source:** Section 18.2 of architecture_design.md

- [ ] **Step 1: Create document with Config content**

## 配置项

| 配置项 | 来源 | 说明 |
|--------|------|------|
| `MOZI_MODEL` | 环境变量 | 默认模型 |
| `MOZI_CONFIG_PATH` | 环境变量 | 配置文件路径 |
| `~/.mozi/config.json` | 配置文件 | 用户配置 |

## 错误码

| 错误码 | 说明 |
|--------|------|
| E1001 | 模型调用失败 |
| E1002 | 工具执行失败 |
| E2001 | 会话不存在 |
| E3001 | 权限不足 |
| E4001 | 配置错误 |

## 降级策略

| 场景 | 降级行为 |
|------|----------|
| 模型超时 | 重试 3 次，失败后返回错误 |
| 工具执行失败 | 返回错误信息给用户 |
| 存储服务不可用 | 降级到内存模式 |

## 依赖关系
- 依赖：无
- 被依赖：所有模块

---

## Task 13: Condense Overview Document

**File:** `docs/iteration/v1.0/design/2026-03-28_architecture_design.md`

**Action:** Remove sections 2-9 (detailed module content), keep:
- Section 1 (System Overview - simplified)
- Section 9 (Request Lifecycle)
- Section 10 (Project Directory)
- Section 17 (Evolution Plan)
- Section 11 (Glossary)
- Add links to each module document

- [ ] **Step 1: Rewrite overview document**

---

## Task 14: Update v1.0 README

**File:** `docs/iteration/v1.0/README.md`

- [ ] **Step 1: Add module documents to v1.0 README**

---

## Task 15: Commit All Documents

- [ ] **Step 1: Git add all new documents**
- [ ] **Step 2: Git commit with message "docs: split architecture design into 12 module documents""
