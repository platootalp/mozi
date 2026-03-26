# OpenClaw、OpenCode、Cursor 规划与任务系统深度调研

本文对 **OpenClaw**、**OpenCode**、**Cursor** 三者的**规划（Planning）**与**任务系统（Task System）**做深度调研与对比，便于选型与架构参考。

---

## 一、OpenClaw 的规划与任务系统

### 1.1 定位与整体架构

OpenClaw 是「多入口、单内核」的 AI 私人助理运行时：**Ingress → Control Plane（Gateway）→ Execution Plane（Agent）**。规划与任务执行集中在 **Execution Plane**，由 **Lane/Queue** 与 **Agent Loop** 共同保证串行/并行与一致性。

- **无显式「Plan Mode」**：不区分「先规划再执行」的独立模式，规划与执行在单次 Agent Loop 内由模型（ReAct）自行决定。
- **任务粒度**：以 **Run** 为单元；一次用户消息 → 一个 Run → 多轮 Attempt（含重试/故障转移）→ 最终回复。

### 1.2 执行平面：Run / Attempt / Queue / Lane

**Run（运行）**  
- 一次完整 agent 执行的编排单元。  
- 负责：韧性顺序、上下文窗口保护、**两级排队**（Session 内顺序 + 全局并发上限）。  

**Attempt（尝试）**  
- 单次真实执行事务，带清理保证：总是清理订阅与 active runs，等待 compaction 重试结束，并在发起 prompt 前完成 subscribe。  

**Queue + Lane（队列与通道）**  
- **Session Lane**：按 `sessionKey` 串行，同一会话同时只允许一个 Run，避免工具/会话竞争与历史错乱。  
- **Global Lane（main）**：所有会话的 Run 先入 Session Lane，再入全局 Lane，由 `agents.defaults.maxConcurrent` 限制总并发（如 4）。  
- **Sub-agent Lane**：子 agent 可走独立 Lane，并发度更高（如 8），用于并行子任务。  

**入口**  
- CLI：`agent` 命令。  
- Gateway RPC：`agent`、`agent.wait`（可等待 lifecycle end/error，返回 `status: ok|error|timeout`）。  

### 1.3 Agent Loop 与事件流

单次 Loop 的权威路径：  
**intake → context assembly → model inference → tool execution → streaming replies → persistence**。

**事件流**  
- `stream: "lifecycle"`（phase: start | end | error）  
- `stream: "assistant"`（文本增量）  
- `stream: "tool"`（工具执行状态）  

**Hook 点（可介入规划/任务前后）**  
- **Gateway Hooks**：如 `agent:bootstrap`，在 system prompt 定稿前注入/修改 bootstrap 上下文。  
- **Plugin Hooks**：`before_agent_start`、`before_tool_call`/`after_tool_call`、`before_compaction`/`after_compaction`、`agent_end` 等，可在执行前后注入或观测。  

### 1.4 消息队列模式（Channel → Lane）

渠道可配置 **queue mode**（如 collect/steer/followup），将多条消息合并或引导后再送入 Lane，避免同一会话短时间多消息导致多次 Run 排队冲突。  

- **collect**：一段时间内收集多条消息再触发（可配 `debounceMs`、`cap`、`drop: "summarize"` 等）。  
- 支持按渠道覆盖（如 `byChannel: { discord: "collect" }`）。  

### 1.5 心跳与主动任务（Heartbeat）

- **Heartbeat**：定时（如每 30 分钟）触发，检查任务清单并**主动发起** autonomous 动作，无需用户发消息。  
- 与「规划」的关系：清单可视为长期任务/计划，由系统按节奏驱动执行。  

### 1.6 小结：OpenClaw 规划与任务特点

| 维度           | 说明 |
|----------------|------|
| 显式规划       | 无独立 Plan Mode；规划隐含在 ReAct Loop 内。 |
| 任务单元       | Run（单次用户请求）→ Attempt（单次执行事务）。 |
| 并发控制       | Session Lane 串行 + Global Lane 限并发 + 可选 Sub-agent Lane 并行。 |
| 可观测性       | lifecycle/assistant/tool 事件流；`agent.wait` 可等 Run 结束。 |
| 可扩展点       | Gateway/Plugin Hooks（bootstrap、compaction、agent_end 等）。 |
| 主动任务       | Heartbeat + 任务清单驱动周期执行。 |

---

## 二、OpenCode 的规划与任务系统

### 2.1 定位与双主 Agent 设计

OpenCode 是开源 AI 编程助手，**显式区分「规划」与「执行」**：  
- **Plan**：主 Agent，**只分析、只规划，不写代码、不执行 bash**。  
- **Build**：主 Agent，全工具权限，负责实现。  

用户通过 **Tab 切换**主 Agent（Build ⇄ Plan），或通过 **@ 提及** 调用子 Agent（如 `@general`、`@explore`）。

### 2.2 Primary Agents：Build 与 Plan

**Build（默认主 Agent）**  
- **Mode**：`primary`。  
- **用途**：日常开发，需要改文件、跑命令时使用。  
- **权限**：所有工具可开（write、edit、bash 等），可按需配置为 allow/ask/deny。  

**Plan（规划主 Agent）**  
- **Mode**：`primary`。  
- **用途**：分析代码、做方案、写计划、给建议，**不直接改代码**。  
- **权限**：默认 `bash: ask`、`file edits: ask`（或直接 deny），避免误改代码库。  
- **典型用法**：先切到 Plan → 描述需求 → 得到分析与计划 → 再切回 Build 执行。  

### 2.3 Subagents 与任务分解

**General（通用子 Agent）**  
- **Mode**：`subagent`。  
- **用途**：复杂调研、多步任务、**可并行执行多单元工作**。  
- **工具**：除 todo 外基本全开，可改文件、跑命令。  
- **调用**：主 Agent 根据 `description` 自动派发，或用户 `@general ...` 手动调用。  

**Explore（探索子 Agent）**  
- **Mode**：`subagent`。  
- **用途**：只读、快速理解代码库（按模式找文件、按关键词搜代码）。  
- **工具**：只读，不修改文件。  
- **调用**：`@explore ...` 或由主 Agent 自动派发。  

**Task 工具（子 Agent 编排）**  
- 主 Agent / 子 Agent 可通过 **Task 工具** 把工作派给其他子 Agent。  
- **子 Agent 可再派子 Agent**（subagent-to-subagent），形成层级任务。  
- **task_budget**：可配置每 Agent 的调用预算，防止无限委托。  
- **会话**：子任务可在 **独立 child session** 中执行，支持持久化或无状态。  

### 2.4 会话与导航（父/子任务切换）

- **session_child_first**（默认 +Down）：进入第一个子会话。  
- **session_parent**（默认 Up）：回到父会话。  
- **session_child_cycle** / **session_child_cycle_reverse**（Right/Left）：在多个子会话间轮换。  
- **Session Tree**（快捷键 `s`）：树状查看所有会话层级，便于在并行子任务间跳转。  

### 2.5 权限与任务安全

- **permission**：按 Agent 配置 `edit`、`bash`、`webfetch` 的 `deny` / `allow` / `ask`。  
- **bash** 可细粒度到命令模式（如 `"git push": "ask"`、`"grep *": "allow"`）。  
- **permission.task**：控制某 Agent 能通过 Task 工具调用哪些子 Agent（glob 规则，如 `*: deny`、`code-reviewer: ask`）。  
- **hidden**：子 Agent 可设为不在 @ 自动补全中显示，仅由 Task 工具内部调用。  

### 2.6 系统级「任务」Agent（自动触发）

- **compaction**：长上下文压缩为摘要，自动触发。  
- **title**：生成会话标题，自动触发。  
- **summary**：生成会话摘要，自动触发。  

均为 `primary` 但隐藏，不在 UI 中切换。  

### 2.7 小结：OpenCode 规划与任务特点

| 维度           | 说明 |
|----------------|------|
| 显式规划       | **Plan 主 Agent**：只分析/规划，不改代码；与 Build 分离。 |
| 任务分解       | **Subagents**（General/Explore + 自定义） + **Task 工具** 派发与层级委托。 |
| 并行与会话     | 子 Agent 在 **child session** 中执行，可多任务并行；Session Tree 导航。 |
| 权限与安全     | 按 Agent 的 permission（edit/bash/webfetch/task），Plan 默认禁写。 |
| 可配置性       | Agent 可 JSON 或 Markdown 定义；description 驱动主 Agent 自动派发。 |
| 步骤与成本     | **steps**（max steps）限制单 Agent 迭代次数，控制成本。 |

---

## 三、Cursor 的规划与任务系统

### 3.1 定位与 Agent 组成

Cursor 是基于 VS Code 的 AI 编程 IDE，Agent 由 **Model + Tools + Instructions（含 Rules）** 组成，工具由 Cursor 编排、按需调用。**规划**通过 **Plan Mode** 显式完成；**任务执行**在 Agent 模式下一轮轮工具调用完成。

### 3.2 Plan Mode（显式规划）

**激活方式**  
- 在 Agent 输入框按 **Shift+Tab** 切换到 Plan Mode。  
- 或当用户描述复杂任务时，Cursor 会建议使用 Plan Mode。  

**流程**  
1. Agent **研究代码库**，收集相关文件与文档。  
2. Agent **追问澄清**需求与边界。  
3. 生成 **Markdown 计划**：含文件路径、代码引用、分步任务。  
4. 用户**审阅并编辑**计划（在聊天或 Markdown 文件中）。  
5. **点击 Build** 后，再按计划执行实现。  

**计划存储**  
- 默认保存在用户目录的 Markdown 文件。  
- 可 **Save to workspace** 将计划放入仓库，便于团队共享与文档化。  

**适用场景**  
- 架构级决策、需求不清晰、涉及多文件、多种实现路径的复杂功能。  
- 小改或例行任务可直接用 Agent 模式。  

**最佳实践（官方）**  
- 若 Agent 实现与预期不符：先 **revert**，再**细化计划**后重新执行，往往比在实施中修补更快。  

### 3.3 Agent 模式与任务执行

- **单会话内**：多轮对话 + 多步工具调用（读文件、编辑、终端、MCP 等），无显式「子 Agent」概念。  
- **Subagents（v2.4+）**：  
  - **独立子 Agent**，拥有自己的 context 与工具访问。  
  - 可**并行**执行（如多文件、多测试套件同时跑）。  
  - 由主 Agent 或用户触发，用于拆解并行任务。  

### 3.4 Skills 与任务/规划

- **Skills**：`SKILL.md` 中定义的**可复用领域知识**与工作流。  
- 可编码团队规范、常用模式，Agent 在规划与执行时会参考，相当于「规划与执行」的共享上下文。  

### 3.5 小结：Cursor 规划与任务特点

| 维度           | 说明 |
|----------------|------|
| 显式规划       | **Plan Mode**（Shift+Tab）：先研究代码库 + 澄清 → 生成 Markdown 计划 → 审阅编辑 → Build 执行。 |
| 任务单元       | 单会话内多步工具调用；**Subagents** 用于并行、独立上下文的子任务。 |
| 计划产物       | Markdown 文件，可存工作区，便于版本管理与协作。 |
| 与执行的关系   | 计划可在执行中演变（Agent 可增删改条目）；建议「先改计划再重跑」而非边做边修。 |
| 上下文         | 动态发现 + Rules + Memories；Subagents 独立 context。 |

---

## 四、三维度对比总表

| 维度               | OpenClaw | OpenCode | Cursor |
|--------------------|----------|----------|--------|
| **显式规划模式**   | 无；规划在 ReAct Loop 内 | **Plan 主 Agent**（只读/只分析，不改代码） | **Plan Mode**（Shift+Tab，研究+澄清→Markdown 计划→Build） |
| **规划产物**       | 无独立产物；依赖会话与记忆 | 对话中的分析与建议；可自定义「计划」子 Agent 输出 | **Markdown 计划**，可存仓库 |
| **任务分解方式**   | 单 Run 内模型自行拆步；Heartbeat 驱动清单任务 | **Subagents**（General/Explore + 自定义）+ **Task 工具** 层级委托 | 单 Agent 多步工具调用 + **Subagents** 并行 |
| **并发与串行**     | **Session Lane 串行** + Global Lane 限并发 + Sub-agent Lane 并行 | 主会话 + **child session** 并行；Session Tree 导航 | 主会话串行；**Subagents** 并行、独立 context |
| **权限与安全**     | 沙箱 + 工具策略 + 审批（见工具安全调研） | **permission** 按 Agent（edit/bash/webfetch/task）；Plan 默认禁写 | 敏感操作审批；MCP/终端需批准 |
| **可观测与 Hook**  | lifecycle/assistant/tool 流；Gateway/Plugin Hooks | 会话树、步骤限制（steps）、Agent 配置可见 | 计划可编辑、可版本管理；无公开 Run/Hook API |
| **主动/周期任务**  | **Heartbeat** + 任务清单 | 无内置；可配合外部 cron/脚本 | 无内置 |

---

## 五、选型与借鉴要点

- **需要「先规划、再执行」且计划要留档**：  
  - **Cursor Plan Mode** 最直接（Markdown 计划 + 存仓库）。  
  - **OpenCode** 用 **Plan 主 Agent** 也可达到「只规划不改代码」，再切 Build 执行；计划多为对话形式，需自行沉淀。  

- **需要严格「规划阶段零写操作」**：  
  - **OpenCode Plan** 通过 permission 把 write/edit/bash 关掉或设为 ask，最清晰。  
  - **Cursor Plan Mode** 下 Agent 行为由产品设计约束，不以「可写/不可写」细粒度区分。  

- **需要多任务并行与层级分解**：  
  - **OpenCode** 的 **Task 工具 + child session + Session Tree** 最成熟（含 subagent-to-subagent、task_budget）。  
  - **Cursor Subagents** 提供并行与独立 context，但层级与导航能力公开文档较少。  
  - **OpenClaw** 通过 **Sub-agent Lane** 与 Session Lane 分离做并行，更偏通道级并发控制。  

- **需要周期/主动任务与清单驱动**：  
  - **OpenClaw Heartbeat** 是现成能力；OpenCode、Cursor 需自行用外部定时或脚本触发。  

- **需要强可观测与扩展**：  
  - **OpenClaw** 的 Run/Attempt、事件流与 Gateway/Plugin Hooks 最开放，适合做审计与定制。  
  - **OpenCode** 的 Agent 配置与 permission 透明；**Cursor** 侧重产品体验，内部 Run 与 Hook 不暴露。  

---

## 六、参考链接

- **OpenClaw**: [System architecture](https://openclawcn.com/en/docs/concepts/system-architecture/), [Agent Loop](https://openclawcn.com/en/docs/concepts/agent-loop/), [Command Queue](https://openclawcn.com/en/docs/concepts/queue/), [Agent execution state machine](https://openclawcn.com/en/docs/deep-dive/framework-focus/agent-execution-state-machine/)
- **OpenCode**: [Agents](https://opencode.ai/docs/agents/), [Permissions](https://opencode.ai/docs/permissions), [Config](https://opencode.ai/docs/config)
- **Cursor**: [Plan Mode](https://cursor.com/docs/agent/plan-mode), [Creating plans](https://cursor.com/learn/creating-plans), [Agent best practices](https://www.cursor.com/blog/agent-best-practices), [Subagents & Skills (v2.4)](https://cursorworkshop.com/research/cursor-2-4-subagents-skills)
