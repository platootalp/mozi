# 模块拆分设计方案

## 1. 背景与目标

将 `2026-03-28_architecture_design.md` 中的各个功能模块提取为独立文档，实现职责分离、边界清晰。

## 2. 目标文档结构

```
docs/iteration/v1.0/design/
├── 2026-03-28_architecture_design.md    # 总览文档（精简版）
├── 2026-03-28_ingress.md                  # 交互模块
├── 2026-03-28_orchestration.md            # 编排模块
├── 2026-03-28_agent.md                   # 智能体模块
├── 2026-03-28_model.md                   # 模型网关模块
├── 2026-03-28_memory.md                  # 记忆模块
├── 2026-03-28_context.md                  # 上下文模块
├── 2026-03-28_tools.md                   # 工具模块
├── 2026-03-28_storage.md                 # 存储模块
├── 2026-03-28_security.md               # 安全模块
├── 2026-03-28_extensions.md              # 扩展模块
├── 2026-03-28_task_planning.md           # 任务与规划模块
└── 2026-03-28_config.md                  # 配置模块
```

## 3. 模块清单与来源

| 序号 | 文档名 | 来源章节 | 核心内容 |
|------|--------|----------|----------|
| 1 | `ingress.md` | 2. Ingress Layer | CLI / Web UI / IDE Extension |
| 2 | `orchestration.md` | 3. Orchestration Layer | IntentGate / RalphLoop / TodoEnforcer |
| 3 | `agent.md` | 4. Agent Layer | 内置Agent / 扩展Agent / BaseAgent |
| 4 | `model.md` | 5. Model Gateway Layer | ModelGateway / Providers |
| 5 | `memory.md` | 7. Storage Layer (Memory部分) | Working/Short-term/Long-term Memory |
| 6 | `context.md` | 7. Storage Layer (ContextManager部分) | 上下文组装 / Token预算管理 |
| 7 | `tools.md` | 6. Tools Layer | HashAnchorEdit / BuiltinTools / LSPBridge / MCPClient |
| 8 | `storage.md` | 7. Storage Layer | SessionStore / ConfigStore / ArtifactStore |
| 9 | `security.md` | 8. Security Layer | Permission / Sandbox / HITL / Audit |
| 10 | `extensions.md` | 9. Extensions Layer | SkillsEngine / MCPClient |
| 11 | `task_planning.md` | 4.4 任务规划 / 10. 复杂度路由 | TaskManager / TaskRunner / CheckpointManager / 复杂度评估 |
| 12 | `config.md` | 18.2 配置管理 | 配置项 / 来源 / 管理方式 |

## 4. 总览文档精简内容

保留以下章节：
- 1.1 模块结构图（精简版）
- 1.2 模块职责表
- 9. 请求生命周期
- 17. 演进规划（V1.0 / V2.0）

移除：2-9 各模块详细设计

## 5. 模块文档统一模板

每个模块文档包含：

```markdown
## 模块信息
- 模块名称
- 职责描述
- 路径位置

## 组件列表
| 组件 | 职责 |
|------|------|

## 核心接口
```python
# 核心类或函数定义
```

## 数据流
- 输入 → 处理 → 输出

## 依赖关系
- 依赖：xxx模块
- 被依赖：xxx模块
```

## 6. 拆分原则

1. **单一职责**：每个文档只描述一个模块
2. **清晰边界**：模块间通过接口交互，不泄露内部实现
3. **可独立演进**：各模块可独立更新，不影响其他模块
4. **交叉引用**：模块文档间通过链接引用依赖模块

## 7. 实施步骤

1. 创建 12 个模块独立文档
2. 精简总览文档，保留架构全景和依赖关系
3. 更新总览文档中的内部链接，指向各模块文档
4. 提交所有文档到 git
