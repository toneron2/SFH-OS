"""Base Agent - Foundation for all SFH-OS sub-agents."""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

import anthropic

from sfh_os.config import config
from sfh_os.manifests import ConstraintManifest, RequestManifest, ResultManifest
from sfh_os.manifests.result import ResultStatus
from sfh_os.mcp import MCPProtocol, Tool, ToolResult

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all SFH-OS agents.

    Each agent has:
    - A designation (e.g., AG-GEN, AG-SIM)
    - A specialized role and system prompt
    - Access to specific tools via MCP
    - Methods for processing manifests
    """

    designation: str = "AG-BASE"
    role: str = "Base Agent"
    description: str = "Abstract base agent"

    def __init__(self, mcp: MCPProtocol | None = None):
        self.mcp = mcp or MCPProtocol()
        self.client = anthropic.Anthropic(api_key=config.llm.api_key)
        self.conversation_history: list[dict[str, Any]] = []
        self._register_tools()

    @abstractmethod
    def _register_tools(self) -> None:
        """Register agent-specific tools with MCP."""
        pass

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Get the system prompt for this agent."""
        pass

    @property
    def tools_schema(self) -> list[dict[str, Any]]:
        """Get tool schemas for Claude API."""
        return [tool.to_claude_schema() for tool in self.mcp.get_tools(self.designation)]

    async def process_request(
        self,
        request: RequestManifest,
        constraints: ConstraintManifest,
    ) -> ResultManifest:
        """Process a request manifest and return a result manifest.

        This is the main entry point for agent execution.
        """
        logger.info(f"[{self.designation}] Processing request {request.id}")

        result = ResultManifest(
            request_id=request.id,
            source_agent=self.designation,
            iteration=request.iteration,
        )

        try:
            # Build the prompt from manifests
            prompt = self._build_prompt(request, constraints)

            # Execute with Claude
            response = await self._execute(prompt)

            # Parse and validate response
            result = await self._process_response(response, result, constraints)
            result.mark_complete(ResultStatus.SUCCESS)

        except Exception as e:
            logger.error(f"[{self.designation}] Error processing request: {e}")
            result.errors.append(str(e))
            result.mark_complete(ResultStatus.FAILED)

        return result

    def _build_prompt(
        self,
        request: RequestManifest,
        constraints: ConstraintManifest,
    ) -> str:
        """Build a prompt from request and constraint manifests."""
        return f"""{request.to_prompt()}

{constraints.to_prompt()}

Please analyze the request and constraints, then use the available tools to accomplish the goal.
Provide your analysis and reasoning, then execute the appropriate tools.
"""

    async def _execute(self, prompt: str) -> dict[str, Any]:
        """Execute a prompt with Claude, handling tool use."""
        messages = [{"role": "user", "content": prompt}]

        # Agentic loop - continue until no more tool calls
        while True:
            response = self.client.messages.create(
                model=config.llm.model,
                max_tokens=config.llm.max_tokens,
                system=self._get_system_prompt(),
                tools=self.tools_schema if self.tools_schema else None,
                messages=messages,
            )

            # Check for tool use
            tool_uses = [block for block in response.content if block.type == "tool_use"]

            if not tool_uses:
                # No more tool calls, extract final response
                text_blocks = [block.text for block in response.content if hasattr(block, "text")]
                return {
                    "text": "\n".join(text_blocks),
                    "stop_reason": response.stop_reason,
                }

            # Process tool calls
            tool_results = []
            for tool_use in tool_uses:
                result = await self._execute_tool(tool_use.name, tool_use.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": json.dumps(result.to_dict()) if result else "Tool not found",
                })

            # Add assistant response and tool results to conversation
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        return {"text": "", "stop_reason": "error"}

    async def _execute_tool(self, tool_name: str, tool_input: dict[str, Any]) -> ToolResult | None:
        """Execute a tool via MCP."""
        logger.debug(f"[{self.designation}] Executing tool: {tool_name}")
        return await self.mcp.execute_tool(tool_name, tool_input, self.designation)

    @abstractmethod
    async def _process_response(
        self,
        response: dict[str, Any],
        result: ResultManifest,
        constraints: ConstraintManifest,
    ) -> ResultManifest:
        """Process Claude's response and populate the result manifest."""
        pass

    def reset(self) -> None:
        """Reset agent state."""
        self.conversation_history.clear()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(designation={self.designation})"
