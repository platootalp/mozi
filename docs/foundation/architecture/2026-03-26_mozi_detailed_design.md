# Mozi AI Coding Agent 详细设计文档

## 文档信息

| 字段 | 内容 |
|------|------|
| 版本 | v1.1 |
| 状态 | 评审中（第二轮） |
| 创建日期 | 2026-03-26 |
| 用途 | 架构评审会议决策依据 |

---

## 第一章 系统核心工作流

### 1.1 接入层工作流（Ingress）

#### 1.1.1 CLI 模式（Typer）

```
用户输入
    │
    ▼
Typer CLI Parser ──→ 参数解析 + 命令识别
    │
    ▼
Config Loader ──→ 合并配置（系统→用户→项目→环境变量）
    │
    ▼
Orchestrator ──→ 意图识别 → 复杂度评估 → 路由决策
```

**核心场景**：
- 单次命令执行：`mozi "帮我创建一个用户登录API"`
- 交互模式：`mozi --interactive` 进入 REPL
- 配置文件指定：`mozi --config .mozi/dev.json "..."`

#### 1.1.2 Web UI 模式（FastAPI）

```
浏览器请求
    │
    ▼
FastAPI ──→ Session 创建/恢复
    │
    ▼
WebSocket 长连接 ──→ 流式响应
    │
    ▼
Orchestrator ──→ 同 CLI 路由逻辑
```

**核心场景**：
- 新会话创建 → 返回 session_id
- 会话恢复 → 加载历史上下文
- 流式输出 → SSE/WebSocket 推送

#### 1.1.3 MCP Client 模式

```
MCP Host (如 Claude Desktop)
    │
    ▼
JSON-RPC over stdio/sse/http
    │
    ▼
MCP Client ──→ 请求路由到 Orchestrator
    │
    ▼
响应通过同一通道返回
```

**核心场景**：
- 工具调用（tools/call）
- 资源访问（resources/read）
- 提示模板（prompts/get）

---

### 1.2 编排层工作流（Orchestrator）

编排层是系统的核心调度中心，负责从用户输入到任务完成的完整决策流程。

#### 1.2.1 意图识别流程

```
用户原始输入
    │
    ▼
意图识别器（Intent Classifier）
    ├── 任务类型分类：bug_fix / feature_add / refactor / docs / test / ci / ...
    ├── 涉及范围：single_file / multi_file / cross_module / cross_repo
    ├── 依赖推断：显式依赖 / 隐式依赖 / 无依赖
    │
    ▼
结构化意图对象
{
  "task_type": "feature_add",
  "scope": "multi_file",
  "explicit_deps": ["src/auth.py", "tests/auth_test.py"],
  "implied_deps": ["src/db.py"],
  "clarification_needed": false,
  "confidence": 0.92
}
```

**完整性评估**：如果意图缺失关键信息（如目标文件、预期行为），触发需求澄清流程。

**置信度阈值表**：

| 置信度范围 | 决策 | 行为 |
|------------|------|------|
| confidence ≥ 0.8 | 直接执行 | 使用识别出的意图 |
| 0.5 ≤ confidence < 0.8 | 触发澄清 | 向用户提问补充信息 |
| confidence < 0.5 | 拒绝/重试 | 提示用户澄清需求，或使用默认假设 |

**澄清策略**：
- 提供默认假设 + 用户确认（而非先澄清后执行），减少交互成本
- 支持意图假设跳过（高级用户可配置）
- 建立澄清-执行反馈循环，持续修正意图模型

#### 1.2.2 复杂度评估流程

```
结构化意图对象
    │
    ▼
复杂度评估引擎 ──→ 四个维度加权评分
    │
    ├── 预估修改文件数（权重 30%）
    │     └── 分析意图推断 + 历史模式匹配
    ├── 技术栈多样性（权重 20%）
    │     └── 识别涉及的语言/框架数量
    ├── 跨模块依赖深度（权重 30%）
    │     └── 静态分析依赖图
    └── 历史成功率（权重 20%）
          └── 检索相似历史任务
    │
    ▼
复杂度等级
┌─────────────────────────────────────────────┐
│  ≤40 分      │ SIMPLE  │ 单Agent FastPath    │
│  41-70 分    │ MEDIUM  │ 单Agent+监控         │
│  >70 分      │ COMPLEX │ 多Agent DAG调度      │
└─────────────────────────────────────────────┘
```

#### 1.2.3 任务路由决策

```
复杂度等级
    │
    ├── SIMPLE → 直接实例化 Builder Agent，执行 ReAct 循环
    │
    ├── MEDIUM → 单Agent执行，启用步骤限制 + 执行日志
    │
    └── COMPLEX
          │
          ▼
      DAG 计划生成器
          │
          ├── 分析任务依赖关系
          ├── 识别可并行节点
          ├── 生成拓扑排序序列
          │
          ▼
      执行调度器
          │
          ├── 按依赖顺序实例化 Subagent
          ├── 并行执行无依赖节点
          ├── 收集结果，汇总响应
          │
          ▼
      产物：Markdown 格式 DAG 计划（可选导出）
```

**与竞品对比**：

| 系统 | 规划行为 | 用户可见性 | 自动化程度 |
|------|----------|------------|------------|
| Cursor Plan Mode | 研究→澄清→计划→执行 | 高，可编辑 | 手动触发 |
| OpenCode Plan Agent | 只读分析 | 对话式建议 | 需切换 |
| **Mozi COMPLEX** | **自动DAG生成** | **Markdown导出** | **全自动** |

#### 1.2.4 DAG 执行上下文传播

```
根会话（User Request）
    │
    ├── fork() → 子会话 A（explorer）
    ├── fork() → 子会话 B（builder-impl-a）
    └── fork() → 子会话 C（builder-impl-b）
           │
           ▼
    各子会话共享：
    - 项目配置（.mozi/）
    - 向量记忆索引
    - 工具权限（受父会话约束）
           │
           ▼
    各子会话独立：
    - Agent 状态
    - 中间产物
    - 工具执行沙箱
```

---

### 1.3 能力层工作流（Capabilities）

#### 1.3.1 配置加载流程

```
启动时配置合并
    │
    ▼
系统默认配置（代码中）
    │
    ▼
用户全局配置 ~/.mozi/user.json
    │
    ▼
项目本地配置 .mozi/*.json
    │
    ▼
环境变量 MOZI_* 覆盖
    │
    ▼
最终配置（内存中，运行时可修改）
```

**配置变更监听**：使用 watchdog 监控 `.mozi/` 目录，变更时自动重新加载并应用。

#### 1.3.2 工具框架执行流程

```
工具调用请求
    │
    ▼
权限检查（deny优先，五级覆盖）
    │
    ├── 命中 deny → 拒绝执行
    ├── 命中 ask → 暂停，发送 HITL 审批
    └── 允许通过
    │
    ▼
哈希锚定校验（edit/write 工具）
    │
    ├── 读取当前文件内容
    ├── 计算锚点哈希
    ├── 匹配则执行，不匹配则触发冲突处理
    │
    ▼
沙箱执行
    │
    ├── off: 直接执行
    ├── non-main: 非主文件在沙箱
    └── all: 全部在沙箱
    │
    ▼
结果返回 + 审计日志记录
```

**哈希锚定冲突处理**：

```
首次冲突
    │
    ▼
自动重试（重新读取文件，重新计算哈希）
    │
    ▼
连续3次冲突
    │
    ▼
展示冲突详情给用户，等待决策
    │
    ▼
涉及关键文件 → 强制 HITL 审批模式
```

#### 1.3.3 MCP 接入流程

```
MCP Server 配置加载（mcp.json）
    │
    ▼
传输层建立
    │
    ├── stdio: 启动子进程，stdin/stdout 通信
    ├── sse: 建立 Server-Sent Events 连接
    ├── http: 建立 HTTP streaming 连接
    └── websocket: 建立全双工长连接
    │
    ▼
能力协商
    │
    ├── 发送 initialize 请求
    ├── 接收 Server 能力声明（tools/resources/prompts）
    └── 按 tools.json 权限过滤可用能力
    │
    ▼
健康检查（定期 ping）
    │
    ▼
工具注册到工具框架
```

**MCP 安全防护**：

| 风险 | 防护措施 |
|------|----------|
| 配置注入（CVE-2025-54135/54136） | mcp.json 修改需重新审批 |
| 权限提升 | MCP 工具受 tools.json 约束，非继承 Server 声明 |
| 连接隔离 | 每个 MCP Server 独立进程 |
| 网络限制 | 按 tools.json 的 web 策略控制 MCP 网络访问 |

#### 1.3.4 Skills 引擎执行流程

```
触发条件匹配
    │
    ├── 显式触发词：skills.json 中的 triggers 映射
    └── 隐式触发：上下文自动推断
    │
    ▼
解析 Skill 文档（Markdown + Frontmatter）
    │
    ├── 提取元数据（name, description, tags）
    ├── 解析执行步骤
    └── 提取检查清单
    │
    ▼
参数模板填充
    │
    ▼
按步骤执行（可能涉及工具调用）
    │
    ▼
检查清单验证
    │
    ▼
结果返回
```

---

### 1.4 基础设施层工作流（Infrastructure）

#### 1.4.1 四级存储数据流转

```
┌─────────────────────────────────────────────────────────┐
│                         热数据层                         │
│                    （内存，LRU 缓存）                     │
│                                                         │
│  会话上下文、Agent 运行时状态、工具结果缓存                │
│                                                         │
│  生命周期：会话级，会话结束后流转                         │
└─────────────────────────┬───────────────────────────────┘
                          │ 自动分层触发
┌─────────────────────────▼───────────────────────────────┐
│                         温数据层                         │
│                    （向量库 Qdrant）                     │
│                                                         │
│  语义向量、代码嵌入、记忆索引、代码片段 Embedding          │
│                                                         │
│  生命周期：持久，访问频率降低时流转到冷层                   │
└─────────────────────────┬───────────────────────────────┘
                          │ 自动分层触发
┌─────────────────────────▼───────────────────────────────┐
│                         冷数据层                         │
│                    （SQLite WAL）                       │
│                                                         │
│  结构化数据、任务状态、调用记录、审计日志                   │
│                                                         │
│  生命周期：持久，超过保留期限后流转到归档层                 │
└─────────────────────────┬───────────────────────────────┘
                          │ 定时任务触发
┌─────────────────────────▼───────────────────────────────┐
│                        归档层                            │
│                   （文件系统）                            │
│                                                         │
│  历史会话记录、大型日志文件、大型工具输出卸载                │
│                                                         │
│  生命周期：永久保留，可按需恢复                            │
└─────────────────────────────────────────────────────────┘
```

**自动分层触发条件**：

| 流转方向 | 触发条件 |
|----------|----------|
| 热→温 | 会话结束，或超过 30 分钟无活跃访问 |
| 温→冷 | 30 天内访问频率低于阈值 |
| 冷→归档 | 超过 180 天保留期限 |

#### 1.4.2 双轨检索流程

```
用户查询（工作区内）
    │
    ▼
精准检索（grep/glob/ast_grep）
    │
    ├── 文件名模式匹配（glob）
    ├── 文件内容搜索（grep）
    └── AST 语义查询（ast_grep）
    │
    ▼
结果排序与去重
    │
    ▼
返回结果（毫秒级延迟）
```

```
用户查询（跨仓库/语义理解）
    │
    ▼
向量检索（Qdrant）
    │
    ├── 查询文本 Embedding
    ├── 余弦相似度搜索
    └── Top-K 结果召回
    │
    ▼
结果与精准检索混合排序
    │
    ▼
返回结果（百毫秒级延迟）
```

---

## 第二章 技术难点分析

### 2.1 架构设计挑战

#### 2.1.1 复杂度评估准确性

**难点描述**：复杂度评估是路由决策的基础，评分不准确会导致：
- 简单任务被误判为复杂 → 不必要的 DAG 开销
- 复杂任务被误判为简单 → 执行失败或质量不足

**当前方案**：
- 四维度加权评分（文件数、技术栈、依赖深度、历史成功率）
- 静态分析依赖图推断影响范围
- 历史任务模式匹配

**风险点**：
- 依赖图静态分析在大型单体仓库中不准确
- 历史任务样本不足时成功率权重失效
- 技术栈多样性权重主观性较强

**优化方向**：
- 引入动态分析（试运行小范围变更，观察影响）
- 建立任务特征库，积累标注数据
- 可配置阈值，允许用户根据项目特点调整

#### 2.1.2 多 Agent 协调冲突

**难点描述**：多个 Agent 并行执行时可能产生：
- 输出冲突（多个 Agent 改同一文件）
- 执行顺序错误（依赖方先于被依赖方完成）
- 资源竞争（同时调用同一 MCP 服务）

**当前方案**：
- 哈希锚定编辑（LINE#ID + 原始内容哈希）
- DAG 拓扑排序保证执行顺序
- MCP 连接隔离（每个 Server 独立进程）

**风险点**：
- 哈希锚定在高频并发下重试成本高
- DAG 依赖由人工定义或静态分析推断，不完整 **[P0 问题]**
- 缺少运行时依赖发现机制

**必要条件（P0）**：
- DAG 依赖推断必须是 COMPLEX 路由正确运行的前提条件
- 静态分析不完整时，强制降级为 MEDIUM 路由，不允许不完整的 DAG 执行
- 人工定义依赖作为补充，不作为主要依赖推断手段

**优化方向**：
- 引入乐观锁 + 乐观重试机制
- 增加运行时依赖推断（观察文件访问模式）**[优先级降低，依赖静态分析成熟后迭代]**
- 实现 MCP 连接池复用

#### 2.1.3 上下文压缩策略

**难点描述**：上下文 Token 接近上限时需要压缩，压缩不当会导致：
- 关键信息丢失
- Agent 丢失任务目标
- 历史决策上下文断裂

**当前方案**：
- 80% Token 阈值触发压缩
- 生成摘要 + 长结果卸载到文件系统
- 触发记忆冲刷（Agent 写入 MEMORY.md）

**风险点**：
- 摘要生成依赖模型能力，可能遗漏关键细节
- 卸载的长结果如何召回没有明确设计
- MEMORY.md 冲刷频率和内容规范未定义 **[P0 问题]**

**必要条件（P0）**：
- MEMORY.md 格式必须在实现前定义，否则无法进行上下文压缩

**MEMORY.md 格式规范**：

```markdown
# Session Memory

## 任务目标
[原始用户需求描述]

## 进度
- [x] 已完成步骤
- [ ] 进行中步骤
- [ ] 待处理步骤

## 关键决策
- [决策点]: [决策内容] - [日期]

## 待解决问题
- [问题描述]: [当前状态]

## 重要上下文
[不可丢失的关键信息，如业务规则、约束条件]
```

**冲刷时机**：
- 上下文压缩触发时
- 每个 Agent 步骤完成后（可选，取决于 Token 消耗速度）
- 会话结束时（必须）

**召回机制**：压缩后的历史摘要中包含 MEMORY.md 锚点，需要时通过 `memory:recall` 工具从文件系统加载完整内容。

**优化方向**：
- 设计召回机制（按需从文件系统加载历史结果）
- 建立澄清-执行反馈循环
- 压缩比例可配置（紧急压缩 vs 安全压缩）

#### 2.1.4 意图识别的歧义处理

**难点描述**：用户输入往往模糊或不完整，意图识别可能：
- 误判任务类型（bug fix vs refactor）
- 遗漏关键范围（未识别涉及哪些模块）
- 错误评估依赖（显式 vs 隐式）

**当前方案**：
- 意图识别器输出结构化对象 + confidence 分数
- 低于阈值时触发需求澄清
- 澄清问题引导用户补充信息

**风险点**：
- 澄清流程可能打断用户思路
- 多轮澄清增加交互成本
- 某些意图在执行前无法验证合理性

**优化方向**：
- 提供默认假设 + 用户确认（而非先澄清后执行）
- 支持意图假设跳过（高级用户）
- 建立澄清-执行反馈循环，持续修正意图模型

---

### 2.2 工程实现挑战

#### 2.2.1 MCP 协议对接

**难点描述**：MCP 协议有多种传输方式，对接时需要：
- 统一抽象传输层接口
- 处理各传输方式的生命周期差异
- 处理协议握手和能力协商

**当前方案**：
- stdio/sse/http/websocket 四种传输支持
- 统一 MCPClient 接口屏蔽传输差异
- 能力协商后按权限过滤

**风险点**：
- stdio 模式下进程管理复杂（启动/重启/销毁）
- SSE 是单向流，工具调用响应需要额外通道
- 各 MCP Server 实现质量不一，异常处理复杂

**优化方向**：
- 引入连接池管理 stdio 进程
- SSE 模式下使用另一个 SSE 通道接收响应
- 定义 MCP Server 质量标准，异常时降级禁用

#### 2.2.2 四层存储分层的一致性

**难点描述**：数据在四级存储间流转时需要保证：
- 流转触发条件准确
- 数据格式正确转换（如 SQLite 记录 → 文件系统归档）
- 流转原子性（失败回滚）

**当前方案**：
- 定时扫描 + 访问频率追踪
- 各层独立存储，Schema 不同
- 流转记录在 SQLite 元数据表

**风险点**：
- 热→温流转依赖会话结束信号，可能丢失
- 向量数据删除后无法恢复
- 归档数据召回延迟高

**优化方向**：
- 引入事件驱动流转（会话结束事件 → 触发分层）
- 向量库软删除机制（30 天内可恢复）
- 归档索引表支持快速召回定位

#### 2.2.3 异步事件总线设计

**难点描述**：系统内部事件（tool.called、agent.completed、context.compressed）需要：
- 高效分发到多个消费者
- 保证事件顺序（某些场景需要）
- 避免事件丢失（at-least-once）

**当前方案**：
- asyncio Queue 作为事件总线
- 生产者异步推送，消费者异步处理
- 关键事件同步记录到审计日志

**风险点**：
- asyncio Queue 在高并发下可能积压
- 消费者处理失败时事件丢失
- 跨进程事件传递需要额外机制

**迁移触发条件**：当满足以下任一条件时，必须迁移到 Redis/RabbitMQ：
- 单实例日处理事件 > 100,000 条
- 事件消费延迟持续 > 500ms（P99）
- 需要跨进程事件共享（如多实例部署）
- 需要事件回放能力（Event Sourcing 场景）

**当前实现**：asyncio Queue 满足单机部署 + 低并发场景（< 10 并发 Agent）

**优化方向**：
- 引入 Redis/RabbitMQ 作为事件总线（满足迁移条件时）
- 消费者 ACK 机制 + 失败重试队列
- 事件溯源（Event Sourcing）模式记录完整轨迹

#### 2.2.4 熔断降级的边界判定

**难点描述**：系统故障时需要熔断，但边界判定困难：
- 连续 5 次失败触发熔断 → 误触发（网络抖动）
- 熔断后多久尝试半开 → 太短/太长都不合适
- 部分降级 vs 全部降级的决策

**当前方案**：
- 固定阈值（5 次失败 / 60 秒熔断窗口）
- 半开状态允许 1 次探测请求
- 降级策略按组件定义（向量库→关键词检索）

**风险点**：
- 固定阈值不适用于所有场景
- 半开探测本身可能加剧系统负载
- 降级策略需要人工配置，容易遗漏

**优化方向**：
- 动态阈值（基于滑动窗口统计）
- 探测请求携带限流标签
- 自动推导降级策略（观察系统行为）

---

## 第三章 优化点设计

### 3.1 性能优化

#### 3.1.1 Token 消耗控制

| 优化点 | 当前状态 | 优化方案 | 预期效果 |
|--------|----------|----------|----------|
| 上下文压缩 | 80% 阈值触发 | 动态阈值（按模型窗口剩余量调整） | 减少无效压缩 |
| 摘要生成 | 全量摘要 | 层级摘要（近期详细/早期粗略） | 降低摘要 Token 消耗 |
| 工具结果卸载 | 超长结果卸载 | 选择性卸载（保留关键行） | 平衡精度与成本 |
| 向量检索 | 全量召回 | 分层召回（粗排→精排） | 减少向量计算量 |

#### 3.1.2 向量检索效率

| 优化点 | 当前状态 | 优化方案 | 预期效果 |
|--------|----------|----------|----------|
| 索引策略 | 全量索引 | 按仓库/按模块分区索引 | 减少搜索范围 |
| Embedding | 实时计算 | 增量计算 + 缓存 | 降低 CPU 消耗 |
| Top-K | 固定 K 值 | 自适应 K（按结果质量动态调整） | 平衡精度与延迟 |
| 混合检索 | 纯向量 | 向量 + 关键词混合评分 | 提高召回精度 |

#### 3.1.3 SQLite WAL 并发优化

| 优化点 | 当前状态 | 优化方案 | 预期效果 |
|--------|----------|----------|----------|
| 写吞吐 | 单次提交 | 批量写入缓冲（100ms/1000条） | 提高写入效率 |
| 读并发 | 主库读写 | 读写分离（副本读） | 降低主库压力 |
| 大表查询 | 全表扫描 | 按日期分区 + 索引优化 | 查询延迟降低 |
| 连接管理 | 长连接 | 连接池复用 | 降低连接开销 |

---

### 3.2 成本优化

#### 3.2.1 多模型自动降级

```
主模型不可用/超时
    │
    ▼
降级到备用模型 1（如 Claude 3 Haiku）
    │
    ▼
仍不可用 → 降级到备用模型 2（如 GPT-4）
    │
    ▼
仍不可用 → 返回错误（不无限降级）
```

**配置示例**：

```json
{
  "model_fallback": {
    "primary": "claude-3-5-sonnet",
    "fallbacks": ["claude-3-haiku", "gpt-4"],
    "timeout_ms": 5000,
    "max_retries": 2
  }
}
```

#### 3.2.2 Token 用量追踪与告警

| 追踪维度 | 实现方式 | 告警规则 |
|----------|----------|----------|
| 单会话 Token | 实时累加，记录到 SQLite | 超出预算时提示 |
| 单日总用量 | 凌晨重置，累加到日志 | 超出日限额阻断 |
| 单用户用量 | 按 user_id 聚合 | 超出配额提示管理员 |
| Token 费用 | 单价 × Token 数 | 周报发送给 Owner |

#### 3.2.3 MCP 连接复用

| 优化点 | 当前状态 | 优化方案 | 预期效果 |
|--------|----------|----------|----------|
| 连接建立 | 每次调用新建 | 连接池复用 | 降低连接开销 |
| 心跳检测 | 固定间隔 ping | 自适应间隔（低频→高频） | 平衡及时性与开销 |
| 断线重连 | 手动重连 | 自动重连 + 指数退避 | 提高可用性 |

---

### 3.3 可靠性优化

#### 3.3.1 熔断降级策略

| 故障场景 | 熔断条件 | 降级行为 | 恢复策略 |
|----------|----------|----------|----------|
| 模型 API 限流 | 连续 5 次 429 | 切换备用模型 | 60s 后探测 |
| 向量库不可用 | 连续 5 次超时 | 回退关键词检索 | 30s 后探测 |
| MCP 服务崩溃 | ping 失败 3 次 | 禁用该服务工具 | 手动启用 |
| 上下文超限 | 接近 80% 阈值 | 强制压缩 | - |

#### 3.3.2 Checkpoint 与恢复

| 维度 | 策略 |
|------|------|
| 创建时机 | 每完成一个工具调用后、每个 Agent 步骤完成后 |
| 存储内容 | 会话上下文、工具状态、执行位置标记 |
| 保留策略 | 最近 10 个 checkpoint，7 天后自动清理 |
| 恢复粒度 | 可回滚到最近 checkpoint 或完全重启 |

#### 3.3.3 冗余备份

| 数据层 | 冗余策略 | 备份频率 |
|--------|----------|----------|
| 热数据 | 内存双副本 | 实时 |
| 温数据 | 向量库主从复制 | 准实时 |
| 冷数据 | SQLite WAL + 定时快照 | 每小时快照 |
| 归档 | Git 版本控制 + 文件备份 | 每次变更 |

---

## 第四章 包结构设计

### 4.1 分层包架构

```
mozi/
│
├── mozi/                           # 主包
│   │
│   ├── __init__.py
│   │   # 导出核心类和版本信息
│   │   __version__ = "0.1.0"
│   │   from .ingress import CLI, WebUI, MCPClient
│   │   from .orchestrator import Orchestrator
│   │   from .capabilities import ToolFramework, SkillsEngine, ConfigLoader
│   │   from .infrastructure import Storage, VectorStore, ModelAdapter
│   │
│   ├── ingress/                    # 第一层：接入层
│   │   ├── __init__.py
│   │   │
│   │   ├── cli/
│   │   │   ├── __init__.py
│   │   │   ├── typer_app.py       # Typer CLI 应用定义
│   │   │   ├── commands.py         # 命令注册（run, interactive, config）
│   │   │   └── output.py          # 输出格式化（Rich 渲染）
│   │   │
│   │   ├── web/
│   │   │   ├── __init__.py
│   │   │   ├── fastapi_app.py     # FastAPI 应用
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── session.py      # Session CRUD
│   │   │   │   └── ws.py          # WebSocket 流式响应
│   │   │   └── middleware/
│   │   │       ├── __init__.py
│   │   │       ├── auth.py         # 认证中间件
│   │   │       └── logging.py      # 请求日志中间件
│   │   │
│   │   └── mcp/
│   │       ├── __init__.py
│   │       ├── protocol.py        # MCP 协议定义
│   │       ├── client.py          # MCP Client 抽象
│   │       └── transports/
│   │           ├── __init__.py
│   │           ├── stdio.py       # stdio 传输实现
│   │           ├── sse.py         # SSE 传输实现
│   │           ├── http.py        # HTTP streaming 实现
│   │           └── ws.py          # WebSocket 实现
│   │
│   ├── orchestrator/              # 第二层：编排层
│   │   ├── __init__.py
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py    # Orchestrator 主类
│   │   │   ├── intent.py          # 意图识别器
│   │   │   ├── complexity.py      # 复杂度评估引擎
│   │   │   └── router.py          # 任务路由器
│   │   │
│   │   ├── agent/
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # Agent 基类
│   │   │   ├── runtime.py         # Agent 运行时
│   │   │   ├── registry.py        # Agent 注册表
│   │   │   └── pool.py           # Agent 池（复用）
│   │   │
│   │   ├── dag/
│   │   │   ├── __init__.py
│   │   │   ├── planner.py         # DAG 生成器
│   │   │   ├── scheduler.py       # DAG 调度器
│   │   │   ├── executor.py        # 执行器
│   │   │   └── nodes.py           # DAG 节点定义
│   │   │
│   │   └── session/
│   │       ├── __init__.py
│   │       ├── manager.py         # 会话管理器
│   │       ├── context.py         # 会话上下文
│   │       └── checkpoint.py      # Checkpoint 管理
│   │
│   ├── capabilities/              # 第三层：能力层
│   │   ├── __init__.py
│   │   │
│   │   ├── config/
│   │   │   ├── __init__.py
│   │   │   ├── loader.py         # 配置加载器
│   │   │   ├── watcher.py        # 配置变更监听
│   │   │   └── schemas/
│   │   │       ├── __init__.py
│   │   │       ├── config.py     # config.json schema
│   │   │       ├── agents.py     # agents.json schema
│   │   │       ├── tools.py      # tools.json schema
│   │   │       ├── mcp.py        # mcp.json schema
│   │   │       └── skills.py     # skills.json schema
│   │   │
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── framework.py      # 工具框架主类
│   │   │   ├── registry.py      # 工具注册表
│   │   │   ├── permission.py     # 权限检查器
│   │   │   ├── sandbox.py        # 沙箱执行器
│   │   │   ├── hash_anchor.py    # 哈希锚定编辑
│   │   │   └── builtin/
│   │   │       ├── __init__.py
│   │   │       ├── read.py       # read 工具
│   │   │       ├── write.py      # write 工具
│   │   │       ├── edit.py       # edit 工具
│   │   │       ├── bash.py       # bash 工具
│   │   │       ├── grep.py       # grep 工具
│   │   │       ├── glob.py       # glob 工具
│   │   │       ├── lsp.py        # lsp 工具
│   │   │       ├── ast_grep.py   # ast_grep 工具
│   │   │       ├── web_search.py  # web_search 工具
│   │   │       └── web_fetch.py   # web_fetch 工具
│   │   │
│   │   ├── mcp/
│   │   │   ├── __init__.py
│   │   │   ├── manager.py        # MCP Server 管理器
│   │   │   ├── negotiator.py     # 能力协商
│   │   │   ├── health.py         # 健康检查
│   │   │   └── pool.py          # MCP 连接池
│   │   │
│   │   └── skills/
│   │       ├── __init__.py
│   │       ├── engine.py         # Skills 引擎
│   │       ├── parser.py         # Skill 文档解析器
│   │       ├── matcher.py        # 触发词匹配器
│   │       └── executor.py       # Skill 执行器
│   │
│   ├── infrastructure/            # 第四层：基础设施层
│   │   ├── __init__.py
│   │   │
│   │   ├── storage/
│   │   │   ├── __init__.py
│   │   │   ├── tiered.py         # 四级存储管理器
│   │   │   ├── hot.py            # 热数据层（内存）
│   │   │   ├── warm.py           # 温数据层（向量库）
│   │   │   ├── cold.py           # 冷数据层（SQLite）
│   │   │   ├── archive.py       # 归档层（文件系统）
│   │   │   └── migrator.py       # 分层迁移器
│   │   │
│   │   ├── vector/
│   │   │   ├── __init__.py
│   │   │   ├── client.py         # 向量库客户端抽象
│   │   │   ├── qdrant.py         # Qdrant 实现
│   │   │   ├── milvus.py         # Milvus 实现
│   │   │   └── embedder.py       # Embedding 生成器
│   │   │
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── sqlite.py         # SQLite 封装
│   │   │   ├── schema.py         # 数据库 Schema
│   │   │   └── migrations.py     # 数据库迁移
│   │   │
│   │   ├── model/
│   │   │   ├── __init__.py
│   │   │   ├── adapter.py        # 模型适配器抽象
│   │   │   ├── anthropic.py      # Anthropic (Claude) 实现
│   │   │   ├── openai.py         # OpenAI 实现
│   │   │   ├── ollama.py         # Ollama 实现
│   │   │   └── pool.py          # 模型连接池
│   │   │
│   │   └── runtime/
│   │       ├── __init__.py
│   │       ├── sandbox.py        # 沙箱运行时
│   │       └── network.py        # 网络策略
│   │
│   ├── core/                       # 跨层核心模块
│   │   ├── __init__.py
│   │   │
│   │   ├── error.py              # 统一异常类（MoziError）
│   │   ├── event/
│   │   │   ├── __init__.py
│   │   │   ├── bus.py            # 事件总线
│   │   │   ├── producer.py       # 事件生产者
│   │   │   └── consumer.py       # 事件消费者
│   │   │
│   │   ├── circuit_breaker.py    # 熔断器
│   │   ├── rate_limiter.py       # 限流器
│   │   └── audit.py              # 审计日志
│   │
│   └── utils/
│       ├── __init__.py
│       ├── async_utils.py        # 异步工具函数
│       ├── crypto.py             # 哈希工具
│       └── pydantic_utils.py     # Pydantic 扩展
│
├── tests/                          # 测试
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── .mozi/                          # 项目配置（不打包）
│   ├── config.json
│   ├── agents.json
│   ├── tools.json
│   ├── mcp.json
│   └── skills.json
│
├── pyproject.toml
└── README.md
```

### 4.2 核心模块依赖图

```
┌─────────────────────────────────────────────────────────┐
│                        Ingress                          │
│                   (CLI / Web / MCP)                     │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                     Orchestrator                        │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌──────────┐   │
│  │  Intent  │ │Complexity│ │ Router │ │   DAG    │   │
│  │Classifier│ │  Engine  │ │        │ │ Planner  │   │
│  └────┬─────┘ └────┬─────┘ └───┬────┘ └────┬─────┘   │
│       └────────────┴───────────┴───────────┘          │
│                         │                               │
│                    ┌────▼────┐                          │
│                    │ Session │                          │
│                    │ Manager │                          │
│                    └────┬────┘                          │
└─────────────────────────┼───────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
┌─────────────────┐ ┌─────────────┐ ┌───────────────────┐
│   Tool Framework│ │MCP Manager  │ │   Skills Engine   │
│                 │ │             │ │                   │
│ ┌─────────────┐ │ │┌──────────┐│ │┌───────────────┐ │
│ │  Registry   │ │ ││Transport ││ ││    Parser     │ │
│ │  Permission  │ │ ││ Pool     ││ ││    Matcher    │ │
│ │  Sandbox     │ │ │└──────────┘│ │└───────────────┘ │
│ │Hash Anchor   │ │ │             │ │                   │
│ └─────────────┘ │ └─────────────┘ └───────────────────┘
└────────┬─────────┘ └──────┬──────┘ └───────┬───────────┘
         │                   │                │
         └───────────────────┼────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                      Infrastructure                           │
│  ┌─────────┐  ┌───────────┐  ┌──────────┐  ┌────────────┐  │
│  │  Hot    │  │   Warm    │  │   Cold   │  │   Archive  │  │
│  │(Memory) │◄─┤(VectorDB) │◄─┤(SQLite)  │◄─┤(Filesystem)│  │
│  └─────────┘  └───────────┘  └──────────┘  └────────────┘  │
│                                                              │
│  ┌─────────────┐  ┌─────────────────┐  ┌───────────────┐  │
│  │Model Adapter│  │  Event Bus       │  │Circuit Breaker│  │
│  │(Anthropic/  │  │  (asyncio Queue) │  │               │  │
│  │ OpenAI/     │  │                  │  │               │  │
│  │ Ollama)     │  │                  │  │               │  │
│  └─────────────┘  └─────────────────┘  └───────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### 4.3 核心类接口定义

#### 4.3.1 Orchestrator（编排层主类）

```python
from typing import Optional
from dataclasses import dataclass

@dataclass
class Intent:
    task_type: str
    scope: str
    explicit_deps: list[str]
    implied_deps: list[str]
    clarification_needed: bool
    confidence: float

@dataclass
class ComplexityScore:
    total: float
    level: str  # SIMPLE | MEDIUM | COMPLEX
    dimensions: dict[str, float]

class Orchestrator:
    """系统核心编排器"""

    def __init__(self, config: Config):
        self.intent_classifier = IntentClassifier()
        self.complexity_engine = ComplexityEngine()
        self.router = TaskRouter()
        self.session_manager = SessionManager()

    async def process(
        self,
        user_input: str,
        session_id: Optional[str] = None
    ) -> Response:
        """处理用户输入，返回响应"""
        ...

    async def _recognize_intent(self, user_input: str) -> Intent:
        """意图识别"""
        ...

    async def _assess_complexity(self, intent: Intent) -> ComplexityScore:
        """复杂度评估"""
        ...

    async def _route_and_execute(
        self,
        intent: Intent,
        complexity: ComplexityScore,
        session: Session
    ) -> Response:
        """路由并执行任务"""
        ...
```

#### 4.3.2 ToolFramework（工具框架）

```python
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel

class ToolPermission(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"

class ToolResult(BaseModel):
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    metadata: dict[str, Any] = {}

class ToolFramework:
    """工具框架，管理所有工具的注册、执行、权限控制"""

    def __init__(self, config_loader: ConfigLoader):
        self.registry = ToolRegistry()
        self.permission_checker = PermissionChecker(config_loader)
        self.sandbox = Sandbox()
        self.hash_anchor = HashAnchor()

    def register_tool(self, tool: Tool) -> None:
        """注册工具"""
        ...

    async def execute(
        self,
        tool_name: str,
        params: dict[str, Any],
        context: dict[str, Any]
    ) -> ToolResult:
        """执行工具"""
        # 1. 权限检查
        # 2. 哈希锚定校验（如适用）
        # 3. 沙箱执行
        # 4. 审计日志
        # 5. 返回结果
        ...

    async def _check_permission(
        self,
        tool_name: str,
        action: str,
        context: dict[str, Any]
    ) -> ToolPermission:
        """检查权限（五级覆盖，deny 优先）"""
        ...
```

#### 4.3.3 TieredStorage（四级存储管理器）

```python
from typing import TypeVar, Generic, Optional
from abc import ABC, abstractmethod

T = TypeVar('T')

class StorageTier(ABC, Generic[T]):
    """存储层抽象"""

    @abstractmethod
    async def get(self, key: str) -> Optional[T]:
        ...

    @abstractmethod
    async def set(self, key: str, value: T) -> None:
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        ...

class TieredStorage:
    """四级存储管理器"""

    def __init__(
        self,
        hot: StorageTier,
        warm: StorageTier,
        cold: StorageTier,
        archive: StorageTier
    ):
        self.hot = hot        # 内存（LRU）
        self.warm = warm      # 向量库
        self.cold = cold      # SQLite
        self.archive = archive  # 文件系统

    async def get(self, key: str) -> Optional[any]:
        """从热数据开始逐层查找"""
        ...

    async def set(self, key: str, value: any, tier: str) -> None:
        """写入指定层"""
        ...

    async def migrate(
        self,
        key: str,
        from_tier: str,
        to_tier: str
    ) -> None:
        """数据层间迁移"""
        ...

    async def auto_tiering(self) -> None:
        """自动分层调度"""
        ...
```

---

## 第五章 技术决策记录（ADR）

### ADR-001：复杂度评估阈值可配置

**状态**：待评审

**背景**：固定阈值（40/70）可能不适用于所有项目规模。

**决策**：在 `agents.json` 中提供 `complexity_threshold` 配置项，允许项目级覆盖。

**代价**：增加了配置复杂度，用户需要理解阈值含义。

---

### ADR-002：MCP 连接池策略

**状态**：待评审

**背景**：每个 MCP Server 独立进程，高频调用时连接建立开销大。

**决策**：为 stdio 传输实现连接池，复用进程；其他传输复用 HTTP/WebSocket 连接。

**代价**：连接池管理增加复杂度，需要处理进程僵死。

---

### ADR-003：事件总线使用 asyncio Queue

**状态**：待评审

**背景**：轻量级事件分发不需要引入 Redis/RabbitMQ。

**决策**：当前使用 asyncio.Queue，保留未来迁移到消息队列的接口抽象。

**代价**：跨进程事件传递需要额外机制。

---

*文档版本：v1.0*
*更新日期：2026-03-26*
*状态：待架构评审*
