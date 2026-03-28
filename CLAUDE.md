# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Mozi AI Coding Agent** - A four-layer AI coding agent with tagline "Build More, Waste Less".

```
python -m mozi        # Run CLI
uv run pytest         # Run tests
uv run ruff check     # Lint
uv run mypy           # Type check
```

## Build Tool

**uv** is the build tool (not pip or poetry). All commands use `uv run <command>`.

## Development Commands

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest                          # All tests
uv run pytest tests/unit/              # Unit tests only
uv run pytest -v --cov=mozi            # With coverage
uv run pytest -k test_name             # Single test

# Lint and format
uv run ruff check                      # Lint
uv run ruff format                     # Format

# Type check
uv run mypy

# Security
uv run bandit -r mozi/

# Pre-commit hooks
pre-commit install
pre-commit run --all-files
```

## Architecture

### Four-Layer Architecture

```
mozi/
├── cli/                    # Ingress Layer (Typer CLI)
├── orchestrator/           # Orchestrator Layer
│   ├── core/               # Intent recognition, complexity assessment, routing
│   ├── agent/              # Agent runtime with ReAct loop
│   └── session/            # Session management
├── capabilities/           # Capabilities Layer
│   ├── config/             # Configuration schemas and loader
│   └── tools/              # Tool framework and built-in tools
└── infrastructure/         # Infrastructure Layer
    ├── db/                 # SQLite database
    └── model/              # Model API adapters
```

### Complexity-Based Routing

| Score | Level | Strategy |
|-------|-------|----------|
| ≤40 | SIMPLE | FastPath - single-agent, max 5 iterations |
| 40-70 | MEDIUM | Enhanced - single-agent with monitoring, max 15 iterations |
| >70 | COMPLEX | Orchestrated - multi-agent coordination, max 30 iterations |

### Core Flow

1. `MainOrchestrator.execute()` receives task
2. `IntentRecognition.recognize_intent()` identifies intent
3. `ComplexityAssessor` calculates score
4. `TaskRouter` determines strategy
5. `AgentRuntime` executes via ReAct loop

### Tool Framework

Tools are registered in `ToolRegistry` and inherit from `BaseTool`. Built-in tools in `capabilities/tools/builtin/`: bash, edit, glob, grep, read, write.

### Session Management

`SessionManager` creates/resumes sessions stored in SQLite. Sessions track state (ACTIVE/COMPLETED/ERROR), complexity level, and metadata.

## Configuration

`.mozi/` directory with JSON configs:
- `config.json` - Core settings
- `agents.json` - Agent registry
- `tools.json` - Tool policies
- `skills.json` - Skill triggers

## Project Rules (Mandatory)

规则位于 `.claude/rules/`，CI 自动检查：

| Rule | File |
|------|------|
| Workflow | workflow.md |
| CI/CD | ci-cd.md |
| Documentation | documentation.md |
| Coding Style | coding-style.md |
| Testing | testing.md |
| Security | security.md |

**Quality gates:**
- Ruff format + mypy strict type checking
- pytest coverage ≥ 80% (unit ≥ 80%, core ≥ 90%)
- bandit security scan
- Commit message format: `type: subject`

**Branch model:**
```
main ← 2 reviewers
  ↑
develop ← 1 reviewer
  ↑
feature/* fix/* docs/*
```

## Key Terminology

| Term | Meaning |
|------|---------|
| ReAct | Reasoning + Acting loop |
| FastPath | Direct execution for SIMPLE tasks |
| HITL | Human-in-the-Loop approval |
| DAG | Directed Acyclic Graph for task scheduling |
