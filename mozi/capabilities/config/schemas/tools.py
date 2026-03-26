"""Tool configuration schema for Mozi AI Coding Agent.

This module defines the Pydantic schemas for tool policies (tools.json).
It includes allowlist/blocklist, sandbox settings, and permission levels.

Examples
--------
Validate a tool policy configuration:

    policy_data = {
        "allowlist": ["read", "edit", "bash"],
        "sandbox_mode": "non-main",
        "default_permission": "ask"
    }
    policy = ToolPolicy(**policy_data)
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ToolPermission(StrEnum):
    """Tool permission levels.

    Attributes
    ----------
    ALLOW : str
        Tool execution is allowed without confirmation.
    DENY : str
        Tool execution is denied.
    ASK : str
        Tool execution requires Human-in-the-Loop approval.
    """

    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


class SandboxMode(StrEnum):
    """Sandbox execution modes for tools.

    Attributes
    ----------
    OFF : str
        No sandboxing - execute directly.
    NON_MAIN : str
        Sandbox only non-main file operations (read, glob, grep).
    ALL : str
        Sandbox all tool operations.
    """

    OFF = "off"
    NON_MAIN = "non-main"
    ALL = "all"


class ToolPolicy(BaseModel):
    """Tool-specific policy configuration.

    Attributes
    ----------
    name : str
        Tool name this policy applies to.
    permission : ToolPermission
        Permission level for this tool.
    sandbox_mode : SandboxMode
        Sandbox mode for this tool.
    description : str | None
        Optional description of tool behavior.
    """

    name: str
    permission: ToolPermission = ToolPermission.ASK
    sandbox_mode: SandboxMode = SandboxMode.NON_MAIN
    description: str | None = None

    model_config = {"extra": "forbid"}


class ToolGroup(BaseModel):
    """Group of tools with shared policy.

    Attributes
    ----------
    name : str
        Group name.
    tools : list[str]
        List of tool names in this group.
    policy : ToolPolicy
        Shared policy for all tools in the group.
    """

    name: str
    tools: list[str] = Field(default_factory=list)
    policy: ToolPolicy

    model_config = {"extra": "forbid"}


class ToolsConfig(BaseModel):
    """Tool framework configuration.

    Attributes
    ----------
    version : str
        Configuration version.
    allowlist : list[str]
        List of allowed tool names.
        If empty, all non-blocklisted tools are allowed.
    blocklist : list[str]
        List of blocked tool names.
        Takes precedence over allowlist.
    default_permission : ToolPermission
        Default permission for tools not explicitly configured.
    default_sandbox_mode : SandboxMode
        Default sandbox mode for tools not explicitly configured.
    policies : dict[str, ToolPolicy]
        Per-tool policy overrides.
    groups : dict[str, ToolGroup]
        Named tool groups with shared policies.
    builtin_tools_enabled : bool
        Whether to enable built-in tools.
    custom_tools_enabled : bool
        Whether to enable custom tools.
    """

    version: str = "1.0"
    allowlist: list[str] = Field(default_factory=list)
    blocklist: list[str] = Field(default_factory=list)
    default_permission: ToolPermission = ToolPermission.ASK
    default_sandbox_mode: SandboxMode = SandboxMode.NON_MAIN
    policies: dict[str, ToolPolicy] = Field(default_factory=dict)
    groups: dict[str, ToolGroup] = Field(default_factory=dict)
    builtin_tools_enabled: bool = True
    custom_tools_enabled: bool = True

    model_config = {"extra": "forbid"}

    def is_tool_allowed(self, tool_name: str) -> bool:
        """Check if a tool is allowed by policy.

        Parameters
        ----------
        tool_name : str
            Name of the tool to check.

        Returns
        -------
        bool
            True if the tool is allowed, False otherwise.
        """
        # Check blocklist first (deny takes precedence)
        if tool_name in self.blocklist:
            return False

        # Check allowlist if non-empty
        if self.allowlist and tool_name not in self.allowlist:
            return False

        return True

    def get_tool_policy(self, tool_name: str) -> ToolPolicy:
        """Get effective policy for a tool.

        Parameters
        ----------
        tool_name : str
            Name of the tool.

        Returns
        -------
        ToolPolicy
            Effective policy for the tool.
        """
        # Check for explicit policy
        if tool_name in self.policies:
            return self.policies[tool_name]

        # Check group policies
        for group in self.groups.values():
            if tool_name in group.tools:
                return group.policy

        # Return default policy
        return ToolPolicy(
            name=tool_name,
            permission=self.default_permission,
            sandbox_mode=self.default_sandbox_mode,
        )

    def get_permission(self, tool_name: str) -> ToolPermission:
        """Get effective permission for a tool.

        Parameters
        ----------
        tool_name : str
            Name of the tool.

        Returns
        -------
        ToolPermission
            Effective permission for the tool.
        """
        return self.get_tool_policy(tool_name).permission

    def get_sandbox_mode(self, tool_name: str) -> SandboxMode:
        """Get effective sandbox mode for a tool.

        Parameters
        ----------
        tool_name : str
            Name of the tool.

        Returns
        -------
        SandboxMode
            Effective sandbox mode for the tool.
        """
        return self.get_tool_policy(tool_name).sandbox_mode
