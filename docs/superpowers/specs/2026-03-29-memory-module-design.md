# Memory Module Design

## 1. 概述

### 1.1 模块定位

Memory 模块是独立于 Context 的记忆存储层，负责四类记忆的持久化和检索。

### 1.2 四类记忆

| 类型 | 存储内容 | 生命周期 | 检索方式 |
|------|---------|---------|---------|
| Episodic | 会话情景、任务执行历史 | 智能保留（LLM判断） | 向量 + 关键词混合 |
| Preference | 用户偏好（语言、代码风格、工具选择） | 永久（可学习更新） | 精确查询 |
| Experience | 成功/失败模式、任务类型 | 永久（按任务类型索引） | 相似任务召回 |
| Procedural | 工具使用模式、执行策略、代码模式 | 永久（跨项目共享） | 模式匹配 |

### 1.3 与 Context 的边界

- Context 是高层接口，负责上下文组装和遗忘策略
- Memory 是底层存储，提供四类记忆的 CRUD 和检索
- Context.assemble() 调用 Memory 获取记忆，Memory 不知道 Context 的存在

---

## 2. 数据模型

```python
class MemoryType(Enum):
    """记忆类型"""
    EPISODIC = "episodic"           # 情景记忆
    PREFERENCE = "preference"       # 用户偏好
    EXPERIENCE = "experience"        # 历史经验
    PROCEDURAL = "procedural"       # 程序记忆


@dataclass
class MemoryItem:
    """记忆统一数据模型"""
    id: str
    type: MemoryType
    content: str

    # 来源追踪
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    # 重要性（智能保留用）
    importance: float = 0.5

    # 向量检索用
    embedding: Optional[List[float]] = None
    keywords: List[str] = field(default_factory=list)

    # 元数据（类型特定）
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PreferenceItem(MemoryItem):
    """偏好记忆"""
    type: MemoryType = MemoryType.PREFERENCE
    metadata: Dict[str, Any] = field(default_factory=lambda: {
        "category": "coding_style",  # coding_style | tool_choice | model
        "learned": False,
    })


@dataclass
class ExperienceItem(MemoryItem):
    """经验记忆"""
    type: MemoryType = MemoryType.EXPERIENCE
    metadata: Dict[str, Any] = field(default_factory=lambda: {
        "task_type": "",             # 任务类型
        "success": True,
        "tools_used": [],            # 使用的工具列表
        "strategy": "",              # 执行的策略
        "duration_seconds": 0,
    })


@dataclass
class ProceduralItem(MemoryItem):
    """程序记忆"""
    type: MemoryType = MemoryType.PROCEDURAL
    metadata: Dict[str, Any] = field(default_factory=lambda: {
        "pattern_type": "",          # tool_usage | execution_strategy | code_style
        "applicability": "",         # 适用场景描述
        "usage_count": 0,
    })
```

---

## 3. 四类记忆的存储设计

```
MemoryStore (Facade)
├── EpisodicStore      # 情景记忆
├── PreferenceStore    # 偏好记忆
├── ExperienceStore   # 经验记忆
└── ProceduralStore    # 程序记忆
```

### 3.1 EpisodicStore（情景记忆）

```python
class EpisodicStore:
    """
    情景记忆 - SQLite + Qdrant 混合存储

    存储内容：会话中的关键事件、任务执行过程、重要决策点
    生命周期：智能保留（LLM判断是否值得保留）
    检索方式：向量 + 关键词混合检索
    """

    def __init__(self, config: EpisodicConfig):
        self.db_path = config.db_path
        self.vector_store = QdrantStore(config.qdrant)
        self.llm_judger = LLMJudger(config.judger)
        self._init_db()

    async def add(self, item: MemoryItem) -> MemoryItem:
        """添加条目，自动判断是否值得持久化"""
        # 1. LLM 判断是否值得保留
        should_persist = await self.llm_judger.should_persist(
            content=item.content,
            context={"session_id": item.session_id}
        )

        if not should_persist:
            return item  # 不持久化，仅返回

        # 2. 存储到 SQLite + Qdrant
        await self._sqlite_insert(item)
        if item.embedding:
            await self.vector_store.upsert(
                id=item.id,
                vector=item.embedding,
                payload={"content": item.content, "session_id": item.session_id}
            )

        return item

    async def search(
        self,
        query: str,
        session_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[MemoryItem]:
        """混合检索：向量 + 关键词"""
        # 向量搜索
        vector_results = await self.vector_store.search(
            query=query,
            namespace=session_id,
            limit=limit,
        )

        # 关键词搜索
        keyword_results = await self._keyword_search(query, session_id, limit)

        # 合并去重
        return self._merge_results(vector_results, keyword_results, limit)
```

### 3.2 PreferenceStore（偏好记忆）

```python
class PreferenceStore:
    """
    偏好记忆 - SQLite 持久化

    存储内容：用户偏好的语言、代码风格、工具选择、模型选择
    生命周期：永久（可学习更新）
    检索方式：精确查询（key-value）
    """

    def __init__(self, config: PreferenceConfig):
        self.db_path = config.db_path
        self._init_db()

    async def learn(self, session_id: str, preference: Dict[str, str]) -> None:
        """从交互中学习偏好"""
        for key, value in preference.items():
            existing = await self.get(session_id, key)
            if existing:
                await self.update(session_id, key, value)
            else:
                await self.insert(session_id, key, value)

    async def get(self, session_id: str, key: str) -> Optional[str]:
        """精确查询偏好"""
        ...

    async def get_all(self, session_id: str) -> Dict[str, str]:
        """获取用户所有偏好"""
        ...
```

### 3.3 ExperienceStore（经验记忆）

```python
class ExperienceStore:
    """
    经验记忆 - SQLite 持久化

    存储内容：任务执行的成功/失败模式
    生命周期：永久
    检索方式：按任务类型召回相似经验
    """

    async def add(self, outcome: TaskOutcome) -> None:
        """记录任务执行结果"""
        item = ExperienceItem(
            id=str(uuid.uuid4()),
            content=self._summarize_outcome(outcome),
            metadata={
                "task_type": outcome.task_type,
                "success": outcome.success,
                "tools_used": outcome.tools_used,
                "strategy": outcome.strategy,
                "duration_seconds": outcome.duration,
            }
        )
        await self._sqlite_insert(item)

    async def recall_similar(
        self,
        task_type: str,
        limit: int = 5,
    ) -> List[ExperienceItem]:
        """召回相似任务类型的经验"""
        ...
```

### 3.4 ProceduralStore（程序记忆）

```python
class ProceduralStore:
    """
    程序记忆 - SQLite 持久化

    存储内容：工具使用模式、执行策略、代码模式
    生命周期：永久（跨项目共享）
    检索方式：模式匹配
    """

    async def add_tool_pattern(
        self,
        tool_name: str,
        pattern: str,
        applicability: str,
    ) -> None:
        """记录工具使用模式"""
        ...

    async def add_execution_strategy(
        self,
        task_type: str,
        strategy: str,
        success_rate: float,
    ) -> None:
        """记录执行策略"""
        ...

    async def match_procedures(
        self,
        context: Dict[str, Any],
    ) -> List[ProceduralItem]:
        """根据上下文匹配适用的程序记忆"""
        ...
```

---

## 4. 检索层 MemoryQuery

```python
@dataclass
class MemoryQueryCriteria:
    """记忆查询条件"""
    types: List[MemoryType] = field(default_factory=list)  # 空=查所有
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    importance_min: float = 0.0
    time_range: Optional[Tuple[datetime, datetime]] = None


class MemoryQuery:
    """
    统一记忆检索引擎

    负责：
    1. 跨多类记忆的聚合检索
    2. 多维度评分和排序
    3. 记忆召回策略
    """

    def __init__(self, store: MemoryStore):
        self.store = store

    async def retrieve(
        self,
        criteria: MemoryQueryCriteria,
        limit: int = 20,
    ) -> List[MemoryItem]:
        """
        检索记忆
        1. 根据 type 路由到对应 Store
        2. 聚合结果
        3. 多维度排序
        """
        results: List[MemoryItem] = []

        # 路由检索
        if not criteria.types or MemoryType.EPISODIC in criteria.types:
            episodic = await self.store.episodic.search(
                query=criteria.keywords[0] if criteria.keywords else "",
                session_id=criteria.session_id,
                limit=limit,
            )
            results.extend(episodic)

        if not criteria.types or MemoryType.EXPERIENCE in criteria.types:
            if criteria.task_id:
                experience = await self.store.experience.get_by_task(criteria.task_id)
                results.extend(experience)

        if not criteria.types or MemoryType.PREFERENCE in criteria.types:
            if criteria.session_id:
                prefs = await self.store.preference.get_all(criteria.session_id)
                results.extend(self._prefs_to_items(prefs))

        if not criteria.types or MemoryType.PROCEDURAL in criteria.types:
            procedures = await self.store.procedural.match(criteria.keywords)
            results.extend(procedures)

        # 过滤
        results = self._filter(results, criteria)

        # 排序
        results = self._rank(results)

        return results[:limit]

    async def recall_for_task(
        self,
        task_description: str,
        task_type: str,
        session_id: str,
    ) -> Dict[MemoryType, List[MemoryItem]]:
        """
        为任务召回相关记忆
        返回类型分组的结果
        """
        recalled: Dict[MemoryType, List[MemoryItem]] = {
            MemoryType.EPISODIC: [],
            MemoryType.EXPERIENCE: [],
            MemoryType.PREFERENCE: [],
            MemoryType.PROCEDURAL: [],
        }

        # 1. 情景记忆 - 语义召回
        episodic = await self.store.episodic.search(
            query=task_description,
            session_id=session_id,
            limit=5,
        )
        recalled[MemoryType.EPISODIC] = episodic

        # 2. 经验记忆 - 相似任务召回
        experiences = await self.store.experience.recall_similar(
            task_type=task_type,
            limit=5,
        )
        recalled[MemoryType.EXPERIENCE] = experiences

        # 3. 偏好记忆 - 获取用户偏好
        prefs = await self.store.preference.get_all(session_id)
        recalled[MemoryType.PREFERENCE] = self._prefs_to_items(prefs)

        # 4. 程序记忆 - 匹配适用模式
        procedures = await self.store.procedural.match(
            context={"task_description": task_description, "task_type": task_type}
        )
        recalled[MemoryType.PROCEDURAL] = procedures

        return recalled

    def _filter(
        self,
        items: List[MemoryItem],
        criteria: MemoryQueryCriteria,
    ) -> List[MemoryItem]:
        """多条件过滤"""
        result = items

        if criteria.importance_min > 0:
            result = [i for i in result if i.importance >= criteria.importance_min]

        if criteria.time_range:
            start, end = criteria.time_range
            result = [i for i in result if start <= i.created_at <= end]

        if criteria.keywords:
            result = [
                i for i in result
                if any(kw.lower() in i.content.lower() for kw in criteria.keywords)
            ]

        return result

    def _rank(self, items: List[MemoryItem]) -> List[MemoryItem]:
        """多维度评分排序"""
        scored = []
        for item in items:
            score = (
                item.importance * 0.5 +
                self._recency_score(item) * 0.3 +
                self._keyword_match_score(item) * 0.2
            )
            scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored]

    def _recency_score(self, item: MemoryItem) -> float:
        """时间衰减评分"""
        hours_old = (datetime.now() - item.created_at).total_seconds() / 3600
        return 1.0 / (1.0 + hours_old * 0.05)

    def _keyword_match_score(self, item: MemoryItem) -> float:
        if not item.keywords:
            return 0.5
        return 0.5  # 简化

    def _prefs_to_items(self, prefs: Dict[str, str]) -> List[MemoryItem]:
        """偏好字典转换为 MemoryItem 列表"""
        return [
            MemoryItem(
                id=f"pref_{k}",
                type=MemoryType.PREFERENCE,
                content=f"{k}: {v}",
                metadata={"key": k, "value": v},
            )
            for k, v in prefs.items()
        ]
```

---

## 5. 智能保留（LLM Judger）

```python
@dataclass
class JudgerConfig:
    """判断器配置"""
    model: str = "claude-sonnet-4-20250514"
    importance_threshold: float = 0.6  # 重要性 >= 此值才持久化


class LLMJudger:
    """
    LLM 判断器 - 决定记忆是否值得持久化

    工作流程：
    1. 接收候选记忆内容
    2. 构建判断 Prompt
    3. 调用 LLM 判断重要性和保留层级
    4. 返回决策结果
    """

    SYSTEM_PROMPT = """You are a memory importance evaluator for an AI coding assistant.

Given a memory entry, evaluate:
1. Whether it should be persisted for long-term recall (yes/no)
2. Its importance score (0.0-1.0)
3. Memory type: episodic (experience), preference, or procedural (skill)

Consider:
- Episodic: key decisions, error recoveries, successful strategies
- Preference: user habits, coding style, tool preferences
- Procedural: reusable patterns, tool combinations, execution strategies

Respond in JSON format:
{
    "should_persist": true/false,
    "importance": 0.0-1.0,
    "memory_type": "episodic/preference/procedural",
    "keywords": ["keyword1", "keyword2"],
    "summary": "brief one-sentence summary"
}"""

    USER_PROMPT_TEMPLATE = """
Session ID: {session_id}
Memory Content: {content}

Evaluate this memory entry.
"""

    def __init__(self, config: JudgerConfig, model_client: ModelClient):
        self.config = config
        self.model_client = model_client

    async def should_persist(
        self,
        content: str,
        context: Dict[str, str],
    ) -> Tuple[bool, float, MemoryType, List[str], str]:
        """
        判断是否值得持久化

        Returns:
            (should_persist, importance, memory_type, keywords, summary)
        """
        user_prompt = self.USER_PROMPT_TEMPLATE.format(
            session_id=context.get("session_id", "unknown"),
            content=content,
        )

        response = await self.model_client.complete(
            system=self.SYSTEM_PROMPT,
            user=user_prompt,
            json_mode=True,
        )

        result = json.loads(response.content)

        should_persist = result.get("should_persist", False)
        importance = result.get("importance", 0.5)
        memory_type = MemoryType(result.get("memory_type", "episodic"))
        keywords = result.get("keywords", [])
        summary = result.get("summary", content[:100])

        return should_persist, importance, memory_type, keywords, summary

    async def evaluate_batch(
        self,
        items: List[MemoryItem],
    ) -> List[Tuple[MemoryItem, Tuple[bool, float, MemoryType, List[str], str]]]:
        """
        批量评估记忆条目

        用于：
        1. 会话结束时的批量评估
        2. 定期清理前的价值重评
        """
        results = []
        for item in items:
            decision = await self.should_persist(
                content=item.content,
                context={"session_id": item.session_id or ""},
            )
            results.append((item, decision))
        return results
```

---

## 6. MemoryManager Facade

```python
@dataclass
class MemoryConfig:
    """Memory 模块配置"""
    episodic: EpisodicConfig = field(default_factory=EpisodicConfig)
    preference: PreferenceConfig = field(default_factory=PreferenceConfig)
    experience: ExperienceConfig = field(default_factory=ExperienceConfig)
    procedural: ProceduralConfig = field(default_factory=ProceduralConfig)
    judger: JudgerConfig = field(default_factory=JudgerConfig)


class MemoryManager:
    """
    Memory 模块 Facade

    提供统一的记忆管理接口，封装四类记忆的存储和检索。
    Context 模块通过此接口与 Memory 交互。
    """

    def __init__(self, config: MemoryConfig):
        self.config = config
        self.store = MemoryStore(config)
        self.query = MemoryQuery(self.store)
        self.judger = LLMJudger(config.judger)

    # === 写入接口 ===

    async def record(
        self,
        content: str,
        memory_type: MemoryType,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryItem:
        """记录一条记忆（自动判断是否持久化）"""
        item = MemoryItem(
            id=str(uuid.uuid4()),
            type=memory_type,
            content=content,
            session_id=session_id,
            task_id=task_id,
            metadata=metadata or {},
        )

        should_persist, importance, inferred_type, keywords, summary = (
            await self.judger.should_persist(
                content=content,
                context={"session_id": session_id or ""},
            )
        )

        item.importance = importance
        item.keywords = keywords

        if should_persist:
            await self._persist(item, inferred_type)

        return item

    async def record_task_outcome(
        self,
        session_id: str,
        task_id: str,
        task_type: str,
        success: bool,
        content: str,
        tools_used: List[str],
        strategy: str,
        duration: int,
    ) -> ExperienceItem:
        """记录任务执行结果（直接持久化到 Experience）"""
        item = ExperienceItem(
            id=str(uuid.uuid4()),
            type=MemoryType.EXPERIENCE,
            content=content,
            session_id=session_id,
            task_id=task_id,
            metadata={
                "task_type": task_type,
                "success": success,
                "tools_used": tools_used,
                "strategy": strategy,
                "duration_seconds": duration,
            },
            importance=0.8 if success else 0.6,
        )
        await self.store.experience.add(item)
        return item

    async def learn_preference(
        self,
        session_id: str,
        key: str,
        value: str,
    ) -> None:
        """学习用户偏好"""
        await self.store.preference.learn(session_id, {key: value})

    # === 读取接口 ===

    async def recall(
        self,
        task_description: str,
        task_type: str,
        session_id: str,
    ) -> Dict[MemoryType, List[MemoryItem]]:
        """为任务召回相关记忆"""
        return await self.query.recall_for_task(
            task_description=task_description,
            task_type=task_type,
            session_id=session_id,
        )

    async def search(
        self,
        query: str,
        memory_types: Optional[List[MemoryType]] = None,
        session_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[MemoryItem]:
        """搜索记忆"""
        criteria = MemoryQueryCriteria(
            types=memory_types or [],
            session_id=session_id,
            keywords=query.split(),
        )
        return await self.query.retrieve(criteria, limit=limit)

    async def get_preferences(self, session_id: str) -> Dict[str, str]:
        """获取用户所有偏好"""
        return await self.store.preference.get_all(session_id)

    async def get_experiences(
        self,
        task_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[ExperienceItem]:
        """获取历史经验"""
        if task_type:
            return await self.store.experience.recall_similar(task_type, limit)
        return await self.store.experience.get_recent(limit)

    # === 内部方法 ===

    async def _persist(self, item: MemoryItem, inferred_type: MemoryType) -> None:
        """根据推断类型路由到对应存储"""
        match inferred_type:
            case MemoryType.EPISODIC:
                await self.store.episodic.add(item)
            case MemoryType.PREFERENCE:
                if item.metadata.get("key"):
                    await self.store.preference.insert(
                        item.session_id,
                        item.metadata["key"],
                        item.metadata.get("value", item.content),
                    )
            case MemoryType.PROCEDURAL:
                await self.store.procedural.add(item)
            case _:
                await self.store.episodic.add(item)
```

---

## 7. 模块结构

```
mozi/storage/memory/
├── __init__.py
├── types.py              # MemoryType, MemoryItem, PreferenceItem, ExperienceItem, ProceduralItem
├── config.py             # MemoryConfig, EpisodicConfig, PreferenceConfig, ExperienceConfig, ProceduralConfig, JudgerConfig
├── store/
│   ├── __init__.py
│   ├── base.py           # BaseStore 抽象基类
│   ├── episodic.py       # EpisodicStore
│   ├── preference.py     # PreferenceStore
│   ├── experience.py     # ExperienceStore
│   └── procedural.py     # ProceduralStore
├── query.py              # MemoryQuery, MemoryQueryCriteria
├── judger.py             # LLMJudger
└── manager.py            # MemoryManager (Facade)
```

**依赖关系**：
```
MemoryManager
    ├── MemoryStore (Facade for stores)
    │   ├── EpisodicStore (SQLite + Qdrant)
    │   ├── PreferenceStore (SQLite)
    │   ├── ExperienceStore (SQLite)
    │   └── ProceduralStore (SQLite)
    ├── MemoryQuery
    └── LLMJudger
```

---

## 8. 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-03-29 | 初始版本，四层记忆架构设计 |
