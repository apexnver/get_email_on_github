"""
Email extraction and validation utilities.
"""

import re
from typing import List, Dict, Optional, Set, Any
from github_client import GitHubClient


# Pattern for email addresses
EMAIL_PATTERN = re.compile(
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
)

# GitHub noreply email patterns
NOREPLY_PATTERNS = [
    r'.*@users\.noreply\.github\.com',
    r'.*noreply@github\.com',
    r'.*@reply\.github\.com',
]


def normalize_email(email: str) -> Optional[str]:
    """
    Normalize email address.
    
    Args:
        email: Raw email address
        
    Returns:
        Normalized email or None if invalid
    """
    if not email:
        return None
    
    email = email.strip().lower()
    
    # Remove angle brackets
    email = email.strip("<>")
    
    # Remove common prefixes/suffixes
    email = email.replace("mailto:", "")
    
    return email if email else None


def is_valid_email(email: str) -> bool:
    """
    Check if email is valid and not a GitHub noreply address.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid and not noreply
    """
    if not email:
        return False
    
    email = normalize_email(email)
    if not email:
        return False
    
    # Check against noreply patterns
    for pattern in NOREPLY_PATTERNS:
        if re.match(pattern, email, re.IGNORECASE):
            return False
    
    # Basic email format validation
    if not EMAIL_PATTERN.match(email):
        return False
    
    # Additional validation
    parts = email.split("@")
    if len(parts) != 2:
        return False
    
    local, domain = parts
    if not local or not domain:
        return False
    
    if len(local) > 64 or len(domain) > 255:
        return False
    
    return True


def extract_emails_from_text(text: str) -> Set[str]:
    """
    Extract email addresses from text.
    
    Args:
        text: Text to search
        
    Returns:
        Set of valid email addresses
    """
    if not text:
        return set()
    
    emails = set()
    matches = EMAIL_PATTERN.findall(text)
    
    for match in matches:
        normalized = normalize_email(match)
        if normalized and is_valid_email(normalized):
            emails.add(normalized)
    
    return emails


class EmailExtractor:
    """Extract emails from GitHub user profiles and repositories."""
    
    def __init__(self, client: GitHubClient):
        """
        Initialize email extractor.
        
        Args:
            client: GitHub API client
        """
        self.client = client
    
    def extract_emails_from_user(self, username: str) -> Dict[str, Any]:
        """
        Extract all emails and user info from various sources.
        
        Args:
            username: GitHub username
            
        Returns:
            Dictionary with keys: emails (list), name, location, user_data
        """
        results = []
        seen_emails: Set[str] = set()
        user_name = None
        user_location = None
        
        # 1. Extract from user profile
        user_data = self.client.get_user(username)
        if user_data:
            # Extract user name
            user_name = user_data.get("name") or user_data.get("login")
            
            # Extract location
            user_location = user_data.get("location", "")
            # Email field (if public)
            if user_data.get("email") and is_valid_email(user_data["email"]):
                email = normalize_email(user_data["email"])
                if email and email not in seen_emails:
                    seen_emails.add(email)
                    results.append({
                        "email": email,
                        "source": "profile"
                    })
            
            # Bio field
            bio = user_data.get("bio", "")
            if bio:
                emails = extract_emails_from_text(bio)
                for email in emails:
                    if email not in seen_emails:
                        seen_emails.add(email)
                        results.append({
                            "email": email,
                            "source": "profile"
                        })
            
            # Blog/homepage field
            blog = user_data.get("blog", "")
            if blog:
                emails = extract_emails_from_text(blog)
                for email in emails:
                    if email not in seen_emails:
                        seen_emails.add(email)
                        results.append({
                            "email": email,
                            "source": "homepage"
                        })
        
        # 2. Extract from repositories (optimized: reduced repos and commits)
        repos = self.client.get_user_repos(username, max_repos=10)  # Reduced from 50 to 10
        
        for repo in repos:
            repo_name = repo.get("name", "")
            repo_owner = repo.get("owner", {}).get("login", username)
            
            # Only process repositories owned by the target user
            # (skip forks or repos where user is just a collaborator)
            if repo_owner.lower() != username.lower():
                continue
            
            # Homepage field (quick check)
            homepage = repo.get("homepage", "")
            if homepage:
                emails = extract_emails_from_text(homepage)
                for email in emails:
                    if email not in seen_emails:
                        seen_emails.add(email)
                        results.append({
                            "email": email,
                            "source": "homepage",
                            "repo": f"{repo_owner}/{repo_name}"
                        })
            
            # README content - skip entirely to avoid extracting other contributors' emails
            # Most users have their email in profile or commits, which are more reliable
            # readme_content = self.client.get_repo_content(repo_owner, repo_name, "README.md")
            # Skipped to avoid extracting emails from other contributors mentioned in README
            
            # Commits - use author filter to only fetch commits by the target user
            # This significantly reduces API calls and processing time
            commits = self.client.get_repo_commits(repo_owner, repo_name, max_commits=10, author=username)  # Reduced from 30 to 10
            
            for commit in commits:
                commit_data = commit.get("commit", {})
                author = commit_data.get("author", {})
                committer = commit_data.get("committer", {})
                
                # Since we filtered by author, we can trust these commits are from the target user
                # But double-check to be safe
                commit_author = commit.get("author")
                commit_committer = commit.get("committer")
                
                author_login = commit_author.get("login") if commit_author and isinstance(commit_author, dict) else None
                committer_login = commit_committer.get("login") if commit_committer and isinstance(commit_committer, dict) else None
                
                # Author email - verify it's the target user
                if author_login and isinstance(author_login, str) and author_login.lower() == username.lower():
                    author_email = author.get("email", "")
                    if author_email and is_valid_email(author_email):
                        email = normalize_email(author_email)
                        if email and email not in seen_emails:
                            seen_emails.add(email)
                            results.append({
                                "email": email,
                                "source": "commit",
                                "repo": f"{repo_owner}/{repo_name}",
                                "commit_sha": commit.get("sha", "")[:8]
                            })
                            # Early exit if we found a valid email from commit
                            if len(results) >= 5:  # Stop after finding 5 emails per user
                                break
                
                # Committer email - verify it's the target user
                if committer_login and isinstance(committer_login, str) and committer_login.lower() == username.lower():
                    committer_email = committer.get("email", "")
                    if committer_email and is_valid_email(committer_email):
                        email = normalize_email(committer_email)
                        if email and email not in seen_emails:
                            seen_emails.add(email)
                            results.append({
                                "email": email,
                                "source": "commit",
                                "repo": f"{repo_owner}/{repo_name}",
                                "commit_sha": commit.get("sha", "")[:8]
                            })
                            # Early exit if we found a valid email from commit
                            if len(results) >= 5:  # Stop after finding 5 emails per user
                                break
            
            # Early exit if we've found enough emails for this user
            if len(results) >= 5:
                break
        
        return {
            "emails": results,
            "name": user_name or username,
            "location": user_location or "",
            "user_data": user_data or {}
        }

