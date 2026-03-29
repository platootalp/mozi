# SQLite 会话模式设计

## 概述

会话存储采用 SQLite 数据库，提供持久化和恢复能力。

## 数据库模式

### 表: sessions

| 字段 | 类型 | 约束 | 描述 |
|------|------|------|------|
| id | TEXT | PRIMARY KEY | UUID 会话标识 |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL | 更新时间 |
| status | TEXT | NOT NULL | ACTIVE/COMPLETED/ERROR |
| complexity_level | TEXT | NOT NULL | SIMPLE/MEDIUM/COMPLEX |
| complexity_score | INTEGER | | 复杂度评分 |
| metadata | JSON | | 额外元数据 |

### 表: messages

| 字段 | 类型 | 约束 | 描述 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 消息 ID |
| session_id | TEXT | FOREIGN KEY | 会话外键 |
| role | TEXT | NOT NULL | user/assistant/system |
| content | TEXT | NOT NULL | 消息内容 |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |

### 表: checkpoints

| 字段 | 类型 | 约束 | 描述 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 检查点 ID |
| session_id | TEXT | FOREIGN KEY | 会话外键 |
| state | JSON | NOT NULL | 恢复状态 |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |

### 表: audit_logs

| 字段 | 类型 | 约束 | 描述 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 日志 ID |
| session_id | TEXT | | 会话外键（可选） |
| action | TEXT | NOT NULL | 操作类型 |
| tool | TEXT | | 工具名称 |
| result | TEXT | | 结果 |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |

## 索引

```sql
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_created ON sessions(created_at);
CREATE INDEX idx_messages_session ON messages(session_id);
CREATE INDEX idx_checkpoints_session ON checkpoints(session_id);
CREATE INDEX idx_audit_logs_session ON audit_logs(session_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at);
```

## ER 图

```
┌─────────────┐       ┌─────────────┐
│  sessions   │       │   messages  │
├─────────────┤       ├─────────────┤
│ id (PK)     │──1:N──│ id (PK)     │
│ created_at  │       │ session_id  │
│ updated_at  │       │ role        │
│ status      │       │ content     │
│ complexity  │       │ created_at  │
│ metadata    │       └─────────────┘
└─────────────┘

┌─────────────┐       ┌─────────────┐
│ checkpoints│       │ audit_logs  │
├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │
│ session_id  │──1:N──│ session_id  │
│ state (JSON)│       │ action      │
│ created_at  │       │ tool        │
└─────────────┘       │ result      │
                      │ created_at  │
                      └─────────────┘
```

## SQL 脚本

```sql
-- 会话表
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    complexity_level TEXT NOT NULL DEFAULT 'SIMPLE',
    complexity_score INTEGER,
    metadata JSON
);

-- 消息表
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- 检查点表
CREATE TABLE checkpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    state JSON NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- 审计日志表
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    action TEXT NOT NULL,
    tool TEXT,
    result TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```

---

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2026-03-28 | 初始模式 |
