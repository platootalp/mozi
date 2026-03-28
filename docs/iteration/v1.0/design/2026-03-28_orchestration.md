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

## 1. 组件列表

| 组件 | 职责 |
|------|------|
| **IntentGate** | 意图识别，路由到对应 Agent |
| **RalphLoop** | 自循环执行，确保任务 100% 完成 |
| **TodoEnforcer** | 监控空闲 Agent，重新激活 |

## 2. IntentGate

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

## 3. RalphLoop

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

## 4. TodoEnforcer

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

## 5. 依赖关系

- **依赖模块**: Agent Layer, Model Layer
- **被依赖模块**: Ingress Layer

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-03-28 | 初始版本，从架构文档拆分 |
