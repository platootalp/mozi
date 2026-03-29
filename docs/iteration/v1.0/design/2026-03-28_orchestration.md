# Orchestration Module (编排层)

## 文档信息

| 字段 | 内容 |
|------|------|
| 模块名称 | Orchestration |
| 职责 | 意图识别、任务编排、自循环执行 |
| 路径 | `mozi/orchestration/` |
| 文档版本 | v1.0 |
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
        """自循环执行任务"""
        iteration = 0
        results = []

        while not task.is_complete and iteration < self.max_iterations:
            result = await executor.execute(task)
            results.append(result)

            # 检查进度
            if result.progress >= self.progress_threshold:
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

    def _is_stuck(self, results: List[Result]) -> bool:
        """检测是否卡死（连续3次结果相同）"""
        if len(results) < 3:
            return False
        return all(
            r == results[-1] for r in results[-3:]
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
| `MEDIUM` | 41-70 | Builder + Reviewer | 15 |
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
│  │  ┌───────┐    ┌───────┐    ┌───────┐               │    │
│  │  │Agent 1│───→│Agent 2│───→│Agent N│──→ 完成      │    │
│  │  └───────┘    └───────┘    └───────┘               │    │
│  │       │                                               │    │
│  │       ▼                                               │    │
│  │  ┌─────────────┐                                      │    │
│  │  │TodoEnforcer │ (如果卡死)                          │    │
│  │  └─────────────┘                                      │    │
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

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-03-28 | 初始版本，从架构文档拆分 |
