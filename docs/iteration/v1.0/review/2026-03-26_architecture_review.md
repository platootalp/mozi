# 架构文档评审报告

**文档**: `docs/architecture.md`
**评审日期**: 2026-03-26
**评审依据**: `AI_AGENT_PLANNING_TASK_COMPARISON.md`, `AI_AGENT_TOOLS_SECURITY_COMPARISON.md`

---

## 一、评审摘要

本文档整体架构清晰，六层架构（接入层→配置层→编排层→能力层→安全层→存储层）设计合理。但在**术语一致性**、**竞争对比准确性**、**关键机制细节**方面存在改进空间。建议优先修正与竞品的对比维度和 MCP 安全机制描述。

---

## 二、问题分类与修改建议

### 🔴 严重问题（影响理解准确性）

#### 1. 第11节对比表 - OpenCode 规划模式描述错误
**当前描述**: `Plan/Build 分离`
**问题**: OpenCode 并非"模式"切换，而是两个独立的 **Primary Agent**（Build 与 Plan），用户通过 Tab 键切换主 Agent。
**建议修改为**: `双主 Agent 分离（Tab 切换 Build/Plan）`

#### 2. 第11节对比表 - Cursor 多 Agent 描述不完整
**当前描述**: `Subagents`
**问题**: Cursor 实际上有两套并行机制：
- **Plan Mode**: 研究代码库 → 澄清需求 → 生成 Markdown 计划 → Build 执行
- **Subagents**: 并行执行独立子任务
**建议修改为**: `Plan Mode + Subagents`

#### 3. 第8.1节 - 温数据"云端"与部署架构冲突
**当前描述**: `云端向量库 (Qdrant/Milvus)`
**问题**: 第9节明确"核心引擎本地运行，确保代码安全"，但默认温数据指向云端，逻辑矛盾。
**建议修改为**: `向量库（可配置本地 Qdrant / 云端服务 / 嵌入式 Milvus）`

---

### 🟠 中等问题（机制描述不完整）

#### 4. 第3.2节 - 复杂度评估阈值过于简化
**当前阈值**: `>3文件 → 复杂, >2技术栈 → 复杂`

**问题分析**:
- 大型单体仓库中修改1个核心文件可能影响数十个模块
- 微服务架构中修改3个文件可能完全是独立变更
- 缺少**影响范围分析**和**加权评分**机制

**建议补充**:
```markdown
评估维度细化:
1. 预估修改文件数（权重 30%）
2. 技术栈多样性（权重 20%）
3. 跨模块依赖深度（静态分析，权重 30%）
4. 历史成功率（权重 20%）

阈值策略:
- 加权总分 > 70 → COMPLEX
- 40 < 加权总分 ≤ 70 → MEDIUM
- 加权总分 ≤ 40 → SIMPLE
```

#### 5. 第5.2节 - 权限层级冲突规则缺失
**当前描述**: 五级权限层级，deny 优先
**问题**: 未说明**同级别冲突**如何解决

**建议补充**:
```markdown
### 5.2.1 冲突解决规则

同级别冲突时，按以下优先级（从高到低）:
1. `deny` 显式声明
2. `ask` 显式声明
3. `allow` 显式声明
4. 继承上级策略

示例场景:
- Agent 级 `bash: allow` + 工具级 `"git push": deny` → `deny` 生效
- Agent 级 `"npm install": ask` + 全局 `bash: allow` → `ask` 生效
```

#### 6. 第4.1节 - MCP 安全机制缺失
**背景**: Cursor 曾出现 CVE-2025-54135/54136（MCP 配置注入漏洞）

**建议新增小节** `4.1.1 MCP 安全防护`:
```markdown
### 4.1.1 MCP 安全防护

| 风险 | 防护措施 |
|------|----------|
| 配置注入 | mcp.json 修改需重新审批 |
| 权限提升 | MCP 工具受 tools.json 策略约束，非继承 Server 声明 |
| 连接隔离 | 每个 MCP Server 独立进程，崩溃不影响主系统 |
| 网络限制 | 按 tools.json 的 web 策略控制 MCP 网络访问 |
```

---

### 🟡 轻微问题（可读性/一致性）

#### 7. 术语首次出现未解释
| 术语 | 位置 | 建议处理 |
|------|------|----------|
| HITL | 5.1节 | 改为"人工介入确认 (HITL, Human-in-the-Loop)" |
| DAG | 3.3节 | 增加括号解释"(Directed Acyclic Graph，有向无环图)" |
| ReAct | 3.3节 | 增加括号解释"(Reasoning + Acting)" |

#### 8. 第10节数据流图示冗余
**问题**: ASCII 流程图可读性差，维护成本高
**建议**: 移除 ASCII 流程图，改用时序图描述格式，或指向 Mermaid/PlantUML 文件

#### 9. 第3.3节表格 - COMPLEX 通道描述不准确
**当前**: `多Agent协作`
**建议**: `多Agent协作（Orchestrator 调度 + DAG 执行）`
理由: 强调与 OpenCode、Cursor 的差异点（Mozi 是调度器驱动，非子 Agent 自发协作）

---

## 三、建议新增内容

### 3.1 第3.5节 - 规划模式详细设计（新增）

Mozi 的自适应规划是与竞品的核心差异化功能，当前描述过简。

```markdown
### 3.5 规划模式实现

| 复杂度 | 规划行为 | 产物 | 用户可见性 |
|--------|----------|------|------------|
| SIMPLE | 无显式规划，ReAct 循环内隐式规划 | 无 | 无 |
| MEDIUM | 步骤列表追踪（内存中） | 执行日志 | 低 |
| COMPLEX | 生成 DAG 计划，支持导出 | Markdown 计划文档 | 高 |

**DAG 计划结构**:
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

**与竞品对比**:
- Cursor Plan Mode: 研究→澄清→计划→执行，计划可编辑
- OpenCode Plan Agent: 只读分析，产出对话式建议
- Mozi COMPLEX 模式: 调度器生成 DAG，自动化并行，产物可导出
```

### 3.2 附录 - 术语表（新增）

```markdown
| 术语 | 英文全称 | 含义 |
|------|----------|------|
| HITL | Human-in-the-Loop | 人工介入确认，敏感操作需用户批准 |
| DAG | Directed Acyclic Graph | 有向无环图，用于任务依赖编排 |
| MCP | Model Context Protocol | 模型上下文协议，标准化工具扩展接口 |
| ReAct | Reasoning + Acting | 推理+行动循环，LLM Agent 基础模式 |
| Lane | - | 执行通道，用于并发控制与隔离 |
| FastPath | - | 快速通道，简单任务的直接执行路径 |
```

---

## 四、优先级汇总

| 优先级 | 问题编号 | 修改类型 | 预计工作量 |
|--------|----------|----------|------------|
| 🔴 P0 | 1, 2, 3 | 修正描述 | 30分钟 |
| 🟠 P1 | 4, 5, 6 | 补充机制 | 2小时 |
| 🟡 P2 | 7, 8, 9 | 优化可读性 | 1小时 |
| 📋 P3 | 3.1, 3.2 | 新增章节 | 3小时 |

---

## 五、竞品对比关键差异（供参考）

基于调研文档，Mozi 与竞品的**核心差异点**应在架构文档中强调：

| 维度 | Mozi | 优势说明 |
|------|------|----------|
| 规划模式 | **自适应**（SIMPLE/MEDIUM/COMPLEX 自动路由） | Cursor/OpenCode 需用户显式选择 |
| 多 Agent 调度 | **Orchestrator 中心化调度** | OpenCode 是层级委托，Cursor 是并行执行 |
| 存储架构 | **四级存储 + 自动分层** | 竞品多为单一存储或需手动配置 |
| 安全模型 | **四层防护 + HITL** | 层级最完整，含审批机制 |
| 心跳/主动任务 | **内置 Heartbeat** | OpenCode/Cursor 需外部 cron |

---

*评审完成*
