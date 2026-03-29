# Shared Types (共享类型定义)

## 文档信息

```
| 字段 | 内容 |
|------|------|
| 模块名称 | Shared Types |
| 职责 | 各模块公共类型定义 |
| 文档版本 | v1.1 |
| 状态 | 规划中 |
| 创建日期 | 2026-03-29 |
```

---

## 0. 导入说明

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
```

---

## 1. Orchestration 类型

### 1.1 Intent 枚举

```python
class Intent(Enum):
    """意图类型"""
    EXPLORE = "explore"      # 探索代码库
    CODE = "code"            # 编写/修改代码
    REVIEW = "review"        # 审查代码
    PLAN = "plan"            # 规划任务
    RESEARCH = "research"    # 研究技术

class IntentStatus(Enum):
    """意图识别状态"""
    CLEAR = "clear"          # 意图清晰
    AMBIGUOUS = "ambiguous"  # 意图模糊
    CONFLICTING = "conflicting"  # 意图冲突

@dataclass
class IntentResult:
    """意图识别结果"""
    status: IntentStatus
    intent: Optional[Intent] = None
    confidence: float = 1.0
    needs_clarification: bool = False
    explicit: Optional[Intent] = None
    implicit: Optional[Intent] = None
    routing: Optional[Dict[str, Any]] = None
```

**使用示例**:

```python
# 意图识别结果创建
result = IntentResult(
    status=IntentStatus.CLEAR,
    intent=Intent.CODE,
    confidence=0.95,
    routing={"agent": "builder", "max_iterations": 5}
)

# 意图冲突场景
ambiguous_result = IntentResult(
    status=IntentStatus.AMBIGUOUS,
    needs_clarification=True,
    explicit=Intent.CODE,
    implicit=Intent.REVIEW
)
```

### 1.2 Complexity 类型

```python
class ComplexityLevel(Enum):
    """复杂度级别"""
    SIMPLE = "simple"    # ≤40
    MEDIUM = "medium"    # 40-70
    COMPLEX = "complex"  # >70

@dataclass
class ComplexityResult:
    """复杂度评估结果"""
    score: float
    level: ComplexityLevel
    breakdown: Dict[str, float]
```

**使用示例**:

```python
# 复杂度评估结果
result = ComplexityResult(
    score=65.5,
    level=ComplexityLevel.MEDIUM,
    breakdown={
        "file_count": 20.0,
        "tech_diversity": 15.0,
        "dependency": 18.0,
        "history": 12.5
    }
)

# 根据复杂度级别路由
if result.level == ComplexityLevel.SIMPLE:
    max_iterations = 5
elif result.level == ComplexityLevel.MEDIUM:
    max_iterations = 15
else:
    max_iterations = 30
```

### 1.3 Loop 类型

```python
class LoopState(Enum):
    """循环状态"""
    COMPLETED = "completed"
    MAX_ITERATIONS_EXCEEDED = "max_iterations_exceeded"
    STUCK = "stuck"
    ERROR = "error"

@dataclass
class LoopResult:
    """循环执行结果"""
    state: LoopState
    iterations: int
    final_result: Optional[Any] = None
```

**使用示例**:

```python
# 成功完成
loop_result = LoopResult(
    state=LoopState.COMPLETED,
    iterations=3,
    final_result=AgentRunResult(...)
)

# 达到最大迭代
loop_result = LoopResult(
    state=LoopState.MAX_ITERATIONS_EXCEEDED,
    iterations=30,
    final_result=AgentRunResult(...)
)
```

### 1.4 Task 类型

```python
class TaskState(Enum):
    """任务状态"""
    INITIAL = "initial"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class ReenactResult:
    """重新激活结果"""
    success: bool
    reenactment_count: int
    reason: Optional[str] = None

@dataclass
class Task:
    """任务（抽象基类）"""
    id: str
    description: str
    session_id: str
    state: TaskState = TaskState.INITIAL
    checkpoint: Optional[Dict[str, Any]] = None
    reenactment_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        return self.state == TaskState.COMPLETED

    @property
    def has_checkpoint(self) -> bool:
        return self.checkpoint is not None

    def clear_context(self) -> None:
        """清空上下文"""
        pass

    def set_state(self, state: TaskState) -> None:
        """设置状态"""
        self.state = state

    def restore_checkpoint(self) -> None:
        """恢复检查点"""
        pass
```

**使用示例**:

```python
# 创建任务
task = Task(
    id="task-001",
    description="Fix login bug in user authentication",
    session_id="session-123"
)

# 任务状态转换
task.set_state(TaskState.IN_PROGRESS)

# 检查点保存
task.checkpoint = {"last_tool": "read", "last_file": "auth.py"}

# 重新激活
reenact_result = await todo_enforcer.reenact(task)
if reenact_result.success:
    print(f"Task reenacted, count: {reenact_result.reenactment_count}")
```

### 1.5 Permission 类型

```python
class PermissionStatus(Enum):
    """权限状态"""
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"

@dataclass
class PermissionResult:
    """权限检查结果"""
    status: PermissionStatus
    tool: str
    reason: Optional[str] = None
    requires_approval: bool = False
```

**使用示例**:

```python
# 权限检查结果处理
result = await permission_checker.check("bash", {"command": "git push origin main"})

if result.status == PermissionStatus.DENY:
    return ToolResult(success=False, error=f"Permission denied: {result.reason}")
elif result.status == PermissionStatus.ASK:
    # 触发 HITL
    approval_id = await hitl_manager.request_approval(tool_name, params, context)
```

---

## 2. Agent 类型

### 2.1 核心类型

```python
class AgentState(Enum):
    """Agent 状态"""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING = "waiting"
    DONE = "done"
    ERROR = "error"

@dataclass
class Thought:
    """思考结果"""
    needs_tool: bool                          # 是否需要调用工具
    tool: Optional[str] = None               # 工具名称
    params: Optional[Dict[str, Any]] = None  # 工具参数
    reasoning: Optional[str] = None           # 推理过程
    plan: Optional[List[str]] = None          # 执行计划

class ResultState(Enum):
    """结果状态"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"

@dataclass
class Result:
    """执行结果"""
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    progress: float = 0.0
    tool_used: Optional[str] = None
    state: ResultState = ResultState.SUCCESS

@dataclass
class AgentRunResult:
    """Agent 运行结果"""
    thought: Thought
    result: Result
    iterations: int = 1
```

**使用示例**:

```python
# Agent 思考结果
thought = Thought(
    needs_tool=True,
    tool="read",
    params={"path": "/project/main.py"},
    reasoning="需要读取主文件来理解项目结构",
    plan=["读取主文件", "分析代码", "修改bug"]
)

# Agent 执行结果
result = Result(
    success=True,
    content="File content here...",
    progress=0.5,
    tool_used="read",
    state=ResultState.SUCCESS
)

# 完整运行结果
run_result = AgentRunResult(
    thought=thought,
    result=result,
    iterations=1
)
```

---

## 3. Tools 类型

### 3.1 ToolContext

```python
@dataclass
class ToolContext:
    """工具执行上下文"""
    session_id: str
    user_id: Optional[str] = None
    working_dir: Path = Path.cwd()
    env: Dict[str, str] = field(default_factory=dict)

@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_error(self) -> bool:
        return not self.success

@dataclass
class ToolCall:
    """工具调用请求"""
    id: str
    tool_name: str
    params: Dict[str, Any]
    context: ToolContext
    created_at: datetime = field(default_factory=datetime.now)
```

**使用示例**:

```python
# 工具上下文创建
context = ToolContext(
    session_id="session-123",
    user_id="user-456",
    working_dir=Path("/project"),
    env={"PATH": "/usr/bin"}
)

# 工具调用请求
tool_call = ToolCall(
    id="call-001",
    tool_name="read",
    params={"path": "/project/main.py"},
    context=context
)

# 工具结果处理
result = ToolResult(
    success=True,
    content="file content",
    metadata={"lines_read": 100, "total_lines": 500}
)

if result.is_error:
    print(f"Error: {result.error}")
```

---

## 4. Memory 类型

### 4.1 Memory 类型

```python
class MemoryType(Enum):
    """记忆类型"""
    WORKING = "working"
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"

@dataclass
class MemoryEntry:
    """记忆条目"""
    id: int
    session_id: str
    type: MemoryType
    content: str
    created_at: datetime
    expires_at: Optional[datetime] = None

@dataclass
class UserPreferences:
    """用户偏好"""
    preferred_model: Optional[str] = None
    preferred_language: str = "en"
    coding_style: Optional[str] = None

@dataclass
class MemoryContext:
    """记忆上下文"""
    working: List[Any]
    short_term: List[MemoryEntry]
    long_term: UserPreferences

@dataclass
class Experience:
    """历史经验"""
    id: int
    session_id: str
    task_type: str
    success: bool
    summary: str
    details: Dict[str, Any]
    created_at: datetime
```

**使用示例**:

```python
# 创建记忆条目
entry = MemoryEntry(
    id=1,
    session_id="session-123",
    type=MemoryType.SHORT_TERM,
    content="用户之前询问过如何配置数据库",
    created_at=datetime.now(),
    expires_at=datetime.now() + timedelta(days=180)
)

# 用户偏好
prefs = UserPreferences(
    preferred_model="claude-sonnet-4-20250514",
    preferred_language="en",
    coding_style="google"
)

# 记忆上下文组装
memory_context = MemoryContext(
    working=[message1, message2],
    short_term=[entry1, entry2],
    long_term=prefs
)
```

---

## 5. Storage 类型

### 5.1 Session 类型

```python
class SessionStatus(Enum):
    """会话状态"""
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"

@dataclass
class Session:
    """会话"""
    id: str
    created_at: datetime
    updated_at: datetime
    status: SessionStatus
    complexity_level: Optional[ComplexityLevel] = None
    complexity_score: Optional[int] = None
    model: Optional[str] = None
    message_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_activity: Optional[datetime] = None

@dataclass
class Artifact:
    """Artifact 元数据"""
    id: str
    session_id: str
    name: str
    file_path: Path
    size: int
    content_type: str
    created_at: datetime
```

**使用示例**:

```python
# 创建会话
session = Session(
    id="session-123",
    created_at=datetime.now(),
    updated_at=datetime.now(),
    status=SessionStatus.ACTIVE,
    complexity_level=ComplexityLevel.MEDIUM,
    complexity_score=55,
    model="claude-sonnet-4-20250514",
    message_count=10
)

# 会话状态查询
active_sessions = await session_store.list(status=SessionStatus.ACTIVE)

# Artifact 存储
artifact = Artifact(
    id="artifact-001",
    session_id="session-123",
    name="output.png",
    file_path=Path("/artifacts/artifact-001_output.png"),
    size=1024,
    content_type="image/png",
    created_at=datetime.now()
)
```

---

## 6. Security 类型

### 6.1 HITL 类型

```python
class ApprovalStatus(Enum):
    """审批状态"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"

@dataclass
class PendingApproval:
    """待审批操作"""
    id: str
    tool_name: str
    params: Dict[str, Any]
    context: ToolContext
    created_at: datetime
    status: ApprovalStatus
    decided_at: Optional[datetime] = None
    reject_reason: Optional[str] = None

@dataclass
class AuditLog:
    """审计日志"""
    id: int
    session_id: Optional[str]
    action: str
    tool: Optional[str]
    params: Optional[Dict[str, Any]]
    result: Optional[str]
    user_decision: Optional[str]
    created_at: datetime
```

**使用示例**:

```python
# 创建待审批请求
approval = PendingApproval(
    id="approval-001",
    tool_name="bash",
    params={"command": "rm -rf /tmp/test"},
    context=tool_context,
    created_at=datetime.now(),
    status=ApprovalStatus.PENDING
)

# 审批操作
await hitl_manager.approve("approval-001")
# 或
await hitl_manager.reject("approval-001", reason="危险操作")

# 审计日志记录
audit_log = AuditLog(
    id=1,
    session_id="session-123",
    action="tool_call",
    tool="bash",
    params={"command": "git push"},
    result="success",
    user_decision="approved",
    created_at=datetime.now()
)
```

---

## 7. Context 类型

### 7.1 Message 类型

```python
@dataclass
class Message:
    """消息"""
    role: str  # "user" | "assistant" | "system"
    content: str
    name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Context:
    """执行上下文（跨模块引用）"""
    session_id: str
    task: Task
    memory: MemoryContext
    config: Dict[str, Any] = field(default_factory=dict)
    messages: List[Message] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
```

**使用示例**:

```python
# 消息创建
message = Message(
    role="user",
    content="帮我修复登录bug",
    metadata={"timestamp": datetime.now().isoformat()}
)

# 上下文创建
context = Context(
    session_id="session-123",
    task=task,
    memory=memory_context,
    messages=[message]
)

# 添加消息到上下文
context.messages.append(Message(role="assistant", content="我来帮你修复"))
```

---

## 8. Claude Code 对齐

### 8.1 类型映射

| Claude Code 类型 | Mozi 类型 | 说明 |
|-----------------|-----------|------|
| Conversation message | `Message` | 对话消息 |
| Session | `Session` | 会话 |
| Task | `Task` | 任务 |
| Tool use | `ToolCall` | 工具调用 |
| Permission | `PermissionResult` | 权限结果 |
| Memory entry | `MemoryEntry` | 记忆条目 |

### 8.2 Claude Code 权限模式

```python
class PermissionMode(Enum):
    """Claude Code 权限模式"""
    DEFAULT = "default"           # 操作前确认
    ACCEPT_EDITS = "acceptEdits"  # 自动接受编辑
    DONT_ASK = "dontAsk"          # 自动拒绝确认
    BYPASS_PERMISSIONS = "bypassPermissions"  # 跳过所有确认
    PLAN = "plan"                 # 只读探索模式
```

---

## 9. 类型一致性映射表

### 9.1 模块间类型引用

| 类型 | 定义位置 | 被引用模块 |
|------|----------|-----------|
| `Intent` | shared_types | orchestration, agent |
| `IntentResult` | shared_types | orchestration |
| `IntentStatus` | shared_types | orchestration |
| `ComplexityLevel` | shared_types | orchestration, storage |
| `ComplexityResult` | shared_types | orchestration |
| `LoopState` | shared_types | orchestration |
| `LoopResult` | shared_types | orchestration |
| `TaskState` | shared_types | orchestration |
| `Task` | shared_types | orchestration, agent, context |
| `ReenactResult` | shared_types | orchestration |
| `PermissionStatus` | shared_types | tools, security |
| `PermissionResult` | shared_types | tools, security |
| `AgentState` | shared_types | agent |
| `Thought` | shared_types | agent |
| `Result` | shared_types | agent, orchestration |
| `ResultState` | shared_types | agent |
| `AgentRunResult` | shared_types | agent, orchestration |
| `ToolContext` | shared_types | tools, security |
| `ToolResult` | shared_types | tools |
| `ToolCall` | shared_types | security |
| `MemoryType` | shared_types | memory |
| `MemoryEntry` | shared_types | memory, context |
| `UserPreferences` | shared_types | memory, context |
| `MemoryContext` | shared_types | memory, context |
| `Experience` | shared_types | memory |
| `SessionStatus` | shared_types | storage |
| `Session` | shared_types | storage |
| `Artifact` | shared_types | storage |
| `ApprovalStatus` | shared_types | security |
| `PendingApproval` | shared_types | security |
| `AuditLog` | shared_types | security |
| `Message` | shared_types | context |
| `Context` | shared_types | agent, orchestration |
| `PermissionMode` | shared_types | security |

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-03-29 | 初始版本，抽取各模块公共类型 |
| v1.1 | 2026-03-29 | 1. 添加缺失的 `ToolCall` 类型<br>2. 添加缺失的 `Context` 类型<br>3. 添加缺失的 `Message` 类型<br>4. 添加 `Task` 抽象基类<br>5. 添加 `field` 导入说明<br>6. 添加所有类型的完整 type annotations<br>7. 添加各类型的详细使用示例<br>8. 添加类型一致性映射表<br>9. 添加 Claude Code 对齐章节 |
