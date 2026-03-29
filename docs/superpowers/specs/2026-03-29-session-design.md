# Session 管理模块设计方案

> 对标 Claude Code 的会话管理系统

---

## 1. 概述

本模块为 Mozi AI Coding Agent 提供完整的会话管理能力，包括会话生命周期管理、持久化存储、上下文压缩和 CLI 命令集成。

### 1.1 设计目标

- **会话持久化**：支持会话中断恢复
- **命名会话**：通过名称标识和恢复会话
- **上下文压缩**：避免 context 溢出
- **CLI 集成**：支持 `-c`, `-n`, `-r`, `-p` 等命令行标志

### 1.2 核心组件

| 组件 | 职责 |
|------|------|
| `Session` | 会话数据模型 |
| `SessionManager` | 会话生命周期管理 |
| `SessionStorage` | 持久化层（JSON Lines） |
| `ContextCompactor` | 上下文压缩器 |
| `SessionCLI` | CLI 命令集成 |

---

## 2. 数据模型

### 2.1 Session

```python
@dataclass
class Session:
    id: str                          # UUID
    name: str | None                 # 可选名称
    project_path: str                # 项目路径
    state: SessionState              # ACTIVE/PAUSED/COMPLETED/ABANDONED/ERROR
    created_at: datetime
    updated_at: datetime
    complexity_score: int            # 0-100
    complexity_level: ComplexityLevel
    message_count: int              # 消息计数（用于压缩触发）
    total_tokens: int               # 总 token 数（用于压缩触发）
}
```

### 2.2 SessionMessage

```python
@dataclass
class SessionMessage:
    id: str                         # UUID
    role: str                       # user/assistant/system
    content: str                    # 消息内容
    timestamp: datetime
    tokens: int                      # token 计数
    artifacts: list[Artifact]       # 可选的 artifacts
```

### 2.3 SessionState

```python
class SessionState(Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"
    ERROR = "ERROR"
```

---

## 3. 存储结构

### 3.1 目录结构

```
~/.ai/projects/{project-id}/{session-id}/
├── conversation.jsonl   # 对话历史（每行一条 JSON）
├── metadata.json         # 会话元数据
└── subagents/           # 子 Agent 记录
    └── {agent-id}.jsonl
```

### 3.2 conversation.jsonl 格式

每行一条 JSON 消息：

```jsonl
{"id": "msg_xxx", "role": "user", "content": "...", "timestamp": "2026-03-29T10:00:00", "tokens": 150}
{"id": "msg_yyy", "role": "assistant", "content": "...", "timestamp": "2026-03-29T10:00:05", "tokens": 300}
```

### 3.3 metadata.json 格式

```json
{
  "id": "sess_abc123",
  "name": "my-session",
  "project_path": "/path/to/project",
  "state": "ACTIVE",
  "created_at": "2026-03-29T10:00:00",
  "updated_at": "2026-03-29T10:30:00",
  "complexity_score": 55,
  "complexity_level": "MEDIUM",
  "message_count": 42,
  "total_tokens": 80000
}
```

---

## 4. SessionManager

### 4.1 核心接口

```python
class SessionManager:
    def __init__(self, storage: SessionStorage): ...

    async def create_session(
        self,
        project_path: str,
        name: str | None = None,
        complexity_score: int = 0,
    ) -> Session: ...

    async def get_session(self, session_id: str) -> Session: ...

    async def get_session_by_name(self, name: str, project_path: str) -> Session | None: ...

    async def resume_session(self, session_id: str) -> Session: ...

    async def pause_session(self, session_id: str) -> Session: ...

    async def complete_session(self, session_id: str) -> Session: ...

    async def abandon_session(self, session_id: str) -> Session: ...

    async def delete_session(self, session_id: str) -> None: ...

    async def list_sessions(
        self,
        project_path: str | None = None,
        state: SessionState | None = None,
    ) -> list[Session]: ...

    async def add_message(self, session_id: str, message: SessionMessage) -> Session: ...

    async def get_messages(self, session_id: str) -> list[SessionMessage]: ...

    async def compact_if_needed(self, session_id: str) -> bool: ...
```

### 4.2 名称管理

- 同一项目下会话名称唯一
- `get_session_by_name` 支持通过名称查找会话
- 名称不区分大小写（规范化处理）

---

## 5. SessionStorage

### 5.1 接口

```python
class SessionStorage(ABC):
    @abstractmethod
    async def save_session(self, session: Session) -> None: ...

    @abstractmethod
    async def load_session(self, session_id: str) -> Session | None: ...

    @abstractmethod
    async def delete_session(self, session_id: str) -> None: ...

    @abstractmethod
    async def append_message(self, session_id: str, message: SessionMessage) -> None: ...

    @abstractmethod
    async def load_messages(self, session_id: str) -> list[SessionMessage]: ...

    @abstractmethod
    async def overwrite_messages(self, session_id: str, messages: list[SessionMessage]) -> None: ...
```

### 5.2 实现：FileSessionStorage

使用文件系统存储，支持：
- 自动创建目录
- 原子写入（先写临时文件再 rename）
- JSON Lines 格式追加写入

---

## 6. ContextCompactor

### 6.1 触发条件

当 `total_tokens >= context_limit * 0.95` 时触发压缩。

### 6.2 压缩算法

1. **聚类分析**：将消息按时间/主题分组
2. **摘要生成**：每个聚类生成摘要
3. **保留策略**：
   - 保留最近 N 条消息（不压缩）
   - 保留系统消息
   - 保留工具调用结果
   - 保留决策点消息
4. **压缩目标**：压缩至原始大小的 30-50%

### 6.3 接口

```python
class ContextCompactor:
    def __init__(self, llm_client: LLMClient): ...

    async def compact(self, messages: list[SessionMessage]) -> list[SessionMessage]:
        """返回压缩后的消息列表"""
        ...
```

---

## 7. CLI 集成

### 7.1 命令行标志

| 标志 | 说明 |
|------|------|
| `mozi` | 启动交互会话 |
| `mozi "task"` | 带初始提示的交互会话 |
| `mozi -p "query"` | 非交互模式（print mode） |
| `mozi -c` | 继续最近会话 |
| `mozi -r <name/id>` | 恢复指定会话 |
| `mozi -n <name>` | 创建命名会话 |
| `mozi --list-sessions` | 列出所有会话 |
| `mozi --delete-session <id>` | 删除会话 |

### 7.2 交互模式

- 启动时检查项目路径
- 自动加载或创建会话
- 会话状态持久化到 storage

### 7.3 非交互模式

- 执行单个查询并输出结果
- 打印模式（`-p/--print`）

---

## 8. 状态机

```
                    ┌──────────────────────────────────────────┐
                    │                                          │
                    ▼                                          │
              ┌──────────┐                                     │
    ┌────────►│  ACTIVE  │◄────────────┐                       │
    │         └────┬─────┘             │                       │
    │              │                   │                       │
    │              │ pause()           │ resume()              │
    │              │                   │                       │
    │              ▼                   │                       │
    │         ┌────────┐               │                       │
    │         │ PAUSED │───────────────┘                       │
    │         └────────┘                                     │
    │                                                          │
    │ complete()                                               │
    │                                                          │
    │              ┌────────────┐                              │
    └──────────────│ COMPLETED  │                             │
                   └────────────┘                              │
                                                              │
   abandon() ─────────────────────────────────────────► ABANDONED
                                                              │
                                                              │
   error() ─────────────────────────────────────────► ERROR

```

---

## 9. 项目结构

```
mozi/
├── cli/
│   ├── session.py          # SessionCLI 类
│   └── main.py             # CLI 入口
├── orchestrator/
│   └── session/
│       ├── __init__.py
│       ├── models.py        # Session, SessionMessage, SessionState
│       ├── manager.py       # SessionManager
│       ├── storage.py       # SessionStorage, FileSessionStorage
│       └── compactor.py     # ContextCompactor
└── tests/
    └── unit/
        └── orchestrator/
            └── session/
                ├── test_models.py
                ├── test_manager.py
                ├── test_storage.py
                └── test_compactor.py
```

---

## 10. 实现优先级

### P0 - 核心功能

- [ ] `Session`, `SessionMessage`, `SessionState` 数据模型
- [ ] `SessionStorage` 抽象和 `FileSessionStorage` 实现
- [ ] `SessionManager` 基础 CRUD
- [ ] CLI `-c`, `-r` 标志支持

### P1 - 重要功能

- [ ] 命名会话支持 (`-n`)
- [ ] `ContextCompactor` 实现
- [ ] `mozi --list-sessions` 命令

### P2 - 增强功能

- [ ] 子 Agent 会话记录
- [ ] 项目级会话过滤

---

*文档版本: 1.0*
*创建日期: 2026-03-29*
