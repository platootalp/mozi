# Product Manager Agent 职责边界设计

**版本**: v1.0
**日期**: 2026-03-26
**状态**: 已批准

---

## 1. 角色定义

### 1.1 product-manager

**职责范围**：

| 包含 | 不包含 |
|------|--------|
| 竞品分析 | API契约 |
| PRD文档 | 详细排期/人天估算 |
| 优先级与迭代规划 | UI/UX详细设计 |
| 数据指标设计 | 技术实现规格 |

**PRD文档结构**（精简版）：
1. 文档信息
2. 概述（背景、目标用户、解决的问题、成功指标）
3. 用户故事与用例
4. 功能需求（产品级描述，非技术规格）
5. 数据需求（业务数据，不含技术模型）
6. 非功能需求
7. 验收标准（自动化可测试）
8. 风险与依赖
9. 优先级与迭代范围（P0/P1/P2清单）
10. 假设与约束
11. 不在范围内

### 1.2 product-review-agent

**职责**：审批 product-manager 产出的产品文档

**触发方式**：自动触发（product-manager 完成后自动通知）

**审批维度**：

| 维度 | 检查项 |
|------|--------|
| 完整性 | PRD各章节是否齐全 |
| 一致性 | 与架构文档是否冲突 |
| 可操作性 | 验收标准是否可测试 |
| 优先级合理性 | MoSCoW是否合理 |

**审批结论**：
- `APPROVED` - 可直接进入开发
- `NEEDS_REVISION` - 需修改，自动打回 product-manager
- `BLOCKED` - 与架构文档冲突，通知人工介入

---

## 2. 协作流程

```
用户需求
    ↓
product-manager
    ↓ 生成文档
product-review-agent (自动触发)
    ↓ 审批
  ├─ APPROVED → 文档进入开发流程
  ├─ NEEDS_REVISION → 自动打回 product-manager 重新生成
  └─ BLOCKED → 通知人工介入
```

---

## 3. Agent 文件

- `/Users/lijunyi/road/mozi/.claude/agents/product-manager.md`
- `/Users/lijunyi/road/mozi/.claude/agents/product-review-agent.md` (新建)

---

## 4. 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-03-26 | 初始版本 |
