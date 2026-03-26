# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **documentation-only repository** for the **Mozi AI Coding Agent** system architecture. It contains comprehensive architecture design documents, competitive analysis, and review reports.

Mozi is a proposed AI Coding Agent with the tagline "Build More, Waste Less", featuring:
- Four-layer architecture (Ingress → Orchestrator → Capabilities → Infrastructure)
- Adaptive planning with automatic complexity-based routing (SIMPLE/MEDIUM/COMPLEX)
- Orchestrator-centric multi-agent scheduling
- Four-tier storage with automatic tiering (Hot/Warm/Cold/Archive)
- MCP (Model Context Protocol) integration
- Four-layer security model with HITL (Human-in-the-Loop) approval

## Repository Structure

```
mozi/
├── README.md                    # Project overview (minimal)
├── LICENSE                      # License file
├── docs/
│   ├── architecture.md          # Core architecture design (v1.2, primary document)
│   ├── architecture_review.md   # Initial review of architecture
│   ├── architecture_review_v2.md # Second review (latest)
│   ├── AI_AGENT_PLANNING_TASK_COMPARISON.md  # OpenClaw/OpenCode/Cursor comparison
│   ├── AI_AGENT_TOOLS_SECURITY_COMPARISON.md # Tools/security comparison
│   ├── AI_AGENT_MEMORY_CONTEXT_COMPARISON.md # Memory/context comparison
│   └── resume.md                # Resume/professional summary
└── .claude/settings.local.json  # Local Claude Code settings
```

## Key Architecture Concepts

### Four-Layer Architecture
1. **Ingress Layer**: CLI (Typer), Web UI (FastAPI), API Gateway, IDE Extension, MCP Client
2. **Orchestrator Layer**: Intent recognition, complexity assessment, task routing, DAG scheduler, session management
3. **Capabilities Layer**: Configuration management, tool framework, MCP integration, Skills engine
4. **Infrastructure Layer**: Tiered storage (memory/vector DB/SQLite/files), model API adapters

### Complexity-Based Routing
| Score | Level | Strategy |
|-------|-------|----------|
| ≤40 | SIMPLE | Single-agent FastPath, implicit ReAct planning |
| 40-70 | MEDIUM | Single-agent with enhanced monitoring |
| >70 | COMPLEX | Multi-agent with Orchestrator DAG scheduling |

### Configuration System
Configuration files (in `.mozi/` directory):
- `config.json` - Core system configuration
- `agents.json` - Agent registry with permissions and model settings
- `tools.json` - Tool policies and sandbox configuration
- `mcp.json` - MCP server configurations
- `skills.json` - Skill registry and triggers

Configuration loading priority (highest to lowest):
1. Environment variables (`MOZI_*`)
2. `.mozi/*.json` (project-local)
3. `~/.mozi/user.json` (user-global)
4. System defaults

## Working with This Repository

### Document Standards
- Architecture documentation uses **Chinese** as the primary language
- Diagrams use ASCII art within code blocks
- Configuration schemas use JSON examples
- Comparison documents analyze OpenClaw, OpenCode, and Cursor

### Key Terminology
| Term | Meaning |
|------|---------|
| HITL | Human-in-the-Loop |
| DAG | Directed Acyclic Graph |
| MCP | Model Context Protocol |
| ReAct | Reasoning + Acting |
| FastPath | Direct execution for simple tasks |
| Hot/Warm/Cold/Archive | Four-tier storage strategy |

### Claude Code Settings
The `.claude/settings.local.json` grants permissions for:
- `Bash(git add:*)`
- `Bash(git commit:*)`

## Project Rules (Mandatory)

规则是**强制性命令**，位于 `.mozi/rules/`，CI 自动检查：

| 规则 | 文件 |
|------|------|
| Workflow | [workflow.md](./.mozi/rules/workflow.md) |
| CI/CD | [ci-cd.md](./.mozi/rules/ci-cd.md) |
| Documentation | [documentation.md](./.mozi/rules/documentation.md) |
| Coding Style | [coding-style.md](./.mozi/rules/coding-style.md) |
| Testing | [testing.md](./.mozi/rules/testing.md) |

**强制检查:**
- Ruff/Black/Prettier 格式
- mypy/tsc 类型
- pytest 测试通过
- 覆盖率 ≥ 80%
- bandit/truffleHog 安全
- 分支/提交规范

**分支模型:**
```
main ← 2人
  ↑
develop ← 1人
  ↑
feature/* fix/* docs/*
```

## Important Notes

- This is an **architecture design repository**, not an implementation
- All code examples in docs are illustrative/specification
- No build system, tests, or runtime code exists
- Documentation follows a structured review cycle (see `architecture_review_v2.md`)
