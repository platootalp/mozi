"""Mozi AI Coding Agent.

A four-layer AI coding agent architecture featuring:
- Ingress Layer: CLI, Web UI, API Gateway, IDE Extension, MCP Client
- Orchestrator Layer: Intent recognition, complexity assessment, task routing
- Capabilities Layer: Configuration, tools, MCP integration, Skills engine
- Infrastructure Layer: Tiered storage, model API adapters

Examples
--------
Run the agent via CLI:
    $ python -m mozi

Import the package:
    import mozi
"""

__version__ = "0.1.0"
__author__: str = "Mozi Team"


class MoziError(Exception):
    """Base exception for all Mozi errors.

    All custom exceptions in the mozi package should inherit from this class.
    """

    pass


__all__ = [
    "MoziError",
    "__version__",
]
