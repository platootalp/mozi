# Agent 循环概念统一实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 统一 Agent 模块和 Orchestration 模块文档中的循环概念，消除设计文档之间的描述冲突，明确各层职责边界。

**Architecture:**
- 本计划专注于**文档设计统一**，不涉及 Python 代码实现
- 设计原则：RalphLoop（Orchestration 层）负责多轮迭代控制，Agent（Agent 层）提供单次 ReAct 迭代能力
- 后续通过代码重构实现该设计（见 2.3 节）

**Tech Stack:** 文档修改

---

## 1. 问题分析

### 1.1 当前文档冲突

| 文档 | 描述的循环概念 | 问题 |
|------|---------------|------|
| `agent.md` 3.1 节 | `BaseAgent.run()` = "完整的 Agent 运行流程（think + execute）" | 称为"ReAct 循环"，语义不清 |
| `orchestration.md` 3.2 节 | `RalphLoop.execute()` while 循环调用 `executor.execute()` | 同样描述为循环 |
| `orchestration.md` 4.1 节 | 执行流程图中 Agent 内部有"继续 THINK"箭头 | 暗示 Agent 自己有循环 |

**问题本质**：两个文档都声称自己有"循环"，但实际上应该只有一处循环控制。

### 1.2 当前代码实现（参考）

| 实际代码 | 实现 |
|---------|------|
| `AgentRuntime.run()` (runtime.py:357) | while 循环实现 ReAct，max_iterations=10 |
| `AgentBase.think()` / `act()` (base.py) | 定义了接口，但 AgentRuntime 并未调用 |

**设计 vs 实现**：文档描述的 IntentGate/RalphLoop 是目标架构，实际代码中 `AgentRuntime.run()` 自带循环。

### 1.3 统一后的文档设计

```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestration Layer                        │
│                                                             │
│  RalphLoop.execute(task, agent)                             │
│      │                                                      │
│      ├── iteration=1: agent.run_single(task, context)        │
│      │                 └── think() + execute()              │
│      │                 └── 返回 result + progress           │
│      │                                                      │
│      ├── 检查 progress >= 0.95?                             │
│      ├── 检查 is_stuck(results)?                            │
│      └── 继续或终止                                          │
└─────────────────────────────────────────────────────────────┘

职责边界:
- Orchestration: RalphLoop 负责多轮迭代 + 卡死恢复
- Agent: 提供单次 think+act 能力（不自己循环）
```

### 1.4 实现路线图（后续任务，不在本计划范围内）

| 阶段 | 任务 |
|------|------|
| Phase 1 (本计划) | 文档设计统一 |
| Phase 2 | 实现 `RalphLoop` 类（从 `AgentRuntime.run()` 提取） |
| Phase 3 | 重构 `AgentRuntime` 使用 `RalphLoop` |
| Phase 4 | 实现 `AgentBase.run_single()` 方法 |

---

## 2. 文件变更

### 2.1 变更范围

**本计划仅修改文档设计，不涉及 Python 代码。**

文档路径：
- `docs/iteration/v1.0/design/module/2026-03-28_agent.md`
- `docs/iteration/v1.0/design/module/2026-03-28_orchestration.md`

### 2.2 Agent 模块变更 (agent.md)

**目标**：澄清 `BaseAgent.run()` 是单次迭代，"ReAct 循环"的概念属于 Orchestration 层

| 位置 | 变更内容 |
|------|---------|
| 3.1 节 BaseAgent.run() 注释 | 明确是"单次 ReAct 迭代"而非"循环" |
| 7.1 节 ReAct 流程图 | 添加"单次迭代"标签，标注由 RalphLoop 控制循环 |
| 7.2 节（新增） | 添加"Agent 迭代与 RalphLoop 的关系"说明 |
| 变更记录 | 添加 v1.2 记录 |

### 2.3 Orchestration 模块变更 (orchestration.md)

**目标**：澄清 `RalphLoop` 负责多轮迭代，每次调用 `agent.run()` 单次迭代

| 位置 | 变更内容 |
|------|---------|
| 3.2 节 RalphLoop 注释 | 明确每次迭代调用 `agent.run()` |
| 3.2 节 execute 方法 | 更新参数说明为 `agent.run(task, context)` |
| 3.2 节 is_stuck 方法 | 更新参数类型为 `List[AgentRunResult]` |
| 4.1 节执行流程图 | 明确 RalphLoop 调用 `agent.run()` |
| 变更记录 | 添加 v1.2 记录 |

### 2.4 变更详情

#### Agent 模块变更 (2026-03-28_agent.md)

1. **第 3.1 节 BaseAgent 接口定义**
   - 修改 `run()` 方法注释，明确是"单次 ReAct 迭代"
   - 添加 `iterate()` 方法作为可选的多轮迭代支持

2. **第 7 节核心工作流**
   - 修改 ReAct 流程图，明确标注"单次迭代"
   - 说明 RalphLoop 在 Orchestration 层负责循环

#### Orchestration 模块变更 (2026-03-28_orchestration.md)

1. **第 3.2 节 RalphLoop**
   - 明确 RalphLoop 每次迭代调用 `agent.run(task, context)`
   - 明确 `agent.run()` 返回 `AgentRunResult`，包含 progress 字段
   - 移除对 "Agent 内部循环" 的混淆描述

2. **第 4.1 节任务执行流程**
   - 更新流程图，明确 RalphLoop 和 Agent.run() 的关系

---

## 3. 任务分解

### Task 1: 更新 Agent 模块文档

**Files:**
- Modify: `docs/iteration/v1.0/design/module/2026-03-28_agent.md`

**关键变更点：**
- 第 111-117 行：`BaseAgent.run()` 注释改为"单次迭代"
- 第 396 行：流程图中"继续 THINK"箭头改为 RalphLoop 控制
- 第 403-409 行后：新增 7.2 节说明 Agent 与 RalphLoop 关系
- 末尾变更记录：添加 v1.2 条目

---

### Task 2: 更新 Orchestration 模块文档

**Files:**
- Modify: `docs/iteration/v1.0/design/module/2026-03-28_orchestration.md`

**关键变更点：**
- 第 128-203 行：RalphLoop 类注释和方法说明
- 第 4.1 节执行流程图：明确 agent.run() 调用关系
- 末尾变更记录：添加 v1.2 条目

---

## 4. 验证

- [ ] **验证 1: 检查 Agent 文档更新**

Run: `grep -n "单次迭代\|单次 ReAct" docs/iteration/v1.0/design/module/2026-03-28_agent.md`
Expected: 应找到"单次迭代"相关描述

- [ ] **验证 2: 检查 Orchestration 文档更新**

Run: `grep -n "agent.run" docs/iteration/v1.0/design/module/2026-03-28_orchestration.md`
Expected: 应找到 `agent.run(task, context)` 调用说明

- [ ] **验证 3: 检查 Agent 文档中的循环箭头已修改**

Run: `grep -n "继续 THINK" docs/iteration/v1.0/design/module/2026-03-28_agent.md`
Expected: 应为空或已改为 "RalphLoop 判断"

- [ ] **验证 4: 检查新增的 7.2 节**

Run: `grep -n "7.2 Agent 迭代与 RalphLoop" docs/iteration/v1.0/design/module/2026-03-28_agent.md`
Expected: 应找到新增章节

---

## 5. 总结

### 统一后的文档设计

| 组件 | 职责 | 所在文档 |
|------|------|---------|
| `Agent.run()` | 单次 ReAct 迭代（think + execute），返回 AgentRunResult | agent.md |
| `RalphLoop` | 多轮迭代控制，进度检测，卡死恢复 | orchestration.md |
| `ExecutionStrategy` | 定义 max_iterations（5/15/30） | orchestration.md |
| `TodoEnforcer` | 卡死时重新激活任务 | orchestration.md |

### 文档修改清单

| 文档 | 修改点 |
|------|--------|
| `agent.md` | 1. BaseAgent.run() 注释 2. ReAct 流程图 3. 新增 7.2 节 |
| `orchestration.md` | 1. RalphLoop 注释 2. execute 方法 3. 执行流程图 |

### 后续工作（不在本计划范围）

| 阶段 | 任务 | 说明 |
|------|------|------|
| Phase 2 | 实现 RalphLoop 类 | 从 AgentRuntime.run() 提取循环逻辑 |
| Phase 3 | 重构 AgentRuntime | 使用 RalphLoop |
| Phase 4 | 实现 AgentBase.run_single() | 提供单次迭代方法 |

