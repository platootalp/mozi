# Context Module Redesign Design

## 1. 概述

### 1.1 模块定位

Context 模块负责**上下文全生命周期管理**，包括：编码、存储、检索、整合、遗忘。

### 1.2 核心职责

| 职责 | 说明 |
|------|------|
| 编码 (Encode) | 将所有上下文数据统一为 ContextItem 数据模型 |
| 存储 (Store) | 三层存储：Working / Short-term / Long-term |
| 检索 (Retrieve) | 按条件查询 + 语义召回 |
| 整合 (Assemble) | 将多源上下文组装为 PromptContext |
| 遗忘 (Forget) | LRU 淘汰、TTL 删除、重要性过滤、压缩摘要 |

### 1.3 与其他模块的边界

| 模块 | 边界 |
|------|------|
| Session | Session 只负责会话生命周期（创建/暂停/恢复/结束）；Context 负责上下文内容管理 |
| Memory | Memory 是 Context 的子模块，负责三层记忆存储；Context 定义数据模型和检索策略 |
| Orchestrator | Orchestrator 调用 Context.assemble() 获取 PromptContext，不直接操作存储 |

---

## 2. 统一数据模型：ContextItem

### 2.1 数据结构

```python
@dataclass
class ContextItem:
    """上下文统一数据模型"""

    id: str                          # 唯一标识 (UUID)
    type: ContextType                 # 条目类型
    role: str                        # user / assistant / system / tool

    # 核心内容
    content: str                     # 原始内容

    # 元信息
    created_at: datetime
    session_id: str
    task_id: Optional[str] = None

    # 存储控制
    storage_tier: StorageTier = StorageTier.WORKING
    importance: float = 0.5          # 重要程度 0.0-1.0
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)

    # 检索用
    embedding: Optional[List[float]] = None
    keywords: List[str] = field(default_factory=list)

    # 压缩用
    summary: Optional[str] = None    # 摘要（压缩后生成）
    is_compacted: bool = False
```

### 2.2 ContextType 枚举

```python
class ContextType(Enum):
    """上下文条目类型"""
    MESSAGE = "message"              # 对话消息
    TOOL_REQUEST = "tool_request"   # 工具调用请求
    TOOL_RESPONSE = "tool_response"  # 工具调用响应
    ARTIFACT = "artifact"           # 生成产物（代码、文档）
    MEMORY = "memory"               # 记忆条目
    FILE_SNAPSHOT = "file_snapshot" # 文件快照
    ERROR = "error"                 # 错误记录
    USER_PREFERENCE = "user_preference"  # 用户偏好
    EXPERIENCE = "experience"        # 经验记录
```

### 2.3 Experience 类型

```python
@dataclass
class Experience:
    """经验记录"""
    id: Optional[int] = None
    session_id: str
    task_type: str
    success: bool
    summary: str
    details: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
```

### 2.4 Artifact 类型

```python
@dataclass
class Artifact:
    """生成产物"""
    id: str
    type: ArtifactType  # CODE, DOCUMENT, CONFIG, etc.
    content: str
    file_path: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


class ArtifactType(Enum):
    CODE = "code"
    DOCUMENT = "document"
    CONFIG = "config"
    TEST = "test"
    OTHER = "other"
```

### 2.5 StorageTier 枚举

```python
class StorageTier(Enum):
    """存储层级"""
    WORKING = "working"      # 会话内存（LRU，容量有限）
    SHORT_TERM = "short_term" # 项目级（TTL 180天，向量检索）
    LONG_TERM = "long_term"   # 用户级（永久，跨项目）
```

---

## 3. 存储层：ContextStore

### 3.1 架构

```
ContextStore
├── WorkingStore    # 会话内存，LRU 淘汰
├── ShortTermStore  # 项目级，SQLite + Qdrant
└── LongTermStore   # 用户级，SQLite
```

### 3.2 WorkingStore

```python
class WorkingStore:
    """Working Memory - 会话内存

    - 容量: 可配置 max_items（默认 1000 条）
    - 淘汰策略: LRU（最近最少使用）
    - 持久化: 否（进程内存）
    """

    def __init__(self, config: WorkingConfig):
        self.max_items = config.max_items
        self._cache: OrderedDict[str, ContextItem] = OrderedDict()

    async def add(self, item: ContextItem) -> None:
        """添加条目，超限时淘汰最旧条目"""
        item.storage_tier = StorageTier.WORKING
        self._cache[item.id] = item
        self._evict_if_needed()

    def _evict_if_needed(self) -> None:
        """LRU 淘汰超出容量的条目"""
        while len(self._cache) > self.max_items:
            self._cache.popitem(last=False)

    async def get(self, item_id: str) -> Optional[ContextItem]:
        """获取条目并更新访问记录"""
        item = self._cache.get(item_id)
        if item:
            item.access_count += 1
            item.last_accessed = datetime.now()
        return item

    async def query(
        self,
        session_id: str,
        types: Optional[List[ContextType]] = None,
        limit: int = 100,
    ) -> List[ContextItem]:
        """查询会话的上下文条目（按时间倒序，返回最近的 limit 条）"""
        items = [item for item in self._cache.values()
                 if item.session_id == session_id]
        if types:
            items = [i for i in items if i.type in types]
        # 按 created_at 倒序，取最近的 limit 条
        items.sort(key=lambda x: x.created_at, reverse=True)
        return items[:limit]

    async def evict_lru(self, count: int) -> None:
        """LRU 驱逐：移除最旧的 count 个条目"""
        for _ in range(min(count, len(self._cache))):
            self._cache.popitem(last=False)

    async def count(self, session_id: str) -> int:
        return sum(1 for item in self._cache.values()
                    if item.session_id == session_id)
```

### 3.3 ShortTermStore

```python
class ShortTermStore:
    """Short-term Memory - 项目级持久化

    - 容量: 无限
    - TTL: 180 天
    - 检索: 向量搜索 + 关键词混合
    """

    def __init__(self, config: ShortTermConfig):
        self.db_path = config.db_path
        self.vector_store = QdrantStore(config.qdrant)
        self._init_db()

    def _init_db(self) -> None:
        """初始化 SQLite 表"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS context_items (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                session_id TEXT NOT NULL,
                task_id TEXT,
                importance REAL DEFAULT 0.5,
                keywords TEXT,  -- JSON array
                summary TEXT,
                is_compacted INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_created
            ON context_items(session_id, created_at)
        """)
        conn.commit()
        conn.close()

    async def add(self, item: ContextItem) -> None:
        """添加条目：SQLite + 向量数据库"""
        item.storage_tier = StorageTier.SHORT_TERM

        # SQLite
        await self._sqlite_insert(item)

        # 向量
        if item.embedding:
            await self.vector_store.upsert(
                id=item.id,
                vector=item.embedding,
                payload={"content": item.content, "session_id": item.session_id},
            )

    async def query(
        self,
        session_id: str,
        types: Optional[List[ContextType]] = None,
        limit: int = 100,
    ) -> List[ContextItem]:
        """按 session_id 和类型查询条目"""
        conn = sqlite3.connect(self.db_path)

        type_filter = ""
        params: List[Any] = [session_id]
        if types:
            type_placeholders = ",".join("?" * len(types))
            type_filter = f"AND type IN ({type_placeholders})"
            params.extend([t.value for t in types])

        cursor = conn.execute(
            f"""
            SELECT * FROM context_items
            WHERE session_id = ? {type_filter}
            ORDER BY created_at DESC
            LIMIT ?
            """,
            params + [limit],
        )
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_item(row) for row in rows]

    async def delete(self, item_id: str) -> None:
        """删除条目"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_delete, item_id)

    def _sync_delete(self, item_id: str) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM context_items WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()

    async def _sqlite_insert(self, item: ContextItem) -> None:
        """同步插入 SQLite（线程执行）"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_insert, item)

    def _sync_insert(self, item: ContextItem) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            INSERT INTO context_items (id, type, role, content, session_id, task_id, importance, keywords, summary, is_compacted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.id,
                item.type.value,
                item.role,
                item.content,
                item.session_id,
                item.task_id,
                item.importance,
                json.dumps(item.keywords),
                item.summary,
                1 if item.is_compacted else 0,
            ),
        )
        conn.commit()
        conn.close()

    def _row_to_item(self, row: tuple) -> ContextItem:
        return ContextItem(
            id=row[0],
            type=ContextType(row[1]),
            role=row[2],
            content=row[3],
            session_id=row[4],
            task_id=row[5],
            importance=row[6],
            keywords=json.loads(row[7]) if row[7] else [],
            summary=row[8],
            is_compacted=bool(row[9]),
            created_at=datetime.fromisoformat(row[10]),
            last_accessed=datetime.fromisoformat(row[11]) if row[11] else datetime.now(),
        )

    async def _keyword_search(
        self,
        query: str,
        session_id: str,
        limit: int,
    ) -> List[ContextItem]:
        """关键词搜索"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._sync_keyword_search, query, session_id, limit
        )

    def _sync_keyword_search(
        self,
        query: str,
        session_id: str,
        limit: int,
    ) -> List[ContextItem]:
        keywords = query.lower().split()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            """
            SELECT * FROM context_items
            WHERE session_id = ? AND is_compacted = 0
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (session_id, limit * 2),
        )
        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            content_lower = row[3].lower()
            if any(kw in content_lower for kw in keywords):
                results.append(self._row_to_item(row))
            if len(results) >= limit:
                break

        return results

    async def search(
        self,
        query: str,
        session_id: str,
        limit: int = 10,
    ) -> List[ContextItem]:
        """语义搜索 + 关键词混合检索"""
        # 向量搜索
        vector_results = await self.vector_store.search(
            query=query,
            namespace=session_id,
            limit=limit,
        )

        # 关键词搜索
        keyword_results = await self._keyword_search(query, session_id, limit)

        # 合并去重
        seen = set()
        merged = []
        for item in vector_results + keyword_results:
            if item.id not in seen:
                seen.add(item.id)
                merged.append(item)

        return merged[:limit]

    async def get_expired(self, ttl_days: int = 180) -> List[str]:
        """获取过期条目 ID"""
        cutoff = datetime.now() - timedelta(days=ttl_days)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT id FROM context_items WHERE created_at < ?",
            (cutoff.isoformat(),)
        )
        ids = [row[0] for row in cursor]
        conn.close()
        return ids
```

### 3.4 LongTermStore

```python
class LongTermStore:
    """Long-term Memory - 用户级持久化

    - 用途: 用户偏好、跨项目经验
    - 容量: 无限
    - TTL: 永久
    """

    def __init__(self, config: LongTermConfig):
        self.db_path = config.db_path
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS experiences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                task_type TEXT,
                success BOOLEAN,
                summary TEXT,
                details TEXT,  -- JSON
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS context_items_long (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                session_id TEXT,
                task_id TEXT,
                importance REAL DEFAULT 0.5,
                keywords TEXT,
                summary TEXT,
                is_compacted INTEGER DEFAULT 0,
                access_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    async def add_preference(self, key: str, value: str) -> None:
        ...

    async def get_preference(self, key: str) -> Optional[str]:
        ...

    async def add_experience(self, experience: Experience) -> None:
        ...

    async def get_experiences(
        self,
        task_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Experience]:
        ...

    async def add_context_item(self, item: ContextItem) -> None:
        """添加上下文条目到 Long-term"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_insert_item, item)

    def _sync_insert_item(self, item: ContextItem) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            INSERT OR REPLACE INTO context_items_long
            (id, type, role, content, session_id, task_id, importance, keywords, summary, is_compacted, access_count, last_accessed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.id, item.type.value, item.role, item.content,
                item.session_id, item.task_id, item.importance,
                json.dumps(item.keywords), item.summary,
                1 if item.is_compacted else 0,
                item.access_count,
                item.last_accessed.isoformat(),
            ),
        )
        conn.commit()
        conn.close()

    async def get_low_importance(
        self,
        threshold: float,
    ) -> List[ContextItem]:
        """获取低重要性条目"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._sync_get_low_importance, threshold
        )

    def _sync_get_low_importance(self, threshold: float) -> List[ContextItem]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT * FROM context_items_long WHERE importance < ? LIMIT 100",
            (threshold,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_item(row) for row in rows]

    def _row_to_item(self, row: tuple) -> ContextItem:
        return ContextItem(
            id=row[0],
            type=ContextType(row[1]),
            role=row[2],
            content=row[3],
            session_id=row[4],
            task_id=row[5],
            importance=row[6],
            keywords=json.loads(row[7]) if row[7] else [],
            summary=row[8],
            is_compacted=bool(row[9]),
            access_count=row[10],
            last_accessed=datetime.fromisoformat(row[11]) if row[11] else datetime.now(),
            created_at=datetime.fromisoformat(row[12]) if row[12] else datetime.now(),
        )

    async def archive(self, item_id: str) -> None:
        """归档条目（标记为低重要性或删除）"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_archive, item_id)

    def _sync_archive(self, item_id: str) -> None:
        # 归档：降低重要性或移动到归档表
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE context_items_long SET importance = 0.1 WHERE id = ?",
            (item_id,),
        )
        conn.commit()
        conn.close()
```

### 3.5 ContextStore Facade

```python
class ContextStore:
    """上下文存储 Facade"""

    def __init__(self, config: ContextConfig):
        self.working = WorkingStore(config.working)
        self.short_term = ShortTermStore(config.short_term)
        self.long_term = LongTermStore(config.long_term)

    async def put(self, item: ContextItem) -> None:
        """存储上下文条目（自动路由到对应层级）"""
        match item.storage_tier:
            case StorageTier.WORKING:
                await self.working.add(item)
            case StorageTier.SHORT_TERM:
                await self.short_term.add(item)
            case StorageTier.LONG_TERM:
                await self.long_term.add(item)

    async def get(
        self,
        item_id: str,
        tier: StorageTier,
    ) -> Optional[ContextItem]:
        store = self._store_for(tier)
        return await store.get(item_id)

    async def query(
        self,
        session_id: str,
        tier: StorageTier,
        types: Optional[List[ContextType]] = None,
        limit: int = 100,
    ) -> List[ContextItem]:
        store = self._store_for(tier)
        return await store.query(session_id, types, limit)

    def _store_for(self, tier: StorageTier):
        return {StorageTier.WORKING: self.working,
                StorageTier.SHORT_TERM: self.short_term,
                StorageTier.LONG_TERM: self.long_term}[tier]
```

---

## 4. 检索层：ContextQuery

### 4.1 QueryCriteria

```python
@dataclass
class QueryCriteria:
    """查询条件"""
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    types: List[ContextType] = field(default_factory=list)
    time_range: Optional[Tuple[datetime, datetime]] = None
    importance_min: float = 0.0
    keywords: List[str] = field(default_factory=list)
    embedding_query: Optional[str] = None
```

### 4.2 ContextQuery

```python
class ContextQuery:
    """上下文检索引擎"""

    def __init__(self, store: ContextStore):
        self.store = store

    async def retrieve(
        self,
        criteria: QueryCriteria,
        tier: StorageTier = StorageTier.WORKING,
    ) -> List[ContextItem]:
        """
        检索上下文条目
        1. 根据条件过滤
        2. 多维度评分排序
        3. 返回结果
        """
        items = await self.store.query(
            session_id=criteria.session_id,
            tier=tier,
            types=criteria.types,
            limit=500,
        )

        items = self._filter(items, criteria)
        items = self._rank(items, criteria)

        return items

    async def recall(
        self,
        task_description: str,
        session_id: str,
    ) -> List[ContextItem]:
        """
        任务相关的上下文召回
        1. 语义搜索短时记忆
        2. 查找相关长期经验
        3. 合并去重返回
        """
        # 短时记忆语义召回
        short_term = await self.store.short_term.search(
            query=task_description,
            session_id=session_id,
            limit=10,
        )

        # 长期经验召回
        experiences = await self.store.long_term.get_experiences(limit=5)
        experience_items = [self._experience_to_item(e) for e in experiences]

        # 合并
        seen = set()
        merged = []
        for item in short_term + experience_items:
            if item.id not in seen:
                seen.add(item.id)
                merged.append(item)

        return merged

    def _experience_to_item(self, experience: Experience) -> ContextItem:
        """将 Experience 转换为 ContextItem"""
        return ContextItem(
            id=f"exp_{experience.id}",
            type=ContextType.EXPERIENCE,
            role="system",
            content=f"[Experience] {experience.task_type}: {experience.summary}",
            session_id=experience.session_id,
            created_at=experience.created_at,
            importance=0.8 if experience.success else 0.4,
        )

    def _filter(
        self,
        items: List[ContextItem],
        criteria: QueryCriteria,
    ) -> List[ContextItem]:
        """多条件过滤"""
        result = items

        if criteria.types:
            result = [i for i in result if i.type in criteria.types]

        if criteria.importance_min > 0:
            result = [i for i in result
                      if i.importance >= criteria.importance_min]

        if criteria.time_range:
            start, end = criteria.time_range
            result = [i for i in result
                      if start <= i.created_at <= end]

        if criteria.keywords:
            result = [
                i for i in result
                if any(kw.lower() in i.content.lower() for kw in criteria.keywords)
            ]

        return result

    def _rank(
        self,
        items: List[ContextItem],
        criteria: QueryCriteria,
    ) -> List[ContextItem]:
        """多维度评分排序"""
        scored = []
        for item in items:
            score = (
                item.importance * 0.4 +
                item.access_count * 0.1 +
                self._recency_score(item) * 0.3 +
                self._keyword_match_score(item, criteria.keywords) * 0.2
            )
            scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored]

    def _recency_score(self, item: ContextItem) -> float:
        """时间衰减评分"""
        hours_old = (datetime.now() - item.last_accessed).total_seconds() / 3600
        return 1.0 / (1.0 + hours_old * 0.1)

    def _keyword_match_score(
        self,
        item: ContextItem,
        keywords: List[str],
    ) -> float:
        if not keywords:
            return 0.5
        matches = sum(1 for kw in keywords if kw in item.content)
        return matches / len(keywords) if keywords else 0.0
```

---

## 5. 整合层：ContextAssembler

### 5.1 AssemblyRequest & PromptContext

```python
@dataclass
class AssemblyRequest:
    """组装请求"""
    task: str
    session_id: str
    mode: AssemblyMode = AssemblyMode.FULL
    max_tokens: int = 150000


class AssemblyMode(Enum):
    FULL = "full"          # 完整上下文
    COMPACT = "compact"   # 压缩上下文
    MINIMAL = "minimal"   # 最小上下文（仅当前任务 + 关键记忆）


@dataclass
class PromptContext:
    """组装后的 Prompt 上下文"""
    system: str
    messages: List[Dict[str, str]]
    artifacts: List[Artifact] = field(default_factory=list)
    token_count: int = 0
    sources: List[str] = field(default_factory=list)
    context_items: List[ContextItem] = field(default_factory=list)

    def to_llm_messages(self) -> List[Dict[str, str]]:
        """转换为 LLM 消息格式"""
        result = [{"role": "system", "content": self.system}]
        result.extend(self.messages)
        return result
```

### 5.2 ContextAssembler

```python
class ContextAssembler:
    """上下文组装器"""

    SYSTEM_PROMPT_TEMPLATE = """You are Mozi, an AI coding assistant.

## Capabilities
- Read, edit, and analyze code
- Execute shell commands
- Search and navigate codebases
- Work with Git and version control

## Context Structure
- Working memory: recent session context
- Short-term memory: project-relevant history (RAG)
- Long-term memory: user preferences and patterns

## Guidelines
- Prefer explicit file operations over vague instructions
- Confirm destructive actions before execution
- Explain reasoning when relevant
"""

    def __init__(
        self,
        store: ContextStore,
        query: ContextQuery,
        config: ContextConfig,
    ):
        self.store = store
        self.query = query
        self.config = config

    async def assemble(
        self,
        request: AssemblyRequest,
    ) -> PromptContext:
        """
        组装完整上下文
        1. 获取工作记忆
        2. 召回相关记忆
        3. 获取用户偏好
        4. 计算 Token 预算
        5. 如需要，触发压缩
        6. 返回 PromptContext
        """
        sources = []
        context_items: List[ContextItem] = []

        # 1. 系统 Prompt
        system = self._build_system_prompt()

        # 2. 获取工作记忆
        working_items = await self.query.retrieve(
            criteria=QueryCriteria(session_id=request.session_id),
            tier=StorageTier.WORKING,
        )
        sources.append(f"working:{len(working_items)}")
        context_items.extend(working_items)

        # 3. 召回相关记忆（仅 FULL 模式）
        recalled: List[ContextItem] = []
        if request.mode == AssemblyMode.FULL:
            recalled = await self.query.recall(
                task_description=request.task,
                session_id=request.session_id,
            )
            sources.append(f"recalled:{len(recalled)}")
            context_items.extend(recalled)

        # 4. 获取用户偏好
        preferences = await self._get_preferences(request.session_id)
        sources.append(f"preferences:{len(preferences)}")

        # 5. 构建消息列表
        messages = self._build_messages(working_items, recalled, preferences)
        messages.append({"role": "user", "content": request.task})

        # 6. Token 预算检查
        token_count = self._count_tokens(system, messages)

        if token_count > request.max_tokens:
            messages, token_count = await self._compact(
                messages, request.max_tokens
            )
            sources.append("compacted")

        return PromptContext(
            system=system,
            messages=messages,
            artifacts=self._extract_artifacts(context_items),
            token_count=token_count,
            sources=sources,
            context_items=context_items,
        )

    def _build_system_prompt(self) -> str:
        return self.SYSTEM_PROMPT_TEMPLATE

    def _build_messages(
        self,
        working: List[ContextItem],
        recalled: List[ContextItem],
        preferences: Dict[str, str],
    ) -> List[Dict[str, str]]:
        messages = []

        # 工作记忆
        for item in working:
            if item.type == ContextType.MESSAGE:
                messages.append({
                    "role": item.role,
                    "content": item.content,
                })

        # 召回记忆（作为 system 上下文）
        if recalled:
            recalled_content = "\n".join(
                f"- {item.content}" for item in recalled[:5]
            )
            messages.append({
                "role": "system",
                "content": f"## Relevant History\n{recalled_content}"
            })

        # 用户偏好
        if preferences:
            pref_content = "\n".join(
                f"- {k}: {v}" for k, v in preferences.items()
            )
            messages.append({
                "role": "system",
                "content": f"## User Preferences\n{pref_content}"
            })

        return messages

    async def _compact(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
    ) -> Tuple[List[Dict[str, str]], int]:
        """压缩消息到目标 Token 数量"""
        # 1. 保留 system prompt 和最近的消息
        # 2. 对中间消息生成摘要
        # 3. 迭代直到满足预算

        while self._count_tokens_messages(messages) > max_tokens:
            if len(messages) <= 3:
                break

            # 压缩中间消息
            middle_start = 1  # 跳过 system
            middle_end = len(messages) - 5  # 保留最近 5 条

            if middle_end <= middle_start:
                break

            middle_messages = messages[middle_start:middle_end]
            summary = await self._summarize(middle_messages)

            # 替换为摘要
            messages = (
                messages[:middle_start] +
                [{"role": "system", "content": f"## Earlier Context Summary\n{summary}"}] +
                messages[middle_end:]
            )

        return messages, self._count_tokens_messages(messages)

    async def _summarize(
        self,
        messages: List[Dict[str, str]],
    ) -> str:
        """生成消息摘要"""
        content = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        # 调用 LLM 生成摘要（此处简化）
        return f"[Summary of {len(messages)} earlier messages]"

    def _count_tokens(self, system: str, messages: List[Dict[str, str]]) -> int:
        return len(system) // 4 + sum(
            len(m["content"]) // 4 for m in messages
        )

    def _count_tokens_messages(self, messages: List[Dict[str, str]]) -> int:
        return sum(len(m["content"]) // 4 for m in messages)

    async def _get_preferences(
        self,
        session_id: str,
    ) -> Dict[str, str]:
        """获取用户偏好"""
        prefs = await self.store.long_term.get_preference(f"{session_id}:*")
        return prefs or {}

    def _extract_artifacts(
        self,
        items: List[ContextItem],
    ) -> List[Artifact]:
        """从上下文条目中提取产物"""
        artifacts = []
        for item in items:
            if item.type == ContextType.ARTIFACT:
                artifacts.append(Artifact(
                    id=item.id,
                    type=ArtifactType.CODE,  # 默认类型
                    content=item.content,
                ))
        return artifacts
```

---

## 6. 遗忘层：ContextPolicy

### 6.1 ForgettingPolicy

```python
@dataclass
class ForgettingPolicy:
    """遗忘策略配置"""
    working_max_items: int = 1000
    working_max_tokens: int = 100000
    short_term_ttl_days: int = 180
    long_term_importance_threshold: float = 0.3
    compact_trigger_ratio: float = 0.9
    archive_low_importance: bool = True


@dataclass
class ForgetAction:
    """遗忘动作"""
    type: ForgetType
    tier: StorageTier
    count: int = 0
    items: List[str] = field(default_factory=list)


class ForgetType(Enum):
    EVICT = "evict"     # LRU 驱逐
    DELETE = "delete"   # TTL 删除
    ARCHIVE = "archive" # 降级归档
    COMPACT = "compact"  # 压缩摘要
```

### 6.2 ContextPolicy

```python
class ContextPolicy:
    """遗忘策略执行器"""

    def __init__(
        self,
        store: ContextStore,
        config: ForgettingPolicy,
    ):
        self.store = store
        self.config = config

    async def evaluate(self, session_id: str) -> List[ForgetAction]:
        """
        评估需要执行的遗忘动作
        """
        actions = []

        # 1. Working Memory 超限
        working_count = await self.store.working.count(session_id)
        if working_count > self.config.working_max_items:
            actions.append(ForgetAction(
                type=ForgetType.EVICT,
                tier=StorageTier.WORKING,
                count=working_count - self.config.working_max_items,
            ))

        # 2. Short-term Memory TTL 过期
        expired_ids = await self.store.short_term.get_expired(
            ttl_days=self.config.short_term_ttl_days
        )
        if expired_ids:
            actions.append(ForgetAction(
                type=ForgetType.DELETE,
                tier=StorageTier.SHORT_TERM,
                items=expired_ids,
            ))

        # 3. 低重要性 Long-term 条目（归档）
        if self.config.archive_low_importance:
            low_importance = await self.store.long_term.get_low_importance(
                threshold=self.config.long_term_importance_threshold
            )
            if low_importance:
                actions.append(ForgetAction(
                    type=ForgetType.ARCHIVE,
                    tier=StorageTier.LONG_TERM,
                    items=[item.id for item in low_importance],
                ))

        return actions

    async def execute(self, actions: List[ForgetAction]) -> None:
        """
        执行遗忘动作
        """
        for action in actions:
            match action.type:
                case ForgetType.EVICT:
                    await self.store.working.evict_lru(action.count)
                case ForgetType.DELETE:
                    for item_id in action.items:
                        await self.store.short_term.delete(item_id)
                case ForgetType.ARCHIVE:
                    for item_id in action.items:
                        await self.store.long_term.archive(item_id)
                case ForgetType.COMPACT:
                    # 触发 ContextAssembler 压缩
                    pass
```

---

## 7. Facade：ContextManager

```python
class ContextManager:
    """
    Context 模块 Facade
    提供统一的上下文管理接口
    """

    def __init__(self, config: ContextConfig):
        self.config = config
        self.store = ContextStore(config)
        self.query = ContextQuery(self.store)
        self.assembler = ContextAssembler(self.store, self.query, config)
        self.policy = ContextPolicy(self.store, config.forgetting)

    # === 存储 ===

    async def add(
        self,
        content: str,
        role: str,
        item_type: ContextType,
        session_id: str,
        task_id: Optional[str] = None,
        importance: float = 0.5,
        tier: StorageTier = StorageTier.WORKING,
    ) -> ContextItem:
        """添加上下文条目"""
        item = ContextItem(
            id=str(uuid.uuid4()),
            type=item_type,
            role=role,
            content=content,
            created_at=datetime.now(),
            session_id=session_id,
            task_id=task_id,
            importance=importance,
            storage_tier=tier,
        )
        await self.store.put(item)
        return item

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        task_id: Optional[str] = None,
    ) -> ContextItem:
        """添加消息"""
        return await self.add(
            content=content,
            role=role,
            item_type=ContextType.MESSAGE,
            session_id=session_id,
            task_id=task_id,
            importance=0.7 if role == "assistant" else 0.5,
        )

    async def add_tool_result(
        self,
        session_id: str,
        tool_name: str,
        result: str,
        task_id: Optional[str] = None,
    ) -> ContextItem:
        """添加工具调用结果"""
        return await self.add(
            content=f"Tool '{tool_name}' result: {result}",
            role="tool",
            item_type=ContextType.TOOL_RESPONSE,
            session_id=session_id,
            task_id=task_id,
            importance=0.6,
        )

    # === 检索 ===

    async def get_history(
        self,
        session_id: str,
        limit: int = 50,
    ) -> List[ContextItem]:
        """获取会话历史"""
        return await self.query.retrieve(
            criteria=QueryCriteria(session_id=session_id),
            tier=StorageTier.WORKING,
        )

    async def recall(
        self,
        task: str,
        session_id: str,
    ) -> List[ContextItem]:
        """召回相关上下文"""
        return await self.query.recall(
            task_description=task,
            session_id=session_id,
        )

    # === 整合 ===

    async def assemble_prompt(
        self,
        task: str,
        session_id: str,
        mode: AssemblyMode = AssemblyMode.FULL,
    ) -> PromptContext:
        """组装 Prompt 上下文"""
        return await self.assembler.assemble(
            AssemblyRequest(
                task=task,
                session_id=session_id,
                mode=mode,
                max_tokens=self.config.max_tokens,
            )
        )

    # === 遗忘 ===

    async def enforce_policy(self, session_id: str) -> None:
        """执行遗忘策略"""
        actions = await self.policy.evaluate(session_id)
        await self.policy.execute(actions)
```

---

## 8. 模块结构

```
mozi/storage/context/
├── __init__.py
├── types.py              # ContextItem, ContextType, StorageTier, etc.
├── config.py             # ContextConfig, ForgettingPolicy, WorkingConfig, etc.
├── store/
│   ├── __init__.py
│   ├── base.py           # BaseStore interface
│   ├── working.py        # WorkingStore (内存 LRU)
│   ├── short_term.py     # ShortTermStore (SQLite + Qdrant)
│   └── long_term.py      # LongTermStore (SQLite)
├── query.py              # ContextQuery
├── assembler.py          # ContextAssembler
├── policy.py             # ContextPolicy
└── manager.py            # ContextManager (Facade)
```

---

## 9. 配置

```python
@dataclass
class ContextConfig:
    """Context 模块配置"""
    max_tokens: int = 150000
    working: WorkingConfig = field(default_factory=WorkingConfig)
    short_term: ShortTermConfig = field(default_factory=ShortTermConfig)
    long_term: LongTermConfig = field(default_factory=LongTermConfig)
    forgetting: ForgettingPolicy = field(default_factory=ForgettingPolicy)


@dataclass
class WorkingConfig:
    max_items: int = 1000


@dataclass
class ShortTermConfig:
    db_path: str = "~/.mozi/short_term.db"
    qdrant_url: str = "http://localhost:6333"
    collection_name: str = "mozi_context"
    ttl_days: int = 180


@dataclass
class LongTermConfig:
    db_path: str = "~/.mozi/long_term.db"
```

---

## 10. 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.1 | 2026-03-29 | 修复审查问题：补全 ShortTermStore.query/delete 方法、补全 LongTermStore.get_low_importance/archive 方法、补全 WorkingStore.evict_lru 方法、添加 Experience/Artifact 类型定义、补全 LongTermStore schema 的 access_count/last_accessed 字段、修复 WorkingStore.query 返回顺序、补全 _filter 关键词过滤、添加 _experience_to_item 和 _extract_artifacts 辅助方法 |
| v1.0 | 2026-03-29 | 初始版本，重新设计 Context 模块 |
