# Mozi v1.0 迭代计划

## 概述

基于四层架构（Ingress → Orchestrator → Capabilities → Infrastructure）和功能优先级（P0/P1/P2），将项目分解为 **7 个逻辑迭代**，总计约 **37 周**。

---

## 迭代概览表

| 迭代 | 名称 | 目标 | 优先级 | 周期 |
|------|------|------|--------|------|
| 1 | Foundation Core | CLI + Orchestrator FastPath + SQLite Sessions | P0 | 6周 |
| 2 | Tool Framework & Security | Built-in tools + Permission system + Audit | P0 | 5周 |
| 3 | Complexity Routing | Complexity assessment engine + MEDIUM tasks | P0 | 4周 |
| 4 | Multi-Agent & DAG | COMPLEX routing + DAG planner + Multi-Agent | P1 | 6周 |
| 5 | Memory Architecture | Three-tier memory + Vector store + RAG | P1 | 5周 |
| 6 | MCP Integration & HITL | MCP protocol + External tools + Approval flow | P1 | 5周 |
| 7 | Web UI & Polish | FastAPI UI + Skills engine + IDE Extension | P2 | 6周 |

---

## 迭代 1: Foundation Core

### 1.1 目标
建立核心基础设施和 CLI 入口层，实现基本编排（仅 FastPath 处理 SIMPLE 任务）。

### 1.2 关键文档交付物

| 文档 | 描述 |
|------|------|
| `iteration/v1.0/README.md` | 迭代概览和目标 |
| `iteration/v1.0/prd/cli-spec.md` | CLI 命令规范 |
| `iteration/v1.0/design/fastpath-design.md` | FastPath 执行设计 |
| `iteration/v1.0/development/session-schema.md` | SQLite 会话模式 |

### 1.3 输入依赖

| 依赖 | 来源 | 状态 |
|------|------|------|
| 架构概览 | `docs/foundation/architecture/2026-03-26_mozi_architecture.md` | 可用 |
| PRD | `docs/foundation/requirement/2026-03-26_mozi_overall_prd.md` | 可用 |
| 四层架构 | CLAUDE.md | 可用 |

### 1.4 输出产物

| 产物 | 描述 |
|------|------|
| `mozi/cli/` | CLI 入口层实现 |
| `mozi/orchestrator/core/` | 核心编排器（意图识别、FastPath 路由） |
| `mozi/infrastructure/db/` | SQLite 会话存储 |
| `mozi/core/error.py` | 统一错误类 |
| `mozi/__init__.py` | 包导出 |

### 1.5 里程碑检查点

| 里程碑 | 交付物 | 验收标准 |
|--------|--------|----------|
| M1.1: CLI 启动 | `mozi` 命令可用 | `mozi --help` 返回有效输出 |
| M1.2: 配置加载 | 多级配置合并 | Env > User > Project > System |
| M1.3: 意图识别 | IntentClassifier 工作 | 分类任务类型（bug_fix, feature_add 等） |
| M1.4: FastPath 执行 | SIMPLE 任务执行 | 单文件编辑成功完成 |
| M1.5: 会话持久化 | SQLite 存储 | 会话持久化和恢复 |

### 1.6 周期: 6 周

---

## 迭代 2: Tool Framework & Security

### 2.1 目标
实现工具框架，包含内置工具、权限系统和审计日志。

### 2.2 关键文档交付物

| 文档 | 描述 |
|------|------|
| `iteration/v1.0/design/tool-framework-design.md` | 工具注册和执行 |
| `iteration/v1.0/design/permission-design.md` | 五级权限系统 |
| `iteration/v1.0/design/audit-design.md` | 审计日志规范 |
| `iteration/v1.0/testing/tool-testing.md` | 工具集成测试 |

### 2.3 输入依赖

| 依赖 | 来源 | 状态 |
|------|------|------|
| CLI 框架 | 迭代 1 | 阻塞 |
| 配置模式 | `docs/foundation/architecture/` (Section 3) | 可用 |

### 2.4 输出产物

| 产物 | 描述 |
|------|------|
| `mozi/capabilities/tools/framework.py` | 工具框架核心 |
| `mozi/capabilities/tools/builtin/` | 内置工具（read, write, edit, bash, grep, glob） |
| `mozi/capabilities/tools/permission.py` | 权限检查器（deny-first） |
| `mozi/capabilities/tools/sandbox.py` | 沙箱执行 |
| `mozi/capabilities/tools/hash_anchor.py` | 基于哈希的编辑锚定 |
| `mozi/core/audit.py` | 审计日志 |

### 2.5 里程碑检查点

| 里程碑 | 交付物 | 验收标准 |
|--------|--------|----------|
| M2.1: 工具注册 | 工具可注册 | `register_tool()` 添加到注册表 |
| M2.2: 内置工具 | 6 个基础工具可用 | read/write/edit/bash/grep/glob 功能正常 |
| M2.3: 权限检查器 | deny-first 策略执行 | deny > ask > allow 优先级 |
| M2.4: 沙箱执行 | 沙箱工具运行 | non-main 模式阻止主目录访问 |
| M2.5: 审计日志 | 敏感操作记录 | 所有 bash/write 调用被记录 |

### 2.6 周期: 5 周

---

## 迭代 3: Complexity Routing

### 3.1 目标
实现复杂度评估引擎和 MEDIUM 任务处理，包含增强监控。

### 3.2 关键文档交付物

| 文档 | 描述 |
|------|------|
| `iteration/v1.0/design/complexity-engine-design.md` | 四维评分设计 |
| `iteration/v1.0/design/medium-task-design.md` | MEDIUM 路由与步骤跟踪 |
| `iteration/v1.0/testing/complexity-testing.md` | 复杂度测试用例 |

### 3.3 输入依赖

| 依赖 | 来源 | 状态 |
|------|------|------|
| 意图识别 | 迭代 1 | 阻塞 |
| 会话上下文 | 迭代 1 | 阻塞 |
| 配置模式 | 迭代 1 | 阻塞 |

### 3.4 输出产物

| 产物 | 描述 |
|------|------|
| `mozi/orchestrator/core/complexity.py` | 复杂度评估引擎 |
| `mozi/orchestrator/core/router.py` | 任务路由器（SIMPLE/MEDIUM/COMPLEX） |
| `mozi/orchestrator/session/` | 增强的会话管理 |
| 配置模式 | Pydantic 模型（config.json, agents.json） |

### 3.5 里程碑检查点

| 里程碑 | 交付物 | 验收标准 |
|--------|--------|----------|
| M3.1: 复杂度评分 | 四维加权评分 | 评分与预期复杂度匹配 |
| M3.2: SIMPLE 路由 | FastPath 处理 ≤40 分 | 直接执行，无需规划 |
| M3.3: MEDIUM 路由 | Enhanced 路径处理 41-70 分 | 步骤跟踪对用户可见 |
| M3.4: 阈值配置 | 阈值可配置 | `complexity_threshold` 在 agents.json |
| M3.5: 会话增强 | 逐步日志记录 | MEDIUM 任务显示执行计划 |

### 3.6 周期: 4 周

---

## 迭代 4: Multi-Agent & DAG

### 4.1 目标
实现 COMPLEX 任务处理，包含 DAG 生成、多Agent协调和并行执行。

### 4.2 关键文档交付物

| 文档 | 描述 |
|------|------|
| `iteration/v1.0/design/dag-planner-design.md` | DAG 生成算法 |
| `iteration/v1.0/design/multi-agent-design.md` | 多Agent协调 |
| `iteration/v1.0/design/session-forking-design.md` | 会话 fork/执行上下文 |
| `iteration/v1.0/testing/dag-testing.md` | DAG 执行测试 |

### 4.3 输入依赖

| 依赖 | 来源 | 状态 |
|------|------|------|
| 复杂度引擎 | 迭代 3 | 阻塞 |
| 工具框架 | 迭代 2 | 阻塞 |
| 会话管理 | 迭代 3 | 阻塞 |

### 4.4 输出产物

| 产物 | 描述 |
|------|------|
| `mozi/orchestrator/dag/planner.py` | DAG 生成器 |
| `mozi/orchestrator/dag/scheduler.py` | DAG 拓扑调度器 |
| `mozi/orchestrator/dag/executor.py` | 并行执行器 |
| `mozi/orchestrator/agent/` | Agent 运行时、注册表、池 |
| `mozi/orchestrator/session/checkpoint.py` | 检查点管理 |

### 4.5 里程碑检查点

| 里程碑 | 交付物 | 验收标准 |
|--------|--------|----------|
| M4.1: DAG 生成 | 静态依赖分析 | 为已知依赖生成有效 DAG |
| M4.2: 并行执行 | 独立节点并行运行 | 测量加速效果 |
| M4.3: Agent 池 | Agent 重用和生命周期 | 池管理 Agent 创建/销毁 |
| M4.4: 会话 Fork | 带上下文的子会话 | fork() 创建隔离子会话 |
| M4.5: 检查点恢复 | 状态恢复 | 崩溃后从检查点恢复 |
| M4.6: 冲突处理 | 哈希锚定重试 | 3 次重试后通知用户 |

### 4.6 周期: 6 周

---

## 迭代 5: Memory Architecture

### 5.1 目标
实现三层记忆架构，包含向量存储集成和 RAG 检索。

### 5.2 关键文档交付物

| 文档 | 描述 |
|------|------|
| `iteration/v1.0/design/memory-tier-design.md` | 三层记忆设计 |
| `iteration/v1.0/design/vector-store-design.md` | Qdrant 集成 |
| `iteration/v1.0/design/rag-retrieval-design.md` | 混合检索（BM25 + vector） |
| `iteration/v1.0/design/memory-hierarchy-design.md` | 数据流和层级转换 |
| `iteration/v1.0/testing/memory-testing.md` | 记忆系统测试 |

### 5.3 输入依赖

| 依赖 | 来源 | 状态 |
|------|------|------|
| SQLite 模式 | 迭代 1 | 阻塞 |
| 会话管理 | 迭代 3 | 阻塞 |
| 工具框架 | 迭代 2 | 阻塞 |

### 5.4 输出产物

| 产物 | 描述 |
|------|------|
| `mozi/infrastructure/memory/manager.py` | 记忆管理器 |
| `mozi/infrastructure/memory/working.py` | 工作记忆（LLM 上下文） |
| `mozi/infrastructure/memory/short_term.py` | 短期记忆（向量存储） |
| `mozi/infrastructure/memory/long_term.py` | 长期记忆（文件系统） |
| `mozi/infrastructure/vector/` | 向量存储客户端 |
| `mozi/infrastructure/memory/retrieval.py` | 混合检索 |

### 5.5 里程碑检查点

| 里程碑 | 交付物 | 验收标准 |
|--------|--------|----------|
| M5.1: 工作记忆 | LLM 上下文管理 | 滑动窗口保持最近上下文 |
| M5.2: 短期存储 | 向量嵌入和搜索 | 语义搜索返回结果 |
| M5.3: 长期持久化 | 文件系统存储 | 偏好跨会话持久化 |
| M5.4: 层级转换 | 自动数据流 | Working → Short → Long 触发转换 |
| M5.5: 混合检索 | BM25 + vector 组合 | 查询返回相关记忆 |
| M5.6: 记忆召回 | `memory:recall` 工具 | 可检索存储的记忆 |

### 5.6 周期: 5 周

---

## 迭代 6: MCP Integration & HITL

### 6.1 目标
实现 MCP 协议支持、外部工具集成和 Human-in-the-Loop 审批流程。

### 6.2 关键文档交付物

| 文档 | 描述 |
|------|------|
| `iteration/v1.0/design/mcp-integration-design.md` | MCP 客户端和传输 |
| `iteration/v1.0/design/hitl-design.md` | HITL 审批工作流 |
| `iteration/v1.0/design/mcp-security-design.md` | MCP 安全措施 |
| `iteration/v1.0/testing/mcp-testing.md` | MCP 集成测试 |

### 6.3 输入依赖

| 依赖 | 来源 | 状态 |
|------|------|------|
| 工具框架 | 迭代 2 | 阻塞 |
| 权限系统 | 迭代 2 | 阻塞 |
| 会话管理 | 迭代 4 | 阻塞 |

### 6.4 输出产物

| 产物 | 描述 |
|------|------|
| `mozi/ingress/mcp/protocol.py` | MCP 协议定义 |
| `mozi/ingress/mcp/client.py` | MCP 客户端抽象 |
| `mozi/ingress/mcp/transports/` | stdio, sse, http, ws 传输 |
| `mozi/capabilities/mcp/` | MCP 管理器、协商器、健康检查、池 |
| `mozi/capabilities/skills/` | Skills 引擎实现 |
| HITL 审批流程 | 用户提示 + 审批跟踪 |

### 6.5 里程碑检查点

| 里程碑 | 交付物 | 验收标准 |
|--------|--------|----------|
| M6.1: MCP 客户端 | stdio 传输工作 | 可与 MCP 服务器通信 |
| M6.2: 多传输 | 4 种传输支持 | stdio/sse/http/ws 功能正常 |
| M6.3: 能力协商 | 工具按权限过滤 | tools.json 策略执行 |
| M6.4: MCP 健康检查 | Ping/pong 监控 | 失败服务器被禁用 |
| M6.5: HITL 触发 | 敏感操作暂停 | bash/write/MCP 触发审批 |
| M6.6: Skills 引擎 | Skill 文档执行 | Trigger → parse → execute → verify |

### 6.6 周期: 5 周

---

## 迭代 7: Web UI & Polish

### 7.1 目标
实现 Web UI、高级 Skills、IDE 扩展和系统级优化。

### 7.2 关键文档交付物

| 文档 | 描述 |
|------|------|
| `iteration/v1.0/design/web-ui-design.md` | FastAPI Web UI |
| `iteration/v1.0/design/websocket-streaming.md` | SSE/WebSocket 流式传输 |
| `iteration/v1.0/design/ide-extension-design.md` | IDE 插件架构 |
| `iteration/v1.0/testing/e2e-testing.md` | 端到端测试场景 |

### 7.3 输入依赖

| 依赖 | 来源 | 状态 |
|------|------|------|
| 核心编排器 | 迭代 4 | 阻塞 |
| 记忆系统 | 迭代 5 | 阻塞 |
| MCP 集成 | 迭代 6 | 阻塞 |

### 7.4 输出产物

| 产物 | 描述 |
|------|------|
| `mozi/ingress/web/` | FastAPI 应用 |
| `mozi/ingress/web/routes/` | 会话和 WebSocket 路由 |
| `mozi/ingress/web/middleware/` | 认证和日志中间件 |
| `mozi/infrastructure/model/` | 模型适配器（OpenAI, Claude, Ollama） |
| `mozi/core/event/` | 事件总线实现 |
| `mozi/core/circuit_breaker.py` | 熔断器 |
| `mozi/core/rate_limiter.py` | 限流器 |

### 7.5 里程碑检查点

| 里程碑 | 交付物 | 验收标准 |
|--------|--------|----------|
| M7.1: Web UI | FastAPI 应用运行 | `/health` 返回 200 |
| M7.2: WebSocket 流 | 实时输出 | SSE 推送 Agent 输出 |
| M7.3: 模型适配器 | 多提供商支持 | Claude/OpenAI/Ollama 工作 |
| M7.4: 事件总线 | 异步事件处理 | 事件传播到消费者 |
| M7.5: 熔断器 | 故障处理 | 5 次失败 → 60s 熔断 |
| M7.6: 限流器 | 成本控制 | Token 预算执行 |
| M7.7: IDE 扩展 | VSCode 插件脚手架 | 扩展结构完整 |

### 7.6 周期: 6 周

---

## 跨切面关注点

### 1. 安全（所有迭代）

| 迭代 | 安全重点 |
|------|----------|
| 1 | 错误处理，无信息泄露 |
| 2 | 权限检查器、沙箱、审计 |
| 3 | 复杂度评分不可利用 |
| 4 | DAG 执行隔离 |
| 5 | 静态记忆加密 |
| 6 | MCP 安全（CVE-2025-54135/54136） |
| 7 | Web 认证、API 安全 |

**关键文档:**
- `.claude/rules/security.md`
- `docs/foundation/architecture/` Section 6

### 2. 可观测性（迭代 1-7）

| 组件 | 实现迭代 |
|------|----------|
| 日志 | 迭代 1（结构化 JSON） |
| 指标 | 迭代 4（Prometheus） |
| 追踪 | 迭代 4（OpenTelemetry） |
| 健康检查 | 迭代 7（FastAPI `/health`） |

### 3. 错误处理与弹性（迭代 2-7）

| 模式 | 首次实现 |
|------|----------|
| 指数退避重试 | 迭代 2 |
| 熔断器 | 迭代 7 |
| 优雅降级 | 迭代 5（向量回退） |
| 检查点恢复 | 迭代 4 |

### 4. 配置管理（迭代 1-3）

| 配置文件 | 模式定义 |
|----------|----------|
| config.json | 迭代 1 |
| agents.json | 迭代 3 |
| tools.json | 迭代 2 |
| mcp.json | 迭代 6 |
| skills.json | 迭代 6 |

---

## 总结

| 类别 | 数量 | 说明 |
|------|------|------|
| 总迭代数 | 7 | 逻辑分解 |
| 总里程碑数 | 35 | 每迭代平均 5 个 |
| 总周期 | ~37 周 | 9 个月 |
| P0 覆盖 | 迭代 1-3 | 核心基础 |
| P1 覆盖 | 迭代 4-6 | 增强功能 |
| P2 覆盖 | 迭代 7 | 高级功能 |
| 跨切面文档 | 4 | 安全、可观测性、错误处理、配置 |

---

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 1.0 | 2026-03-28 | 初始迭代计划 |
