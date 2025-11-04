"""
GitHub API Client with rate limiting and error handling.
"""

import time
import requests
from typing import List, Optional, Dict, Any
from datetime import datetime
from urllib.parse import quote


class GitHubClient:
    """Client for interacting with GitHub REST API."""
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, token: Optional[str] = None, rate_limit: int = 30):
        """
        Initialize GitHub client.
        
        Args:
            token: GitHub Personal Access Token (optional but recommended)
            rate_limit: Maximum requests per minute
        """
        self.token = token
        self.rate_limit = rate_limit
        self.session = requests.Session()
        
        if token:
            self.session.headers.update({
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            })
        else:
            self.session.headers.update({
                "Accept": "application/vnd.github.v3+json"
            })
        
        self.last_request_time = 0.0
        self.min_request_interval = 60.0 / rate_limit
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Make a request to GitHub API with rate limiting and retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative to BASE_URL)
            **kwargs: Additional arguments for requests
            
        Returns:
            Response JSON or None if error
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        # Rate limiting
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            sleep_time = self.min_request_interval - elapsed
            time.sleep(sleep_time)
        
        max_retries = 3
        retry_count = 0
        base_delay = 1.0
        
        while retry_count < max_retries:
            try:
                self.last_request_time = time.time()
                response = self.session.request(method, url, **kwargs)
                
                # Check rate limit headers
                remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
                reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
                
                if response.status_code == 403 and remaining == 0:
                    # Rate limit exceeded
                    wait_time = max(reset_time - int(time.time()), 1)
                    print(f"  Rate limit exceeded. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                
                if response.status_code == 429:
                    # Secondary rate limit
                    retry_after = int(response.headers.get("Retry-After", 60))
                    print(f"  Secondary rate limit hit. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                retry_count += 1
                if retry_count >= max_retries:
                    print(f"  Request failed after {max_retries} retries: {e}")
                    return None
                
                # Exponential backoff with jitter
                delay = base_delay * (2 ** retry_count) + (time.time() % 1)
                print(f"  Request failed, retrying in {delay:.2f}s... ({retry_count}/{max_retries})")
                time.sleep(delay)
        
        return None
    
    def search_users(self, query: str, max_results: int = 100) -> List[str]:
        """
        Search for GitHub users.
        
        Args:
            query: Search query string
            max_results: Maximum number of users to return
            
        Returns:
            List of usernames
        """
        users = []
        page = 1
        per_page = min(100, max_results)
        
        while len(users) < max_results:
            encoded_query = quote(query, safe="")
            endpoint = f"/search/users?q={encoded_query}&page={page}&per_page={per_page}"
            data = self._make_request("GET", endpoint)
            
            if not data:
                # If data is None, the request failed - break to avoid infinite loop
                print(f"  ⚠ No data returned from GitHub API for query: {query}")
                break
            
            # Check for API errors
            if "items" not in data:
                # Check if there's an error message
                if "message" in data:
                    print(f"  ⚠ GitHub API error: {data.get('message')}")
                else:
                    print(f"  ⚠ Unexpected API response format (no 'items' key)")
                break
            
            items = data.get("items", [])
            if not items:
                break
            
            for item in items:
                login = item.get("login")
                if login:
                    users.append(login)
                if len(users) >= max_results:
                    break
            
            # Check if there are more pages
            if len(items) < per_page:
                break
            
            page += 1
        
        return users[:max_results]
    
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get user profile information.
        
        Args:
            username: GitHub username
            
        Returns:
            User profile data or None
        """
        return self._make_request("GET", f"/users/{username}")
    
    def get_user_repos(self, username: str, max_repos: int = 100) -> List[Dict[str, Any]]:
        """
        Get user's repositories.
        
        Args:
            username: GitHub username
            max_repos: Maximum number of repos to fetch
            
        Returns:
            List of repository data
        """
        repos = []
        page = 1
        per_page = min(100, max_repos)
        
        while len(repos) < max_repos:
            endpoint = f"/users/{username}/repos?page={page}&per_page={per_page}&sort=updated"
            data = self._make_request("GET", endpoint)
            
            if not data:
                break
            
            if not isinstance(data, list):
                break
            
            repos.extend(data)
            
            if len(data) < per_page:
                break
            
            page += 1
        
        return repos[:max_repos]
    
    def get_repo_commits(self, owner: str, repo: str, max_commits: int = 100, author: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get repository commits.
        
        Args:
            owner: Repository owner
            repo: Repository name
            max_commits: Maximum number of commits to fetch
            author: Filter commits by author username (optional)
            
        Returns:
            List of commit data
        """
        commits = []
        page = 1
        per_page = min(100, max_commits)
        
        while len(commits) < max_commits:
            endpoint = f"/repos/{owner}/{repo}/commits?page={page}&per_page={per_page}"
            if author:
                endpoint += f"&author={author}"
            data = self._make_request("GET", endpoint)
            
            if not data:
                break
            
            if not isinstance(data, list):
                break
            
            commits.extend(data)
            
            if len(data) < per_page:
                break
            
            page += 1
        
        return commits[:max_commits]
    
    def get_repo_content(self, owner: str, repo: str, path: str = "README.md") -> Optional[str]:
        """
        Get repository file content.
        
        Args:
            owner: Repository owner
            repo: Repository name
            path: File path (default: README.md)
            
        Returns:
            File content as string or None
        """
        endpoint = f"/repos/{owner}/{repo}/contents/{path}"
        data = self._make_request("GET", endpoint)
        
        if not data or "content" not in data:
            return None
        
        import base64
        try:
            content = base64.b64decode(data["content"]).decode("utf-8")
            return content
        except Exception:
            return None

