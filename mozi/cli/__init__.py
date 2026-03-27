"""CLI module for Mozi AI Coding Agent.

This module provides the command-line interface for the Mozi agent,
including interactive mode, task execution, and session management.

Examples
--------
Run the CLI:

    $ mozi --help

Execute a task:

    $ mozi "Read the main.py file"

Start interactive mode:

    $ mozi --interactive
"""

from __future__ import annotations

from mozi.cli.main import app

__all__ = ["app"]
