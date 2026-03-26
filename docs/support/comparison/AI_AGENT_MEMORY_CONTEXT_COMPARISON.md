# Cursor、OpenClaw、OpenCode 记忆与上下文系统架构与对比

本文分别说明三种 AI 编程助手（Cursor、OpenClaw、OpenCode）的**记忆（memory）与上下文（context）系统架构**，并在文末给出**多维度对比**，便于选型与理解差异。

---

## 一、Cursor 的记忆与上下文系统架构

### 1.1 设计目标

Cursor 在 IDE 内为模型提供「该看什么」的编排：通过**上下文编排 + 动态发现 + 规则与记忆**，把合适的信息在合适时机放进模型的 context window，并控制 token 与噪音。

### 1.2 上下文编排（自动注入什么、谁优先）

- **光标与当前文件优先**：当前文件、光标附近代码、当前文件内注释被视为强信号，优先进入上下文。
- **最近性优先于语义**：最近打开/编辑过的文件权重大于「仅语义相关但未打开」的文件；一旦最近打开，会以该上下文为主。
- **语义检索**：对仓库做嵌入检索，拉取与当前问题语义相关的文件；结果可被「最近打开」覆盖。
- **自动附带**：根据当前状态自动带入打开的文件、终端输出、linter 错误等（Cursor 2.0 起部分原先需手动 @ 的如 Git、Linter 由 Agent 自行按需拉取）。

### 1.3 动态上下文发现（Dynamic Context Discovery）

不在一开始塞满上下文，而是**按需拉取**：

- **长工具结果写文件**：Shell、MCP 等返回过长时，不整段塞进对话，而是写入临时文件，Agent 用 `tail`/读文件按需查看，避免撑爆 context。
- **总结时引用历史**：上下文接近满时触发总结；总结时把完整对话历史作为可引用文件，Agent 若发现摘要缺细节可再查历史。
- **终端当文件**：终端输出同步到本地文件，Agent 可 grep/按需读取，而非整段注入。
- **MCP 按需加载**：MCP 工具描述先存为文件索引，Agent 仅在需要时查阅，减少静态注入的 token（官方称可显著降低 token）。
- **Skills 按需拉取**：Agent Skills 仅将名称/描述放入静态上下文，具体内容通过搜索等工具按需拉取。

### 1.4 规则系统（Rules）— 持久、显式指引

- **四种规则**  
  - **Project Rules**：`.cursor/rules/*.md` 或 `*.mdc`，随项目版本控制，作用域为当前代码库。  
  - **User Rules**：Cursor 设置 → Rules，全局，所有项目生效。  
  - **Team Rules**：Dashboard 管理，团队/企业计划，全团队全项目。  
  - **AGENTS.md**：项目根或子目录的 Markdown，简单指令，无复杂元数据。
- **应用方式**  
  - **Always Apply**：每次对话都注入。  
  - **Apply Intelligently**：Agent 根据 `description` 判断是否相关后注入。  
  - **Apply to Specific Files**：仅当涉及文件匹配 `globs` 时注入。  
  - **Apply Manually**：仅在被 `@规则名` 提及时注入。
- **实现**：规则内容在「应用时」被拼到**模型 context 开头**，实现跨会话的持久指引；无向量检索，纯「读文件 + 按类型/描述/globs 选择后注入」。

### 1.5 记忆系统（Memories）— 个性化与事实

- **存储**：云端 **Knowledge Base**，与用户账号绑定；**双存储**：原文 + 向量表示，便于检索。
- **隔离**：以 **Git remote URL** 区分不同项目的记忆空间；无 remote 的项目共用一个默认空间，易产生记忆混杂。
- **写入**  
  - **自动**：从对话中用模型筛出「有价值」的陈述并打分，高分写入。  
  - **显式**：用户说 **「Remember...」** 或通过 UI 创建；内部有类似 `add_to_memory` 的 CRUD。
- **读取**：按当前对话做**向量相似度检索**，从候选中筛出相关记忆，以 **XML 标签** 形式注入系统提示，每条带唯一 ID 便于更新/删除。
- **管理**：Settings → Rules → **Memories**；需关闭隐私模式；企业强制隐私时不可用。

### 1.6 单会话内与总结

- **当次对话**：多轮消息与回复均在同一条 conversation context 中，模型自然可见。
- **接近上下文上限时**：触发**总结**，将旧对话压缩为摘要；同时给 Agent 对「完整历史」的引用（如可搜索的历史文件），需要时可再查细节。
- **聊天记录持久化**：本地存于 `~/Library/Application Support/Cursor/User/workspaceStorage/`（macOS），各工作区子目录下有 `state.vscdb`（SQLite），用于 UI 展示与恢复，非 Memories 的存储。

### 1.7 小结：Cursor 架构要点

| 层次       | 载体/机制 |
|------------|-----------|
| 持久规则   | Rules（Project/User/Team/AGENTS.md）→ 每次对话按类型注入 context 开头 |
| 持久记忆   | Memories（云端 Knowledge Base）→ 向量检索后以 XML 注入 |
| 半持久     | 对话历史 + 总结时历史文件引用 |
| 临时       | 当前 context window（光标/最近文件/语义检索/动态发现） |

---

## 二、OpenClaw 的记忆与上下文系统架构

### 2.1 设计目标

OpenClaw 明确将「记忆」视为**系统设计**而非模型能力：通过 **Markdown 文件 + 会话历史 + 检索** 把该记住的内容写盘，再在适当时机注入或按需拉入 context，从而在无状态 LLM 上模拟「记得住」。

### 2.2 三层存储（按持久程度）

| 层级     | 内容 | 持久性 |
|----------|------|--------|
| **永久** | 工作区 Markdown 文件 | 不删即永久存在，重启/换会话不影响 |
| **半永久** | 会话历史（如 JSONL） | 存盘可恢复，过长部分被压缩成摘要，细节会丢 |
| **临时** | 当前 context window | 仅当前请求可见（如 Claude 约 200K tokens），会话结束即失效 |

### 2.3 永久层：Markdown 文件与工作区布局

- **身份与规则**（每次会话可加载）：  
  `SOUL.md`、`AGENTS.md`、`USER.md`、`TOOLS.md`、`IDENTITY.md` 等，定义 Agent 身份、工作流、用户稳定信息。
- **长期记忆**（仅主私密会话加载，群聊/频道不加载）：  
  **`MEMORY.md`** — 长期、精选的事实与决定（偏好、决策、教训）。
- **按日日志**：  
  **`memory/YYYY-MM-DD.md`** — 按天追加，记录当日发生的事、决定、任务；约定「会话启动时读今天 + 昨天」。

默认工作区路径：`~/.openclaw/workspace/`。这些文件是**记忆的唯一起源（source of truth）**。

### 2.4 信息如何进入模型：注入与检索

**（1）启动时注入（Bootstrap）**

- 会话开始时**自动加载**一批工作区文件到 context：如 `AGENTS.md`、`SOUL.md`、`TOOLS.md`、`IDENTITY.md`、`USER.md`。
- **主私密会话**还会加载 `MEMORY.md`；群组/频道**不**加载 `MEMORY.md`（隐私）。
- 单文件约 2 万字符上限，所有配置类文件合计约 15 万字符（约 50K tokens），超出部分会被截断。

**（2）会话历史重建与压缩（Compaction）**

- 继续已有会话时，从磁盘**读取会话历史**并重建进 context，实现「同一会话内」的连续感。
- 当历史超过 context 容量，**旧轮次被压缩成摘要**（compaction），只保留大意，细节丢失。

**（3）压缩前记忆冲刷（Memory Flush）**

- 在**即将进行压缩**前，触发一次**静默的 Agent 轮次**，提醒模型：「快要把上下文压掉了，请先把该长期保留的内容写进记忆文件。」
- 默认引导写入 `memory/YYYY-MM-DD.md`（或 `MEMORY.md`），并鼓励以 `NO_REPLY` 回复，用户通常看不到该轮。
- 配置项：`agents.defaults.compaction.memoryFlush`（可开关、阈值、提示文案）。

**（4）按需检索（memory_search / memory_get）**

- 对 `MEMORY.md` 和 `memory/*.md` 建索引（向量 + 可选关键词），模型通过工具**按需查询**。
- **`memory_search`**：语义/关键词检索，将相关片段拉入当前 context。  
- **`memory_get`**：按文件/行范围精确读取。  
- 只有**已写入这些 Markdown** 的内容才能被检索；仅存在于对话中未写盘的内容无法被检索。  
- 默认由 `memory-core` 插件提供；可设 `plugins.slots.memory = "none"` 关闭。

### 2.5 向量检索细节（可选）

- 默认对 `MEMORY.md` 与 `memory/*.md` 建**向量索引**（如 SQLite + 向量扩展）。  
- Embedding 可配置：Mistral / Voyage / Gemini / OpenAI 等远程 API，或本地模型。  
- 检索管线可包含：**向量 + 关键词 → 加权合并 → 时间衰减（temporalDecay）→ 排序 → MMR 去重 → Top-K**。  
  - 例如 30 天半衰期，越旧分数越低；MMR 平衡相关性与多样性。

### 2.6 小结：OpenClaw 架构要点

| 层次     | 载体/机制 |
|----------|------------|
| 永久     | Markdown（SOUL/AGENTS/USER/MEMORY.md、memory/YYYY-MM-DD.md）→ Bootstrap 注入 + memory_search 按需拉取 |
| 半永久   | 会话历史存盘 → 重建进 context；过长则压缩，压缩前 memory flush 提醒写盘 |
| 临时     | 当前 context window |

---

## 三、OpenCode 的记忆与上下文系统架构

### 3.1 设计目标

OpenCode **核心**不内置向量记忆或长期记忆库，主要依赖「指令文件 + Agent 配置 + 会话持久化 + 压缩」维持上下文；**长期可检索记忆**通常由**插件**（如 opencode-supermemory、opencode-agent-memory）提供。

### 3.2 核心：指令、Agent、会话、压缩

| 组件 | 实现方式 |
|------|----------|
| **指令（Instructions）** | 配置项 `instructions`：数组指定路径/通配符，如 `["CONTRIBUTING.md", ".cursor/rules/*.md"]`，内容在会话中注入模型上下文。 |
| **Agent 与 Prompt** | `.opencode/agents/`、`~/.config/opencode/agents/`、`opencode.json`；每类 Agent（Build/Plan 等）可有独立 `prompt`（含 `{file:./prompts/build.txt}`），系统提示按 Agent 加载。 |
| **配置合并** | Remote → Global → Custom → Project → Inline；后覆盖前；项目与全局均可放置 agents、plugins、skills 等。 |
| **会话存储** | 本地：`~/.local/share/opencode/storage/` 按项目 ID 存会话 JSON；元数据在 `opencode.db`（SQLite）。支持 `/sessions` 恢复历史会话。 |
| **压缩（Compaction）** | 隐藏系统 Agent「compaction」在上下文接近满时执行摘要压缩；可配置 `compaction.auto`、`compaction.prune`、`compaction.reserved`。 |

**已知问题**：压缩时若未把 AGENTS.md/CLAUDE.md 等指令传入压缩调用的 system，压缩后 Agent 会丢失项目规则与行为约束（社区已反馈）。

### 3.3 内置隐藏 Agent（与上下文相关）

- **compaction**：执行上下文压缩，不可在 UI 选择。  
- **title**：生成会话标题。  
- **summary**：生成会话摘要。  

均由系统在适当时机自动调用。

### 3.4 通过插件的「记忆」能力（如 opencode-supermemory）

- **双作用域（Dual-Scope）**  
  - **User Scope**：按 Git `user.email` 生成标签（如 `opencode_user_{hash}`），跨项目共享（偏好、习惯、通用知识）。  
  - **Project Scope**：按当前项目路径哈希生成标签（如 `opencode_project_{hash}`），仅当前项目有效（架构、业务决策、项目专属事实）。  
- **工具**：`add` / `search` / `forget` / `list`（或类似），以**短 ID** 管理记忆块，便于精确更新与删除。  
- **注入时机**：新会话开始时，从向量/存储中拉取与当前上下文相关的 User + Project 记忆，注入系统或上下文。  
- **写入**：用户说「Remember this...」或通过对话让 Agent 调用 add；部分实现支持 CLI 初始化。  
- **存储**：多为远程向量服务（如 Supermemory API）或本地索引；同一 Git 邮箱 + 同一服务时可跨设备同步。

### 3.5 小结：OpenCode 架构要点

| 层次     | 载体/机制 |
|----------|------------|
| 持久     | instructions 指向的文件、.opencode/agents、插件记忆（User/Project Scope） |
| 半持久   | 会话 JSON + SQLite；/sessions 恢复；compaction 压缩（存在指令丢失风险） |
| 临时     | 当前 context window |

---

## 四、三者对比

### 4.1 总表：产品形态与持久化

| 维度 | Cursor | OpenClaw | OpenCode（核心 + 常见插件） |
|------|--------|----------|-----------------------------|
| **产品形态** | IDE 内置，云端 + 本地 | CLI/网关，本地工作区为主 | CLI/TUI/服务，本地 + 可选远程 |
| **持久化载体** | Rules 文件（.cursor/rules、AGENTS.md 等）+ 可选云端 Memories | 工作区 Markdown（MEMORY.md、memory/YYYY-MM-DD.md、SOUL/AGENTS/USER 等） | 指令文件 + 会话 JSON/SQLite + 插件记忆（常为远程向量） |
| **谁决定「记住什么」** | Rules 人工维护；Memories 可自动抽取 + 用户「Remember...」 | 用户/Agent 显式写入 Markdown；无自动抽取 | 指令人工维护；插件记忆由用户/Agent「Remember...」或工具调用 |
| **作用域** | User Rules（全局）、Project Rules（项目）、Team Rules（团队）、Memories（按 Git remote 隔离） | 无显式 User/Project 分离；MEMORY.md 仅主私密会话加载 | 插件常为 User Scope（跨项目）与 Project Scope（当前项目） |
| **检索方式** | Rules 按描述/globs/始终应用；Memories 云端向量检索 | 本地向量 + 关键词混合（memory_search），时间衰减、MMR 等 | 指令静态注入；插件记忆向量/关键词检索后注入 |
| **压缩/总结** | 有总结；总结时引用历史文件供 Agent 再查 | 压缩前 memory flush 提醒写盘；旧轮次压成摘要 | 有 compaction；存在压缩后丢失 AGENTS.md 等指令的已知问题 |
| **隐私与部署** | Memories 在云端；企业可关隐私 | 记忆全在本地工作区；MEMORY.md 不在群聊加载 | 核心全本地；插件记忆多为远程 API，可自建 |

### 4.2 记忆与上下文的「层次」对比

| 层次 | Cursor | OpenClaw | OpenCode |
|------|--------|----------|----------|
| **持久层** | Rules（.cursor/rules、AGENTS.md、User/Team Rules）；Memories（云端 KB） | SOUL.md、AGENTS.md、USER.md、MEMORY.md、memory/YYYY-MM-DD.md | instructions 文件、.opencode/agents；插件 User/Project 记忆 |
| **半持久层** | 多轮对话 + 总结时历史文件引用 | 会话历史存盘；压缩前 memory flush；旧轮次压成摘要 | 会话 JSON/SQLite，/sessions 恢复；compaction 压缩 |
| **临时层** | 当前 context（光标/最近文件/语义检索/动态发现） | 当前 context window | 当前 context window |

### 4.3 存储位置与关键文件

| 系统 | 存储/配置位置 | 关键文件或概念 |
|------|----------------|----------------|
| **Cursor** | workspaceStorage：`~/Library/Application Support/Cursor/User/workspaceStorage/`（macOS）；规则在项目 `.cursor/rules` 或设置中 | state.vscdb（会话）；Rules；Memories（云端） |
| **OpenClaw** | 工作区默认 `~/.openclaw/workspace/` | MEMORY.md、memory/YYYY-MM-DD.md、SOUL.md、AGENTS.md、USER.md |
| **OpenCode** | 会话：`~/.local/share/opencode/storage/`，`opencode.db`；配置：`~/.config/opencode/`、项目 `.opencode/`、`opencode.json` | instructions 列表；agents 目录；插件记忆存储（由插件决定） |

### 4.4 设计哲学简要对比

- **Cursor**：以「规则 + 可选云端记忆」为主；规则显式、可版本管理；Memories 偏个性化与事实，带自动抽取与向量检索；上下文编排强调光标与最近性，动态发现省 token。
- **OpenClaw**：**文件即真相**；所有需长期保留的必须写入 Markdown；压缩前主动提醒写盘；检索在本地，隐私与可控性强。
- **OpenCode**：**核心做指令与会话，记忆交给插件**；插件常见双域（User/Project）、ID 管理、会话初注入；压缩能力有，但指令在压缩后保持仍是改进点。

---

## 五、参考与延伸阅读

- **Cursor**：[Context](https://cursor.com/learn/context)、[Dynamic context discovery](https://cursor.com/blog/dynamic-context-discovery)、[Rules / Memories](https://cursor.com/docs/context/memories)、[Prompting agents (@ mentions)](https://cursor.com/docs/context/mentions)
- **OpenClaw**：[Memory](https://openclaws.io/docs/concepts/memory/)、[Session management + compaction](https://openclaws.io/docs/reference/session-management-compaction)、[Agent workspace](https://openclaws.io/docs/concepts/agent-workspace)
- **OpenCode**：[Config](https://opencode.ai/docs/config)、[Agents](https://opencode.ai/docs/agents)、[Compaction 配置](https://opencode.ai/docs/config#compaction)、[Instructions](https://opencode.ai/docs/config#instructions)；插件如 [opencode-supermemory](https://github.com/supermemoryai/opencode-supermemory) 的 [Memory Scope](https://lzw.me/docs/opencodedocs/supermemoryai/opencode-supermemory/core/memory-management/)

---

*文档基于公开文档与社区资料整理，具体行为以各产品当前版本为准。*
