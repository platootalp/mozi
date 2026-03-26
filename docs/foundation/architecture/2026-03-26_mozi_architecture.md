# AI Coding Agent 系统架构设计

## 1. 系统整体架构（四层）

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           第一层：接入层 (Ingress)                        │
│                                                                         │
│   CLI (Typer) │ Web UI (FastAPI) │ API Gateway │ IDE Extension          │
│   MCP Client  │                                                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                         第二层：编排层 (Orchestrator)                     │
│                                                                         │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────────┐ │
│   │  意图识别   │  │ 复杂度评估  │  │  任务路由器 │  │   会话管理    │ │
│   │  需求澄清   │  │  策略选择   │  │  DAG调度器  │  │   (生命周期)  │ │
│   └─────────────┘  └─────────────┘  └─────────────┘  └───────────────┘ │
│                                                                         │
│   • 单Agent FastPath (简单任务)                                         │
│   • 多Agent协作调度 (复杂任务，Orchestrator中心化调度)                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                         第三层：能力层 (Capabilities)                     │
│                                                                         │
│   ┌───────────────┐  ┌───────────────┐  ┌───────────────────────────┐  │
│   │   配置管理    │  │   工具框架    │  │       MCP 接入层          │  │
│   │               │  │               │  │                           │  │
│   │  config.json  │  │  • 内置工具   │  │  • stdio / sse / http     │  │
│   │  agents.json  │  │  • 工具权限   │  │  • 能力发现               │  │
│   │  tools.json   │  │  • 哈希锚定   │  │  • 健康检查               │  │
│   │  mcp.json     │  │  • HITL审批   │  │  • 安全防护               │  │
│   │  skills.json  │  │               │  │                           │  │
│   │               │  │  Skills引擎   │  │  安全与权限 (横切)        │  │
│   │  *.md 文档    │  │  • 工作流编排  │  │  • 沙箱隔离               │  │
│   │               │  │  • 参数模板   │  │  • 四层权限               │  │
│   │               │  │               │  │  • 审计日志               │  │
│   └───────────────┘  └───────────────┘  └───────────────────────────┘  │
│                                                                         │
│   配置加载优先级：环境变量 → 项目配置 → 用户全局 → 系统默认            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                      第四层：基础设施层 (Infrastructure)                  │
│                                                                         │
│   ┌─────────────┐  ┌─────────────────────┐  ┌─────────────┐  ┌────────┐ │
│   │    热数据   │  │       温数据        │  │    冷数据   │  │ 归档   │ │
│   │   (内存)    │  │     (向量库)        │  │  (SQLite)   │  │(文件)  │ │
│   │             │  │ 本地Qdrant/嵌入式   │  │             │  │        │ │
│   │ 会话上下文  │  │ Milvus/云端服务     │  │ 结构化数据  │  │ 历史   │ │
│   │ Agent状态   │  │ 语义向量/记忆索引   │  │ 任务状态    │  │ 日志   │ │
│   └─────────────┘  └─────────────────────┘  └─────────────┘  └────────┘ │
│                                                                         │
│   • 模型API接入 (OpenAI/Claude/Ollama)                                  │
│   • 网络层 / 沙箱运行时                                                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 技术选型

### 2.1 编程语言

| 层级 | 语言 | 选型理由 |
|------|------|----------|
| 核心引擎 | Python 3.11+ | 生态丰富，AI/ML库支持好，快速迭代 |
| 性能关键路径 | Rust (可选) | 工具调用、文件IO性能敏感部分 |
| CLI/Web | Python + Typer/FastAPI | 统一技术栈，降低维护成本 |

### 2.2 核心框架与库

| 用途 | 选型 | 备选 |
|------|------|------|
| Agent运行时 | LangGraph / Pydantic AI | 自研精简版 |
| 工作流编排 | 自研DAG引擎 | Temporal / Cadence |
| 向量数据库 | Qdrant | Milvus, Chroma |
| 关系数据库 | SQLite + aiosqlite | PostgreSQL (云端部署) |
| 配置解析 | Pydantic Settings | python-dotenv |
| 依赖注入 | python-dependency-injector | 手动管理 |
| CLI框架 | Typer + Rich | Click |

### 2.3 通信机制

| 场景 | 机制 | 序列化 |
|------|------|--------|
| 内部组件 | 异步消息队列 (asyncio Queue) | Python对象 |
| MCP通信 | stdio/sse/http/websocket | JSON-RPC |
| 持久化 | SQLite WAL | - |
| 缓存 | 内存LRU (可选Redis) | pickle/json |

---

## 3. 配置管理（能力层子模块）

### 3.1 文件组织

```
.mozi/                          # 项目级配置
├── config.json                 # 系统核心配置
├── agents.json                 # Agent注册表
├── tools.json                  # 工具策略配置
├── mcp.json                    # MCP服务配置
├── skills.json                 # Skill注册表
├── agents/                     # Agent提示词文档 (*.md)
├── skills/                     # Skill工作流文档 (*.md)
├── rules/                      # 项目规则 (*.md)
└── memory/                     # 持久化记忆 (*.md)

~/.mozi/                        # 用户全局配置
├── user.json                   # 用户偏好覆盖
├── agents/                     # 自定义Agent
└── skills/                     # 自定义Skill
```

### 3.2 配置Schema

**config.json** - 系统核心配置

| 字段 | 类型 | 说明 |
|------|------|------|
| `server` | Object | 服务端配置（host, port, ssl） |
| `storage` | Object | 存储层配置（SQLite路径、向量库连接等） |
| `security` | Object | 安全策略（审批规则、沙箱模式） |
| `features` | Object | 功能开关（实验性功能启用） |
| `logging` | Object | 日志配置（级别、输出、轮转策略） |

**agents.json** - Agent注册表

| 字段 | 类型 | 说明 |
|------|------|------|
| `agents` | Array | Agent定义列表 |
| `agents[].name` | String | Agent唯一标识 |
| `agents[].description` | String | 调度描述（用于意图匹配） |
| `agents[].mode` | Enum | `primary` / `subagent` / `hidden` |
| `agents[].prompt` | String | Markdown提示词文件路径 |
| `agents[].model` | Object | 模型配置（provider, model, temperature） |
| `agents[].permissions` | Object | 工具权限（read/edit/bash/webfetch/task） |
| `agents[].tools` | Array | 显式工具白名单 |
| `agents[].mcp_servers` | Array | 关联的MCP服务名称 |
| `agents[].max_steps` | Number | 单会话最大步数限制 |
| `agents[].timeout` | Number | 单次调用超时（秒） |
| `default_agent` | String | 默认使用的Agent名称 |
| `complexity_threshold` | Object | 复杂度评估阈值配置（见3.2节） |

**tools.json** - 工具策略配置

| 字段 | 类型 | 说明 |
|------|------|------|
| `policies` | Object | 全局工具策略 |
| `policies.*.default` | Enum | `allow` / `deny` / `ask` |
| `allowlist` | Array | 命令白名单（支持通配符，如 `"git push*"`） |
| `sandbox` | Object | 沙箱配置（mode, image, resources） |

**mcp.json** - MCP服务配置

| 字段 | 类型 | 说明 |
|------|------|------|
| `servers` | Object | MCP服务配置映射 |
| `servers.*.transport` | Enum | `stdio` / `sse` / `http` / `websocket` |
| `servers.*.command` | String | stdio模式下的启动命令 |
| `servers.*.url` | String | 网络模式下的服务端点 |
| `servers.*.env` | Object | 环境变量配置 |
| `servers.*.permissions` | Object | 该Server的工具权限覆盖 |

**skills.json** - Skill注册表

| 字段 | 类型 | 说明 |
|------|------|------|
| `scan_paths` | Array | Skill文档扫描路径列表 |
| `auto_load` | Boolean | 是否自动加载所有发现的Skill |
| `triggers` | Object | 触发词到Skill的映射 |

### 3.3 配置加载优先级（从高到低）

1. 环境变量 (`MOZI_*`) —— 用于临时覆盖
2. `.mozi/*.json` (项目本地) —— 项目特定配置
3. `user.json` (用户全局) —— 用户偏好
4. 系统默认配置 —— 兜底默认值

---

## 4. 编排层组件

### 4.1 意图识别器

**职责**：解析用户输入，识别任务类型和意图，检查需求完整性

**输入**：用户原始输入 + 当前会话上下文

**输出**：结构化意图描述 + 完整性评估 + 澄清问题（如有）

### 4.2 复杂度评估引擎

**评估维度与权重**：

| 维度 | 权重 | 说明 |
|------|------|------|
| 预估修改文件数 | 30% | 根据意图推断需要修改的文件数量 |
| 技术栈多样性 | 20% | 涉及的技术栈种类数 |
| 跨模块依赖深度 | 30% | 静态分析依赖图，评估影响范围 |
| 历史成功率 | 20% | 相似历史任务的完成成功率 |

**阈值策略**：

| 加权总分 | 复杂度等级 | 路由策略 |
|----------|------------|----------|
| ≤ 40 | SIMPLE | 单Agent FastPath，ReAct循环内隐式规划 |
| 40 < 总分 ≤ 70 | MEDIUM | 单Agent执行，步骤列表追踪（内存中） |
| > 70 | COMPLEX | 多Agent协作，Orchestrator生成DAG计划，产物可导出 |

**说明**：
- 大型单体仓库中修改1个核心文件可能影响数十个模块 → 依赖深度权重提升
- 微服务架构中修改3个独立文件 → 依赖深度权重降低

### 4.3 任务路由器

**路由策略**：

| 复杂度 | 执行通道 | 说明 |
|--------|----------|------|
| SIMPLE | 单Agent FastPath | 直接实例化Builder Agent执行，无显式规划产物 |
| MEDIUM | 单Agent增强监控 | 单Agent执行，增加步骤限制和监控，执行日志可见 |
| COMPLEX | 多Agent协作（Orchestrator调度 + DAG执行） | 生成DAG计划，自动化并行，产物可导出为Markdown |

**与竞品对比**：
- **Cursor Plan Mode**: 研究→澄清→计划→执行，计划可编辑，用户手动触发
- **OpenCode Plan Agent**: 只读分析，产出对话式建议，需切回Build执行
- **Mozi COMPLEX模式**: 调度器**自动**生成DAG，自动化并行，无需用户显式选择

### 4.4 规划模式详细设计

| 复杂度 | 规划行为 | 产物 | 用户可见性 |
|--------|----------|------|------------|
| SIMPLE | 无显式规划，ReAct（Reasoning + Acting）循环内隐式规划 | 无 | 无 |
| MEDIUM | 步骤列表追踪（内存中） | 执行日志 | 低 |
| COMPLEX | 生成DAG（Directed Acyclic Graph，有向无环图）计划，支持导出 | Markdown计划文档 | 高 |

**DAG计划结构示例**：

```json
{
  "nodes": [
    {"id": "explore", "type": "subagent", "agent": "explorer"},
    {"id": "impl-a", "type": "subagent", "agent": "builder", "deps": ["explore"]},
    {"id": "impl-b", "type": "subagent", "agent": "builder", "deps": ["explore"]},
    {"id": "review", "type": "subagent", "agent": "reviewer", "deps": ["impl-a", "impl-b"]}
  ]
}
```

### 4.5 会话管理层

**生命周期管理**：

| 操作 | 说明 |
|------|------|
| create | 创建新会话，分配ID和初始上下文 |
| resume | 恢复已有会话，加载历史状态 |
| fork | 从父会话创建子会话（用于并行Subagent） |
| archive | 归档会话，数据移至冷存储 |

**上下文压缩策略**：

- **触发条件**：上下文Token数接近模型上限的80%
- **压缩动作**：
  1. 生成历史对话摘要
  2. 长工具结果卸载到文件系统
  3. 触发记忆冲刷，Agent写入MEMORY.md

### 4.6 请求生命周期与数据流

#### 4.6.1 同步请求流程（CLI模式）

```
User Input
    │
    ▼
┌─────────────────┐
│   CLI Parser    │ ──→ Typer解析参数
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Config Loader  │ ──→ 合并配置（系统→用户→项目→环境变量）
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Orchestrator  │ ──→ 意图识别 → 复杂度评估 → 路由决策
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌─────────────┐
│Simple  │ │  Complex    │
│FastPath│ │  DAG生成    │
└───┬────┘ └──────┬──────┘
    │             │
    ▼             ▼
┌─────────────────────────┐
│     Agent Runtime       │ ──→ ReAct循环，工具调用
│  ┌─────┐ ┌─────┐       │
│  │Tool1│ │Tool2│ ...   │
│  └──┬──┘ └──┬──┘       │
│     └───────┘           │
└────────┬────────────────┘
         │
         ▼
┌─────────────────┐
│  Response组装   │ ──→ 结果聚合，格式化输出
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Persistence   │ ──→ 异步写入SQLite/向量库
└─────────────────┘
```

#### 4.6.2 异步事件流

**事件总线设计**:

```
                    ┌──────────────┐
     ┌─────────────→│ Event Bus    │←─────────────┐
     │              │ (asyncio)    │              │
     │              └──────┬───────┘              │
     │                     │                       │
┌────┴────┐          ┌─────┴──────┐         ┌────┴────┐
│Producer │          │  Router    │         │Consumer │
│- Ingress│          │  - 分发    │         │- Logger │
│- Agent  │          │  - 过滤    │         │- Metrics│
│- Tools  │          │  - 转换    │         │- Audit  │
└─────────┘          └────────────┘         └─────────┘
```

**关键事件类型**:

| 事件 | 生产者 | 消费者 | 处理时延要求 |
|------|--------|--------|--------------|
| tool.called | Agent | Logger, Audit | 同步 |
| context.compressed | SessionMgr | Storage | 异步 |
| agent.completed | Runtime | Metrics | 异步 |
| mcp.disconnected | MCPMgr | HealthChecker | 同步 |

#### 4.6.3 跨层调用链示例

**MCP工具调用链路**:

```
Layer 4: 用户层
  │ "搜索代码"
  ▼
Layer 3: 编排层 (Orchestrator)
  │ 识别意图 → 路由到Agent
  ▼
Layer 2: 能力层 (Capabilities)
  │ Agent Runtime
  │   └─→ 决策使用 mcp-server-git
  ▼
Layer 2: MCP接入层
  │ 查找Server → 建立stdio连接
  │   └─→ 发送JSON-RPC请求
  ▼
Layer 1: 外部进程
  │ mcp-server-git 执行 git grep
  │   └─→ 返回结果
  ▼
Layer 2: 结果解析 → 返回Agent
Layer 3: 结果聚合 → 返回用户
```

---

## 5. 能力层组件

### 5.1 MCP接入层

**支持传输协议**：

| 协议 | 适用场景 | 说明 |
|------|----------|------|
| stdio | 本地工具 | 启动子进程，stdin/stdout通信 |
| sse | 远程服务 | Server-Sent Events单向流 |
| http | 远程服务 | HTTP streaming双向流 |
| websocket | 实时交互 | 全双工长连接 |

**能力协商流程**：

1. 建立传输连接
2. 发送初始化握手
3. 接收Server能力声明（Tools/Resources/Prompts/Roots）
4. 根据权限策略过滤可用能力
5. 注册到工具框架

#### 5.1.1 MCP安全防护

| 风险 | 防护措施 |
|------|----------|
| 配置注入（CVE-2025-54135/54136） | mcp.json修改需重新审批 |
| 权限提升 | MCP工具受tools.json策略约束，非继承Server声明 |
| 连接隔离 | 每个MCP Server独立进程，崩溃不影响主系统 |
| 网络限制 | 按tools.json的web策略控制MCP网络访问 |

### 5.2 Skills引擎

**Skill文档结构**（Markdown）：

```markdown
---
name: skill-name
description: Skill功能描述
tags: [tag1, tag2]
triggers: ["触发词1", "触发词2"]
---

# Skill名称

## 适用场景
何时使用该Skill

## 执行步骤
1. 步骤一
2. 步骤二
   - 子步骤

## 检查清单
- [ ] 检查项1
- [ ] 检查项2

## 示例
代码示例或输出样例
```

**执行流程**：

1. 解析Frontmatter元数据
2. 匹配触发条件
3. 参数模板填充
4. 按步骤执行（可能涉及工具调用）
5. 检查清单验证
6. 返回结果

### 5.3 工具框架

**内置工具列表**：

| 工具 | 类型 | 权限要求 | 说明 |
|------|------|----------|------|
| read | 文件 | allow | 读取文件内容 |
| write | 文件 | ask | 写入新文件 |
| edit | 文件 | ask | 基于哈希锚定的安全编辑 |
| bash | 执行 | ask | 执行shell命令 |
| grep | 搜索 | allow | 代码内容搜索 |
| glob | 搜索 | allow | 文件模式匹配 |
| lsp | 语义 | allow | LSP服务器查询 |
| ast_grep | 语义 | allow | AST语法树查询 |
| web_search | 外部 | ask | 网络搜索 |
| web_fetch | 外部 | ask | 网页抓取 |
| task | 编排 | allow | 委派子任务（调用其他Agent） |

**哈希锚定编辑机制**：

解决多Agent并发编辑冲突，每处编辑包含：
- 行号标识（LINE#ID）
- 原始内容哈希
- 期望替换内容

**冲突处理策略**：

1. **首次冲突** → 自动重试（重新读取文件最新状态，重新计算哈希）
2. **连续冲突**（重试3次失败）→ 向用户展示冲突详情，等待决策
3. **涉及关键文件**（如.gitignore、配置文件）→ 强制转为HITL审批模式

编辑前校验锚点是否匹配，不匹配时按上述策略处理。

---

## 6. 安全与权限（能力层横切关注点）

### 6.1 四层安全防护

| 层级 | 机制 | 说明 |
|------|------|------|
| 沙箱隔离 | Sandbox | 工具执行环境隔离（off/non-main/all） |
| 工具策略 | Tool Policy | 工具级权限控制（allow/deny/ask） |
| 审批机制 | HITL（Human-in-the-Loop） | 敏感操作人工介入确认 |
| 审计日志 | Audit | 全量操作记录与追溯 |

### 6.2 权限层级（deny优先）

1. 全局默认策略
2. Agent级策略覆盖
3. 工具特定策略
4. 沙箱内策略
5. 单次调用覆盖

#### 6.2.1 冲突解决规则

同级别冲突时，按以下优先级（从高到低）：

1. `deny` 显式声明
2. `ask` 显式声明
3. `allow` 显式声明
4. 继承上级策略

**示例场景**：
- Agent级 `bash: allow` + 工具级 `"git push": deny` → `deny` 生效
- Agent级 `"npm install": ask` + 全局 `bash: allow` → `ask` 生效

### 6.3 敏感操作类型

- bash命令执行
- 文件覆盖写入（特别是配置文件）
- MCP工具调用
- 网络请求（web_search/web_fetch）

### 6.4 密钥管理

| 密钥类型 | 存储方式 | 轮换策略 |
|----------|----------|----------|
| API Keys | 系统密钥链 / HashiCorp Vault | 90天 |
| MCP凭证 | 加密文件 (AES-256) | 按需 |
| 数据库密码 | 环境变量 / K8s Secret | 180天 |

### 6.5 数据安全

- **静态加密**: SQLite使用SQLCipher加密
- **传输加密**: TLS 1.3 (MCP/http)
- **内存安全**: 敏感数据使用后立即清零

### 6.6 审计要求

| 操作 | 记录内容 | 保留期 |
|------|----------|--------|
| 敏感工具调用 | 用户、时间、参数、结果 | 1年 |
| 配置变更 | 变更前后、操作人 | 永久 |
| 权限变更 | 授予/撤销记录 | 永久 |

---

## 7. 错误处理与韧性设计

### 7.1 错误分类与处理策略

| 错误类型 | 处理策略 | 说明 |
|----------|----------|------|
| 模型调用失败 | 指数退避重试 | 最多3次，间隔1s/2s/4s |
| 工具执行失败 | 错误分类→重试/降级/终止 | 区分可重试错误和逻辑错误 |
| MCP连接失败 | 健康检查+自动重连 | 带熔断机制，连续失败5次后暂停 |
| 上下文超限 | 触发压缩+摘要生成 | 保留关键信息，卸载长文本 |
| Agent崩溃 | 会话恢复+状态回滚 | 从上一个checkpoint恢复 |

**Checkpoint策略**：

| 维度 | 策略 |
|------|------|
| 创建时机 | 每完成一个工具调用后、每个Agent步骤完成后、显式检查点 |
| 存储内容 | 会话上下文、工具状态、执行位置标记、变量绑定 |
| 保留策略 | 保留最近10个checkpoint，自动清理超过7天的旧数据 |
| 恢复粒度 | 可选择回滚到最近checkpoint或完全重启会话 |

### 7.2 熔断与降级

**熔断机制**：
- 连续失败阈值：5次
- 熔断时间窗口：60秒
- 半开状态：允许1次探测请求

**降级策略**：
- 向量库不可用：降级为纯关键词检索
- MCP服务不可用：禁用该服务相关工具
- 模型API限流：切换备用模型提供商

### 7.3 限流与成本控制

| 维度 | 策略 | 配置 |
|------|------|------|
| 模型调用 | Token/分钟限制 | configurable per provider |
| 工具调用 | 次数/会话限制 | 防止无限循环 |
| MCP请求 | 并发连接限制 | per server configurable |
| 成本告警 | 单会话预算上限 | 超出时提示用户确认 |

### 7.4 系统级容错设计

#### 7.4.1 隔离策略

| 隔离级别 | 机制 | 场景 |
|----------|------|------|
| 进程隔离 | 每个MCP Server独立进程 | MCP崩溃不影响主系统 |
| 线程隔离 | Agent运行在独立线程池 | 单个Agent阻塞不拖垮系统 |
| 资源隔离 | 内存/CPU限制（cgroups） | 防止单个任务耗尽资源 |

#### 7.4.2 冗余与备份

**多模型冗余**:
- 主模型：Claude 3.5 Sonnet
- 备用模型：GPT-4 / Claude 3 Haiku
- 降级策略：主模型超时/失败 → 自动切换备用

**存储冗余**:
- 热数据：内存双副本
- 温数据：向量库主从
- 冷数据：SQLite定时备份到文件

#### 7.4.3 优雅降级策略

| 故障场景 | 降级行为 | 用户体验 |
|----------|----------|----------|
| 向量库不可用 | 回退到关键词检索 | 搜索结果质量下降，功能可用 |
| MCP服务崩溃 | 禁用该服务，提示用户 | 相关工具不可用，其他正常 |
| 模型API限流 | 切换备用模型/延迟重试 | 响应变慢，功能可用 |
| 上下文超限 | 强制压缩，丢失早期细节 | 长会话精度下降 |

---

## 8. 可观测性

### 8.1 三大支柱

| 支柱 | 实现 | 存储 | 查询 |
|------|------|------|------|
| **Metrics** | Prometheus客户端 | Prometheus/Grafana | PromQL |
| **Logging** | 结构化JSON日志 | Loki/Elasticsearch | LogQL/KQL |
| **Tracing** | OpenTelemetry | Jaeger/Zipkin | TraceID查询 |

### 8.2 关键指标（SLI/SLO）

| 指标 | 类型 | SLO | 告警阈值 |
|------|------|-----|----------|
| 请求延迟 (p99) | Latency | < 5s | > 10s |
| 错误率 | Error Rate | < 1% | > 5% |
| 吞吐量 | Traffic | - | 突发 > 10x |
| 饱和度 | Saturation | CPU < 70% | > 85% |

### 8.3 链路追踪

**Trace结构示例**:

```
Trace: user_request_123
├── Span: intent_recognition (50ms)
├── Span: complexity_assessment (30ms)
├── Span: agent_execution (2000ms)
│   ├── Span: tool_call_1 (500ms)
│   ├── Span: tool_call_2 (800ms)
│   └── Span: llm_inference (600ms)
└── Span: persistence (20ms)
```

**上下文传播**: W3C Trace Context / Baggage

### 8.4 告警规则

| 告警 | 条件 | 级别 | 通知渠道 |
|------|------|------|----------|
| 高错误率 | 错误率>5%持续5min | P1 | PagerDuty + Slack |
| 高延迟 | p99>10s持续5min | P2 | Slack |
| MCP服务宕机 | 健康检查失败 | P2 | Slack |
| 磁盘不足 | 剩余<10% | P1 | PagerDuty |

### 8.5 日志与追踪详情

| 类型 | 内容 | 存储位置 |
|------|------|----------|
| 操作日志 | 工具调用、Agent切换、用户操作 | SQLite + 文件 |
| 审计日志 | 敏感操作、权限变更、审批记录 | 文件（只追加） |
| 性能追踪 | 模型延迟、工具执行时间、Token消耗 | SQLite |
| 错误日志 | 异常堆栈、错误上下文 | 文件 |

### 8.6 健康检查

- **API端点**: `/health` 返回各组件状态
- **MCP健康**: 定期ping，标记不可用服务
- **存储健康**: 检查SQLite和向量库连接

---

## 9. 基础设施层

### 9.1 四级存储架构

| 层级 | 载体 | 数据类型 | 持久性 | 访问延迟 |
|------|------|----------|--------|----------|
| 热 | 内存 | 当前会话上下文、Agent状态、工具缓存 | 会话级 | 极低 |
| 温 | 向量库 | 语义向量、代码嵌入、记忆索引 | 持久 | 低 |
| 冷 | SQLite | 结构化数据、任务状态、调用记录 | 持久 | 中 |
| 归档 | 文件系统 | 历史会话、日志归档、大文件卸载 | 持久 | 高 |

**向量库部署选项**（可配置）：
- **本地Qdrant**: 本地Docker或二进制运行
- **嵌入式Milvus**: 单机Lite模式
- **云端服务**: 托管Qdrant/Milvus集群（需显式配置）

**SQLite并发优化策略**：

| 优化手段 | 说明 |
|----------|------|
| WAL模式 | Write-Ahead Logging支持并发读写 |
| 批量写入缓冲 | 100ms/1000条批量提交 |
| 大表自动分区 | 按日期分区操作日志表 |
| 读写分离 | 查询走副本，写入走主库 |

**自动分层策略**：

- 热→温：会话结束或超过时间阈值
- 温→冷：向量访问频率降低
- 冷→归档：超过保留策略期限

### 9.2 双轨检索策略

| 场景 | 策略 | 工具 |
|------|------|------|
| 工作区内 | 精准检索 | grep/glob/ast_grep |
| 跨仓库 | 语义检索 | 向量库相似度搜索 |
| 混合 | 混合排序 | 结合精准命中和语义相似度 |

---

## 10. 部署架构与运维

### 10.1 部署模式

| 模式 | 适用场景 | 资源需求 |
|------|----------|----------|
| **单机模式** | 个人开发者 | 4核8GB |
| **Docker Compose** | 小团队 | 8核16GB |
| **K8s集群** | 企业/大规模 | 按需 |

### 10.2 部署架构

```
┌─────────────────────────────────────────────────────────┐
│                    本地部署 (Local)                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Core Engine                                    │   │
│  │  - Orchestrator                                │   │
│  │  - Agent Runtime                               │   │
│  │  - Tool Framework                              │   │
│  │  - Skills Engine                               │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Local Storage                                  │   │
│  │  - SQLite (结构化数据)                          │   │
│  │  - Qdrant/Milvus (本地或嵌入式)                 │   │
│  │  - File System (文档/归档)                      │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                            │
                            ↓ 可选连接
┌─────────────────────────────────────────────────────────┐
│              云端服务 (Cloud Services)                   │
│  ┌─────────────────────┐  ┌─────────────────────────┐  │
│  │  Vector Database    │  │  Model API              │  │
│  │  (托管Qdrant/Milvus)│  │  (OpenAI/Claude/Ollama) │  │
│  └─────────────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**混合模式说明**：

- 核心引擎本地运行，确保代码安全和低延迟
- 向量库默认本地（Qdrant/嵌入式Milvus），可配置云端以支持大规模语义检索
- 模型API可配置多提供商，支持本地Ollama或云端服务

### 10.3 配置管理示例

```yaml
# docker-compose.yml 示例
version: '3.8'
services:
  mozi-core:
    image: mozi/core:latest
    volumes:
      - ./.mozi:/app/.mozi
      - ~/.mozi:/root/.mozi
    environment:
      - MOZI_LOG_LEVEL=info

  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - qdrant-data:/qdrant/storage
```

### 10.4 升级策略

| 策略 | 说明 | 风险 |
|------|------|------|
| 滚动升级 | 逐个实例升级 | 低，但需兼容版本 |
| 蓝绿部署 | 新旧版本并行 | 中，资源翻倍 |
| 金丝雀 | 小流量验证 | 低，推荐 |

### 10.5 备份策略

| 数据 | 频率 | 保留 | 方式 |
|------|------|------|------|
| SQLite | 实时 | 7天 | WAL + 定时快照 |
| 向量库 | 每日 | 30天 | 全量导出 |
| 配置文件 | 每次修改 | 永久 | Git版本控制 |

---

## 11. 可扩展性设计

### 11.1 水平扩展架构

```
                    ┌──────────────┐
                    │   Load       │
                    │  Balancer    │
                    └──────┬───────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
      ┌─────────┐     ┌─────────┐     ┌─────────┐
      │ Mozi    │     │ Mozi    │     │ Mozi    │
      │Instance │     │Instance │     │Instance │
      │  #1     │     │  #2     │     │  #3     │
      └────┬────┘     └────┬────┘     └────┬────┘
           │               │               │
           └───────────────┼───────────────┘
                           ▼
                    ┌──────────────┐
                    │   Shared     │
                    │   Storage    │
                    │ (PostgreSQL  │
                    │  /Redis)     │
                    └──────────────┘
```

### 11.2 有状态 vs 无状态

| 组件 | 状态 | 扩展策略 |
|------|------|----------|
| Ingress (API Gateway) | 无状态 | 水平扩展 + 负载均衡 |
| Orchestrator | 有状态（会话） | 粘性会话 / 会话迁移 |
| Agent Runtime | 有状态（执行中） | 垂直扩展 + 限流 |
| Storage | 有状态 | 主从复制 / 分片 |

### 11.3 插件化扩展点

**扩展接口设计**:

```python
# 自定义Agent注册
class CustomAgent(AgentPlugin):
    name = "my-agent"
    description = "自定义Agent"

    async def execute(self, context: Context) -> Result:
        pass

# 自定义工具注册
class CustomTool(ToolPlugin):
    name = "my-tool"
    permissions = ["read"]

    async def run(self, params: dict) -> Result:
        pass
```

---

## 12. 与其他系统的对比定位

| 维度 | Mozi | Cursor | OpenCode | OpenClaw |
|------|------|--------|----------|----------|
| **部署模式** | 混合（本地+云端） | 云端IDE | 本地CLI | 本地CLI |
| **规划模式** | **自适应**（SIMPLE/MEDIUM/COMPLEX自动路由） | Plan Mode显式 | 双主Agent分离（Tab切换Build/Plan） | ReAct隐式 |
| **多Agent** | **Orchestrator中心化调度** | Plan Mode + Subagents | Task工具层级委托 | Sub-agent Lane |
| **配置格式** | JSON + Markdown | Rules(.mdc) | JSON/Markdown | YAML/Markdown |
| **工具扩展** | MCP + 内置 | MCP | 内置 + MCP | 插件系统 |
| **记忆系统** | 四级存储+自动分层+双轨检索 | 云端Knowledge Base | 插件依赖 | 本地Markdown |
| **安全模型** | 四层防护+HITL | 默认审批 | 权限配置 | 沙箱+策略 |
| **心跳/主动任务** | **内置Heartbeat** | 无 | 无 | 内置Heartbeat |

**Mozi核心差异化优势**：

1. **自适应规划**: 无需用户显式选择模式，系统自动根据复杂度路由
2. **Orchestrator中心化调度**: 区别于OpenCode的层级委托和Cursor的并行执行
3. **四级存储+自动分层**: 竞品多为单一存储或需手动配置
4. **完整四层安全防护**: 含HITL审批机制，层级最完整

---

## 附录：术语表

| 术语 | 英文全称 | 含义 |
|------|----------|------|
| HITL | Human-in-the-Loop | 人工介入确认，敏感操作需用户批准 |
| DAG | Directed Acyclic Graph | 有向无环图，用于任务依赖编排 |
| MCP | Model Context Protocol | 模型上下文协议，标准化工具扩展接口 |
| ReAct | Reasoning + Acting | 推理+行动循环，LLM Agent基础模式 |
| Lane | - | 执行通道，用于并发控制与隔离 |
| FastPath | - | 快速通道，简单任务的直接执行路径 |

---

*文档版本: 1.3*
*更新日期: 2026-03-26*
