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
    检索方式：模式匹配（关键词 + 语义）
    """

    def __init__(self, config: ProceduralConfig):
        self.db_path = config.db_path
        self._init_db()

    async def add(self, item: ProceduralItem) -> None:
        """添加程序记忆"""
        await self._sqlite_insert(item)

    async def add_tool_pattern(
        self,
        tool_name: str,
        pattern: str,
        applicability: str,
    ) -> None:
        """记录工具使用模式"""
        item = ProceduralItem(
            id=str(uuid.uuid4()),
            type=MemoryType.PROCEDURAL,
            content=pattern,
            metadata={
                "pattern_type": "tool_usage",
                "tool_name": tool_name,
                "applicability": applicability,
                "usage_count": 0,
            }
        )
        await self.add(item)

    async def add_execution_strategy(
        self,
        task_type: str,
        strategy: str,
        success_rate: float,
    ) -> None:
        """记录执行策略"""
        item = ProceduralItem(
            id=str(uuid.uuid4()),
            type=MemoryType.PROCEDURAL,
            content=strategy,
            metadata={
                "pattern_type": "execution_strategy",
                "task_type": task_type,
                "success_rate": success_rate,
                "usage_count": 0,
            }
        )
        await self.add(item)

    async def add_code_pattern(
        self,
        pattern: str,
        language: str,
        applicability: str,
    ) -> None:
        """记录代码模式"""
        item = ProceduralItem(
            id=str(uuid.uuid4()),
            type=MemoryType.PROCEDURAL,
            content=pattern,
            metadata={
                "pattern_type": "code_style",
                "language": language,
                "applicability": applicability,
                "usage_count": 0,
            }
        )
        await self.add(item)

    async def match(
        self,
        context: Dict[str, Any],
    ) -> List[ProceduralItem]:
        """
        根据上下文匹配适用的程序记忆

        匹配策略：
        1. 工具使用模式：匹配 task_description 中的工具名
        2. 执行策略：匹配 task_type
        3. 代码模式：匹配 language 或 applicability

        Args:
            context: 包含 task_description, task_type, language 等

        Returns:
            按匹配度排序的程序记忆列表
        """
        task_description = context.get("task_description", "")
        task_type = context.get("task_type", "")
        language = context.get("language", "")
        task_lower = f"{task_description} {task_type}".lower()

        items = await self._get_all()
        scored = []

        for item in items:
            score = 0.0
            pattern_type = item.metadata.get("pattern_type", "")
            applicability = item.metadata.get("applicability", "")

            if pattern_type == "tool_usage":
                tool_name = item.metadata.get("tool_name", "")
                if tool_name and tool_name.lower() in task_lower:
                    score = 1.0
                elif applicability and applicability.lower() in task_lower:
                    score = 0.7

            elif pattern_type == "execution_strategy":
                if item.metadata.get("task_type") == task_type:
                    score = 1.0
                elif applicability and applicability.lower() in task_lower:
                    score = 0.6

            elif pattern_type == "code_style":
                if item.metadata.get("language") == language:
                    score = 0.8
                elif applicability and applicability.lower() in task_lower:
                    score = 0.5

            if score > 0:
                scored.append((score, item))

        # 按分数降序
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored]
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
        results = self._rank(results, criteria.keywords)

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

    def _rank(
        self,
        items: List[MemoryItem],
        query_keywords: List[str] = None,
    ) -> List[MemoryItem]:
        """多维度评分排序"""
        keywords = query_keywords or []
        scored = []
        for item in items:
            score = (
                item.importance * 0.5 +
                self._recency_score(item) * 0.3 +
                self._keyword_match_score(item, keywords) * 0.2
            )
            scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored]

    def _recency_score(self, item: MemoryItem) -> float:
        """时间衰减评分"""
        hours_old = (datetime.now() - item.created_at).total_seconds() / 3600
        return 1.0 / (1.0 + hours_old * 0.05)

    def _keyword_match_score(
        self,
        item: MemoryItem,
        query_keywords: List[str],
    ) -> float:
        """关键词匹配评分"""
        if not item.keywords or not query_keywords:
            return 0.5

        item_keywords_lower = [kw.lower() for kw in item.keywords]
        query_keywords_lower = [kw.lower() for kw in query_keywords]

        matches = sum(1 for qk in query_keywords_lower if qk in item_keywords_lower)
        return matches / len(query_keywords_lower) if query_keywords_lower else 0.5

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

## 5. 智能保留（Heuristics + LLM Judger）

为避免每次写入都调用 LLM，采用两级判断策略：

```python
@dataclass
class JudgerConfig:
    """判断器配置"""
    model: str = "claude-sonnet-4-20250514"
    importance_threshold: float = 0.6  # 重要性 >= 此值才持久化
    system_prompt: str = """You are a memory importance evaluator for an AI coding assistant.

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


class HeuristicJudger:
    """
    轻量级启发式判断器 - 实时判断，无需 LLM 调用

    规则：
    1. 长度过短（<20字符）-> 不持久化
    2. 包含重要性关键词 -> 高重要性
    3. 重复内容 -> 降低重要性
    4. 错误/失败相关 -> 高重要性
    """

    AUTO_PERSIST_KEYWORDS = {
        "error", "fail", "success", "decision", "important",
        "fixed", "resolved", "pattern", "strategy", "learned",
    }

    AUTO_REJECT_THRESHOLD = 20  # 字符数

    def judge(self, content: str) -> Tuple[bool, float, List[str]]:
        """
        启发式判断

        Returns:
            (should_persist, estimated_importance, keywords)
        """
        content_lower = content.lower()

        # 规则1: 长度过短
        if len(content) < self.AUTO_REJECT_THRESHOLD:
            return False, 0.3, []

        # 规则2: 重要性关键词
        found_keywords = [
            kw for kw in self.AUTO_PERSIST_KEYWORDS
            if kw in content_lower
        ]

        # 规则3: 错误/失败 -> 高重要性
        if any(kw in content_lower for kw in ["error", "fail", "fixed", "resolved"]):
            return True, 0.8, found_keywords

        # 规则4: 有关键词 -> 中等重要性
        if found_keywords:
            return True, 0.6, found_keywords

        # 默认: 可持久化但需 LLM 最终判断
        return True, 0.5, []


class MemoryJudger:
    """
    记忆判断器 - 启发式 + LLM 两级判断

    工作流程：
    1. 实时路径：HeuristicJudger 快速判断
       - 明确不持久化 -> 直接返回
       - 明确持久化 -> 存储，必要时调用 LLM 补充 metadata
    2. 批量路径：会话结束时 LLM 批量评估，补充遗漏的高价值记忆
    """

    def __init__(self, config: JudgerConfig, model_client: ModelClient):
        self.config = config
        self.model_client = model_client
        self.heuristic = HeuristicJudger()

    async def should_persist(
        self,
        content: str,
        context: Dict[str, str],
    ) -> Tuple[bool, float, MemoryType, List[str], str]:
        """
        判断是否值得持久化（实时路径）

        优先使用启发式规则，必要时调用 LLM
        """
        # 1. 启发式快速判断
        should_persist, estimated_importance, keywords = self.heuristic.judge(content)

        if not should_persist:
            return False, estimated_importance, MemoryType.EPISODIC, keywords, content[:100]

        # 2. 启发式判断为高重要性 -> 直接持久化，只调用 LLM 补充 keywords
        if estimated_importance >= 0.7:
            try:
                _, importance, memory_type, llm_keywords, summary = await self._call_llm(
                    content, context
                )
                # 合并 keywords
                all_keywords = list(set(keywords + llm_keywords))
                return True, importance, memory_type, all_keywords, summary
            except Exception:
                # LLM 调用失败，使用启发式结果
                return True, estimated_importance, MemoryType.EPISODIC, keywords, content[:100]

        # 3. 中等重要性 -> 调用 LLM 最终判断
        return await self._call_llm(content, context)

    async def _call_llm(
        self,
        content: str,
        context: Dict[str, str],
    ) -> Tuple[bool, float, MemoryType, List[str], str]:
        """调用 LLM 判断，失败时返回安全默认值"""
        try:
            user_prompt = f"""Session ID: {context.get('session_id', 'unknown')}
Memory Content: {content}

Evaluate this memory entry."""

            response = await self.model_client.complete(
                system=self.config.system_prompt,
                user=user_prompt,
                json_mode=True,
            )

            result = json.loads(response.content)

            should_persist = result.get("should_persist", True)
            importance = result.get("importance", 0.5)
            memory_type = MemoryType(result.get("memory_type", "episodic"))
            keywords = result.get("keywords", [])
            summary = result.get("summary", content[:100])

            return should_persist, importance, memory_type, keywords, summary

        except Exception:
            # LLM 调用失败，返回安全默认值（持久化但低重要性）
            return True, 0.4, MemoryType.EPISODIC, [], content[:100]

    async def evaluate_batch(
        self,
        items: List[MemoryItem],
    ) -> List[Tuple[MemoryItem, Tuple[bool, float, MemoryType, List[str], str]]]:
        """
        批量评估记忆条目（批量路径）

        用于：
        1. 会话结束时的批量评估
        2. 定期清理前的价值重评

        将所有条目打包发给 LLM 一次评估，减少 API 调用
        """
        if not items:
            return []

        try:
            # 构建批量 prompt
            entries_text = "\n\n".join(
                f"[{i}] {item.content}"
                for i, item in enumerate(items)
            )

            user_prompt = f"""Evaluate the following memory entries. For each, determine:
- should_persist: whether it should be kept long-term
- importance: 0.0-1.0
- memory_type: episodic/preference/procedural
- keywords: relevant keywords
- summary: brief summary

Entries:
{entries_text}

Respond in JSON array format:
[
  {{"index": 0, "should_persist": true/false, "importance": 0.0-1.0, "memory_type": "...", "keywords": [...], "summary": "..."}},
  ...
]"""

            response = await self.model_client.complete(
                system=self.config.system_prompt,
                user=user_prompt,
                json_mode=True,
            )

            results_json = json.loads(response.content)
            results_map = {r["index"]: r for r in results_json}

            results = []
            for i, item in enumerate(items):
                if i in results_map:
                    r = results_map[i]
                    decision = (
                        r.get("should_persist", True),
                        r.get("importance", 0.5),
                        MemoryType(r.get("memory_type", "episodic")),
                        r.get("keywords", []),
                        r.get("summary", item.content[:100]),
                    )
                else:
                    # 缺失的条目使用安全默认值
                    decision = (True, 0.4, MemoryType.EPISODIC, [], item.content[:100])
                results.append((item, decision))

            return results

        except Exception:
            # 批量评估失败，所有条目使用安全默认值
            return [
                (item, (True, 0.4, MemoryType.EPISODIC, [], item.content[:100]))
                for item in items
            ]
```

---

## 6. Embedder 接口

```python
class Embedder(Protocol):
    """向量嵌入生成器接口"""

    async def embed(self, text: str) -> List[float]:
        """生成文本的向量嵌入"""
        ...


class OpenAIEmbedder:
    """OpenAI Embeddings 实现"""

    def __init__(self, model: str = "text-embedding-3-small"):
        self.model = model

    async def embed(self, text: str) -> List[float]:
        response = await openai.embeddings.create(
            model=self.model,
            input=text,
        )
        return response.data[0].embedding


class ClaudeEmbedder:
    """Claude Embeddings 实现（使用 Anthropic API）"""

    def __init__(self, model: str = "claude-embedding"):
        self.model = model

    async def embed(self, text: str) -> List[float]:
        # 注意：Anthropic 官方暂不提供 embedding API
        # 此处使用 OpenAI 或其他兼容实现
        raise NotImplementedError("Use OpenAIEmbedder or other provider")
```

---

## 7. MemoryManager Facade

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

    def __init__(self, config: MemoryConfig, model_client: ModelClient, embedder: Embedder):
        self.config = config
        self.model_client = model_client
        self.embedder = embedder
        self.store = MemoryStore(config)
        self.query = MemoryQuery(self.store)
        self.judger = MemoryJudger(config.judger, model_client)

    # === 写入接口 ===

    async def record(
        self,
        content: str,
        memory_type: MemoryType,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryItem:
        """
        记录一条记忆（自动判断是否持久化）

        流程：
        1. 调用 Judger 判断是否值得持久化
        2. 生成 embedding（用于向量检索）
        3. 根据判断结果路由存储
        """
        item = MemoryItem(
            id=str(uuid.uuid4()),
            type=memory_type,
            content=content,
            session_id=session_id,
            task_id=task_id,
            metadata=metadata or {},
        )

        # 1. 判断是否持久化
        should_persist, importance, inferred_type, keywords, summary = (
            await self.judger.should_persist(
                content=content,
                context={"session_id": session_id or ""},
            )
        )

        item.importance = importance
        item.keywords = keywords

        # 2. 生成 embedding（异步，不阻塞判断）
        if should_persist and memory_type == MemoryType.EPISODIC:
            try:
                item.embedding = await self.embedder.embed(content)
            except Exception:
                pass  # embedding 生成失败不影响存储

        # 3. 持久化
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
        """
        记录任务执行结果（直接持久化到 Experience）

        经验直接持久化，因为任务执行结果本身就是高价值记忆。
        重要性根据结果质量浮动。
        """
        # 基础重要性
        base_importance = 0.85 if success else 0.65

        # 根据持续时间调整（过短或过长都降低重要性）
        if duration < 10:  # 10秒以内，可能是误触发
            base_importance -= 0.1
        elif duration > 3600:  # 1小时以上，效率可能有问题
            base_importance -= 0.1

        base_importance = max(0.4, min(0.95, base_importance))

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
            importance=base_importance,
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
├── judger.py             # HeuristicJudger, MemoryJudger
├── embedder.py           # Embedder, OpenAIEmbedder
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
    ├── MemoryJudger (HeuristicJudger + LLM fallback)
    └── Embedder
```

---

## 8. 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.1 | 2026-03-29 | 修复审查问题：LLM Judger 改为启发式+批量评估、添加 Embedder 接口、修复 ProceduralStore.match() 逻辑、修复 _keyword_match_score、修复 record_task_outcome 重要性计算、SYSTEM_PROMPT 可配置、添加 LLM 调用错误处理 |
| v1.0 | 2026-03-29 | 初始版本，四层记忆架构设计 |
