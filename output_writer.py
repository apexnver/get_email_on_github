"""
Output writers for different file formats.
"""

import csv
import json
from pathlib import Path
from typing import List, Dict
from collections import defaultdict


class OutputWriter:
    """Write extracted emails to various output formats."""
    
    def __init__(self, output_dir: Path):
        """
        Initialize output writer.
        
        Args:
            output_dir: Directory to write output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def write_txt(self, results: List[Dict], finding_date: str = "") -> None:
        """
        Write emails to plain text file in date/location grouped format.
        Appends to existing file if it exists.
        
        Args:
            results: List of email data dictionaries
            finding_date: Date when emails were found
        """
        output_file = self.output_dir / "emails.txt"
        
        # Read existing content to preserve structure and extract emails
        existing_emails_set = set()
        file_has_new_format = False
        if output_file.exists():
            with open(output_file, "r", encoding="utf-8") as f:
                content = f.read()
                # Check if file uses new format (has "Today -" or date pattern)
                if "Today -" in content or (len(content.splitlines()) > 0 and any("/" in line and ":" in line and "Location:" in content for line in content.splitlines()[:5])):
                    file_has_new_format = True
                
                # Extract existing emails
                for line in content.splitlines():
                    line = line.strip()
                    # Skip date headers, location headers, and empty lines
                    if (line and 
                        not line.startswith("Location:") and 
                        not line.startswith("Today") and
                        not line.startswith("#") and
                        not ("/" in line and ":" in line and len(line.split()) <= 2) and  # Skip date lines
                        "@" in line and "." in line.split("@")[1] if "@" in line else False):
                        existing_emails_set.add(line.lower())
        
        # Group new results by location and date
        from datetime import datetime
        
        # Get current date/time (Windows-compatible format)
        now = datetime.now()
        # Format: "11/3 10:12:30" or "11/4 23:31:10"
        # Remove leading zeros: use format without leading zeros
        month = now.month
        day = now.day
        date_str = f"{month}/{day} {now.strftime('%H:%M:%S')}"
        
        # Group by location
        location_groups = defaultdict(list)
        new_emails = []
        
        for result in results:
            email = result.get("email", "")
            if email:
                email_lower = email.lower()
                if email_lower not in existing_emails_set:
                    existing_emails_set.add(email_lower)
                    new_emails.append(email)
                    location = result.get("location", "Unknown")
                    if not location or location.strip() == "":
                        location = result.get("category", "Unknown")
                    location_groups[location].append(email)
        
        # Write to file
        if new_emails:
            # If file exists and has old format, we need to convert it
            if output_file.exists() and not file_has_new_format:
                # Convert old format to new format
                # Read all existing emails and rewrite in new format
                existing_emails_list = []
                if output_file.exists():
                    with open(output_file, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "@" in line:
                                existing_emails_list.append(line)
                
                # Write in new format with all emails
                with open(output_file, "w", encoding="utf-8") as f:
                    # Write existing emails in a generic location (if we don't have location info)
                    if existing_emails_list:
                        f.write(f"11/3 10:12:30\n\n")
                        f.write(f"Location: Unknown\n")
                        for email in sorted(existing_emails_list, key=str.lower):
                            f.write(f"{email}\n")
                        f.write("\n")
            
            # Append new entries
            with open(output_file, "a", encoding="utf-8") as f:
                # Write date header with "Today -" prefix
                f.write(f"Today - {date_str}\n\n")
                
                # Write emails grouped by location
                for location, emails in sorted(location_groups.items()):
                    f.write(f"Location: {location}\n")
                    for email in sorted(emails, key=str.lower):
                        f.write(f"{email}\n")
                    f.write("\n")
    
    def write_json(self, results: List[Dict], finding_date: str = "") -> None:
        """
        Write emails to JSON file with metadata.
        Appends to existing file if it exists.
        
        Args:
            results: List of email data dictionaries
            finding_date: Date when emails were found
        """
        output_file = self.output_dir / "emails.json"
        
        # Read existing emails if file exists
        existing_results = []
        if output_file.exists():
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                    if isinstance(existing_data, dict) and "emails" in existing_data:
                        existing_results = existing_data["emails"]
                    elif isinstance(existing_data, list):
                        existing_results = existing_data
            except (json.JSONDecodeError, KeyError):
                existing_results = []
        
        # Merge existing and new results
        all_results = existing_results + results
        
        # Deduplicate by (username, email) pairs (case-insensitive)
        seen_pairs = set()
        unique_results = []
        for result in all_results:
            username = result.get("username", "").lower()
            email = result.get("email", "").lower()
            pair_key = (username, email)
            if pair_key not in seen_pairs:
                seen_pairs.add(pair_key)
                unique_results.append(result)
        
        # Count new emails
        existing_pairs = set()
        for result in existing_results:
            username = result.get("username", "").lower()
            email = result.get("email", "").lower()
            existing_pairs.add((username, email))
        
        new_count = 0
        for result in results:
            username = result.get("username", "").lower()
            email = result.get("email", "").lower()
            if (username, email) not in existing_pairs:
                new_count += 1
        
        # Create output with metadata
        output_data = {
            "finding_date": finding_date,
            "total_emails": len(unique_results),
            "unique_emails": len(set(r.get("email", "").lower() for r in unique_results if r.get("email"))),
            "new_emails_added": new_count,
            "emails": unique_results
        }
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    def write_csv(self, results: List[Dict], finding_date: str = "") -> None:
        """
        Write emails to CSV file with metadata.
        Appends to existing file if it exists.
        
        Args:
            results: List of email data dictionaries
            finding_date: Date when emails were found
        """
        output_file = self.output_dir / "emails.csv"
        
        fieldnames = ["username", "name", "email", "location", "category", "source", "repo", "commit_sha", "collected_at", "finding_date"]
        
        # Read existing emails if file exists
        existing_results = []
        if output_file.exists():
            try:
                with open(output_file, "r", newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    existing_results = list(reader)
            except Exception:
                existing_results = []
        
        # Merge existing and new results
        all_results = existing_results + results
        
        # Deduplicate by (username, email) pairs (case-insensitive)
        seen_pairs = set()
        unique_results = []
        for result in all_results:
            username = (result.get("username") or "").lower()
            email = (result.get("email") or "").lower()
            pair_key = (username, email)
            if pair_key not in seen_pairs:
                seen_pairs.add(pair_key)
                # Update finding_date for new entries
                if finding_date and pair_key not in set(
                    ((r.get("username") or "").lower(), (r.get("email") or "").lower())
                    for r in existing_results
                ):
                    result["finding_date"] = finding_date
                unique_results.append(result)
        
        # Write combined results
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in unique_results:
                row = {
                    "username": result.get("username", ""),
                    "name": result.get("name", ""),
                    "email": result.get("email", ""),
                    "location": result.get("location", ""),
                    "category": result.get("category", "Unknown"),
                    "source": result.get("source", ""),
                    "repo": result.get("repo", ""),
                    "commit_sha": result.get("commit_sha", ""),
                    "collected_at": result.get("collected_at", ""),
                    "finding_date": result.get("finding_date", finding_date)
                }
                writer.writerow(row)
    
    def write_by_category(self, results: List[Dict], finding_date: str = "") -> None:
        """
        Write emails organized by category (location/country) into separate files.
        
        Args:
            results: List of email data dictionaries
            finding_date: Date when emails were found
        """
        # Group by category
        categories = defaultdict(list)
        for result in results:
            category = result.get("category", "Unknown")
            if not category or category.strip() == "":
                category = "Unknown"
            categories[category].append(result)
        
        # Create category directory
        category_dir = self.output_dir / "categories"
        category_dir.mkdir(exist_ok=True)
        
        # Write summary file
        summary_file = category_dir / "summary.json"
        summary_data = {
            "finding_date": finding_date,
            "total_categories": len(categories),
            "total_emails": len(results),
            "categories": {}
        }
        
        # Write files for each category
        for category, category_results in categories.items():
            # Sanitize category name for filename
            safe_category = "".join(c for c in category if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_category = safe_category.replace(' ', '_')[:50]  # Limit length
            
            if not safe_category:
                safe_category = "Unknown"
            
            # Deduplicate by (username, email) pairs
            seen_pairs = set()
            unique_results = []
            for result in category_results:
                username = result.get("username", "").lower()
                email = result.get("email", "").lower()
                pair_key = (username, email)
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    unique_results.append(result)
            
            # Update summary
            summary_data["categories"][category] = {
                "count": len(unique_results),
                "unique_emails": len(set(r.get("email", "").lower() for r in unique_results if r.get("email")))
            }
            
            # Write category CSV
            csv_file = category_dir / f"{safe_category}.csv"
            with open(csv_file, "w", newline="", encoding="utf-8") as f:
                fieldnames = ["username", "name", "email", "location", "category", "source", "repo", "commit_sha", "collected_at", "finding_date"]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for result in unique_results:
                    row = {
                        "username": result.get("username", ""),
                        "name": result.get("name", ""),
                        "email": result.get("email", ""),
                        "location": result.get("location", ""),
                        "category": result.get("category", "Unknown"),
                        "source": result.get("source", ""),
                        "repo": result.get("repo", ""),
                        "commit_sha": result.get("commit_sha", ""),
                        "collected_at": result.get("collected_at", ""),
                        "finding_date": finding_date
                    }
                    writer.writerow(row)
            
            # Write category TXT
            txt_file = category_dir / f"{safe_category}.txt"
            seen_emails = set()
            with open(txt_file, "w", encoding="utf-8") as f:
                f.write(f"# Category: {category}\n")
                f.write(f"# Finding Date: {finding_date}\n")
                f.write(f"# Total Emails: {len(unique_results)}\n\n")
                
                for result in unique_results:
                    email = result.get("email", "")
                    if email:
                        email_lower = email.lower()
                        if email_lower not in seen_emails:
                            seen_emails.add(email_lower)
                            name = result.get("name", "")
                            if name:
                                f.write(f"{email} ({name})\n")
                            else:
                                f.write(f"{email}\n")
        
        # Write summary
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)

