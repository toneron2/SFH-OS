"""MCP Protocol - Model Context Protocol implementation for tool binding."""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result from a tool execution."""

    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    artifacts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "artifacts": self.artifacts,
        }


@dataclass
class ToolParameter:
    """A parameter for a tool."""

    name: str
    type: str  # "string", "number", "boolean", "object", "array"
    description: str
    required: bool = True
    enum: list[str] | None = None
    default: Any = None


@dataclass
class Tool:
    """A tool that can be executed via MCP."""

    name: str
    description: str
    parameters: list[ToolParameter]
    handler: Callable[..., Coroutine[Any, Any, ToolResult]]
    allowed_agents: list[str] = field(default_factory=list)  # Empty = all agents

    def to_claude_schema(self) -> dict[str, Any]:
        """Convert to Claude API tool schema."""
        properties = {}
        required = []

        for param in self.parameters:
            prop: dict[str, Any] = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }


class MCPProtocol:
    """Model Context Protocol implementation.

    Manages tool registration, permissions, and execution.
    """

    def __init__(self):
        self._tools: dict[str, Tool] = {}
        self._execution_log: list[dict[str, Any]] = []

    def register_tool(self, tool: Tool) -> None:
        """Register a tool with the protocol."""
        if tool.name in self._tools:
            logger.warning(f"Tool {tool.name} already registered, overwriting")
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def register_tools(self, tools: list[Tool]) -> None:
        """Register multiple tools."""
        for tool in tools:
            self.register_tool(tool)

    def get_tool(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def get_tools(self, agent_designation: str | None = None) -> list[Tool]:
        """Get all tools, optionally filtered by agent access."""
        if agent_designation is None:
            return list(self._tools.values())

        return [
            tool for tool in self._tools.values()
            if not tool.allowed_agents or agent_designation in tool.allowed_agents
        ]

    def can_execute(self, tool_name: str, agent_designation: str) -> bool:
        """Check if an agent can execute a tool."""
        tool = self._tools.get(tool_name)
        if not tool:
            return False
        if not tool.allowed_agents:
            return True
        return agent_designation in tool.allowed_agents

    async def execute_tool(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        agent_designation: str,
    ) -> ToolResult | None:
        """Execute a tool with the given parameters."""
        tool = self._tools.get(tool_name)

        if not tool:
            logger.error(f"Tool not found: {tool_name}")
            return ToolResult(success=False, error=f"Tool not found: {tool_name}")

        if not self.can_execute(tool_name, agent_designation):
            logger.error(f"Agent {agent_designation} cannot execute tool {tool_name}")
            return ToolResult(
                success=False,
                error=f"Permission denied: {agent_designation} cannot execute {tool_name}",
            )

        try:
            logger.info(f"Executing tool {tool_name} for {agent_designation}")
            result = await tool.handler(**parameters)

            self._execution_log.append({
                "tool": tool_name,
                "agent": agent_designation,
                "parameters": parameters,
                "success": result.success,
            })

            return result

        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return ToolResult(success=False, error=str(e))

    def get_execution_log(self) -> list[dict[str, Any]]:
        """Get the tool execution log."""
        return self._execution_log.copy()

    def clear_log(self) -> None:
        """Clear the execution log."""
        self._execution_log.clear()
