# Task Planning Module (任务与规划模块)

## 文档信息

| 字段 | 内容 |
|------|------|
| 模块名称 | Task & Planning |
| 职责 | 任务创建分解、执行调度、检查点、进度跟踪 |
| 路径 | `mozi/orchestration/` |
| 文档版本 | v1.0 |
| 状态 | 规划中 |
| 创建日期 | 2026-03-28 |

---

## 1. 组件列表

| 组件 | 职责 |
|------|------|
| **TaskManager** | 任务创建、分解、状态跟踪 |
| **TaskRunner** | 任务执行调度 |
| **CheckpointManager** | 检查点保存与恢复 |
| **ProgressTracker** | 进度跟踪 |

## 2. 复杂度路由

### 评估维度

| 维度 | 权重 |
|------|------|
| 预估修改文件数 | 30% |
| 技术栈多样性 | 20% |
| 跨模块依赖深度 | 30% |
| 历史成功率 | 20% |

### 路由策略

| 复杂度 | 范围 | Agent 行为 |
|--------|------|----------|
| **SIMPLE** | ≤40 | Builder 直接执行 |
| **MEDIUM** | 41-70 | Builder + Reviewer |
| **COMPLEX** | >70 | Planner → Explorer → Builder → Reviewer |

## 3. Task Schema

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

## 4. 依赖关系

- **依赖模块**: Agent Layer, Storage Layer
- **被依赖模块**: Orchestration Layer

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-03-28 | 初始版本，从架构文档拆分 |
