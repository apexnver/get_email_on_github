#!/usr/bin/env python3
"""
GitHub Developer Contact Extractor
A CLI tool to extract publicly available email addresses from GitHub profiles.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

from github_client import GitHubClient
from email_utils import EmailExtractor, normalize_email, is_valid_email
from output_writer import OutputWriter


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Extract publicly available email addresses from GitHub profiles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --location "San Francisco" --languages "Python,JavaScript" --max-results 10
  %(prog)s --location "New York" --min-followers 100 --token YOUR_GITHUB_TOKEN --output ./results
  %(prog)s --dry-run --location "London" --max-results 5

Note: This tool only collects publicly visible emails. Many users hide their email addresses.
      GitHub's API and Acceptable Use policies must be followed.
        """
    )
    
    parser.add_argument(
        "--location",
        type=str,
        help="Location to search for developers (e.g., 'San Francisco', 'New York')"
    )
    
    parser.add_argument(
        "--languages",
        type=str,
        help="Comma-separated list of programming languages (e.g., 'Python,JavaScript,Java')"
    )
    
    parser.add_argument(
        "--min-followers",
        type=int,
        default=0,
        help="Minimum number of followers (default: 0)"
    )
    
    parser.add_argument(
        "--created",
        type=str,
        help="Filter by account creation date (e.g., '>=2020-01-01', '>2023-01-01', '<2024-01-01')"
    )
    
    parser.add_argument(
        "--repo",
        type=str,
        help="Filter by repository count (e.g., '>5', '>=10', '<20')"
    )
    
    parser.add_argument(
        "--max-results",
        type=int,
        default=100,
        help="Maximum number of users to process (default: 100)"
    )
    
    parser.add_argument(
        "--token",
        type=str,
        help="GitHub Personal Access Token (PAT) for authenticated requests. "
             "Can also be set via GITHUB_TOKEN environment variable or .env file."
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="./output",
        help="Output directory path (default: ./output)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without writing files"
    )
    
    parser.add_argument(
        "--rate",
        type=int,
        default=30,
        help="Maximum requests per minute (default: 30)"
    )
    
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Number of concurrent requests (default: 1)"
    )
    
    return parser.parse_args()


def build_search_query(args: argparse.Namespace) -> str:
    """Build GitHub search query from arguments."""
    query_parts = []
    
    if args.location:
        query_parts.append(f'location:"{args.location}"')
    
    if args.languages:
        langs = [lang.strip() for lang in args.languages.split(",")]
        # GitHub search: use language filter without parentheses for better compatibility
        if len(langs) == 1:
            # Single language - use directly
            query_parts.append(f"language:{langs[0]}")
        else:
            # Multiple languages - use OR with parentheses
            lang_query = " OR ".join([f'language:{lang}' for lang in langs])
            query_parts.append(f"({lang_query})")
    
    if args.min_followers > 0:
        query_parts.append(f"followers:>={args.min_followers}")
    
    if args.created:
        query_parts.append(f"created:{args.created}")
    
    if args.repo:
        query_parts.append(f"repos:{args.repo}")
    
    # Search for users
    query_parts.append("type:user")
    
    return " ".join(query_parts) if query_parts else "type:user"


def main():
    """Main entry point."""
    # Set UTF-8 encoding for Windows console
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            # Python < 3.7 or encoding not available
            pass
    
    # Load environment variables from .env file if available
    if DOTENV_AVAILABLE:
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    
    args = parse_args()
    
    # Validate arguments
    if not args.location and not args.languages:
        print("Error: At least one of --location or --languages must be provided.", file=sys.stderr)
        sys.exit(1)
    
    # Get token from command line argument, environment variable, or .env file
    token = args.token or os.environ.get("GITHUB_TOKEN")
    
    # Create output directory
    output_dir = Path(args.output)
    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"GitHub Email Harvester")
    print(f"{'='*50}")
    print(f"Search query: {build_search_query(args)}")
    print(f"Max results: {args.max_results}")
    print(f"Output directory: {output_dir}")
    print(f"Dry run: {args.dry_run}")
    print(f"Token: {'Set' if token else 'Not set (using unauthenticated requests)'}")
    print(f"{'='*50}\n")
    
    # Initialize components
    client = GitHubClient(token=token, rate_limit=args.rate)
    extractor = EmailExtractor(client)
    writer = OutputWriter(output_dir)
    
    # Collect emails
    all_results = []
    seen_emails: Set[str] = set()
    seen_username_email_pairs: Set[tuple] = set()  # Track (username, email) pairs to avoid duplicates
    
    try:
        # Search for users
        # If multiple languages, search each separately and combine results
        if args.languages:
            langs = [lang.strip() for lang in args.languages.split(",")]
            if len(langs) > 1:
                # Multiple languages: search each separately and combine
                all_users = set()
                for lang in langs:
                    # Create a temporary args object for this language
                    temp_args = argparse.Namespace(
                        location=args.location,
                        languages=lang,
                        min_followers=args.min_followers,
                        created=args.created,
                        repo=args.repo,
                        max_results=args.max_results,
                        token=args.token,
                        output=args.output,
                        dry_run=args.dry_run,
                        rate=args.rate,
                        concurrency=args.concurrency
                    )
                    search_query = build_search_query(temp_args)
                    lang_users = client.search_users(search_query, max_results=args.max_results)
                    all_users.update(lang_users)
                    # Rate limiting between language searches
                    if len(langs) > 1:
                        time.sleep(1.0)
                
                users = list(all_users)[:args.max_results]
                print(f"Found {len(users)} users (combined from {len(langs)} language searches)\n")
            else:
                # Single language - use normal search
                search_query = build_search_query(args)
                users = client.search_users(search_query, max_results=args.max_results)
                print(f"Found {len(users)} users to process\n")
        else:
            # No languages specified
            search_query = build_search_query(args)
            users = client.search_users(search_query, max_results=args.max_results)
            print(f"Found {len(users)} users to process\n")
        
        for idx, username in enumerate(users, 1):
            print(f"[{idx}/{len(users)}] Processing user: {username}")
            
            try:
                user_info = extractor.extract_emails_from_user(username)
                user_name = user_info.get("name", username)
                user_location = user_info.get("location", args.location or "")
                emails_list = user_info.get("emails", [])
                
                for email_data in emails_list:
                    email = email_data.get("email")
                    if email:
                        # Create unique key: (username, email) to avoid duplicates
                        username_email_key = (username.lower(), email.lower())
                        
                        # Only add if this (username, email) combination hasn't been seen
                        if username_email_key not in seen_username_email_pairs:
                            seen_username_email_pairs.add(username_email_key)
                            
                            # Also track email separately for statistics
                            if email.lower() not in seen_emails:
                                seen_emails.add(email.lower())
                            
                            email_data["username"] = username
                            email_data["name"] = user_name
                            email_data["location"] = user_location
                            email_data["category"] = user_location or "Unknown"
                            email_data["collected_at"] = datetime.utcnow().isoformat() + "Z"
                            all_results.append(email_data)
                            print(f"  ✓ Found email: {email} (name: {user_name}, source: {email_data.get('source')})")
                        # else: silently skip duplicate (username, email) pairs
                
            except Exception as e:
                print(f"  ✗ Error processing {username}: {e}")
                continue
            
            # Rate limiting
            if idx < len(users):
                time.sleep(60.0 / args.rate)
        
        # Write output files
        if not args.dry_run:
            print(f"\nWriting output files...")
            finding_date = datetime.utcnow().strftime("%Y-%m-%d")
            writer.write_txt(all_results, finding_date)
            writer.write_json(all_results, finding_date)
            writer.write_csv(all_results, finding_date)
            writer.write_by_category(all_results, finding_date)
            print(f"✓ Output files written to {output_dir}")
        else:
            print(f"\n[Dry run] Would write {len(all_results)} email entries")
        
        print(f"\n{'='*50}")
        print(f"Summary:")
        print(f"  Users processed: {len(users)}")
        print(f"  Unique emails found: {len(seen_emails)}")
        print(f"{'='*50}")
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

