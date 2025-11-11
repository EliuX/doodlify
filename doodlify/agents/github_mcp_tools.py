"""
GitHub operations using MCP (Model Context Protocol) via Haystack integration.
Replaces direct API calls with MCP tools for better composability.
"""

from typing import Dict, Any, Optional, List
from haystack_integrations.tools.mcp import MCPTool, StdioServerInfo


class GitHubMCPTools:
    """Wrapper for GitHub operations via MCP protocol."""
    
    def __init__(self, github_token: str):
        """
        Initialize GitHub MCP tools.
        
        Args:
            github_token: GitHub Personal Access Token
        """
        self.github_token = github_token
        self._tools_cache = {}
    
    def _get_or_create_tool(self, tool_name: str) -> MCPTool:
        """Get or create an MCP tool for GitHub operations."""
        if tool_name not in self._tools_cache:
            # Use the official GitHub MCP server Docker image
            server_info = StdioServerInfo(
                command="docker",
                args=[
                    "run",
                    "--rm",
                    "-i",
                    "-e",
                    "GITHUB_PERSONAL_ACCESS_TOKEN",
                    "-e",
                    "GITHUB_DYNAMIC_TOOLSETS",
                    "ghcr.io/github/github-mcp-server"
                ],
                env={
                    "GITHUB_PERSONAL_ACCESS_TOKEN": self.github_token,
                    "GITHUB_DYNAMIC_TOOLSETS": "true"
                }
            )
            self._tools_cache[tool_name] = MCPTool(
                name=tool_name,
                server_info=server_info
            )
        return self._tools_cache[tool_name]
    
    def create_branch(self, owner: str, repo: str, branch: str, from_branch: str = "main") -> Dict[str, Any]:
        """
        Create a new branch in a GitHub repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            branch: New branch name
            from_branch: Source branch
        
        Returns:
            Result dictionary
        """
        tool = self._get_or_create_tool("create_branch")
        return tool.invoke(
            owner=owner,
            repo=repo,
            branch=branch,
            from_branch=from_branch
        )
    
    def push_files(
        self,
        owner: str,
        repo: str,
        branch: str,
        files: List[Dict[str, str]],
        message: str
    ) -> Dict[str, Any]:
        """
        Push multiple files to a GitHub repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name
            files: List of file dicts with 'path' and 'content'
            message: Commit message
        
        Returns:
            Result dictionary
        """
        tool = self._get_or_create_tool("push_files")
        return tool.invoke(
            owner=owner,
            repo=repo,
            branch=branch,
            files=files,
            message=message
        )
    
    def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str,
        body: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a pull request.
        
        Args:
            owner: Repository owner
            repo: Repository name
            title: PR title
            head: Source branch
            base: Target branch
            body: Optional PR description
        
        Returns:
            Result dictionary with PR URL
        """
        tool = self._get_or_create_tool("create_pull_request")
        return tool.invoke(
            owner=owner,
            repo=repo,
            title=title,
            head=head,
            base=base,
            body=body or ""
        )
    
    def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a GitHub issue.
        
        Args:
            owner: Repository owner
            repo: Repository name
            title: Issue title
            body: Issue body
            labels: Optional labels
        
        Returns:
            Result dictionary with issue URL and number
        """
        tool = self._get_or_create_tool("create_issue")
        return tool.invoke(
            owner=owner,
            repo=repo,
            title=title,
            body=body or "",
            labels=labels or []
        )
    
    def search_issues(
        self,
        owner: str,
        repo: str,
        query: str,
        state: str = "all"
    ) -> Dict[str, Any]:
        """
        Search for issues in a repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            query: Search query
            state: Issue state (open, closed, all)
        
        Returns:
            Result dictionary with matching issues
        """
        tool = self._get_or_create_tool("search_issues")
        return tool.invoke(
            owner=owner,
            repo=repo,
            q=f"{query} repo:{owner}/{repo}",
            state=state
        )
    
    def get_file_contents(
        self,
        owner: str,
        repo: str,
        path: str,
        branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get file contents from a GitHub repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            path: File path
            branch: Optional branch name
        
        Returns:
            Result dictionary with file content
        """
        tool = self._get_or_create_tool("get_file_contents")
        return tool.invoke(
            owner=owner,
            repo=repo,
            path=path,
            branch=branch or "main"
        )
