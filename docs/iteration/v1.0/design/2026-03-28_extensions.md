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

## 1. 组件列表

| 组件 | 职责 |
|------|------|
| **SkillsEngine** | Skill 解析与执行 |
| **MCPClient** | MCP 协议客户端 |

## 2. Skills Engine

Skill 文档结构：

```markdown
---
name: git-master
triggers:
  - "atomic commit"
  - "safe rebase"
---

# Git Master Skill

## 执行步骤
1. 检查 git 状态
2. 生成提交消息
3. 执行提交
```

## 3. MCP Client

支持的传输方式：stdio / sse / http / websocket

```python
class MCPClient:
    async def connect(self, transport: str, endpoint: str) -> None: ...
    async def call_tool(self, tool_name: str, params: dict) -> Any: ...
    async def list_tools(self) -> List[Tool]: ...
```

## 4. 依赖关系

- **依赖模块**: Tools Layer
- **被依赖模块**: Agent Layer

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-03-28 | 初始版本，从架构文档拆分 |
