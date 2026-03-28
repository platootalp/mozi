# Mozi v1.0 迭代说明

## 版本目标与范围

**本地优先的 AI Coding Agent**，通过自适应复杂度路由和差异化记忆/安全模型提供智能编程辅助。

### 核心差异化

| 维度 | Mozi | 差异点 |
|------|------|--------|
| **记忆系统** | 三层分离（Working/Long-term/Short-term） | 智能压缩 + 用户可控 |
| **安全模型** | 工具名单 + 通配符 + HITL + 沙箱 | 命令级控制，无复杂审批流 |
| **多 Agent** | 中心化 Orchestrator + 5 内置子 Agent | Sisyphus 风格（灵感来自 oh-my-opencode） |

### 架构决策

| 决策点 | 选择 |
|--------|------|
| Agent 架构 | 中心化（Orchestrator 唯一决策者） |
| 子 Agent | 5 个（Builder + Reviewer + Explorer + Planner + Researcher） |
| 会话/记忆 | 完全分离 |
| 工具执行 | 同步阻塞 |
| 记忆优先级 | Working → Long-term → Short-term |

## 阶段规划

| 阶段 | 名称 | 目标 | 周期 | 状态 |
|------|------|------|------|------|
| **Phase 1** | 基础平台 | CLI + Orchestrator + 5 Agent + Session | 8-10 周 | 规划中 |
| **Phase 2** | 能力层 | 工具框架 + 安全模型 + Skills | 8-10 周 | 待开始 |
| **Phase 3** | 记忆系统 | Working → Long-term → Short-term | 8-10 周 | 待开始 |
| **Phase 4** | 生态扩展 | MCP + Web UI + IDE | 8-10 周 | 待开始 |

**总周期: 32-40 周（约 8-10 个月）**

## 关键交付物清单

| 类别 | 数量 | 说明 |
|------|------|------|
| 阶段文档 | 4 | 每阶段独立规划 |
| 设计文档 | 15+ | 各组件详细设计 |
| 测试用例 | 100+ | 覆盖≥80% |

## 里程碑时间线

```
Month 1-2:   Phase 1 - 基础平台 (CLI + Orchestrator + 5 Agent)
Month 3-4:   Phase 2 - 能力层 (工具框架 + 安全模型)
Month 5-6:   Phase 3 - 记忆系统 (Working/Long-term/Short-term)
Month 7-8+:   Phase 4 - 生态扩展 (MCP + Web UI + IDE)
```

## 版本状态

**状态**: 规划中

**开始日期**: 2026-03-28
**预计结束日期**: 2026-12-31

## 模块设计文档

架构文档已拆分为 12 个独立模块，详细设计见各模块文档：

| 模块 | 文档 | 职责 |
|------|------|------|
| 交互模块 | `design/2026-03-28_ingress.md` | CLI / Web UI / IDE Extension |
| 编排模块 | `design/2026-03-28_orchestration.md` | IntentGate / RalphLoop / TodoEnforcer |
| 智能体模块 | `design/2026-03-28_agent.md` | 内置Agent / 扩展Agent / BaseAgent |
| 模型网关模块 | `design/2026-03-28_model.md` | ModelGateway / Providers |
| 记忆模块 | `design/2026-03-28_memory.md` | Working/Short-term/Long-term Memory |
| 上下文模块 | `design/2026-03-28_context.md` | ContextManager / Token预算 |
| 工具模块 | `design/2026-03-28_tools.md` | HashAnchorEdit / BuiltinTools / LSPBridge |
| 存储模块 | `design/2026-03-28_storage.md` | SessionStore / ConfigStore / ArtifactStore |
| 安全模块 | `design/2026-03-28_security.md` | Permission / Sandbox / HITL / Audit |
| 扩展模块 | `design/2026-03-28_extensions.md` | SkillsEngine / MCPClient |
| 任务与规划模块 | `design/2026-03-28_task_planning.md` | TaskManager / TaskRunner / 复杂度路由 |
| 配置模块 | `design/2026-03-28_config.md` | 配置项 / 错误码 / 降级策略 |

架构总览: `design/2026-03-28_architecture_design.md`

## 核心架构

```
                        ┌─────────────────┐
                        │   CLI (Typer)   │
                        └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │   Orchestrator   │
                        │                 │
                        │ Intent Recon.   │
                        │ Complexity Eng.  │
                        │ Task Router     │
                        │                 │
                        │ Orchestrator    │
                        │   Agent         │
                        │ (唯一决策者)    │
                        │                 │
                        │ Sub-Agent Pool  │
                        │ Builder/Reviewer│
                        │ Explorer/Planner│
                        │ Researcher     │
                        └────────┬────────┘
                                 │
           ┌─────────────────────┼─────────────────────┐
           │                     │                     │
           ▼                     ▼                     ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│  Session Manager │   │   Capabilities  │   │  Memory System  │
│  (独立于Memory)  │   │  Tools+Security │   │ (独立于Session) │
└─────────────────┘   └─────────────────┘   └─────────────────┘
```

## 依赖关系

```
Phase 1 (基础平台)
    │
    ├──────────────────────────────┐
    │                              │
    ▼                              ▼
Phase 2 (能力层)              Phase 3 (记忆系统)
    │                              │
    │         ┌────────────────────┘
    │         │
    └─────────┴─────────────────┐
                                 │
                          Phase 4 (生态扩展)
```

---

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 1.0 | 2026-03-28 | 初始规划，基于架构决策讨论 |
| 1.1 | 2026-03-28 | 新增模块设计文档（12个独立模块） |
