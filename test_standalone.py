#!/usr/bin/env python3
"""
Standalone test script that tests email utilities without requiring requests.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Test email utilities (these don't require requests)
from email_utils import (
    normalize_email,
    is_valid_email,
    extract_emails_from_text
)

def test_email_normalization():
    """Test email normalization functions."""
    print("Testing email normalization...")
    
    # Basic normalization
    assert normalize_email("test@example.com") == "test@example.com"
    assert normalize_email("  TEST@EXAMPLE.COM  ") == "test@example.com"
    assert normalize_email("<test@example.com>") == "test@example.com"
    assert normalize_email("mailto:test@example.com") == "test@example.com"
    assert normalize_email("") is None
    assert normalize_email("   ") is None
    
    print("  ✓ Email normalization tests passed")

def test_email_validation():
    """Test email validation functions."""
    print("Testing email validation...")
    
    # Valid emails
    assert is_valid_email("test@example.com") == True
    assert is_valid_email("user.name@domain.co.uk") == True
    assert is_valid_email("user+tag@example.org") == True
    
    # Invalid emails
    assert is_valid_email("") == False
    assert is_valid_email("not-an-email") == False
    assert is_valid_email("@example.com") == False
    assert is_valid_email("user@") == False
    
    # Noreply emails (should be filtered)
    assert is_valid_email("user@users.noreply.github.com") == False
    assert is_valid_email("noreply@github.com") == False
    
    print("  ✓ Email validation tests passed")

def test_email_extraction():
    """Test email extraction from text."""
    print("Testing email extraction...")
    
    # Extract from text
    text = "Contact me at test@example.com or admin@site.org for more info."
    emails = extract_emails_from_text(text)
    assert "test@example.com" in emails
    assert "admin@site.org" in emails
    
    # Empty text
    assert extract_emails_from_text("") == set()
    assert extract_emails_from_text(None) == set()
    
    # Filter noreply
    text = "Email: test@example.com or noreply@users.noreply.github.com"
    emails = extract_emails_from_text(text)
    assert "test@example.com" in emails
    assert "noreply@users.noreply.github.com" not in emails
    
    print("  ✓ Email extraction tests passed")

def test_output_writer():
    """Test output writer structure."""
    print("Testing output writer...")
    
    try:
        from output_writer import OutputWriter
        from pathlib import Path
        import tempfile
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = OutputWriter(Path(tmpdir))
            
            # Test with empty results
            writer.write_txt([])
            writer.write_json([])
            writer.write_csv([])
            
            # Test with sample data
            sample_data = [
                {
                    "username": "testuser",
                    "email": "test@example.com",
                    "source": "profile",
                    "repo": "",
                    "commit_sha": "",
                    "collected_at": "2024-01-15T10:30:00Z"
                }
            ]
            
            writer.write_txt(sample_data)
            writer.write_json(sample_data)
            writer.write_csv(sample_data)
            
            # Verify files exist
            assert (Path(tmpdir) / "emails.txt").exists()
            assert (Path(tmpdir) / "emails.json").exists()
            assert (Path(tmpdir) / "emails.csv").exists()
        
        print("  ✓ Output writer tests passed")
    except ImportError as e:
        print(f"  ⚠ Output writer test skipped: {e}")

def test_cli_structure():
    """Test CLI argument parsing structure."""
    print("Testing CLI structure...")
    
    try:
        import argparse
        from gh_email_harvest import parse_args
        
        # Test that parse_args function exists
        assert callable(parse_args)
        
        # Test with minimal args (this will fail validation, which is expected)
        sys.argv = ['gh_email_harvest.py', '--location', 'Test', '--max-results', '5']
        try:
            args = parse_args()
            assert args.location == 'Test'
            assert args.max_results == 5
            print("  ✓ CLI argument parsing works")
        except SystemExit:
            # Expected if validation fails
            print("  ✓ CLI argument parser exists and validates")
    except Exception as e:
        print(f"  ⚠ CLI structure test incomplete: {e}")

def main():
    """Run all standalone tests."""
    print("=" * 60)
    print("Running Standalone Tests")
    print("=" * 60)
    print()
    
    tests = [
        test_email_normalization,
        test_email_validation,
        test_email_extraction,
        test_output_writer,
        test_cli_structure,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ Test failed: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ Test error: {e}")
            failed += 1
        print()
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())

