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
        Write emails to plain text file (one per line).
        
        Args:
            results: List of email data dictionaries
            finding_date: Date when emails were found
        """
        output_file = self.output_dir / "emails.txt"
        
        # Deduplicate by email (case-insensitive)
        seen_emails = set()
        with open(output_file, "w", encoding="utf-8") as f:
            # Write header with finding date and count
            if finding_date:
                f.write(f"# Emails found on {finding_date}\n")
            f.write(f"# Total unique emails: {len(set(r.get('email', '').lower() for r in results if r.get('email')))}\n\n")
            
            for result in results:
                email = result.get("email", "")
                if email:
                    email_lower = email.lower()
                    if email_lower not in seen_emails:
                        seen_emails.add(email_lower)
                        f.write(f"{email}\n")
    
    def write_json(self, results: List[Dict], finding_date: str = "") -> None:
        """
        Write emails to JSON file with metadata.
        
        Args:
            results: List of email data dictionaries
            finding_date: Date when emails were found
        """
        output_file = self.output_dir / "emails.json"
        
        # Deduplicate by (username, email) pairs (case-insensitive)
        seen_pairs = set()
        unique_results = []
        for result in results:
            username = result.get("username", "").lower()
            email = result.get("email", "").lower()
            pair_key = (username, email)
            if pair_key not in seen_pairs:
                seen_pairs.add(pair_key)
                unique_results.append(result)
        
        # Create output with metadata
        output_data = {
            "finding_date": finding_date,
            "total_emails": len(unique_results),
            "unique_emails": len(set(r.get("email", "").lower() for r in unique_results if r.get("email"))),
            "emails": unique_results
        }
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    def write_csv(self, results: List[Dict], finding_date: str = "") -> None:
        """
        Write emails to CSV file with metadata.
        
        Args:
            results: List of email data dictionaries
            finding_date: Date when emails were found
        """
        output_file = self.output_dir / "emails.csv"
        
        if not results:
            # Create empty CSV with headers
            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "username", "name", "email", "location", "category", "source", "repo", "commit_sha", "collected_at", "finding_date"
                ])
                writer.writeheader()
            return
        
        # Deduplicate by (username, email) pairs (case-insensitive)
        seen_pairs = set()
        unique_results = []
        for result in results:
            username = result.get("username", "").lower()
            email = result.get("email", "").lower()
            pair_key = (username, email)
            if pair_key not in seen_pairs:
                seen_pairs.add(pair_key)
                unique_results.append(result)
        
        with open(output_file, "w", newline="", encoding="utf-8") as f:
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

