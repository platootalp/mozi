# Extensions Module (扩展层)

## 文档信息

| 字段 | 内容 |
|------|------|
| 模块名称 | Extensions |
| 职责 | Skill 解析与执行、MCP 协议支持 |
| 路径 | `mozi/extensions/` |
| 文档版本 | v1.0 |
| 状态 | 规划中 |
| 创建日期 | 2026-03-28 |

---

## 1. 模块概述

Extensions 模块是系统的扩展层，提供 Skills Engine 和 MCP Client 两大扩展机制，支持用户自定义技能和外部工具集成。

### 1.1 核心职责

- Skill 解析与执行
- Skill 触发器匹配
- MCP 协议支持
- 外部工具集成

### 1.2 差异化特性

| 特性 | 说明 |
|------|------|
| 按需加载 | Skill 懒加载，只在触发时加载 |
| Markdown 定义 | 使用 Markdown 定义 Skill，易读易写 |
| 多传输支持 | 支持 stdio/sse/http/websocket |
| 热插拔 | MCP 工具动态注册 |

---

## 2. 模块结构

```
mozi/extensions/
├── __init__.py
├── skills/                # Skills Engine
│   ├── __init__.py
│   ├── engine.py         # Skill 引擎
│   ├── loader.py         # Skill 加载器
│   ├── parser.py         # Skill 解析器
│   ├── matcher.py        # 触发器匹配器
│   └── executor.py       # Skill 执行器
│
├── mcp/                  # MCP Client
│   ├── __init__.py
│   ├── client.py         # MCP 客户端
│   ├── protocol.py       # MCP 协议
│   ├── transport/        # 传输层
│   │   ├── __init__.py
│   │   ├── stdio.py     # STDIO 传输
│   │   ├── sse.py       # SSE 传输
│   │   ├── http.py      # HTTP 传输
│   │   └── websocket.py # WebSocket 传输
│   └── registry.py       # MCP 工具注册表
│
└── registry.py            # 扩展注册表
```

---

## 3. Skills Engine

### 3.1 概述

Skills Engine 提供自定义技能的解析和执行能力。Skill 使用 Markdown 格式定义，包含元数据和执行步骤。

### 3.2 Skill 文档结构

```markdown
---
name: git-atomic-commit
triggers:
  - "atomic commit"
  - "safe commit"
  - "commit with message"
description: "Perform an atomic git commit with proper message format"
version: "1.0.0"
author: "user"
tags:
  - git
  - commit
---

# Git Atomic Commit Skill

## 描述
执行一个原子的 git 提交，确保提交消息格式正确。

## 执行步骤
1. 检查 git 状态
2. 生成提交消息
3. 执行 git add 和 git commit

## 参数
- `message`: 提交消息（可选）

## 示例
```
/skill git-atomic-commit
```
```

### 3.3 SkillParser

```python
@dataclass
class SkillMetadata:
    name: str
    triggers: List[str]
    description: str
    version: str
    author: str
    tags: List[str]

@dataclass
class Skill:
    metadata: SkillMetadata
    content: str
    steps: List[str]
    parameters: Dict[str, Any]

class SkillParser:
    """Skill 解析器"""

    FRONT_MATTER_PATTERN = re.compile(
        r"^---\n(.*?)\n---\n(.*)",
        re.DOTALL
    )

    def parse(self, content: str) -> Skill:
        """解析 Skill 文档"""
        # 1. 解析 front matter
        match = self.FRONT_MATTER_PATTERN.match(content.strip())
        if not match:
            raise SkillParseError("Invalid skill format: missing front matter")

        front_matter_raw = match.group(1)
        body = match.group(2)

        # 2. 解析元数据
        metadata = self._parse_front_matter(front_matter_raw)

        # 3. 解析执行步骤
        steps = self._parse_steps(body)

        # 4. 解析参数
        parameters = self._parse_parameters(body)

        return Skill(
            metadata=metadata,
            content=content,
            steps=steps,
            parameters=parameters,
        )

    def _parse_front_matter(self, raw: str) -> SkillMetadata:
        """解析 YAML front matter"""
        data = yaml.safe_load(raw)
        return SkillMetadata(
            name=data["name"],
            triggers=data.get("triggers", []),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            author=data.get("author", ""),
            tags=data.get("tags", []),
        )

    def _parse_steps(self, body: str) -> List[str]:
        """解析执行步骤"""
        steps = []
        for line in body.split("\n"):
            line = line.strip()
            if line.startswith("## 执行步骤") or line.startswith("## Steps"):
                continue
            if re.match(r"^\d+\.", line):
                steps.append(re.sub(r"^\d+\.\s*", "", line))
        return steps

    def _parse_parameters(self, body: str) -> Dict[str, Any]:
        """解析参数定义"""
        params = {}
        in_params = False
        for line in body.split("\n"):
            line = line.strip()
            if line.startswith("## 参数") or line.startswith("## Parameters"):
                in_params = True
                continue
            if in_params and line.startswith("-"):
                match = re.match(r"- `(\w+)`: (.+)", line)
                if match:
                    params[match.group(1)] = match.group(2)
        return params
```

### 3.4 SkillMatcher

```python
class SkillMatcher:
    """Skill 触发器匹配器"""

    def __init__(self, skills: List[Skill]):
        self.skills = {s.metadata.name: s for s in skills}
        self._build_index()

    def _build_index(self) -> None:
        """构建触发器索引"""
        self.trigger_index: Dict[str, List[str]] = {}  # trigger -> skill names

        for skill in self.skills.values():
            for trigger in skill.metadata.triggers:
                if trigger not in self.trigger_index:
                    self.trigger_index[trigger] = []
                self.trigger_index[trigger].append(skill.metadata.name)

    def match(self, user_input: str) -> Optional[Skill]:
        """匹配用户输入到 Skill"""
        user_input_lower = user_input.lower()

        # 精确匹配
        for trigger, skill_names in self.trigger_index.items():
            if trigger.lower() in user_input_lower:
                return self.skills[skill_names[0]]

        # 模糊匹配
        for skill_name, skill in self.skills.items():
            if skill_name.lower().replace("-", " ") in user_input_lower:
                return skill

        return None

    def get_skill(self, name: str) -> Optional[Skill]:
        """按名称获取 Skill"""
        return self.skills.get(name)
```

### 3.5 SkillExecutor

```python
class SkillExecutor:
    """Skill 执行器"""

    def __init__(
        self,
        tool_executor: ToolExecutor,
        model: ModelGateway,
    ):
        self.tool_executor = tool_executor
        self.model = model

    async def execute(
        self,
        skill: Skill,
        params: Dict[str, Any],
        context: ToolContext,
    ) -> SkillResult:
        """执行 Skill"""
        results = []

        for step in skill.steps:
            # 1. 渲染步骤模板
            rendered = self._render_step(step, params, context)

            # 2. 判断步骤类型
            if rendered.startswith("bash:"):
                command = rendered[5:].strip()
                result = await self.tool_executor.execute(
                    "bash",
                    {"command": command},
                    context,
                )
            elif rendered.startswith("llm:"):
                prompt = rendered[4:].strip()
                response = await self.model.complete([
                    Message(role="user", content=prompt)
                ])
                result = ToolResult(success=True, content=response.content)
            else:
                result = await self.tool_executor.execute(
                    "bash",
                    {"command": rendered},
                    context,
                )

            results.append(SkillStepResult(step=step, result=result))

            # 3. 如果步骤失败，停止执行
            if not result.success:
                break

        return SkillResult(
            skill_name=skill.metadata.name,
            success=all(r.result.success for r in results),
            step_results=results,
        )

    def _render_step(
        self,
        step: str,
        params: Dict[str, Any],
        context: ToolContext,
    ) -> str:
        """渲染步骤模板"""
        # 替换参数
        for key, value in params.items():
            step = step.replace(f"{{{key}}}", str(value))

        return step

@dataclass
class SkillStepResult:
    step: str
    result: ToolResult

@dataclass
class SkillResult:
    skill_name: str
    success: bool
    step_results: List[SkillStepResult]
```

### 3.6 SkillsEngine

```python
class SkillsEngine:
    """Skills 引擎"""

    def __init__(
        self,
        skill_dir: Path,
        tool_executor: ToolExecutor,
        model: ModelGateway,
    ):
        self.skill_dir = skill_dir
        self.tool_executor = tool_executor
        self.model = model

        self.parser = SkillParser()
        self.executor = SkillExecutor(tool_executor, model)
        self.matcher: Optional[SkillMatcher] = None

    async def load(self) -> None:
        """加载所有 Skill"""
        skills = []

        for path in self.skill_dir.glob("**/*.md"):
            try:
                content = path.read_text()
                skill = self.parser.parse(content)
                skills.append(skill)
            except Exception as e:
                logger.warning(f"Failed to load skill {path}: {e}")

        self.matcher = SkillMatcher(skills)
        logger.info(f"Loaded {len(skills)} skills")

    async def execute_from_input(
        self,
        user_input: str,
        context: ToolContext,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[SkillResult]:
        """从用户输入执行 Skill"""
        if not self.matcher:
            await self.load()

        # 1. 匹配 Skill
        skill = self.matcher.match(user_input)
        if not skill:
            return None

        # 2. 执行 Skill
        return await self.executor.execute(
            skill,
            params or {},
            context,
        )
```

---

## 4. MCP Client

### 4.1 概述

MCP Client 实现 Model Context Protocol 协议客户端，支持与外部 MCP Server 通信。

### 4.2 MCP 协议

```python
class MCPProtocol:
    """MCP 协议"""

    VERSION = "1.0.0"

    # 消息类型
    class MessageType(Enum):
        INITIALIZE = "initialize"
        TOOLS_LIST = "tools/list"
        TOOLS_CALL = "tools/call"
        RESOURCES_LIST = "resources/list"
        RESOURCES_READ = "resources/read"
        PROMPTS_LIST = "prompts/list"
        PROMPTS_GET = "prompts/get"

    # 消息格式
    @dataclass
    class MCPMessage:
        jsonrpc: str = "2.0"
        id: Optional[str] = None
        method: Optional[str] = None
        params: Optional[Dict[str, Any]] = None
        result: Optional[Any] = None
        error: Optional[Dict[str, Any]] = None
```

### 4.3 MCPClient

```python
class MCPClient:
    """MCP 客户端"""

    def __init__(self, config: MCPConfig):
        self.config = config
        self.transport: Optional[Transport] = None
        self.tools: Dict[str, MCPTool] = {}
        self._connected = False

    async def connect(self) -> None:
        """连接 MCP Server"""
        # 创建传输层
        if self.config.transport == "stdio":
            self.transport = StdioTransport(self.config.command, self.config.args)
        elif self.config.transport == "sse":
            self.transport = SSETransport(self.config.url)
        elif self.config.transport == "http":
            self.transport = HTTPTransport(self.config.url)
        elif self.config.transport == "websocket":
            self.transport = WebSocketTransport(self.config.url)

        await self.transport.connect()

        # 初始化
        await self._initialize()

        # 获取工具列表
        await self._list_tools()

        self._connected = True

    async def disconnect(self) -> None:
        """断开连接"""
        if self.transport:
            await self.transport.close()
            self._connected = False

    async def _initialize(self) -> None:
        """发送初始化请求"""
        request = MCPProtocol.MCPMessage(
            id=str(uuid.uuid4()),
            method=MCPProtocol.MessageType.INITIALIZE.value,
            params={
                "protocolVersion": MCPProtocol.VERSION,
                "capabilities": {
                    "tools": True,
                    "resources": True,
                    "prompts": True,
                },
                "clientInfo": {
                    "name": "mozi",
                    "version": "1.0.0",
                },
            },
        )

        response = await self.transport.send(request)
        if response.error:
            raise MCPError(f"Initialize failed: {response.error}")

    async def _list_tools(self) -> None:
        """获取工具列表"""
        request = MCPProtocol.MCPMessage(
            id=str(uuid.uuid4()),
            method=MCPProtocol.MessageType.TOOLS_LIST.value,
        )

        response = await self.transport.send(request)
        if response.result and "tools" in response.result:
            for tool_def in response.result["tools"]:
                self.tools[tool_def["name"]] = MCPTool(
                    name=tool_def["name"],
                    description=tool_def.get("description", ""),
                    input_schema=tool_def.get("inputSchema", {}),
                )

    async def call_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
    ) -> ToolResult:
        """调用工具"""
        if tool_name not in self.tools:
            return ToolResult(success=False, error=f"Tool {tool_name} not found")

        request = MCPProtocol.MCPMessage(
            id=str(uuid.uuid4()),
            method=MCPProtocol.MessageType.TOOLS_CALL.value,
            params={
                "name": tool_name,
                "arguments": params,
            },
        )

        response = await self.transport.send(request)

        if response.error:
            return ToolResult(success=False, error=str(response.error))

        return ToolResult(
            success=True,
            content=str(response.result),
        )

    def list_tools(self) -> List[MCPTool]:
        """列出所有工具"""
        return list(self.tools.values())

@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: Dict[str, Any]

    def to_tool(self) -> Tool:
        """转换为 Mozi Tool"""
        return MCPToolWrapper(self)
```

### 4.4 传输层

```python
class Transport(ABC):
    """传输层抽象"""

    @abstractmethod
    async def connect(self) -> None:
        pass

    @abstractmethod
    async def send(self, message: MCPProtocol.MCPMessage) -> MCPProtocol.MCPMessage:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass

class StdioTransport(Transport):
    """STDIO 传输"""

    def __init__(self, command: str, args: List[str]):
        self.command = command
        self.args = args
        self.process: Optional[asyncio.subprocess.Process] = None
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None

    async def connect(self) -> None:
        self.process = await asyncio.create_subprocess_exec(
            self.command,
            *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
        )
        self._reader = self.process.stdout
        self._writer = self.process.stdin

    async def send(self, message: MCPProtocol.MCPMessage) -> MCPProtocol.MCPMessage:
        data = json.dumps(message.__dict__).encode() + b"\n"
        self._writer.write(data)
        await self._writer.drain()

        response_data = await self._reader.readline()
        return MCPProtocol.MCPMessage(**json.loads(response_data))

    async def close(self) -> None:
        if self.process:
            self.process.terminate()
            await self.process.wait()
```

### 4.5 配置

```python
@dataclass
class MCPConfig:
    name: str
    transport: str = "stdio"  # stdio | sse | http | websocket
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)
    url: Optional[str] = None
    env: Dict[str, str] = field(default_factory=dict)
```

---

## 5. MCP 工具注册表

### 5.1 MCPToolRegistry

```python
class MCPToolRegistry:
    """MCP 工具注册表"""

    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self.mcp_clients: Dict[str, MCPClient] = {}

    async def register_server(self, config: MCPConfig) -> None:
        """注册 MCP Server"""
        client = MCPClient(config)
        await client.connect()

        self.mcp_clients[config.name] = client

        # 注册工具到工具注册表
        for tool in client.list_tools():
            self.tool_registry.register(tool.to_tool())

    async def unregister_server(self, name: str) -> None:
        """注销 MCP Server"""
        if name in self.mcp_clients:
            await self.mcp_clients[name].disconnect()
            del self.mcp_clients[name]

    def get_client(self, name: str) -> Optional[MCPClient]:
        """获取 MCP Client"""
        return self.mcp_clients.get(name)

    def list_servers(self) -> List[str]:
        """列出所有注册的 Server"""
        return list(self.mcp_clients.keys())
```

---

## 6. 核心工作流

### 6.1 Skill 执行流程

```
用户输入
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                   SkillsEngine                               │
│                                                             │
│  1. SkillMatcher.match()                                   │
│     └── 匹配触发器                                          │
│                                                             │
│  2. SkillExecutor.execute()                                │
│     └── 逐步骤执行                                          │
│         ├── bash: 命令执行                                  │
│         └── llm: LLM 生成                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
返回 SkillResult
```

### 6.2 MCP 工具调用流程

```
工具调用请求
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                   MCPClient                                  │
│                                                             │
│  1. 构建 MCPMessage                                        │
│     └── JSON-RPC 格式                                      │
│                                                             │
│  2. Transport.send()                                       │
│     └── stdio/sse/http/websocket                           │
│                                                             │
│  3. 解析响应                                               │
│     └── 转换为 ToolResult                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
返回 ToolResult
```

---

## 7. 依赖关系

- **依赖模块**: Tools Layer
- **被依赖模块**: Agent Layer

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-03-28 | 初始版本，从架构文档拆分 |
