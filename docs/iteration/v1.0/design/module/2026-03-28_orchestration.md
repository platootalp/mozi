# Orchestration Module (编排层)

> **引用**: 本文档使用的共享类型定义请参考 [2026-03-28_shared_types.md](./2026-03-28_shared_types.md)

## 文档信息

| 字段 | 内容 |
|------|------|
| 模块名称 | Orchestration |
| 职责 | 意图识别、任务编排、自循环执行 |
| 路径 | `mozi/orchestration/` |
| 文档版本 | v1.1 |
| 状态 | 规划中 |
| 创建日期 | 2026-03-28 |

---

## 1. 模块概述

Orchestration 模块是系统的核心编排层，负责协调各个 Agent 完成用户任务。通过 IntentGate 进行意图识别，通过 RalphLoop 实现自循环执行，通过 TodoEnforcer 处理任务卡死恢复。

### 1.1 核心职责

- 意图识别与路由
- 任务复杂度评估
- Agent 调度与协调
- 自循环执行控制
- 任务卡死检测与恢复

### 1.2 差异化特性

| 特性 | 说明 |
|------|------|
| 意图冲突检测 | 显式/隐式意图冲突时请求用户澄清 |
| 自循环执行 | RalphLoop 确保任务 100% 完成 |
| 卡死恢复 | TodoEnforcer 自动重新激活 |
| 复杂度路由 | 根据复杂度选择不同执行策略 |

---

## 2. 模块结构

```
mozi/orchestration/
├── __init__.py
├── intent_gate.py        # 意图识别与路由
├── ralph_loop.py         # 自循环执行器
├── todo_enforcer.py      # 任务强制执行器
├── complexity_assessor.py # 复杂度评估器
├── task_router.py        # 任务路由器
└── plugins/             # 可插拔组件
    ├── __init__.py
    └── strategies/      # 执行策略
        ├── simple.py    # SIMPLE 策略
        ├── medium.py    # MEDIUM 策略
        └── complex.py   # COMPLEX 策略
```

---

## 3. 组件详情

### 3.1 IntentGate

**职责**: 意图识别与路由

**核心功能点**:

| 功能 | 说明 |
|------|------|
| 显式指令解析 | 解析用户明确指定的指令 |
| 隐式意图推断 | 通过 LLM 分析用户真实意图 |
| 冲突检测 | 检测显式/隐式意图冲突 |
| 路由决策 | 根据意图选择合适的 Agent |

**意图类型**:

| 意图 | Agent | 说明 |
|------|-------|------|
| `EXPLORE` | Explorer | 探索代码库结构 |
| `CODE` | Builder | 编写或修改代码 |
| `REVIEW` | Reviewer | 审查代码质量 |
| `PLAN` | Planner | 规划复杂任务 |
| `RESEARCH` | Researcher | 技术研究 |

**接口定义**:

```python
class IntentGate:
    async def analyze(self, user_input: str, context: Context) -> IntentResult:
        """分析用户输入，识别意图"""
        # 1. 显式指令解析
        explicit = self.parse_explicit(user_input)

        # 2. 隐式意图推断
        implicit = await self.model.analyze(
            messages=[SystemMessage(prompt=INTENT_ANALYSIS_PROMPT), UserMessage(user_input)]
        )

        # 3. 冲突检测
        if self._has_conflict(explicit, implicit):
            return IntentResult(
                status=IntentStatus.AMBIGUOUS,
                needs_clarification=True,
                explicit=explicit,
                implicit=implicit
            )

        # 4. 确定路由
        routing = self._determine_routing(implicit)
        return IntentResult(status=IntentStatus.CLEAR, routing=routing)

    EXPLICIT_PATTERNS: Dict[str, Intent] = {
        r"^(explore|查看|了解)\s": Intent.EXPLORE,
        r"^(write|create|添加|新建)\s": Intent.CODE,
        r"^(review|审查|检查)\s": Intent.REVIEW,
        r"^(plan|规划)\s": Intent.PLAN,
        r"^(research|研究|调研)\s": Intent.RESEARCH,
    }

    def parse_explicit(self, user_input: str) -> Optional[Intent]:
        """解析显式指令"""
        for pattern, intent in EXPLICIT_PATTERNS.items():
            if re.search(pattern, user_input, re.IGNORECASE):
                return intent
        return None
```

### 3.2 RalphLoop

**职责**: 自循环执行器，确保任务 100% 完成

**核心功能点**:

| 功能 | 说明 |
|------|------|
| 循环执行 | 持续调用 Agent 直到任务完成 |
| 进度检测 | 检测任务进度 (progress >= 0.95) |
| 卡死检测 | 检测任务是否陷入循环 |
| 强制恢复 | 卡死时触发 TodoEnforcer |

**接口定义**:

```python
class RalphLoop:
    """
    自循环执行器 - 负责多轮迭代直到任务完成

    设计原则:
    - RalphLoop 每次迭代调用 agent.run()，这是单次 ReAct 迭代
    - Agent.run() 返回 AgentRunResult，包含 progress 字段
    - RalphLoop 根据 progress 判断是否继续迭代
    - TodoEnforcer 处理卡死恢复

    与 Agent 的职责边界:
    - RalphLoop: 循环控制、进度检测、卡死恢复
    - Agent.run(): 单次 think + execute，返回 progress
    """

    def __init__(
        self,
        todo_enforcer: TodoEnforcer,
        max_iterations: int = 30,
        progress_threshold: float = 0.95,
    ):
        self.todo_enforcer = todo_enforcer
        self.max_iterations = max_iterations
        self.progress_threshold = progress_threshold

    async def execute(self, task: Task, executor: Agent) -> LoopResult:
        """
        自循环执行任务

        每次迭代调用 agent.run(task, context)，这是单次 ReAct 迭代。
        循环持续直到:
        - progress >= progress_threshold (任务完成)
        - 达到 max_iterations 上限
        - is_stuck() 检测到卡死
        """
        iteration = 0
        results = []

        while not task.is_complete and iteration < self.max_iterations:
            # 调用 agent.run() 执行单次 ReAct 迭代
            # agent.run() 内部调用 think() + execute()
            agent_result = await executor.run(task, context)
            results.append(agent_result)

            # 检查进度 - agent.run() 返回的 AgentRunResult 包含 progress
            if agent_result.progress >= self.progress_threshold:
                task.is_complete = True
                return LoopResult(
                    state=LoopState.COMPLETED,
                    iterations=iteration + 1,
                    final_result=result
                )

            # 检查是否卡死
            if self._is_stuck(results):
                await self.todo_enforcer.reenact(task)
                results.clear()  # 重置历史

            iteration += 1

        if iteration >= self.max_iterations:
            return LoopResult(
                state=LoopState.MAX_ITERATIONS_EXCEEDED,
                iterations=iteration,
                final_result=results[-1] if results else None
            )

        return LoopResult(
            state=LoopState.COMPLETED,
            iterations=iteration,
            final_result=results[-1] if results else None
        )

    def _is_stuck(self, results: List[AgentRunResult]) -> bool:
        """
        检测是否卡死（连续3次 agent.run() 结果相同）

        卡死条件:
        - 连续3次返回相同的 tool_used
        - 且内容也相同

        这表明 Agent 在重复相同的行动而没有进展。
        """
        if len(results) < 3:
            return False
        recent = results[-3:]
        return (
            recent[0].thought.tool_used == recent[1].thought.tool_used == recent[2].thought.tool_used
            and recent[0].result.content == recent[1].result.content == recent[2].result.content
        )
```

### 3.3 TodoEnforcer

**职责**: 监控空闲 Agent，重新激活卡住的任务

**核心功能点**:

| 功能 | 说明 |
|------|------|
| 上下文清空 | 清空当前上下文，重新开始 |
| 状态重置 | 将任务状态重置为 INITIAL |
| 检查点恢复 | 从上一次的检查点恢复 |
| 重试计数 | 跟踪重试次数 |

**接口定义**:

```python
class TodoEnforcer:
    def __init__(self, max_reenactments: int = 3):
        self.max_reenactments = max_reenactments

    async def reenact(self, task: Task) -> ReenactResult:
        """重新激活任务"""
        # 增加重试计数
        task.reenactment_count += 1

        if task.reenactment_count > self.max_reenactments:
            return ReenactResult(
                success=False,
                reason="max_reenactments_exceeded"
            )

        # 清空当前上下文
        task.clear_context()

        # 重置任务状态
        task.set_state(TaskState.INITIAL)

        # 恢复检查点
        if task.has_checkpoint:
            task.restore_checkpoint()

        return ReenactResult(success=True, reenactment_count=task.reenactment_count)
```

### 3.4 ComplexityAssessor

**职责**: 评估任务复杂度

**评估维度**:

| 维度 | 权重 | 说明 |
|------|------|------|
| 预估修改文件数 | 30% | 任务涉及的文件数量 |
| 技术栈多样性 | 20% | 涉及的技术栈数量 |
| 跨模块依赖深度 | 30% | 模块间依赖复杂度 |
| 历史成功率 | 20% | 类似任务历史完成率 |

**接口定义**:

```python
class ComplexityAssessor:
    async def assess(self, task: Task, context: Context) -> ComplexityResult:
        """评估任务复杂度"""
        # 1. 预估修改文件数
        file_count_score = self._assess_file_count(task)

        # 2. 技术栈多样性
        tech_diversity_score = self._assess_tech_diversity(task, context)

        # 3. 跨模块依赖深度
        dependency_score = self._assess_dependency_depth(task)

        # 4. 历史成功率
        history_score = await self._assess_history(task)

        # 计算加权总分
        total_score = (
            file_count_score * 0.30 +
            tech_diversity_score * 0.20 +
            dependency_score * 0.30 +
            history_score * 0.20
        )

        # 确定复杂度级别
        if total_score <= 40:
            level = ComplexityLevel.SIMPLE
        elif total_score <= 70:
            level = ComplexityLevel.MEDIUM
        else:
            level = ComplexityLevel.COMPLEX

        return ComplexityResult(
            score=total_score,
            level=level,
            breakdown={
                "file_count": file_count_score,
                "tech_diversity": tech_diversity_score,
                "dependency": dependency_score,
                "history": history_score
            }
        )
```

### 3.5 TaskRouter

**职责**: 根据复杂度路由任务

**路由策略**:

| 复杂度 | 范围 | Agent 行为 | 最大迭代 |
|--------|------|------------|----------|
| `SIMPLE` | ≤40 | Builder 直接执行 | 5 |
| `MEDIUM` | 40-70 | Builder + Reviewer | 15 |
| `COMPLEX` | >70 | Planner → Explorer → Builder → Reviewer | 30 |

---

## 4. 核心工作流

### 4.1 任务执行流程

```
用户输入
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    Orchestration Layer                        │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    │
│  │ IntentGate  │───→│Complexity  │───→│ TaskRouter  │    │
│  │             │    │ Assessor   │    │             │    │
│  └─────────────┘    └─────────────┘    └──────┬──────┘    │
│                                                │             │
│  ┌──────────────────────────────────────────────┴──────┐    │
│  │                    RalphLoop                       │    │
│  │                                                      │    │
│  │  ┌─────────────────────────────────────────────┐   │    │
│  │  │  while not is_complete:                     │   │    │
│  │  │    agent_result = agent.run(task, context) │   │    │
│  │  │    # agent.run() = think() + execute()     │   │    │
│  │  │    # 返回 AgentRunResult(progress)         │   │    │
│  │  │                                             │   │    │
│  │  │    if progress >= 0.95: 完成              │   │    │
│  │  │    if is_stuck(): TodoEnforcer.reenact()  │   │    │
│  │  └─────────────────────────────────────────────┘   │    │
│  │                                                      │    │
│  └───────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
响应输出
```

### 4.2 意图识别流程

```
用户输入
    │
    ▼
显式指令解析 ──── 有 ───→ 显式意图
    │                          │
    │ 无                       ▼
    │                    冲突检测
    │                          │
    ▼                          ▼
隐式意图推断 ←── 冲突? ──→ 请求澄清
    │                   (needs_clarification=True)
    │
    ▼
确定路由
```

---

## 5. 依赖关系

- **依赖模块**: Agent Layer, Model Layer
- **被依赖模块**: Ingress Layer

---

## 9. Claude Code Orchestration Comparison

### 9.1 Orchestration Model Overview

| Aspect | Mozi | Claude Code |
|--------|------|-------------|
| **Architecture** | Explicit complexity scoring with IntentGate | Implicit complexity handling |
| **Intent Recognition** | Formal IntentGate with explicit patterns | Natural conversation flow |
| **Complexity Routing** | Formal three-tier (SIMPLE/MEDIUM/COMPLEX) | Task routing through conversation |
| **Loop Control** | RalphLoop with max iterations | ReAct loop with implicit termination |

### 9.2 Key Differences

#### Explicit vs Implicit Complexity Handling

**Mozi (Explicit)**:
- IntentGate performs formal intent recognition with regex patterns
- ComplexityAssessor calculates weighted scores across four dimensions
- TaskRouter explicitly routes based on complexity tier
- Pre-defined max iterations per complexity level (5/15/30)

**Claude Code (Implicit)**:
- Single agent with natural language understanding
- Complexity handled through conversation and user intent
- Task routing emerges from dialogue, not predetermined paths
- Simple request-response loop with implicit termination signals

#### Structural Philosophy

| Dimension | Mozi | Claude Code |
|-----------|------|-------------|
| **Design** | Pipeline: IntentGate -> ComplexityAssessor -> TaskRouter -> RalphLoop | Integrated: Single agent with embedded reasoning |
| **Modularity** | Highly modular, pluggable strategies | Monolithic agent with context awareness |
| **Extensibility** | Strategy plugins per complexity level | Tool-based extension |
| **Determinism** | Score-based routing is deterministic | Intent-driven routing is emergent |

### 9.3 Competitive Advantage Analysis

#### Mozi's IntentGate as Competitive Advantage

**Strengths**:

1. **Predictable Performance**: Explicit routing ensures consistent behavior across similar tasks
2. **Auditability**: Complexity scores provide clear rationale for routing decisions
3. **Multi-Agent Coordination**: Formal orchestration enables complex task decomposition
4. **Resource Planning**: Pre-known iteration limits enable capacity planning
5. **Strategy Selection**: Different strategies can be optimized per complexity tier

**Potential Weaknesses**:

1. **Overhead**: Formal pipeline adds latency for simple tasks
2. **Rigidity**: Pattern-based intent may miss nuanced user requests
3. **Complexity**: More components increase maintenance burden
4. **Cold Start**: IntentGate requires initial context to route effectively

#### Claude Code's Simplicity Advantage

1. **Lower Latency**: Single agent loop for fast task completion
2. **Natural Interaction**: Users don't need to understand complexity concepts
3. **Flexibility**: Adapts organically to task requirements
4. **Simpler Debugging**: Single execution path

### 9.4 Recommended Refinements

Based on the comparison, consider these enhancements:

#### 1. Hybrid Intent Recognition

```python
class HybridIntentGate:
    """Combine explicit patterns with LLM-based implicit recognition"""

    # Keep explicit patterns for common commands
    EXPLICIT_PATTERNS: Dict[str, Intent] = {...}

    # Add lightweight LLM analysis for ambiguous cases
    async def analyze(self, user_input: str, context: Context) -> IntentResult:
        explicit = self.parse_explicit(user_input)

        # Only invoke LLM when explicit pattern fails or conflicts exist
        if explicit is None or self._needs_deep_analysis(user_input):
            implicit = await self._llm_analyze(user_input, context)
            return self._merge_intent(explicit, implicit)

        return IntentResult(status=IntentStatus.CLEAR, explicit=explicit)
```

#### 2. Adaptive Complexity Threshold

```python
class AdaptiveComplexityAssessor:
    """Learn from user feedback to adjust complexity thresholds"""

    async def assess(self, task: Task, context: Context) -> ComplexityResult:
        base_score = await self._calculate_base_score(task)

        # Adjust based on user interaction patterns
        user_preference = await self._get_user_preference(context.user_id)
        adjusted_score = base_score * user_preference.adaptive_factor

        return ComplexityResult(score=adjusted_score, ...)
```

#### 3. Fast-Track for Low Complexity

```python
class FastTrackRouter:
    """Bypass full pipeline for trivial tasks"""

    TRIVIAL_PATTERNS = [
        r"^show me .*",
        r"^what is .*",
        r"^list .*",
    ]

    def route(self, task: Task) -> RoutingResult:
        if self._is_trivial(task):
            return RoutingResult(
                strategy=ExecutionStrategy.DIRECT,
                skip_ralph_loop=True,
                max_iterations=1
            )
        return self._full_routing(task)
```

### 9.5 Convergence Opportunities

Both approaches can learn from each other:

| From Claude Code | From Mozi |
|------------------|-----------|
| Natural intent phrasing | Formal complexity metrics |
| Tool-based extensibility | Multi-agent coordination |
| Conversation-driven flow | Explicit progress tracking |
| Minimal configuration | Strategy patterns |

**Recommended**: Keep Mozi's IntentGate and complexity scoring as core differentiators, but add a "fast-path" mode for trivial tasks that bypasses the full pipeline, reducing latency while maintaining the benefits of explicit routing for complex tasks.

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.2 | 2026-03-29 | 统一 Agent 循环概念：明确 RalphLoop 每次迭代调用 agent.run() 单次 ReAct，移除与 Agent 内部循环的混淆 |
| v1.1 | 2026-03-29 | 新增第9节「Claude Code Orchestration Comparison」，分析显式与隐式复杂度处理差异，评估IntentGate竞争优势，并提出混合意图识别、自适应复杂度阈值、快速通道等优化建议 |
| v1.0 | 2026-03-28 | 初始版本，从架构文档拆分 |
