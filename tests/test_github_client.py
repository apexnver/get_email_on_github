"""
Unit tests for GitHub API client.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path
import requests

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from github_client import GitHubClient


class TestGitHubClient(unittest.TestCase):
    """Test GitHubClient class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = GitHubClient(token="test_token", rate_limit=60)
    
    @patch('github_client.requests.Session')
    def test_search_users(self, mock_session_class):
        """Test user search functionality."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "items": [
                {"login": "user1"},
                {"login": "user2"}
            ]
        }
        mock_response.headers = {
            "X-RateLimit-Remaining": "100",
            "X-RateLimit-Reset": "1234567890"
        }
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        
        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        client = GitHubClient(token="test_token")
        client.session = mock_session
        
        users = client.search_users("location:San Francisco", max_results=10)
        self.assertEqual(len(users), 2)
        self.assertIn("user1", users)
        self.assertIn("user2", users)
    
    @patch('github_client.requests.Session')
    def test_get_user(self, mock_session_class):
        """Test get user profile."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "login": "testuser",
            "email": "test@example.com",
            "bio": "Developer"
        }
        mock_response.headers = {
            "X-RateLimit-Remaining": "100",
            "X-RateLimit-Reset": "1234567890"
        }
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        
        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        client = GitHubClient(token="test_token")
        client.session = mock_session
        
        user = client.get_user("testuser")
        self.assertEqual(user["login"], "testuser")
        self.assertEqual(user["email"], "test@example.com")
    
    @patch('github_client.requests.Session')
    def test_rate_limit_handling(self, mock_session_class):
        """Test rate limit handling."""
        # First response: rate limit exceeded
        rate_limit_response = Mock()
        rate_limit_response.status_code = 403
        rate_limit_response.headers = {
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(__import__('time').time()) + 60)
        }
        
        # Second response: success
        success_response = Mock()
        success_response.json.return_value = {"login": "testuser"}
        success_response.headers = {
            "X-RateLimit-Remaining": "100",
            "X-RateLimit-Reset": "1234567890"
        }
        success_response.status_code = 200
        success_response.raise_for_status = Mock()
        
        mock_session = Mock()
        mock_session.request.side_effect = [rate_limit_response, success_response]
        mock_session_class.return_value = mock_session
        
        client = GitHubClient(token="test_token")
        client.session = mock_session
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            user = client.get_user("testuser")
            self.assertIsNotNone(user)
    
    @patch('github_client.requests.Session')
    def test_pagination(self, mock_session_class):
        """Test pagination handling."""
        # First page
        page1_response = Mock()
        page1_response.json.return_value = {
            "items": [{"login": f"user{i}"} for i in range(100)]
        }
        page1_response.headers = {
            "X-RateLimit-Remaining": "100",
            "X-RateLimit-Reset": "1234567890"
        }
        page1_response.status_code = 200
        page1_response.raise_for_status = Mock()
        
        # Second page (empty)
        page2_response = Mock()
        page2_response.json.return_value = {"items": []}
        page2_response.headers = {
            "X-RateLimit-Remaining": "99",
            "X-RateLimit-Reset": "1234567890"
        }
        page2_response.status_code = 200
        page2_response.raise_for_status = Mock()
        
        mock_session = Mock()
        mock_session.request.side_effect = [page1_response, page2_response]
        mock_session_class.return_value = mock_session
        
        client = GitHubClient(token="test_token")
        client.session = mock_session
        
        users = client.search_users("type:user", max_results=150)
        self.assertEqual(len(users), 100)


if __name__ == "__main__":
    unittest.main()

