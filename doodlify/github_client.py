"""
GitHub MCP client for repository operations using Haystack and MCP.
"""

import os
import shutil
from typing import Optional, List, Dict, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class GitHubMCPClient:
    """Client for GitHub operations using MCP protocol."""
    
    def __init__(self, github_token: str):
        self.github_token = github_token
        self.session: Optional[ClientSession] = None
        self._context_stack = None
        self._server_params = self._get_server_params()
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._context_stack = stdio_client(self._server_params)
        read_stream, write_stream = await self._context_stack.__aenter__()
        self.session = ClientSession(read_stream, write_stream)
        await self.session.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.__aexit__(exc_type, exc_val, exc_tb)
        if self._context_stack:
            await self._context_stack.__aexit__(exc_type, exc_val, exc_tb)
    
    def _get_server_params(self) -> StdioServerParameters:
        """Get MCP server parameters based on available tooling."""
        has_docker = shutil.which("docker") is not None
        
        github_mcp_server_env = {
            "GITHUB_PERSONAL_ACCESS_TOKEN": self.github_token,
            "GITHUB_DYNAMIC_TOOLSETS": "1"
        }
        
        if has_docker:
            return StdioServerParameters(
                command="docker",
                args=[
                    "run",
                    "--rm",
                    "-i",
                    "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
                    "-e", "GITHUB_DYNAMIC_TOOLSETS",
                    "ghcr.io/github/github-mcp-server"
                ],
                env=github_mcp_server_env,
            )
        else:
            return StdioServerParameters(
                command="npx",
                args=[
                    "-y",
                    "@modelcontextprotocol/server-github"
                ],
                env=github_mcp_server_env,
            )
    
    async def get_file_contents(self, owner: str, repo: str, path: str, branch: str = "main") -> str:
        """Get file contents from repository."""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        result = await self.session.call_tool(
            "mcp0_get_file_contents",
            {
                "owner": owner,
                "repo": repo,
                "path": path,
                "branch": branch
            }
        )
        return result
    
    async def list_repository_files(self, owner: str, repo: str, path: str = "", branch: str = "main") -> List[Dict[str, Any]]:
        """List files in a repository path."""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        result = await self.session.call_tool(
            "mcp0_get_file_contents",
            {
                "owner": owner,
                "repo": repo,
                "path": path,
                "branch": branch
            }
        )
        return result
    
    async def create_branch(self, owner: str, repo: str, branch: str, from_branch: str = "main") -> None:
        """Create a new branch in the repository."""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        await self.session.call_tool(
            "mcp0_create_branch",
            {
                "owner": owner,
                "repo": repo,
                "branch": branch,
                "from_branch": from_branch
            }
        )
    
    async def push_files(self, owner: str, repo: str, branch: str, files: List[Dict[str, str]], message: str) -> None:
        """Push multiple files to repository in a single commit."""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        await self.session.call_tool(
            "mcp0_push_files",
            {
                "owner": owner,
                "repo": repo,
                "branch": branch,
                "files": files,
                "message": message
            }
        )
    
    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str,
        draft: bool = False
    ) -> Dict[str, Any]:
        """Create a pull request."""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        result = await self.session.call_tool(
            "mcp0_create_pull_request",
            {
                "owner": owner,
                "repo": repo,
                "title": title,
                "body": body,
                "head": head,
                "base": base,
                "draft": draft
            }
        )
        return result
    
    async def get_default_branch(self, owner: str, repo: str) -> str:
        """Get the default branch of a repository."""
        # This would require additional MCP tool or API call
        # For now, return 'main' as default
        return "main"

    async def create_issue(self, owner: str, repo: str, title: str, body: str, labels: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create a new GitHub issue."""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        payload = {
            "owner": owner,
            "repo": repo,
            "title": title,
            "body": body,
        }
        if labels:
            payload["labels"] = labels
        result = await self.session.call_tool("mcp0_create_issue", payload)
        return result

    async def search_issues(self, owner: str, repo: str, query: str) -> Dict[str, Any]:
        """Search issues and PRs in a repository using GitHub search syntax."""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        q = f"repo:{owner}/{repo} {query} in:title"
        result = await self.session.call_tool("mcp0_search_issues", {"q": q, "per_page": 10, "page": 1})
        return result