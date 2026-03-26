# OpenClaw、Cursor、Claude Code 工具系统与安全防护深度调研

本文对 **OpenClaw**、**Cursor**、**Claude Code（Claude API 代码执行）** 三者的**工具系统架构**与**安全防护机制**做对比调研，便于选型与安全加固参考。

---

## 一、OpenClaw

### 1.1 定位与架构

- **定位**：开源、本地优先的 AI 私人助理，支持编程与自动化，可对接微信/Telegram/Discord/Slack 等 20+ 渠道。
- **运行环境**：跑在用户自己的 Mac/Windows/Linux 上，数据不出本机；支持 Docker 私有部署。
- **模型**：支持 Claude、GPT、Gemini、Ollama 等，API Key 自管。

### 1.2 工具系统

- **内置工具分组**（可配置 allow/deny）：
  - **group:fs**：`read`、`write`、`edit`、`apply_patch`
  - **group:runtime**：`exec`、`bash`、`process`
  - **group:sessions**：`sessions_list`、`sessions_history`、`sessions_send`、`sessions_spawn`、`session_status`
  - **group:memory**：`memory_search`、`memory_get`
  - **group:ui**：`browser`、`canvas`
  - **group:automation**：`cron`、`gateway`
  - **group:messaging**：`message`
  - **group:nodes**：`nodes`
  - **group:openclaw**：所有内置 OpenClaw 工具（不含第三方 provider 插件）

- **工具策略层级**（权限只能收紧不能放宽，`deny` 优先）：
  - 全局：`openclaw.json` 中 `tools.allow` / `tools.deny`
  - 按 Agent：`agents.list[].tools.allow` / `agents.list[].tools.deny`
  - 沙箱内：`tools.sandbox.tools.allow` / `tools.sandbox.tools.deny`
  - 按 Provider：`tools.byProvider[provider].allow/deny`、`tools.profile`

- **exec 工具**：
  - 支持 `host`: `sandbox` | `gateway` | `node`（默认 `sandbox`）
  - 前台/后台、超时、PTY、`workdir`、`env`；主机执行时**拒绝 `env.PATH` 与 `LD_*`/`DYLD_*`** 以防二进制劫持
  - 审批：`~/.openclaw/exec-approvals.json`，支持 allowlist、safe bins、`security=deny|allowlist|full`、`ask=off|on-miss|always`
  - **提权（elevated）**：仅影响 exec，不新增工具；需 `tools.elevated.enabled` 与 `tools.elevated.allowFrom`，用于在沙箱开启时在主机上执行（审批仍可启用）

### 1.3 安全防护

- **三层控制**：
  1. **沙箱（Sandbox）**：工具**在哪里跑**（Docker vs 主机）
     - `mode`: `off`（全主机）、`non-main`（仅非主会话隔离）、`all`（全部容器隔离）
     - 工作区挂载可配 `workspaceAccess: "ro"`/`"rw"`；绑定 `/var/run/docker.sock` 会交出主机控制权，需显式配置
  2. **工具策略（Tool Policy）**：**哪些工具**可用/被拒绝（见上）
  3. **提权（Elevated）**：仅 exec 的「在主机上跑」通道，受 allowFrom 与 enabled 限制

- **调试与审计**：
  - `openclaw sandbox explain`：查看当前沙箱模式、工具允许/拒绝、提权、会话是否被隔离
  - `openclaw security audit`（含 `--deep`、`--fix`）：多发送者共享主会话等风险提示；小模型 + 未开沙箱 + web/browser 工具时会告警

- **最佳实践**（文档建议）：
  - 生产用 Docker 沙箱；最小权限；高风险操作走审批；定期审计；不把解释器当 safeBins 用，用 allowlist + approval

---

## 二、Cursor

### 2.1 定位与架构

- **定位**：基于 VS Code 的 AI 编程 IDE，Agent 可独立完成多步编码任务、跑终端、改代码。
- **组成**：Model + Tools + Instructions（含 Rules）；工具由 Cursor 编排，按需调用。

### 2.2 工具系统

- **一等公民工具**（Agent 直接使用）：
  - **语义检索**：在已索引代码库内按语义搜索
  - **文件/目录搜索**：按路径、关键词、模式查找
  - **Web**：生成搜索请求并执行网页搜索
  - **Fetch Rules**：按类型/描述拉取规则
  - **读文件**：读文件内容，支持图片（png/jpg/gif/webp/svg）给视觉模型
  - **编辑文件**：建议并应用编辑（改完即落盘，配置类需审批）
  - **运行 Shell**：执行终端命令，默认需**逐条审批**
  - **Browser**：导航、交互、截图、验证前端
  - **Image generation**：文生图，默认存项目 `assets/`
  - **Ask questions**：任务中向用户追问

- **第三方工具：MCP（Model Context Protocol）**
  - 传输：stdio（本地）、SSE、Streamable HTTP（可远程）
  - 能力：Tools、Prompts、Resources、Roots、Elicitation、MCP Apps
  - 配置：Cursor Marketplace 一键安装，或 `~/.cursor/mcp.json` / `.cursor/mcp.json`，支持 OAuth、`env`、插值（如 `${env:API_KEY}`）
  - **每次 MCP 连接需用户批准**；**每个 MCP 工具调用默认也需单独批准**，可开 Auto-run（与终端类似，风险自担）

### 2.3 安全防护

- **默认策略**（官方建议保持）：
  - 读文件、代码搜索：不需批准；用 `.cursorignore` 排除敏感路径
  - 改工作区文件：除配置类外自动保存；配置类需批准
  - **终端命令**：默认每条批准；可开 allowlist 自动通过（best-effort，非完全保证）；**禁止使用 "Run Everything"**
  - **MCP**：连接 + 每次工具调用均需批准（除非开 Auto-run）
  - **网络**：仅允许向 Web 搜索提供商、直接链接拉取、GitHub 发请求，**禁止任意外网请求**

- **工作区信任**：支持 VS Code 的 workspace trust，默认关；开启后新工作区可选受限模式（会限制 AI 能力）。

- **已知漏洞与修复**：
  - **CVE-2025-54135（CurXecute）**：通过注入诱导 Agent 修改 `mcp.json` 并在用户批准前执行恶意命令 → RCE；CVSS 8.5。修复：Cursor 1.3 起对 mcpServer 条目**每次修改都需重新批准**。
  - **CVE-2025-54136（MCPoison）**：已批准过的 MCP 配置后续被静默替换为恶意配置不再触发复核 → 团队级持久化风险；CVSS 7.2。修复：同上，配置变更需重新批准。

- **建议**：
  - 关闭 Auto-Run（最大风险）；敏感项目用 Privacy Mode、`.cursorignore`；终端/MCP 尽量审批制；企业可配网络出口与 MDM；漏洞反馈：security-reports@cursor.com。Cursor 持有 SOC 2 Type II。

---

## 三、Claude Code（Claude API 代码执行工具）

此处指 **Anthropic Claude API 的 Code Execution Tool**（`code_execution_20250825`），用于在对话中执行 Bash 与文件操作，而非桌面端「Claude Code」产品。

### 3.1 工具系统

- **能力**：
  - 在**服务端沙箱**中执行 Bash、创建/查看/编辑文件、处理上传文件
  - 与 `web_search` / `web_fetch` 同时使用时，代码执行可免费（仅计 token）
  - 支持**容器复用**（传 `container` ID）在多次请求间保留工作区状态（最长约 30 天）

- **环境**：
  - 架构：x86_64 Linux 容器
  - Python 3.11.12；预装常用库（pandas、numpy、matplotlib、pillow、pypdf 等）
  - 当前版本：Bash + 文件操作；旧版 `code_execution_20250522` 仅 Python

### 3.2 安全与隔离

- **资源限制**：
  - CPU：1 核；内存：5GiB；磁盘：5GiB 工作区
  - 执行超时等会返回 `execution_time_exceeded`、`container_expired`、`too_many_requests` 等

- **网络与访问**：
  - **无外网**：沙箱内不允许出站请求，互联网关闭
  - **文件范围**：仅限工作区目录；与 API Key 的 workspace 一致
  - **隔离**：与主机及其他容器完全隔离

- **与自建工具并存**：若同时提供自建 bash/REPL 等工具，需在 system prompt 中明确区分「Anthropic 沙箱」与「用户本地环境」，避免模型混用环境或假设状态共享。

- **合规**：代码执行功能不适用 Zero Data Retention（ZDR），按常规保留策略。

---

## 四、对比总览

| 维度 | OpenClaw | Cursor | Claude Code (API) |
|------|----------|--------|-------------------|
| **部署** | 本地/自托管，数据在本机 | 云端 IDE + 本地工作区 | 纯 API，执行在 Anthropic 沙箱 |
| **工具范围** | 文件/exec/浏览器/会话/记忆/节点等，可扩展 | 代码库/文件/终端/Web/Browser/MCP/规则 | Bash + 工作区文件，无网络 |
| **执行环境** | 用户主机 或 Docker 沙箱（可配） | 用户本机终端 + 可选 MCP 远程 | 远程 Linux 容器，强隔离 |
| **终端/exec** | 需配置；沙箱/主机/节点可选；审批与 allowlist | 默认每条审批；可 allowlist；禁止 Run Everything | 仅在沙箱内，无主机访问 |
| **网络** | 用户控制（主机/容器策略） | 仅搜索/直链/GitHub | 沙箱内无外网 |
| **权限模型** | 沙箱 + 工具策略 + 提权；deny 优先、层级可配 | 读/搜不批；写除配置外自动；终端与 MCP 默认审批 | 仅工作区 + API Key 作用域 |
| **扩展** | 技能/插件、工具组、byProvider | MCP 服务器（stdio/SSE/HTTP） | 无；需自建 client tools |
| **审计/调试** | `sandbox explain`、`security audit` | 无内置审计；MCP 日志在 Output | 无用户侧审计接口 |
| **已知 CVE** | 无公开 RCE 类 CVE（调研时） | CurXecute、MCPoison（已修复） | 未检索到针对该工具的 CVE |

---

## 五、安全防护小结

- **OpenClaw**：强在**可配置的沙箱 + 工具策略 + 审批**，适合自管环境与生产；主机执行时显式拒绝 PATH/LD_* 等，并有 safeBins vs allowlist 区分，需正确配置避免过度放权。
- **Cursor**：强在**默认敏感操作需批准**与**网络白名单**；MCP 与终端是主要风险面，已通过「每次 MCP 配置变更需批准」缓解 CurXecute/MCPoison；企业需关 Auto-Run、控网络与规则。
- **Claude Code（API）**：强在**无外网、仅工作区、固定资源与过期**，适合把「计算与文件」放在云端且不接受主机访问的场景；与自建执行工具混用时需在提示中明确环境边界。

---

## 参考资料

- OpenClaw: [openclaws.io](https://openclaws.io/zh/), [沙箱与工具策略](https://docs.openclaw.ai/zh-CN/gateway/sandbox-vs-tool-policy-vs-elevated), [Exec 工具](https://docs.openclaw.ai/tools/exec), [security CLI](https://docs.openclaw.ai/zh-CN/cli/security)
- Cursor: [Agent 概览](https://cursor.com/docs/agent/overview), [Agent 安全](https://cursor.com/docs/agent/security), [MCP](https://cursor.com/docs/mcp), [CVE-2025-54135/54136 与修复](https://github.com/cursor/cursor/security/advisories/GHSA-24mc-g4xr-4395)
- Claude: [Code execution tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/code-execution-tool)（资源限制、网络与安全小节）

*文档基于 2025–2026 年公开文档与漏洞公告整理，具体行为以各产品最新文档为准。*
