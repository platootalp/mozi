"""Orchestrator module for Mozi AI Coding Agent.

This module provides the main orchestrator that coordinates the full pipeline
including intent recognition, complexity assessment, task routing, and
agent execution.

Examples
--------
Run a task through the orchestrator:

    orchestrator = MainOrchestrator(model_adapter, tool_registry)
    result = await orchestrator.execute("Edit the main.py file")
"""

from __future__ import annotations

from mozi.orchestrator.orchestrator import (
    MainOrchestrator,
    OrchestratorConfig,
    OrchestratorError,
    OrchestratorResult,
)

__all__ = [
    "MainOrchestrator",
    "OrchestratorConfig",
    "OrchestratorError",
    "OrchestratorResult",
]
