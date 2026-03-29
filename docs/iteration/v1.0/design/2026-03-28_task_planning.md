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

## 1. 模块概述

Task Planning 模块负责任务的创建、分解、调度和跟踪。通过复杂度评估和复杂度路由，选择合适的执行策略。

### 1.1 核心职责

- 任务创建与分解
- 复杂度评估
- 执行调度
- 检查点管理
- 进度跟踪

### 1.2 差异化特性

| 特性 | 说明 |
|------|------|
| 动态分解 | 根据复杂度动态分解任务 |
| 多策略执行 | SIMPLE/MEDIUM/COMPLEX 不同策略 |
| 检查点恢复 | 支持从检查点恢复 |
| 进度可视化 | 实时进度跟踪 |

---

## 2. 模块结构

```
mozi/orchestration/
├── task/
│   ├── __init__.py
│   ├── manager.py       # TaskManager
│   ├── runner.py        # TaskRunner
│   ├── models.py        # Task 模型
│   └── state.py         # Task 状态机
│
├── checkpoint/
│   ├── __init__.py
│   ├── manager.py       # CheckpointManager
│   └── storage.py       # 检查点存储
│
├── progress/
│   ├── __init__.py
│   └── tracker.py       # ProgressTracker
│
└── routing/
    ├── __init__.py
    ├── assessor.py       # ComplexityAssessor
    └── router.py        # TaskRouter
```

---

## 3. TaskManager

### 3.1 任务模型

```python
@dataclass
class Task:
    id: str
    session_id: str
    description: str
    status: TaskStatus
    progress: float = 0.0
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        return self.status == TaskStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        return self.status == TaskStatus.FAILED

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

### 3.2 任务管理器

```python
class TaskManager:
    """任务管理器"""

    def __init__(self, storage: TaskStorage):
        self.storage = storage

    async def create(
        self,
        session_id: str,
        description: str,
        parent_id: Optional[str] = None,
    ) -> Task:
        """创建任务"""
        task = Task(
            id=str(uuid.uuid4()),
            session_id=session_id,
            description=description,
            status=TaskStatus.PENDING,
            parent_id=parent_id,
            created_at=datetime.now(),
        )

        await self.storage.save(task)

        # 更新父任务的子任务列表
        if parent_id:
            parent = await self.storage.get(parent_id)
            if parent:
                parent.children.append(task.id)
                await self.storage.save(parent)

        return task

    async def decompose(
        self,
        task_id: str,
        subtask_descriptions: List[str],
    ) -> List[Task]:
        """分解任务为子任务"""
        parent = await self.storage.get(task_id)
        if not parent:
            raise TaskNotFoundError(f"Task {task_id} not found")

        subtasks = []
        for desc in subtask_descriptions:
            subtask = await self.create(
                session_id=parent.session_id,
                description=desc,
                parent_id=task_id,
            )
            subtasks.append(subtask)

        # 更新父任务状态
        parent.status = TaskStatus.IN_PROGRESS
        await self.storage.save(parent)

        return subtasks

    async def get(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return await self.storage.get(task_id)

    async def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        progress: Optional[float] = None,
    ) -> Task:
        """更新任务状态"""
        task = await self.storage.get(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")

        task.status = status
        if progress is not None:
            task.progress = progress

        if status == TaskStatus.IN_PROGRESS and not task.started_at:
            task.started_at = datetime.now()
        elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            task.completed_at = datetime.now()

        await self.storage.save(task)

        # 如果是子任务，更新父任务进度
        if task.parent_id:
            await self._update_parent_progress(task.parent_id)

        return task

    async def _update_parent_progress(self, parent_id: str) -> None:
        """更新父任务进度"""
        parent = await self.storage.get(parent_id)
        if not parent or not parent.children:
            return

        children = [await self.storage.get(cid) for cid in parent.children]
        completed = sum(1 for c in children if c and c.is_complete)
        parent.progress = completed / len(children)

        await self.storage.save(parent)

    async def list_by_session(self, session_id: str) -> List[Task]:
        """列出会话的所有任务"""
        return await self.storage.list_by_session(session_id)

    async def cancel(self, task_id: str) -> Task:
        """取消任务"""
        task = await self.storage.get(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")

        task.status = TaskStatus.CANCELLED
        await self.storage.save(task)

        # 递归取消子任务
        for child_id in task.children:
            await self.cancel(child_id)

        return task
```

---

## 4. TaskRunner

### 4.1 任务运行器

```python
class TaskRunner:
    """任务运行器"""

    def __init__(
        self,
        task_manager: TaskManager,
        checkpoint_manager: "CheckpointManager",
        progress_tracker: "ProgressTracker",
        complexity_assessor: "ComplexityAssessor",
        task_router: "TaskRouter",
    ):
        self.task_manager = task_manager
        self.checkpoint_manager = checkpoint_manager
        self.progress_tracker = progress_tracker
        self.complexity_assessor = complexity_assessor
        self.task_router = task_router

    async def run(self, task: Task, context: Context) -> TaskResult:
        """运行任务"""
        # 1. 评估复杂度
        complexity = await self.complexity_assessor.assess(task, context)

        # 2. 选择执行策略
        strategy = self.task_router.route(complexity)

        # 3. 创建检查点
        await self.checkpoint_manager.create_checkpoint(task, context)

        # 4. 执行策略
        try:
            result = await strategy.execute(task, context, self)
            await self.task_manager.update_status(task.id, TaskStatus.COMPLETED, 1.0)
            return result
        except Exception as e:
            await self.task_manager.update_status(task.id, TaskStatus.FAILED)
            return TaskResult(success=False, error=str(e))

    async def resume(self, task: Task, context: Context) -> TaskResult:
        """从检查点恢复任务"""
        # 1. 获取检查点
        checkpoint = await self.checkpoint_manager.get_latest_checkpoint(task.id)
        if not checkpoint:
            raise NoCheckpointError(f"No checkpoint for task {task.id}")

        # 2. 恢复上下文
        context = checkpoint.context

        # 3. 继续执行
        return await self.run(task, context)
```

### 4.2 执行策略

```python
class ExecutionStrategy(ABC):
    """执行策略基类"""

    @abstractmethod
    async def execute(
        self,
        task: Task,
        context: Context,
        runner: TaskRunner,
    ) -> TaskResult:
        pass

class SimpleStrategy(ExecutionStrategy):
    """SIMPLE 任务策略"""

    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations

    async def execute(
        self,
        task: Task,
        context: Context,
        runner: TaskRunner,
    ) -> TaskResult:
        """直接执行，最多 5 次迭代"""
        agent = context.get_agent("builder")

        for i in range(self.max_iterations):
            result = await agent.run(task, context)

            if result.is_complete:
                return TaskResult(success=True, result=result)

        return TaskResult(success=False, error="Max iterations exceeded")

class MediumStrategy(ExecutionStrategy):
    """MEDIUM 任务策略"""

    def __init__(self, max_iterations: int = 15):
        self.max_iterations = max_iterations

    async def execute(
        self,
        task: Task,
        context: Context,
        runner: TaskRunner,
    ) -> TaskResult:
        """Builder + Reviewer，最多 15 次迭代"""
        builder = context.get_agent("builder")
        reviewer = context.get_agent("reviewer")

        for i in range(self.max_iterations):
            # Builder 执行
            build_result = await builder.run(task, context)
            if not build_result.is_complete:
                continue

            # Reviewer 审查
            review_result = await reviewer.run(task, context)
            if review_result.is_approved:
                return TaskResult(success=True, result=build_result)

            # 审查失败，Builder 继续修复
            task.description = f"{task.description}\n\nReview feedback: {review_result.feedback}"

        return TaskResult(success=False, error="Review not approved")

class ComplexStrategy(ExecutionStrategy):
    """COMPLEX 任务策略"""

    def __init__(self, max_iterations: int = 30):
        self.max_iterations = max_iterations

    async def execute(
        self,
        task: Task,
        context: Context,
        runner: TaskRunner,
    ) -> TaskResult:
        """Planner → Explorer → Builder → Reviewer"""
        planner = context.get_agent("planner")
        explorer = context.get_agent("explorer")
        builder = context.get_agent("builder")
        reviewer = context.get_agent("reviewer")

        # 1. Planner 规划
        plan = await planner.run(task, context)
        if not plan.is_valid:
            return TaskResult(success=False, error="Planning failed")

        # 2. Explorer 探索（如需要）
        if plan.needs_exploration:
            await explorer.run(task, context)

        # 3. Builder 执行
        build_result = await builder.run(task, context)
        if not build_result.is_complete:
            return TaskResult(success=False, error="Build failed")

        # 4. Reviewer 审查
        review_result = await reviewer.run(task, context)
        if not review_result.is_approved:
            return TaskResult(success=False, error="Review not approved")

        return TaskResult(success=True, result=build_result)

@dataclass
class TaskResult:
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
```

---

## 5. CheckpointManager

### 5.1 检查点管理

```python
class CheckpointManager:
    """检查点管理器"""

    def __init__(self, storage: CheckpointStorage):
        self.storage = storage

    async def create_checkpoint(
        self,
        task: Task,
        context: Context,
    ) -> Checkpoint:
        """创建检查点"""
        checkpoint = Checkpoint(
            id=str(uuid.uuid4()),
            task_id=task.id,
            session_id=task.session_id,
            state={
                "task": self._serialize_task(task),
                "context": self._serialize_context(context),
            },
            created_at=datetime.now(),
        )

        await self.storage.save(checkpoint)
        return checkpoint

    async def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """获取检查点"""
        return await self.storage.get(checkpoint_id)

    async def get_latest_checkpoint(self, task_id: str) -> Optional[Checkpoint]:
        """获取任务的最新检查点"""
        checkpoints = await self.storage.list_by_task(task_id)
        return checkpoints[-1] if checkpoints else None

    async def restore_checkpoint(self, checkpoint_id: str) -> Tuple[Task, Context]:
        """从检查点恢复"""
        checkpoint = await self.storage.get(checkpoint_id)
        if not checkpoint:
            raise CheckpointNotFoundError(f"Checkpoint {checkpoint_id} not found")

        task = self._deserialize_task(checkpoint.state["task"])
        context = self._deserialize_context(checkpoint.state["context"])

        return task, context

    async def delete_old_checkpoints(self, task_id: str, keep_count: int = 3) -> None:
        """删除旧检查点"""
        checkpoints = await self.storage.list_by_task(task_id)
        if len(checkpoints) > keep_count:
            for cp in checkpoints[:-keep_count]:
                await self.storage.delete(cp.id)

    def _serialize_task(self, task: Task) -> Dict[str, Any]:
        return asdict(task)

    def _deserialize_task(self, data: Dict[str, Any]) -> Task:
        return Task(**data)

    def _serialize_context(self, context: Context) -> Dict[str, Any]:
        return context.to_dict()

    def _deserialize_context(self, data: Dict[str, Any]) -> Context:
        return Context.from_dict(data)

@dataclass
class Checkpoint:
    id: str
    task_id: str
    session_id: str
    state: Dict[str, Any]
    created_at: datetime
```

---

## 6. ProgressTracker

### 6.1 进度跟踪

```python
class ProgressTracker:
    """进度跟踪器"""

    def __init__(self, emitter: ProgressEmitter):
        self.emitter = emitter
        self._progress: Dict[str, float] = {}

    async def update(self, task_id: str, progress: float) -> None:
        """更新进度"""
        self._progress[task_id] = progress
        await self.emitter.emit(task_id, progress)

    async def get_progress(self, task_id: str) -> float:
        """获取进度"""
        return self._progress.get(task_id, 0.0)

    async def wait_for_complete(self, task_id: str, timeout: float = 300) -> bool:
        """等待任务完成"""
        start = time.time()
        while time.time() - start < timeout:
            progress = self._progress.get(task_id, 0.0)
            if progress >= 1.0:
                return True
            await asyncio.sleep(0.5)
        return False

class ProgressEmitter(ABC):
    """进度事件发射器"""

    @abstractmethod
    async def emit(self, task_id: str, progress: float) -> None:
        pass

class CLIProgressEmitter(ProgressEmitter):
    """CLI 进度显示"""

    async def emit(self, task_id: str, progress: float) -> None:
        bar = "=" * int(progress * 20) + ">" + " " * (20 - int(progress * 20))
        print(f"\r[{bar}] {int(progress * 100)}% {task_id[:8]}", end="", flush=True)

class WebSocketProgressEmitter(ProgressEmitter):
    """WebSocket 进度推送"""

    def __init__(self, ws_manager: "WSManager"):
        self.ws_manager = ws_manager

    async def emit(self, task_id: str, progress: float) -> None:
        await self.ws_manager.broadcast({
            "type": "progress",
            "task_id": task_id,
            "progress": progress,
        })
```

---

## 7. 复杂度路由

### 7.1 复杂度评估器

```python
class ComplexityAssessor:
    """复杂度评估器"""

    def __init__(
        self,
        history_store: HistoryStore,
    ):
        self.history_store = history_store

    async def assess(self, task: Task, context: Context) -> ComplexityResult:
        """评估任务复杂度"""
        # 1. 预估修改文件数
        file_count_score = self._assess_file_count(task)

        # 2. 技术栈多样性
        tech_diversity_score = self._assess_tech_diversity(task, context)

        # 3. 跨模块依赖深度
        dependency_score = self._assess_dependency_depth(task, context)

        # 4. 历史成功率
        history_score = await self._assess_history(task)

        # 计算加权总分
        total_score = (
            file_count_score * 0.30 +
            tech_diversity_score * 0.20 +
            dependency_score * 0.30 +
            history_score * 0.20
        )

        # 确定复杂度级别
        if total_score <= 40:
            level = ComplexityLevel.SIMPLE
        elif total_score <= 70:
            level = ComplexityLevel.MEDIUM
        else:
            level = ComplexityLevel.COMPLEX

        return ComplexityResult(
            score=total_score,
            level=level,
            breakdown={
                "file_count": file_count_score,
                "tech_diversity": tech_diversity_score,
                "dependency": dependency_score,
                "history": history_score,
            }
        )

    def _assess_file_count(self, task: Task) -> float:
        """评估文件数量"""
        # 简单估算：根据描述中的文件路径
        file_mentions = len(re.findall(r"\.\w+", task.description))
        return min(file_mentions * 10, 100)

    def _assess_tech_diversity(self, task: Task, context: Context) -> float:
        """评估技术栈多样性"""
        tech_keywords = ["react", "vue", "angular", "django", "flask", "spring", "rails"]
        description_lower = task.description.lower()
        tech_count = sum(1 for tech in tech_keywords if tech in description_lower)
        return min(tech_count * 20, 100)

    def _assess_dependency_depth(self, task: Task, context: Context) -> float:
        """评估依赖深度"""
        # 简化实现
        if "dependency" in task.description.lower() or "import" in task.description.lower():
            return 60
        return 30

    async def _assess_history(self, task: Task) -> float:
        """评估历史成功率"""
        similar_tasks = await self.history_store.find_similar(task.description)
        if not similar_tasks:
            return 50  # 默认 50%

        success_rate = sum(1 for t in similar_tasks if t.success) / len(similar_tasks)
        return success_rate * 100

@dataclass
class ComplexityResult:
    score: float
    level: ComplexityLevel
    breakdown: Dict[str, float]
```

### 7.2 任务路由器

```python
class TaskRouter:
    """任务路由器"""

    def __init__(self):
        self.strategies = {
            ComplexityLevel.SIMPLE: SimpleStrategy(),
            ComplexityLevel.MEDIUM: MediumStrategy(),
            ComplexityLevel.COMPLEX: ComplexStrategy(),
        }

    def route(self, complexity: ComplexityResult) -> ExecutionStrategy:
        """根据复杂度选择策略"""
        return self.strategies[complexity.level]
```

---

## 8. 核心工作流

### 8.1 任务执行流程

```
任务输入
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                   TaskPlanning                               │
│                                                             │
│  1. ComplexityAssessor.assess()                            │
│     └── 评估复杂度                                          │
│                                                             │
│  2. TaskRouter.route()                                     │
│     └── 选择策略                                            │
│                                                             │
│  3. CheckpointManager.create_checkpoint()                  │
│     └── 创建检查点                                          │
│                                                             │
│  4. Strategy.execute()                                    │
│     ├── SIMPLE: Builder                                    │
│     ├── MEDIUM: Builder → Reviewer                        │
│     └── COMPLEX: Planner → Explorer → Builder → Reviewer │
│                                                             │
│  5. ProgressTracker.update()                               │
│     └── 更新进度                                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
任务完成
```

---

## 9. 依赖关系

- **依赖模块**: Agent Layer, Storage Layer
- **被依赖模块**: Orchestration Layer

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-03-28 | 初始版本，从架构文档拆分 |
