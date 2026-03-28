# Mozi AI Coding Agent - 架构设计文档

## 文档信息

| 字段 | 内容 |
|------|------|
| 项目名称 | Mozi AI Coding Agent |
| 文档版本 | v16.0 |
| 状态 | 规划中 |
| 创建日期 | 2026-03-28 |
| 最后更新 | 2026-03-28 |
| 作者 | Mozi Team |
| 审核人 | - |

---

## 概述

本文档是架构总览，详细模块设计已拆分到独立文档：

| 模块 | 文档 |
|------|------|
| Ingress | `2026-03-28_ingress.md` |
| Orchestration | `2026-03-28_orchestration.md` |
| Agent | `2026-03-28_agent.md` |
| Model | `2026-03-28_model.md` |
| Memory | `2026-03-28_memory.md` |
| Context | `2026-03-28_context.md` |
| Tools | `2026-03-28_tools.md` |
| Storage | `2026-03-28_storage.md` |
| Security | `2026-03-28_security.md` |
| Extensions | `2026-03-28_extensions.md` |
| Task & Planning | `2026-03-28_task_planning.md` |
| Config | `2026-03-28_config.md` |

---

## 1. 系统整体架构

### 1.1 模块结构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Ingress 模块                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  CLI (Typer)  │  Web UI (FastAPI)  │  IDE Extension (VSCode/JetBrains)      │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Orchestration 模块                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  IntentGate      ───  意图识别，路由到对应 Agent                              │
│  RalphLoop       ───  自循环执行，确保任务 100% 完成                          │
│  TodoEnforcer    ───  监控空闲 Agent，重新激活                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Agent 模块                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  内置 Agent: Builder / Reviewer / Explorer / Planner / Researcher          │
│  扩展 Agent: ~/.mozi/agents/ 目录加载                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Model 模块                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  ModelGateway       ───  多模型统一接口，智能路由                            │
│  AnthropicProvider  ───  Anthropic API 适配                               │
│  OpenAIProvider     ───  OpenAI API 适配                                   │
│  OllamaProvider     ───  Ollama 本地模型适配                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Memory 模块                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  Working Memory   ───  内存，LLM Context 滑动窗口                          │
│  Short-term       ───  Qdrant，语义搜索、RAG                               │
│  Long-term        ───  SQLite，用户偏好、历史经验                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Task & Planning 模块                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  TaskManager         ───  任务创建、分解、状态跟踪                          │
│  TaskRunner          ───  执行调度（按复杂度选择策略）                        │
│  CheckpointManager   ───  检查点保存与恢复                                   │
│  ProgressTracker     ───  进度跟踪                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Context 模块                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  ContextManager    ───  上下文组装、Token 预算管理、记忆检索                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Tools 模块                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  HashAnchorEdit    ───  带哈希验证的安全编辑                                │
│  BuiltinTools      ───  read / write / edit / bash / grep / glob          │
│  LSPBridge         ───  LSP 工具封装                                       │
│  MCPClient         ───  MCP 协议客户端                                     │
│  SkillLoader       ───  Skill 按需加载（加载后为工具）                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             Storage 模块                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  SessionStore      ───  会话持久化 (SQLite)                                 │
│  ConfigStore       ───  配置存储                                           │
│  ArtifactStore     ───  工件存储                                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             Security 模块 [跨切面]                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  Permission    ───  权限检查，支持通配符                                     │
│  Sandbox      ───  沙箱隔离模式                                             │
│  HITL         ───  人工介入确认                                             │
│  Audit        ───  审计日志                                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 模块职责

| 模块 | 职责 |
|------|------|
| **Ingress** | 命令解析、用户交互 |
| **Orchestration** | 意图识别、任务编排、自循环执行 |
| **Agent** | 内置 Agent、扩展 Agent |
| **Model** | 多模型路由、Provider 适配 |
| **Memory** | Working/Short-term/Long-term 记忆 |
| **Task & Planning** | 任务创建分解、执行调度、检查点、进度跟踪 |
| **Context** | 上下文组装、Token 预算管理、记忆检索 |
| **Tools** | 工具定义、注册、执行 |
| **Storage** | Session、Config、Artifact 持久化 |
| **Security** | 权限检查、沙箱、HITL、审计 |

---

## 9. 请求生命周期

```
User Input
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ Ingress Layer                                              │
│ CLI 解析 / 用户交互                                         │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ Orchestration Layer                                        │
│ IntentGate → RalphLoop → TodoEnforcer                     │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ Agent Layer                                                │
│ Builder / Reviewer / Explorer / Planner / Researcher      │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ Model Gateway Layer                                        │
│ 多模型路由 / Provider 适配                                   │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ Tools Layer                                                │
│ HashAnchorEdit / Built-in / LSP / MCP / Skill              │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ Storage Layer                                              │
│ Session / Memory / Config / Artifact                       │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ Security Layer (Cross-cutting)                             │
│ Permission → Sandbox → HITL → Audit                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 10. 项目目录结构

```
mozi/
├── ingress/                    # 交互层
│   ├── cli/                   # CLI (Typer)
│   ├── web/                   # Web UI (FastAPI)
│   └── ide/                   # IDE Extension
│
├── orchestration/              # 编排层
│   ├── intent_gate.py         # 意图识别
│   ├── ralph_loop.py          # 自循环执行
│   ├── todo_enforcer.py       # 任务强制执行
│   └── plugins/               # 可插拔组件
│
├── agent/                     # 智能体层
│   ├── base.py                # Agent 基类
│   ├── builder.py             # Builder Agent
│   ├── reviewer.py            # Reviewer Agent
│   ├── explorer.py            # Explorer Agent
│   ├── planner.py             # Planner Agent
│   └── researcher.py          # Researcher Agent
│
├── model/                     # 模型网关层
│   ├── gateway.py             # 模型网关
│   ├── anthropic.py           # Anthropic Provider
│   ├── openai.py              # OpenAI Provider
│   └── ollama.py              # Ollama Provider
│
├── tools/                     # 工具层
│   ├── registry.py            # 工具注册
│   ├── executor.py            # 工具执行器
│   ├── hash_anchor.py         # Hash 锚定编辑
│   ├── builtin/               # 内置工具
│   │   ├── read.py
│   │   ├── write.py
│   │   ├── edit.py
│   │   ├── bash.py
│   │   ├── grep.py
│   │   ├── glob.py
│   │   └── lsp.py
│   ├── lsp/                   # LSP 桥接
│   │   └── bridge.py
│   ├── mcp/                   # MCP Client
│   │   ├── client.py
│   │   └── protocol.py
│   └── skill/                 # Skill Loader
│       ├── loader.py
│       └── parser.py
│
├── storage/                   # 存储层
│   ├── session/               # Session Store
│   │   ├── manager.py
│   │   └── schema.py
│   ├── memory/                # Memory Store
│   │   ├── working.py
│   │   ├── short_term.py
│   │   └── long_term.py
│   ├── config/               # Config Store
│   │   └── loader.py
│   └── artifact/             # Artifact Store
│
└── config/                    # 配置
    └── schemas.py             # Pydantic schemas
```

---

## 11. 术语表

| 术语 | 说明 |
|------|------|
| **Ingress** | 交互层，命令解析，响应渲染 |
| **Orchestration** | 编排层，IntentGate/RalphLoop/TodoEnforcer |
| **Agent** | 智能体层，Builder/Reviewer/Explorer/Planner/Researcher |
| **Model Gateway** | 模型网关层，多模型路由 |
| **Tools** | 工具层，HashAnchor/内置工具/LSP/MCP/Skill |
| **Storage** | 存储层，Session/Memory/Config/Artifact |

---

## 12. 背景与目标

### 12.1 业务背景

Mozi 是一个**本地优先的 AI Coding Agent**，旨在帮助开发者通过自然语言指令完成编码任务。

**核心差异化**：
- 本地优先，数据不离开本地环境
- 三层记忆系统（Working/Short-term/Long-term）实现智能上下文管理
- 灵活的安全模型（工具名单+HITL+沙箱）
- 可插拔的扩展架构（Skills/MCP）

### 12.2 业务目标

| 指标 | 目标 |
|------|------|
| 任务完成率 | ≥ 90%（简单任务） |
| 响应时间 | < 2s（不含模型调用） |
| Token 效率 | 上下文压缩率 ≥ 50% |
| 安全性 | 零数据泄露 |

### 12.3 约束条件

- 本地运行，不依赖云端服务
- 支持 macOS/Linux/Windows
- Python 3.11+
- CLI 优先，Web/IDE 后续支持

### 12.4 Out of Scope

以下功能不在 V1.0 范围内：
- 云端部署和多租户
- 企业级 SSO/LDAP 认证
- 复杂项目管理功能
- 多语言本地化

---

## 13. 质量属性

### 13.1 性能

| 指标 | 目标 | 说明 |
|------|------|------|
| CLI 启动时间 | < 1s | 冷启动 |
| 工具调用延迟 | < 100ms | 不含网络 |
| 模型调用超时 | 60s | 可配置 |

### 13.2 可用性

| 指标 | 目标 | 说明 |
|------|------|------|
| CLI 可用性 | 99.9% | 纯本地，无网络依赖 |
| 会话恢复 | 100% | 持久化到磁盘 |

### 13.3 安全性

| 要求 | 说明 |
|------|------|
| 密钥管理 | 环境变量注入，禁止硬编码 |
| 沙箱隔离 | bash 命令在受限环境执行 |
| 审计日志 | 所有操作记录可查 |

### 13.4 可扩展性

- 工具系统：支持动态注册新工具
- 模型系统：支持添加新的模型 Provider
- 扩展系统：Skills/MCP 可插拔

---

## 14. 物理/部署视图

### 14.1 部署模式

**单机本地部署**（V1.0）：

```
┌─────────────────────────────────────────────────────────────┐
│                       用户本地环境                              │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   Mozi CLI                           │   │
│  │                                                       │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐              │   │
│  │  │ Ingress │→│  Core   │→│ Runtime │              │   │
│  │  └─────────┘  └─────────┘  └─────────┘              │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                │
│                           ▼                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │               Local Storage                           │   │
│  │   SQLite (Session) │ Qdrant (Vector) │ Files        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            External: LLM Provider                    │   │
│  │         Anthropic / OpenAI / Ollama                  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 14.2 容器化方案（V2.0）

```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -e .
CMD ["mozi"]
```

### 14.3 网络拓扑

| 组件 | 协议 | 说明 |
|------|------|------|
| LLM API | HTTPS | Anthropic/OpenAI API |
| Vector DB | Local | Qdrant 本地部署 |
| Storage | Local | SQLite 文件 |

---

## 15. 数据视图

### 15.1 核心实体

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Session   │────→│    Task    │────→│    Tool    │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       │                   ▼                   │
       │            ┌─────────────┐            │
       └───────────→│   Memory   │←───────────┘
                    └─────────────┘
                          │
                          ▼
                    ┌─────────────┐
                    │   Context   │
                    └─────────────┘
```

### 15.2 核心 Schema

#### Session

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    status TEXT,  -- ACTIVE/COMPLETED/ERROR
    complexity_level TEXT,  -- SIMPLE/MEDIUM/COMPLEX
    complexity_score INTEGER,
    metadata JSON
);
```

#### Task

```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    description TEXT,
    status TEXT,  -- PENDING/IN_PROGRESS/COMPLETED/FAILED
    progress REAL,
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```

#### Memory

```sql
CREATE TABLE memory (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    type TEXT,  -- WORKING/SHORT_TERM/LONG_TERM
    content TEXT,
    embedding BLOB,
    created_at TIMESTAMP,
    expires_at TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```

### 15.3 数据流

```
User Input → Session → Task → Context → Memory → Model → Response
                ↓                                      ↓
           Audit Log                              Tool Call
```

---

## 16. 动态/时序视图

### 16.1 FastPath 执行时序（SIMPLE 任务）

```
User    Orchestration    Core        Runtime     Security
 │           │            │            │            │
 │──Input───→│            │            │            │
 │           │            │            │            │
 │     intent_recognize   │            │            │
 │           │────────────→│            │            │
 │           │     analyze │            │            │
 │           │←────────────│            │            │
 │           │            │            │            │
 │     plan_task           │            │            │
 │           │────────────→│            │            │
 │           │            │            │            │
 │           │     execute_tool───────→│            │
 │           │            │     check_permission   │
 │           │            │←────────────│            │
 │           │            │            │            │
 │           │            │←────────────────────────│
 │           │            │     tool_result        │
 │           │            │            │            │
 │←───────────────────────│────────────│────────────│
 │         response       │            │            │
```

### 16.2 Session 状态机

```
                    ┌──────────┐
                    │  START   │
                    └─────┬────┘
                          │
                          ▼
┌──────────────────────────────────────┐
│             ACTIVE                   │
│                                      │
│  ┌─────────┐    ┌──────────┐         │
│  │ THINKING│───→│ EXECUTING│         │
│  └─────────┘    └────┬─────┘         │
│       ▲              │               │
│       │              ▼               │
│       │         ┌──────────┐         │
│       └─────────│WAITING_HITL│        │
│                 └────┬─────┘         │
└──────────────────────┼───────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │COMPLETED │ │  ERROR   │ │ ABORTED  │
    └──────────┘ └──────────┘ └──────────┘
```

---

## 17. 演进规划

### 17.1 V1.0 交付范围

| 模块 | 功能 |
|------|------|
| Ingress | CLI + 交互式会话 |
| Orchestration | 意图识别 + 复杂度评估 |
| Core | Agent + Model + Memory + Session |
| Runtime | 6 内置工具 + Task Runner |
| Security | Permission + Sandbox + HITL + Audit |
| Extensions | Skills Engine (基础) |

### 17.2 V2.0 路线图

| 功能 | 说明 |
|------|------|
| Web UI | FastAPI Web 界面 |
| IDE Extension | VSCode/JetBrains 插件 |
| MCP Client | 完整 MCP 协议支持 |
| 容器化 | Docker 部署支持 |
| 多模型路由 | 动态模型选择 |

### 17.3 技术债务

| 债务 | 优先级 | 说明 |
|------|--------|------|
| 测试覆盖率 < 80% | P0 | 需补充单元测试 |
| 无性能基准测试 | P1 | 需建立性能指标 |
| 配置管理简陋 | P2 | 需配置中心 |

### 17.4 已知限制

- 大文件处理（> 1MB）性能差
- 复杂重构任务成功率低
- 无断点续传功能

---

## 18. 跨切面关注点

### 18.1 可观测性

#### 日志规范

```
[LEVEL] [TIMESTAMP] [MODULE] [REQUEST_ID] message
INFO  2026-03-28 10:00:00 Core.Agent abc123 Task started
```

#### 指标

| 指标 | 说明 |
|------|------|
| `mozi.task.count` | 任务总数 |
| `mozi.task.duration` | 任务耗时 |
| `mozi.tool.calls` | 工具调用次数 |
| `mozi.model.latency` | 模型响应延迟 |

### 18.2 配置管理

| 配置项 | 来源 | 说明 |
|--------|------|------|
| `MOZI_MODEL` | 环境变量 | 默认模型 |
| `MOZI_CONFIG_PATH` | 环境变量 | 配置文件路径 |
| `~/.mozi/config.json` | 配置文件 | 用户配置 |

### 18.3 错误处理

#### 错误码

| 错误码 | 说明 |
|--------|------|
| E1001 | 模型调用失败 |
| E1002 | 工具执行失败 |
| E2001 | 会话不存在 |
| E3001 | 权限不足 |
| E4001 | 配置错误 |

#### 降级策略

| 场景 | 降级行为 |
|------|----------|
| 模型超时 | 重试 3 次，失败后返回错误 |
| 工具执行失败 | 返回错误信息给用户 |
| 存储服务不可用 | 降级到内存模式 |

### 18.4 弹性模式

- **重试机制**：模型调用、工具执行支持指数退避重试
- **熔断器**：连续失败 5 次后熔断 60s
- **超时控制**：每个工具调用超时 30s

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v16.0 | 2026-03-28 | 拆分为独立模块文档，保留总览 |
| v15.0 | 2026-03-28 | 模块重命名 |
