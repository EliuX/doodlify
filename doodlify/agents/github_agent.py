"""
GitHub agent using direct REST API calls.
"""

import requests
from typing import List, Dict, Any, Optional


class GitHubAgent:
    """GitHub operations agent using direct REST API calls."""

    def __init__(self, github_token: str, openai_api_key: str):
        self.github_token = github_token
        self.openai_api_key = openai_api_key
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

    def search_issues(self, owner: str, repo: str, query: str, labels: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search for issues in a repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            query: Search query
            labels: Optional list of labels to filter by
            
        Returns:
            List of matching issues
        """
        # Build search query
        q_parts = [f"repo:{owner}/{repo}", "is:issue", query]
        if labels:
            for label in labels:
                q_parts.append(f"label:{label}")
        
        search_query = " ".join(q_parts)
        url = f"{self.base_url}/search/issues"
        params = {"q": search_query, "per_page": 100}
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json().get("items", [])
        except Exception as e:
            print(f"Warning: GitHub search failed: {e}")
            return []

    def create_issue(self, owner: str, repo: str, title: str, body: str, labels: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """Create a new issue.
        
        Args:
            owner: Repository owner
            repo: Repository name
            title: Issue title
            body: Issue body
            labels: Optional list of labels
            
        Returns:
            Created issue data or None on failure
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        payload = {
            "title": title,
            "body": body,
            "labels": labels or []
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Warning: Failed to create issue: {e}")
            return None

    def create_or_find_issue(self, owner: str, repo: str, title: str, body: str, labels: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """Create an issue only if it doesn't already exist (dedupe by doodlify-proposal label).
        
        Args:
            owner: Repository owner
            repo: Repository name
            title: Issue title
            body: Issue body
            labels: Optional list of labels (doodlify-proposal will be added automatically)
            
        Returns:
            Existing or newly created issue data, or None on failure
        """
        # Ensure doodlify-proposal label is present
        labels = labels or []
        if "doodlify-proposal" not in labels:
            labels.append("doodlify-proposal")
        
        # Search for existing issues with this label and similar title
        existing = self.search_issues(owner, repo, f"{title}", labels=["doodlify-proposal"])
        
        # Check if any existing issue has the exact title
        for issue in existing:
            if issue.get("title", "").strip() == title.strip():
                print(f"  ℹ️  Issue already exists: #{issue['number']} - {title}")
                return issue
        
        # Create new issue
        print(f"  ✓ Creating issue: {title}")
        return self.create_issue(owner, repo, title, body, labels)

    def run(self, messages: List) -> Dict[str, Any]:
        """Compatibility method for orchestrator (not used for direct API calls)."""
        return {"messages": []}
