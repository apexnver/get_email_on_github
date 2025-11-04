"""
Unit tests for email utilities.
"""

import unittest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from email_utils import (
    normalize_email,
    is_valid_email,
    extract_emails_from_text,
    EmailExtractor
)
from github_client import GitHubClient


class TestEmailNormalization(unittest.TestCase):
    """Test email normalization."""
    
    def test_normalize_basic(self):
        """Test basic email normalization."""
        self.assertEqual(normalize_email("test@example.com"), "test@example.com")
        self.assertEqual(normalize_email("  TEST@EXAMPLE.COM  "), "test@example.com")
    
    def test_normalize_with_angle_brackets(self):
        """Test normalization with angle brackets."""
        self.assertEqual(normalize_email("<test@example.com>"), "test@example.com")
    
    def test_normalize_with_mailto(self):
        """Test normalization with mailto: prefix."""
        self.assertEqual(normalize_email("mailto:test@example.com"), "test@example.com")
    
    def test_normalize_invalid(self):
        """Test normalization of invalid emails."""
        self.assertIsNone(normalize_email(""))
        self.assertIsNone(normalize_email("   "))


class TestEmailValidation(unittest.TestCase):
    """Test email validation."""
    
    def test_valid_emails(self):
        """Test valid email addresses."""
        self.assertTrue(is_valid_email("test@example.com"))
        self.assertTrue(is_valid_email("user.name@domain.co.uk"))
        self.assertTrue(is_valid_email("user+tag@example.org"))
    
    def test_invalid_emails(self):
        """Test invalid email addresses."""
        self.assertFalse(is_valid_email(""))
        self.assertFalse(is_valid_email("not-an-email"))
        self.assertFalse(is_valid_email("@example.com"))
        self.assertFalse(is_valid_email("user@"))
    
    def test_noreply_emails(self):
        """Test GitHub noreply email filtering."""
        self.assertFalse(is_valid_email("user@users.noreply.github.com"))
        self.assertFalse(is_valid_email("noreply@github.com"))
        self.assertFalse(is_valid_email("user@reply.github.com"))


class TestEmailExtraction(unittest.TestCase):
    """Test email extraction from text."""
    
    def test_extract_from_text(self):
        """Test extracting emails from text."""
        text = "Contact me at test@example.com or admin@site.org for more info."
        emails = extract_emails_from_text(text)
        self.assertIn("test@example.com", emails)
        self.assertIn("admin@site.org", emails)
    
    def test_extract_from_empty_text(self):
        """Test extraction from empty text."""
        self.assertEqual(extract_emails_from_text(""), set())
        self.assertEqual(extract_emails_from_text(None), set())
    
    def test_extract_filters_noreply(self):
        """Test that noreply emails are filtered."""
        text = "Email: test@example.com or noreply@users.noreply.github.com"
        emails = extract_emails_from_text(text)
        self.assertIn("test@example.com", emails)
        self.assertNotIn("noreply@users.noreply.github.com", emails)


class TestEmailExtractor(unittest.TestCase):
    """Test EmailExtractor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = Mock(spec=GitHubClient)
        self.extractor = EmailExtractor(self.client)
    
    def test_extract_from_profile(self):
        """Test extracting emails from user profile."""
        self.client.get_user.return_value = {
            "email": "user@example.com",
            "bio": "Developer from SF",
            "blog": ""
        }
        self.client.get_user_repos.return_value = []
        
        results = self.extractor.extract_emails_from_user("testuser")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["email"], "user@example.com")
        self.assertEqual(results[0]["source"], "profile")
    
    def test_extract_from_bio(self):
        """Test extracting emails from bio."""
        self.client.get_user.return_value = {
            "email": None,
            "bio": "Contact me at contact@example.com",
            "blog": ""
        }
        self.client.get_user_repos.return_value = []
        
        results = self.extractor.extract_emails_from_user("testuser")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["email"], "contact@example.com")
    
    def test_extract_from_commits(self):
        """Test extracting emails from commits."""
        self.client.get_user.return_value = {
            "email": None,
            "bio": "",
            "blog": ""
        }
        self.client.get_user_repos.return_value = [
            {"name": "test-repo", "owner": {"login": "testuser"}, "homepage": ""}
        ]
        self.client.get_repo_content.return_value = None
        self.client.get_repo_commits.return_value = [
            {
                "sha": "abc123",
                "commit": {
                    "author": {"email": "author@example.com"},
                    "committer": {"email": "committer@example.com"}
                }
            }
        ]
        
        results = self.extractor.extract_emails_from_user("testuser")
        self.assertGreaterEqual(len(results), 1)
        emails = [r["email"] for r in results]
        self.assertIn("author@example.com", emails)
    
    def test_deduplicate_emails(self):
        """Test that duplicate emails are not included."""
        self.client.get_user.return_value = {
            "email": "test@example.com",
            "bio": "Email: test@example.com",
            "blog": ""
        }
        self.client.get_user_repos.return_value = []
        
        results = self.extractor.extract_emails_from_user("testuser")
        emails = [r["email"] for r in results]
        self.assertEqual(emails.count("test@example.com"), 1)


if __name__ == "__main__":
    unittest.main()

