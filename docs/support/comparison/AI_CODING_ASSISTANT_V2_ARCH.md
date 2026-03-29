# AI Coding Assistant V2 - 多智能体编排架构

> 参考 OpenCode + oh-my-openagent 设计的下一代产品

---

## 目录

1. [设计理念](#1-设计理念)
2. [核心架构](#2-核心架构)
3. [多智能体系统](#3-多智能体系统)
4. [编排引擎](#4-编排引擎)
5. [工具系统](#5-工具系统)
6. [安全编辑机制](#6-安全编辑机制)
7. [技能系统](#7-技能系统)
8. [多模型支持](#8-多模型支持)
9. [会话与持久化](#9-会话与持久化)
10. [TUI 界面设计](#10-tui-界面设计)
11. [LSP 集成](#11-lsp-集成)
12. [配置系统](#12-配置系统)
13. [CLI 设计](#13-cli-设计)
14. [实现路线图](#14-实现路线图)

---

## 1. 设计理念

### 1.1 核心原则

| 原则 | 描述 |
|------|------|
| **多模型编排** | 不绑定单一供应商，发挥各模型特长 |
| **多智能体协作** | 专业化分工，并行执行 |
| **安全第一** | Hash 锚定编辑，防止状态冲突 |
| **意图感知** | IntentGate 理解真实意图而非字面意思 |
| **上下文净化** | Skill-embedded MCP，按需加载 |

### 1.2 与 Claude Code 的差异

| 维度 | Claude Code | 本产品 V2 |
|------|------------|----------|
| 架构 | 单主 Agent | 多智能体编排 |
| 模型 | 仅 Anthropic | 多模型协同 |
| 编辑安全 | 无 | Hash 锚定 |
| 意图理解 | 基础 | IntentGate |
| 循环执行 | 有限 | Ralph Loop |
| TUI | 基础终端 | Bubble Tea TUI |
| 会话存储 | JSON Lines | SQLite |

---

## 2. 核心架构

### 2.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                          TUI 层 (Bubble Tea)                        │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│   │  会话    │  │  消息    │  │  文件    │  │  Agent   │        │
│   │  列表    │  │  视图    │  │  树      │  │  状态    │        │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
├─────────────────────────────────────────────────────────────────────┤
│                        命令层                                        │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  /ultrawork  /init-deep  /start-work  /ulw-loop  /doctor  │  │
│   └─────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│                      编排引擎 (Orchestrator)                        │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  ┌───────────┐  ┌───────────┐  ┌───────────┐            │  │
│   │  │ IntentGate│  │  Ralph    │  │  Todo     │            │  │
│   │  │           │  │  Loop     │  │  Enforcer │            │  │
│   │  └───────────┘  └───────────┘  └───────────┘            │  │
│   └─────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│                       智能体层                                      │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐│
│   │Sisyphus │  │Prometheus│  │Hephaestus│ │ Oracle  │  │ Explore ││
│   │ (主编)  │  │ (规划)  │  │ (执行)  │  │ (架构)  │  │ (搜索)  ││
│   └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘│
├───────┼─────────────┼─────────────┼─────────────┼────────────┼────┤
│       │      Agent Registry & Delegator           │            │    │
├───────┼─────────────┼─────────────┼─────────────┼────────────┼────┤
│                      模型网关 (Model Gateway)                      │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐│
│   │Anthropic│  │ OpenAI  │  │ Gemini  │  │ Groq    │  │ Local   ││
│   └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘│
├─────────────────────────────────────────────────────────────────────┤
│                       工具层                                        │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│   │ Hash     │  │ LSP      │  │ MCP      │  │ Skill    │        │
│   │ Anchor   │  │ Tools    │  │ Client   │  │ Loader   │        │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
├─────────────────────────────────────────────────────────────────────┤
│                       存储层                                        │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│   │ SQLite   │  │ Config   │  │ Memory   │  │ Artifact │        │
│   │ Session  │  │ Store    │  │ Store    │  │ Store    │        │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 核心组件职责

| 组件 | 类型 | 职责 |
|------|------|------|
| **Orchestrator** | 核心 | 智能体生命周期、任务分发、结果汇总 |
| **IntentGate** | 感知层 | 用户意图分类、歧义消解、任务路由 |
| **RalphLoop** | 执行层 | 自循环执行直到 100% 完成 |
| **TodoEnforcer** | 执行层 | 监控空闲 Agent，重新激活 |
| **ModelGateway** | 网关层 | 多模型负载均衡、故障转移 |
| **HashAnchor** | 安全层 | 编辑验证、冲突检测 |
| **LSPBridge** | 工具层 | 语言服务器协议桥接 |
| **SkillLoader** | 加载层 | Skill 按需加载和卸载 |

---

## 3. 多智能体系统

### 3.1 内置 Agent 定义

| Agent | 默认模型 | 类别 | 职责 |
|-------|---------|------|------|
| **Sisyphus** | Claude Opus 4.6 | 编排 | 主协调器，规划、委托、并行执行 |
| **Prometheus** | Kimi K2.5 | 战略 | 面试式规划，识别范围和歧义 |
| **Hephaestus** | GPT-5.4 | 执行 | 自主深度执行，无需逐步指导 |
| **Oracle** | Claude Sonnet 4.6 | 专家 | 架构设计和调试 |
| **Librarian** | Gemini 2.5 | 检索 | 文档和代码搜索 |
| **Explore** | Haiku | 快速 | 轻量级代码库搜索 |
| **Looker** | Vision | 多模态 | 视觉任务处理 |

### 3.2 Agent 类别路由

```yaml
categories:
  visual-engineering:
    description: "前端和 UI/UX 任务"
    default_model: gpt-5.4
    agents: [Sisyphus, Oracle]

  deep:
    description: "自主研究和执行"
    default_model: claude-opus-4.6
    agents: [Hephaestus, Sisyphus]

  quick:
    description: "单文件修改和 typo 修复"
    default_model: minimax
    agents: [Explore]

  ultrabrain:
    description: "困难逻辑和架构决策"
    default_model: gpt-5.4-xhigh
    agents: [Hephaestus, Oracle]
```

### 3.3 Agent 接口定义

```python
class Agent(ABC):
    """智能体基类"""

    @property
    def name(self) -> str:
        """智能体名称"""
        pass

    @property
    def category(self) -> str:
        """所属类别"""
        pass

    @property
    def default_model(self) -> str:
        """默认模型"""
        pass

    @abstractmethod
    async def plan(self, task: Task, context: Context) -> Plan:
        """规划任务步骤"""
        pass

    @abstractmethod
    async def execute(self, plan: Plan, context: Context) -> Result:
        """执行计划"""
        pass

    @abstractmethod
    async def delegate(self, sub_task: Task, agent_type: str) -> Result:
        """委托子任务"""
        pass


class Sisyphus(Agent):
    """主协调器"""

    async def delegate(self, task: Task, category: str) -> DelegateResult:
        """按类别选择最佳 Agent"""
        agent = self.router.select(category, task)
        return await agent.execute(task)


class Hephaestus(Agent):
    """自主执行器"""

    async def execute(self, goal: Goal, context: Context) -> Result:
        """端到端执行，无需逐步指导"""
        while not goal.is_complete:
            action = self.reasoner.choose_action(goal, context)
            result = await self.executor.run(action)
            goal.update(result)
            if result.needs_verification:
                await self.verifier.verify(result)
        return goal.final_result
```

### 3.4 多智能体通信

```python
@dataclass
class AgentMessage:
    """智能体间消息"""
    from_agent: str
    to_agent: str
    type: MessageType  # DELEGATE, RESULT, HEARTBEAT, INTERRUPT
    payload: dict
    priority: int = 0
    trace_id: str = None


class AgentBus:
    """智能体消息总线"""

    def __init__(self):
        self.subscribers: Dict[str, Agent] = {}
        self.message_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.running = False

    async def publish(self, message: AgentMessage):
        """发布消息"""
        await self.message_queue.put((message.priority, message))

    async def subscribe(self, agent_id: str, agent: Agent):
        """订阅消息"""
        self.subscribers[agent_id] = agent

    async def start(self):
        """启动消息循环"""
        self.running = True
        while self.running:
            priority, message = await self.message_queue.get()
            await self.dispatch(message)
```

---

## 4. 编排引擎

### 4.1 IntentGate

```python
class IntentGate:
    """
    意图分析与路由
    在执行前分析用户真实意图，防止字面误解
    """

    def __init__(self, classifier: ModelClient):
        self.classifier = classifier

    async def analyze(self, user_input: str, context: Context) -> IntentResult:
        """分析用户意图"""

        # 1. 提取显式指令
        explicit = self.parse_explicit(user_input)

        # 2. 隐式意图推断
        implicit = await self.classifier.analyze(
            prompt=f"""
            用户输入: "{user_input}"
            当前上下文: {context.summary}

            分析用户可能的真实意图，考虑:
            1. 可能的打字错误或表述不清
            2. 上下文相关的指代
            3. 常见的误用模式

            返回JSON:
            {{
                "primary_intent": "...",
                "alternative_intents": [...],
                "confidence": 0.0-1.0,
                "clarification_needed": true/false,
                "questions": ["如果需要澄清的问题"]
            }}
            """,
            model="claude-sonnet-4-6"
        )

        # 3. 冲突检测
        if self._has_conflict(explicit, implicit):
            return IntentResult(
                status="ambiguous",
                needs_clarification=True,
                questions=implicit.questions
            )

        return IntentResult(
            status="clear",
            primary_intent=implicit.primary_intent,
            routing=self._determine_routing(implicit)
        )

    def _determine_routing(self, intent: Intent) -> Routing:
        """确定路由策略"""
        if intent.confidence < 0.7:
            return Routing(to="Prometheus", mode="interview")
        elif intent.category == "quick":
            return Routing(to="Explore", mode="direct")
        elif intent.category == "deep":
            return Routing(to="Sisyphus", mode="orchestrate")
        else:
            return Routing(to="Sisyphus", mode="auto")
```

### 4.2 Ralph Loop

```python
class RalphLoop:
    """
    自循环执行器
    持续执行直到 100% 完成或达到最大迭代
    """

    def __init__(
        self,
        max_iterations: int = 100,
        completion_threshold: float = 0.95
    ):
        self.max_iterations = max_iterations
        self.completion_threshold = completion_threshold

    async def execute(
        self,
        task: Task,
        executor: Agent,
        verifier: Verifier = None
    ) -> LoopResult:
        """执行循环"""

        iteration = 0
        task_state = TaskState.PENDING
        results = []

        while iteration < self.max_iterations:
            iteration += 1

            # 检查前置条件
            if not await self._check_prerequisites(task):
                task_state = TaskState.BLOCKED
                break

            # 执行当前迭代
            result = await executor.execute(task)

            # 验证结果
            if verifier:
                verified = await verifier.verify(result)
                if not verified.success:
                    task.remaining_work.append(verified.feedback)
                    continue

            results.append(result)
            task.progress = self._calculate_progress(task, results)

            # 检查完成度
            if task.progress >= self.completion_threshold:
                task_state = TaskState.COMPLETED
                break

            # 检查是否卡住
            if self._is_stuck(results):
                task_state = TaskState.STUCK
                break

            # 重新规划剩余工作
            task = await self._replan(task, results)

        return LoopResult(
            iterations=iteration,
            state=task_state,
            progress=task.progress,
            results=results
        )

    def _is_stuck(self, results: List[Result]) -> bool:
        """检测是否陷入循环"""
        if len(results) < 3:
            return False

        # 检查最近3次结果是否相同
        recent = results[-3:]
        if all(r.similar_to(recent[0]) for r in recent):
            return True

        return False
```

### 4.3 Todo Enforcer

```python
class TodoEnforcer:
    """
    任务强制执行器
    自动重新激活空闲的 Agent 确保任务完成
    """

    def __init__(
        self,
        idle_timeout: timedelta = timedelta(minutes=5),
        maxreenact: int = 3
    ):
        self.idle_timeout = idle_timeout
        self.maxreenact = maxreenact
        self.pending_tasks: Dict[str, Task] = {}

    async def monitor(self, agents: List[Agent], bus: AgentBus):
        """监控 Agent 活动"""

        while True:
            await asyncio.sleep(30)  # 每30秒检查

            for agent in agents:
                if await self._is_idle(agent):
                    task = self.pending_tasks.get(agent.id)
                    if task and task.reenact_count < self.maxreenact:
                        await self._reenact(agent, task, bus)

    async def _reenact(
        self,
        agent: Agent,
        task: Task,
        bus: AgentBus
    ):
        """重新激活 Agent"""
        task.reenact_count += 1

        await bus.publish(AgentMessage(
            from_agent="TodoEnforcer",
            to_agent=agent.name,
            type=MessageType.INTERRUPT,
            payload={
                "action": "resume",
                "task": task,
                "reason": "idle_timeout"
            }
        ))
```

### 4.4 编排器主流程

```python
class Orchestrator:
    """主编排器"""

    def __init__(
        self,
        intent_gate: IntentGate,
        agent_registry: AgentRegistry,
        bus: AgentBus,
        ralph_loop: RalphLoop,
        todo_enforcer: TodoEnforcer
    ):
        self.intent_gate = intent_gate
        self.agents = agent_registry
        self.bus = bus
        self.ralph_loop = ralph_loop
        self.todo_enforcer = todo_enforcer

    async def execute_task(self, user_input: str, context: Context) -> Result:
        """执行用户任务"""

        # 1. 意图分析
        intent = await self.intent_gate.analyze(user_input, context)

        if intent.needs_clarification:
            return Result(
                type="clarification",
                questions=intent.questions
            )

        # 2. 路由选择
        routing = intent.routing

        # 3. 获取目标 Agent
        agent = self.agents.get(routing.to)

        # 4. 创建任务
        task = Task(
            description=intent.primary_intent,
            context=context,
            mode=routing.mode
        )

        # 5. 执行
        if "ultrawork" in user_input or intent.force_parallel:
            # 全部 Agent 并行
            return await self._ultrawork(task)
        elif routing.mode == "interview":
            return await self._interview_mode(task)
        else:
            # Ralph Loop 执行
            return await self.ralph_loop.execute(task, agent)

    async def _ultrawork(self, task: Task) -> Result:
        """全速执行模式 - 所有 Agent 并行"""

        # 启动所有专业 Agent
        coros = []
        for agent in self.agents.get_all():
            coros.append(self.ralph_loop.execute(task, agent))

        # 并行执行
        results = await asyncio.gather(*coros, return_exceptions=True)

        # 汇总结果
        return self._aggregate_results(results)

    async def _interview_mode(self, task: Task) -> Result:
        """面试模式 - Prometheus 规划"""

        prometheus = self.agents.get("Prometheus")

        # Prometheus 识别范围和歧义
        plan = await prometheus.plan(task)

        # 如果需要澄清
        if plan.needs_clarification:
            return Result(
                type="clarification",
                questions=plan.questions
            )

        # 执行验证后的计划
        return await self.ralph_loop.execute(plan, self.agents.get("Sisyphus"))
```

---

## 5. 工具系统

### 5.1 Hash 锚定编辑

```python
class HashAnchorEdit:
    """
    Hash 锚定编辑工具
    通过内容哈希验证编辑安全性
    """

    async def read(self, file_path: str) -> FileContent:
        """读取文件并生成 Hash"""

        content = await aio.read(file_path)
        lines = content.splitlines()

        # 为每行生成哈希
        hashed_lines = []
        for i, line in enumerate(lines, 1):
            line_hash = self._hash_content(line)
            hashed_lines.append(HashedLine(
                number=i,
                content=line,
                hash=line_hash
            ))

        return FileContent(
            path=file_path,
            lines=hashed_lines,
            total_hash=self._hash_content(content)
        )

    async def edit(
        self,
        file_path: str,
        edits: List[EditRequest]
    ) -> EditResult:
        """执行带哈希验证的编辑"""

        # 读取当前文件
        current = await self.read(file_path)

        # 构建行号到哈希的映射
        line_hashes = {line.number: line.hash for line in current.lines}

        validated_edits = []

        for edit in edits:
            # 验证锚点哈希
            if edit.anchor_hash:
                actual_hash = line_hashes.get(edit.line_number)
                if actual_hash != edit.anchor_hash:
                    return EditResult(
                        success=False,
                        error=f"Hash mismatch at line {edit.line_number}. "
                              f"Expected {edit.anchor_hash}, got {actual_hash}. "
                              f"File may have been modified."
                    )

            validated_edits.append(edit)

        # 执行编辑
        new_lines = self._apply_edits(current.lines, validated_edits)

        # 写入
        await aio.write(file_path, '\n'.join(line.content for line in new_lines))

        # 验证完整性
        new_content = await self.read(file_path)
        if new_content.total_hash != current.total_hash:
            # 通知冲突
            await self._notify_conflict(file_path, current, new_content)

        return EditResult(success=True, new_hash=new_content.total_hash)


@dataclass
class EditRequest:
    """编辑请求"""
    line_number: int
    anchor_hash: str  # 编辑前的行哈希
    new_content: str
    end_line: int = None  # 用于范围编辑


@dataclass
class HashedLine:
    """带哈希的行"""
    number: int
    content: str
    hash: str


# 编辑请求示例
edit_request = EditRequest(
    line_number=11,
    anchor_hash="VK|3f4a9b2c",  # 来自之前读取的 Hash
    new_content="def hello():\n    return 'Hello, World!'"
)
```

### 5.2 内置工具

```python
class BuiltinTools:
    """内置工具注册"""

    TOOLS = [
        # 文件操作
        ("Read", "读取文件内容", ReadTool()),
        ("Write", "写入文件", WriteTool()),
        ("Edit", "带哈希验证的编辑", HashAnchorEdit()),
        ("Glob", "文件模式匹配", GlobTool()),
        ("Grep", "内容搜索", GrepTool()),

        # Bash 操作
        ("Bash", "执行 Shell 命令", BashTool()),
        ("InteractiveBash", "交互式 Bash", InteractiveBashTool()),

        # LSP 工具
        ("lsp_rename", "LSP 重命名", LSPRenameTool()),
        ("lsp_goto_definition", "跳转到定义", LSPGotoTool()),
        ("lsp_find_references", "查找引用", LSPFindRefsTool()),
        ("lsp_diagnostics", "诊断信息", LSPDiagnosticsTool()),

        # 网络
        ("WebFetch", "获取网页", WebFetchTool()),
        ("WebSearch", "搜索网络", WebSearchTool()),

        # Git
        ("Git", "Git 操作", GitTool()),
    ]
```

### 5.3 LSP 集成

```python
class LSPBridge:
    """Language Server Protocol 桥接"""

    def __init__(self, lsp_servers: Dict[str, str]):
        """
        Args:
            lsp_servers: 语言 -> 服务器命令的映射
            e.g., {"python": "pyright", "typescript": "tsserver"}
        """
        self.lsp_servers = lsp_servers
        self.clients: Dict[str, LSPClient] = {}

    async def initialize(self, workspace_path: str):
        """初始化 LSP 客户端"""
        for lang, server_cmd in self.lsp_servers.items():
            client = LSPClient(
                command=server_cmd,
                workspace=workspace_path
            )
            await client.start()
            self.clients[lang] = client

    async def rename(self, lang: str, position: Position, new_name: str) -> List[TextEdit]:
        """LSP 重命名"""
        client = self.clients.get(lang)
        if not client:
            raise LSPAvailableError(f"LSP for {lang} not available")
        return await client.rename(position, new_name)

    async def find_references(self, lang: str, position: Position) -> List[Location]:
        """查找引用"""
        return await self.clients[lang].find_references(position)

    async def get_diagnostics(self, lang: str, document: str) -> List[Diagnostic]:
        """获取诊断信息"""
        return await self.clients[lang].diagnostics(document)

    async def shutdown(self):
        """关闭所有 LSP 客户端"""
        for client in self.clients.values():
            await client.shutdown()
```

---

## 6. 安全编辑机制

### 6.1 冲突检测流程

```
┌──────────────────────────────────────────────────────────────────┐
│                        编辑流程                                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. Read(file) ─────► 返回 FileContent + 每行 Hash               │
│                              │                                    │
│                              ▼                                    │
│  2. 生成 EditRequest ──► 需要 anchor_hash                         │
│                              │                                    │
│                              ▼                                    │
│  3. Edit(request) ────► 验证 anchor_hash == 当前行 hash          │
│                              │                                    │
│                     ┌────────┴────────┐                          │
│                     │  匹配?           │                          │
│                     └────────┬────────┘                          │
│                    是          │ 否                               │
│                     │          ▼                                  │
│                     │    ┌────────────────┐                       │
│                     │    │  编辑被拒绝     │                       │
│                     │    │  Hash mismatch │                       │
│                     │    │  error 返回    │                       │
│                     │    └────────────────┘                       │
│                     ▼                                             │
│  4. Apply edit ────► 更新文件                                     │
│                              │                                    │
│                              ▼                                    │
│  5. Verify ─────────► 验证文件完整性                               │
│                              │                                    │
│                     ┌────────┴────────┐                           │
│                     │  完整?          │                           │
│                     └────────┬────────┘                           │
│                    是          │ 否                              │
│                     │          ▼                                 │
│                     │    ┌────────────────┐                       │
│                     │    │  通知冲突      │                       │
│                     │    │  触发解决流程  │                       │
│                     │    └────────────────┘                       │
│                     ▼                                             │
│  6. Return Result ◄─── 成功/失败                                  │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### 6.2 并发安全

```python
class EditCoordinator:
    """编辑协调器 - 处理并发编辑"""

    def __init__(self):
        self.file_locks: Dict[str, asyncio.Lock] = {}
        self.pending_edits: Dict[str, List[EditRequest]] = {}

    async def acquire_lock(self, file_path: str) -> asyncio.Lock:
        """获取文件锁"""
        if file_path not in self.file_locks:
            self.file_locks[file_path] = asyncio.Lock()
        return self.file_locks[file_path]

    async def submit_edit(self, file_path: str, edit: EditRequest) -> EditResult:
        """提交编辑请求"""

        lock = await self.acquire_lock(file_path)

        async with lock:
            # 读取当前状态
            content = await hash_edit.read(file_path)

            # 检查是否与待处理编辑冲突
            pending = self.pending_edits.get(file_path, [])
            for p_edit in pending:
                if self._conflicts(edit, p_edit, content):
                    return EditResult(
                        success=False,
                        error="Conflicts with pending edit"
                    )

            # 添加到待处理
            pending.append(edit)
            self.pending_edits[file_path] = pending

            # 执行编辑
            result = await hash_edit.edit(file_path, [edit])

            # 移除待处理
            pending.remove(edit)

            return result
```

---

## 7. 技能系统

### 7.1 Skill 定义格式

```markdown
# skill: playwright
name: playwright
description: Browser automation using Playwright
category: testing
version: 1.0.0
author: team

# MCP Server 配置 (可选)
mcp:
  type: stdio
  command: npx
  args: ["-y", "@playwright/mcp@latest"]

# 触发条件
triggers:
  - "test * in browser"
  - "automate * in browser"
  - "scrape * website"

# Agent 提示
system_prompt: |
  You are a browser automation expert using Playwright.

  Capabilities:
  - Navigate to URLs
  - Fill forms and click buttons
  - Take screenshots
  - Extract page content
  - Handle dynamic content

  Best practices:
  - Always use explicit waits
  - Handle errors gracefully
  - Clean up resources after use

# 默认参数
defaults:
  headless: true
  timeout: 30000

# 工具限制
allowed_tools:
  - Bash
  - Read
  - Write

denied_tools:
  - Edit
```

### 7.2 Skill 生命周期

```python
class SkillLifecycle:
    """Skill 生命周期管理"""

    def __init__(self, skill_dir: Path):
        self.skill_dir = skill_dir
        self.loaded_skills: Dict[str, Skill] = {}
        self.active_mcps: Dict[str, MCPConnection] = {}

    async def load_skill(self, skill_name: str) -> Skill:
        """按需加载 Skill"""
        if skill_name in self.loaded_skills:
            return self.loaded_skills[skill_name]

        # 读取 Skill 定义
        skill_path = self._find_skill(skill_name)
        skill = await self._parse_skill(skill_path)

        # 启动关联的 MCP
        if skill.mcp:
            mcp = await self.mcp_client.connect(skill.mcp)
            self.active_mcps[skill_name] = mcp

        self.loaded_skills[skill_name] = skill
        return skill

    async def unload_skill(self, skill_name: str):
        """卸载 Skill"""
        if skill_name in self.loaded_skills:
            # 关闭 MCP 连接
            if skill_name in self.active_mcps:
                await self.active_mcps[skill_name].disconnect()
                del self.active_mcps[skill_name]

            del self.loaded_skills[skill_name]

    async def get_tools(self, skill_name: str) -> List[Tool]:
        """获取 Skill 提供的工具"""
        skill = await self.load_skill(skill_name)

        tools = []
        # 内置工具
        tools.extend(skill.builtin_tools)

        # MCP 工具
        if skill_name in self.active_mcps:
            mcp_tools = await self.active_mcps[skill_name].list_tools()
            tools.extend(mcp_tools)

        return tools
```

### 7.3 内置 Skills

| Skill | 用途 | MCP |
|-------|------|-----|
| `playwright` | 浏览器自动化 | @playwright/mcp |
| `git-master` | Git 高级操作 | 无 |
| `frontend-ui-ux` | UI/UX 开发 | 无 |
| `exa-search` | 网络搜索 | Exa MCP |
| `context7` | 官方文档 | Context7 MCP |
| `grep-app` | GitHub 代码搜索 | Grep.app MCP |

### 7.4 Git Master Skill

```markdown
# skill: git-master
name: git-master
description: Advanced Git operations with atomic commits and rebase

triggers:
  - "atomic commit"
  - "rebase safely"
  - "interactive rebase"

system_prompt: |
  You are a Git master. You specialize in:

  1. Atomic Commits
  - Group related changes into single commits
  - Write clear, conventional commit messages
  - Never commit half-done work

  2. Safe Rebase
  - Use --interactive for complex rewrites
  - Resolve conflicts carefully
  - Test after every rebase

  3. Branch Management
  - Create feature branches from clean points
  - Delete merged branches
  - Protect main/master

  Commands:
  - git add -p (patch staging)
  - git commit --amend (modify last)
  - git rebase -i (interactive)
  - git merge --no-ff
```

---

## 8. 多模型支持

### 8.1 模型网关

```python
class ModelGateway:
    """
    多模型网关
    支持 Claude, OpenAI, Gemini, Groq, AWS Bedrock 等
    """

    PROVIDERS = {
        "anthropic": AnthropicProvider,
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
        "groq": GroqProvider,
        "bedrock": BedrockProvider,
        "local": LocalProvider,
    }

    def __init__(self, config: ModelConfig):
        self.providers: Dict[str, ModelProvider] = {}
        self.routing = ModelRouter()
        self._init_providers(config)

    def _init_providers(self, config: ModelConfig):
        """初始化所有provider"""
        for name, provider_class in self.PROVIDERS.items():
            if provider_config := config.get(name):
                self.providers[name] = provider_class(provider_config)

    async def complete(
        self,
        messages: List[Message],
        model: str = None,
        **kwargs
    ) -> Response:
        """统一接口"""
        # 解析模型引用
        provider, model_name = self.routing.resolve(model)

        # 调用对应provider
        return await self.providers[provider].complete(
            messages=messages,
            model=model_name,
            **kwargs
        )


@dataclass
class ModelConfig:
    """模型配置"""
    anthropic: ProviderConfig
    openai: ProviderConfig
    gemini: ProviderConfig
    groq: ProviderConfig
    bedrock: ProviderConfig
    local: ProviderConfig


@dataclass
class ProviderConfig:
    """Provider 配置"""
    api_key: str
    base_url: str = None
    models: List[str] = None
    default_model: str = None
```

### 8.2 模型选择策略

```python
class ModelRouter:
    """
    模型路由
    根据任务类型选择最佳模型
    """

    ROUTING_RULES = {
        # (category, complexity) -> (provider, model)
        ("planning", "high"): ("anthropic", "claude-opus-4-6"),
        ("planning", "medium"): ("anthropic", "claude-sonnet-4-6"),
        ("reasoning", "high"): ("openai", "gpt-5.4"),
        ("reasoning", "medium"): ("anthropic", "claude-sonnet-4-6"),
        ("speed", "low"): ("groq", "llama-3.3-70b"),
        ("creative", "any"): ("gemini", "gemini-2.5-pro"),
        ("vision", "any"): ("anthropic", "claude-sonnet-4-6"),
    }

    def resolve(self, model: str = None, context: dict = None) -> tuple:
        """解析模型引用"""

        # 显式指定
        if model:
            return self._parse_model_string(model)

        # 上下文推断
        if context:
            category = context.get("category", "general")
            complexity = context.get("complexity", "medium")

            key = (category, complexity)
            if key in self.ROUTING_RULES:
                return self.ROUTING_RULES[key]

            # 回退到通用
            return ("anthropic", "claude-sonnet-4-6")

        # 默认
        return ("anthropic", "claude-sonnet-4-6")
```

### 8.3 支持的模型列表

| Provider | 模型 | 用途 |
|----------|------|------|
| **Anthropic** | claude-opus-4-6 | 复杂规划、架构 |
| | claude-sonnet-4-6 | 日常任务 |
| | claude-haiku-4-5 | 快速搜索 |
| **OpenAI** | gpt-5.4 | 深度推理 |
| | gpt-4.1 | 代码生成 |
| **Google** | gemini-2.5-pro | 创意任务 |
| | gemini-2.5-flash | 快速响应 |
| **Groq** | llama-3.3-70b | 超快速任务 |
| **AWS Bedrock** | Claude on Bedrock | 企业部署 |
| **Local** | Ollama / vLLM | 本地推理 |

---

## 9. 会话与持久化

### 9.1 SQLite 会话存储

```python
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

class SQLiteSessionStore:
    """SQLite 会话存储"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                project_path TEXT NOT NULL,
                name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                model TEXT,
                metadata JSON
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );

            CREATE TABLE IF NOT EXISTS agent_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                state JSON,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );

            CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages(session_id);
            CREATE INDEX IF NOT EXISTS idx_agent_states_session
                ON agent_states(session_id);
        """)
        conn.close()

    async def create_session(self, project: str, name: str = None) -> Session:
        """创建会话"""
        session = Session(
            id=str(uuid4()),
            project_path=project,
            name=name,
            created_at=datetime.now()
        )

        async with self._transaction() as conn:
            conn.execute(
                """INSERT INTO sessions (id, project_path, name)
                   VALUES (?, ?, ?)""",
                (session.id, session.project_path, session.name)
            )

        return session

    async def add_message(self, session_id: str, role: str, content: str):
        """添加消息"""
        async with self._transaction() as conn:
            conn.execute(
                """INSERT INTO messages (session_id, role, content)
                   VALUES (?, ?, ?)""",
                (session_id, role, content)
            )
            conn.execute(
                """UPDATE sessions SET updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (session_id,)
            )

    async def get_messages(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Message]:
        """获取消息"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            """SELECT * FROM messages
               WHERE session_id = ?
               ORDER BY created_at DESC
               LIMIT ? OFFSET ?""",
            (session_id, limit, offset)
        )
        rows = cursor.fetchall()
        conn.close()
        return [Message(**dict(row)) for row in rows]

    async def save_agent_state(
        self,
        session_id: str,
        agent_name: str,
        state: dict
    ):
        """保存 Agent 状态"""
        async with self._transaction() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO agent_states
                   (session_id, agent_name, state, updated_at)
                   VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
                (session_id, agent_name, json.dumps(state))
            )

    async def compact_session(self, session_id: str) -> Session:
        """压缩会话 - 总结旧消息"""
        messages = await self.get_messages(session_id, limit=1000)

        # 使用模型总结旧消息
        summary = await self._summarize(messages[:-10])

        async with self._transaction() as conn:
            # 删除旧消息保留最后10条
            conn.execute(
                """DELETE FROM messages
                   WHERE session_id = ? AND id NOT IN
                   (SELECT id FROM messages
                    WHERE session_id = ?
                    ORDER BY created_at DESC LIMIT 10)""",
                (session_id, session_id)
            )

            # 添加总结消息
            conn.execute(
                """INSERT INTO messages (session_id, role, content)
                   VALUES (?, 'system', ?)""",
                (session_id, f"[Session compacted: {summary}]")
            )

        return await self.get_session(session_id)
```

### 9.2 多会话管理

```python
class MultiSessionManager:
    """多会话管理器"""

    def __init__(self, store: SQLiteSessionStore):
        self.store = store
        self.active_sessions: Dict[str, Session] = {}
        self.current_session_id: str = None

    async def create(
        self,
        project: str,
        name: str = None,
        model: str = None
    ) -> Session:
        """创建新会话"""
        session = await self.store.create_session(project, name)
        session.model = model
        self.active_sessions[session.id] = session
        self.current_session_id = session.id
        return session

    async def switch(self, session_id: str) -> Session:
        """切换会话"""
        if session_id not in self.active_sessions:
            session = await self.store.get_session(session_id)
            self.active_sessions[session_id] = session

        self.current_session_id = session_id
        return self.active_sessions[session_id]

    async def list_project_sessions(
        self,
        project: str,
        limit: int = 20
    ) -> List[SessionSummary]:
        """列出项目的会话"""
        conn = sqlite3.connect(self.store.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            """SELECT id, name, created_at, updated_at, model
               FROM sessions
               WHERE project_path = ?
               ORDER BY updated_at DESC
               LIMIT ?""",
            (project, limit)
        )
        rows = cursor.fetchall()
        conn.close()
        return [SessionSummary(**dict(row)) for row in rows]
```

---

## 10. TUI 界面设计

### 10.1 TUI 布局 (Bubble Tea)

```go
// TUI 组件结构
type Model struct {
    // 状态
    sessions    []SessionListItem
    currentIdx  int
    messages    []MessageView
    agentStatus []AgentStatusView
    fileTree    *FileTree

    // 组件
    sessionList *list.Model
    chatView    *ChatView
    agentView   *AgentStatusView
    fileTree    *filetree.Model

    // 状态
    editing     bool
    mode        InputMode // normal, insert, command
}

// 主要视图
const (
    ViewSession List = iota
    ViewChat
    ViewAgents
    ViewFiles
)
```

### 10.2 键盘快捷键

| 快捷键 | 模式 | 功能 |
|--------|------|------|
| `Ctrl+O` | Normal | 打开命令面板 |
| `Ctrl+K` | Normal | 打开快速命令 |
| `Ctrl+S` | Normal | 保存当前会话 |
| `Ctrl+N` | Normal | 新建会话 |
| `Ctrl+W` | Normal | 关闭当前会话 |
| `Tab` | Normal | 切换视图 |
| `j/k` | Normal | 上下导航 |
| `Enter` | Normal | 选择 |
| `i` | Normal | 进入插入模式 |
| `Esc` | Insert | 返回普通模式 |
| `Ctrl+C` | Insert | 取消输入 |
| `Ctrl+Enter` | Insert | 提交 |
| `:` | Normal | 进入命令模式 |

### 10.3 视图组件

```python
@dataclass
class TUIComponents:
    """TUI 组件定义"""

    session_list: Component
    """
    会话列表视图
    - 显示所有会话
    - 显示最后更新时间
    - 显示会话名称/摘要
    """

    message_view: Component
    """
    消息视图
    - Markdown 渲染
    - 代码高亮
    - 差异显示
    """

    agent_status: Component
    """
    Agent 状态
    - 当前活跃 Agent
    - 执行进度
    - Token 使用
    """

    file_tree: Component
    """
    文件树
    - Git 状态
    - LSP 诊断
    - 快速跳转
    """

    command_palette: Component
    """
    命令面板
    - 模糊搜索
    - 历史命令
    - Skill 触发
    """
```

---

## 11. LSP 集成

### 11.1 支持的语言

| 语言 | LSP 服务器 | 安装命令 |
|------|-----------|---------|
| Python | pyright | `pip install pyright` |
| TypeScript | tsserver | 内置 (typescript) |
| Go | gopls | `gop install golang.org/x/tools/gopls` |
| Rust | rust-analyzer | `rustup component add rust-analyzer` |
| Java | jdtls | Eclipse JDT |
| C/C++ | clangd | `apt install clangd` |
| Ruby | solargraph | `gem install solargraph` |

### 11.2 LSP 工具封装

```python
class LSPSupportedTools:
    """LSP 支持的工具"""

    @lsp_tool("lsp_rename")
    async def rename(
        file_path: str,
        old_name: str,
        new_name: str,
        language: str
    ) -> RenameResult:
        """
        重命名符号
        自动更新所有引用
        """
        client = lsp_bridge.clients[language]
        symbol = await client.find_symbol(old_name, file_path)
        edits = await client.rename_symbol(symbol, new_name)
        return RenameResult(edits=edits)

    @lsp_tool("lsp_goto_definition")
    async def goto_definition(
        file_path: str,
        position: Position,
        language: str
    ) -> Location:
        """跳转到定义"""
        return await lsp_bridge.clients[language].goto_definition(
            file_path, position
        )

    @lsp_tool("lsp_find_references")
    async def find_references(
        file_path: str,
        position: Position,
        language: str
    ) -> List[Location]:
        """查找引用"""
        return await lsp_bridge.clients[language].find_references(
            file_path, position
        )

    @lsp_tool("lsp_diagnostics")
    async def get_diagnostics(
        file_path: str,
        language: str
    ) -> List[Diagnostic]:
        """获取诊断"""
        return await lsp_bridge.clients[language].diagnostics(file_path)
```

---

## 12. 配置系统

### 12.1 配置优先级

```
命令行参数
    │
    ▼
项目级 .ai.json / .ai.jsonc
    │
    ▼
用户级 ~/.config/ai/ai.json / ~/.config/ai/ai.jsonc
    │
    ▼
系统级 /etc/ai/ai.json
```

### 12.2 配置结构 (JSONC)

```jsonc
{
  // 注释支持
  "version": "2.0",

  // 模型配置
  "models": {
    "default": "anthropic/claude-sonnet-4-6",
    "providers": {
      "anthropic": {
        "api_key": "${ANTHROPIC_API_KEY}",
        "base_url": "https://api.anthropic.com"
      },
      "openai": {
        "api_key": "${OPENAI_API_KEY}"
      }
    },
    "routing": {
      "quick": "groq/llama-3.3-70b",
      "deep": "anthropic/claude-opus-4-6",
      "reasoning": "openai/gpt-5.4"
    }
  },

  // Agent 配置
  "agents": {
    "sisyphus": {
      "model": "claude-opus-4-6",
      "max_turns": 200
    },
    "prometheus": {
      "model": "kimi-k2.5"
    },
    "hephaestus": {
      "model": "gpt-5.4"
    }
  },

  // LSP 配置
  "lsp": {
    "python": "pyright",
    "typescript": "tsserver",
    "go": "gopls"
  },

  // MCP 服务器
  "mcp_servers": {
    "exa": {
      "type": "http",
      "url": "https://api.exa.ai/mcp"
    },
    "filesystem": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem"]
    }
  },

  // Skills
  "skills": {
    "dir": [".ai/skills", "~/.config/ai/skills"]
  },

  // 安全
  "security": {
    "allowed_tools": ["Read", "Edit", "Write", "Bash"],
    "denied_patterns": ["rm -rf /", "drop database"],
    "confirm_destructive": true
  },

  // 界面
  "ui": {
    "theme": "dark",
    "tui": true,
    "color_scheme": "monokai"
  }
}
```

---

## 13. CLI 设计

### 13.1 命令结构

```
ai [command] [options]

# 会话命令
ai                          # 交互模式
ai "task"                   # 带任务启动
ai -p "query"              # 非交互模式
ai -c                       # 继续最近会话
ai -r <id/name>            # 恢复指定会话
ai sessions list            # 列出会话
ai sessions delete <id>    # 删除会话

# Agent 命令
ai ulw [task]              # ultrawork 全速执行
ai ulw-loop [task]         # Ralph Loop 执行
ai start-work [task]       # 面试模式规划

# Agent 管理
ai agents list             # 列出 Agent
ai agent <name> [task]     # 调用指定 Agent

# 配置命令
ai config edit             # 编辑配置
ai config show             # 显示配置
ai doctor                  # 诊断检查

# MCP 命令
ai mcp add|list|remove
ai mcp search              # 搜索 MCP 服务器

# Skill 命令
ai skill install <name>
ai skill list
ai skill search

# 开发命令
ai init-deep               # 生成 AGENTS.md
ai dev shell               # 调试 shell
```

### 13.2 核心 Flag

| Flag | 说明 |
|------|------|
| `-p, --print` | 非交互模式 |
| `-c, --continue` | 继续会话 |
| `-r, --resume <id>` | 恢复会话 |
| `-n, --name <name>` | 会话名称 |
| `--model <model>` | 指定模型 |
| `--no-tui` | 禁用 TUI |
| `--debug` | 调试模式 |
| `--config <path>` | 指定配置 |

---

## 14. 实现路线图

### P0 - 核心 (MVP)

- [ ] CLI 基础框架
- [ ] 模型网关 (至少 1 个 Provider)
- [ ] 基础 Agent (Sisyphus)
- [ ] 工具注册表 (Read/Edit/Write/Bash/Grep)
- [ ] SQLite 会话存储
- [ ] Hash 锚定编辑

### P1 - 智能体 (V1)

- [ ] 多 Agent 注册表
- [ ] IntentGate 意图分析
- [ ] Prometheus 规划 Agent
- [ ] Hephaestus 执行 Agent
- [ ] Agent 间通信总线
- [ ] Ralph Loop 执行器

### P2 - 工具 (V1)

- [ ] MCP Client 实现
- [ ] LSP Bridge 集成
- [ ] 内置 Skills (git-master, playwright)
- [ ] Skill 按需加载

### P3 - 界面 (V1)

- [ ] Bubble Tea TUI
- [ ] VS Code 扩展
- [ ] JetBrains 插件

### P4 - 高级 (V2)

- [ ] Todo Enforcer
- [ ] 多 Provider 路由
- [ ] 插件系统
- [ ] 团队协作

---

## 附录: 与竞品对比

| 功能 | Claude Code | OpenCode/Crush | oh-my-openagent | 本产品 V2 |
|------|-------------|----------------|-----------------|----------|
| **架构** | 单 Agent | 单 Agent | 多 Agent | 多 Agent 编排 |
| **模型** | 仅 Anthropic | 多 Provider | 多 Provider | 多 Provider + 智能路由 |
| **TUI** | 基础终端 | Bubble Tea | 基础 | Bubble Tea |
| **编辑安全** | 无 | 无 | Hash 锚定 | Hash 锚定 |
| **会话存储** | JSON Lines | SQLite | JSON | SQLite |
| **LSP** | 无 | 有 | 有 | 有 |
| **意图理解** | 基础 | 无 | IntentGate | IntentGate |
| **自循环** | 无 | 无 | Ralph Loop | Ralph Loop |
| **多模型协同** | 无 | 无 | 有 | 有 |
| **Skill MCP** | 无 | 无 | 有 | 有 |

---

*文档版本: 2.0*
*设计模式: 多智能体编排*
*生成日期: 2026-03-28*
