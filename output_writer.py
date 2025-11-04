"""
Output writers for different file formats.
"""

import csv
import json
from pathlib import Path
from typing import List, Dict


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
    
    def write_txt(self, results: List[Dict]) -> None:
        """
        Write emails to plain text file (one per line).
        
        Args:
            results: List of email data dictionaries
        """
        output_file = self.output_dir / "emails.txt"
        
        with open(output_file, "w", encoding="utf-8") as f:
            for result in results:
                email = result.get("email", "")
                if email:
                    f.write(f"{email}\n")
    
    def write_json(self, results: List[Dict]) -> None:
        """
        Write emails to JSON file with metadata.
        
        Args:
            results: List of email data dictionaries
        """
        output_file = self.output_dir / "emails.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    
    def write_csv(self, results: List[Dict]) -> None:
        """
        Write emails to CSV file with metadata.
        
        Args:
            results: List of email data dictionaries
        """
        output_file = self.output_dir / "emails.csv"
        
        if not results:
            # Create empty CSV with headers
            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "username", "email", "source", "repo", "commit_sha", "collected_at"
                ])
                writer.writeheader()
            return
        
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["username", "email", "source", "repo", "commit_sha", "collected_at"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            writer.writeheader()
            
            for result in results:
                row = {
                    "username": result.get("username", ""),
                    "email": result.get("email", ""),
                    "source": result.get("source", ""),
                    "repo": result.get("repo", ""),
                    "commit_sha": result.get("commit_sha", ""),
                    "collected_at": result.get("collected_at", "")
                }
                writer.writerow(row)

