"""
GitHub agent using Haystack AI Agent with MCP tools.
"""

import shutil
from typing import List, Dict, Any

from haystack.components.agents import Agent
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.dataclasses import ChatMessage
from haystack.utils import Secret
from haystack_integrations.tools.mcp import MCPTool, StdioServerInfo, MCPToolset


class SafeMCPTool(MCPTool):
    """MCP Tool wrapper that prevents deepcopy issues in Haystack Agent."""

    def __deepcopy__(self, memo):
        return self  # Do not copy, reuse the instance


class GitHubAgent:
    """GitHub operations agent using Haystack Agent with MCP tools."""

    def __init__(self, github_token: str, openai_api_key: str):
        self.github_token = github_token
        self.openai_api_key = openai_api_key
        self.server_info = self._get_server_info()
        self.tools = self._create_toolset()
        self.agent = self._create_agent()

    def _get_server_info(self) -> StdioServerInfo:
        """Get MCP server info based on available tooling."""
        has_docker = shutil.which("docker") is not None

        github_mcp_server_env = {
            "GITHUB_PERSONAL_ACCESS_TOKEN": self.github_token,
            "GITHUB_DYNAMIC_TOOLSETS": "1"
        }

        if has_docker:
            return StdioServerInfo(
                command="docker",
                args=[
                    "run",
                    "-i",
                    "--rm",
                    "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
                    "-e", "GITHUB_TOOLSETS",
                    "mcp/github"
                ],
                env=github_mcp_server_env,
            )
        else:
            return StdioServerInfo(
                command="npx",
                args=[
                    "-y",
                    "@modelcontextprotocol/server-github"
                ],
                env=github_mcp_server_env,
            )

    def _create_toolset(self):
        return MCPToolset(
            server_info=self.server_info,
            tool_names=[
                "get_file_contents",
                "create_issue",
                "search_issues",
                "list_issues",
                "create_branch",
                "push_files",
                "create_pull_request"
            ]  # Omit to load all tools, but may overwhelm LLM if many
        )

    def _create_agent(self) -> Agent:
        """Create Haystack agent with MCP tools."""
        agent = Agent(
            chat_generator=OpenAIChatGenerator(api_key=Secret.from_token(self.openai_api_key)),
            system_prompt="""
            You can operate GitHub repositories: read files, create/search issues, create branches/PRs. 
            Queries to "search_issues" must include 'is:issue state:open' as prefix.
            Be concise.
            """,
            tools=self.tools,
        )
        agent.warm_up()
        return agent

    def run(self, messages: List[ChatMessage]) -> Dict[str, Any]:
        """Run the agent with a list of messages."""
        return self.agent.run(messages=messages)
