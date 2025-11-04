# GitHub Developer Contact Extractor

A Python CLI tool that searches GitHub for developers by location and programming language, extracts publicly available email addresses from profiles, repositories, and commits, and writes results to text, JSON, and CSV files.

## ⚠️ Important Legal and Ethical Notice

**This tool is designed for legitimate, non-commercial purposes only. By using this tool, you agree to:**

1. **Comply with GitHub's Terms of Service** - Specifically, you must not use harvested emails for:
   - Sending unsolicited emails (spam)
   - Selling or distributing email lists
   - Any purpose that violates GitHub's Acceptable Use Policy
   - Any activity that violates applicable laws (e.g., CAN-SPAM Act, GDPR)

2. **Respect Privacy** - This tool only collects emails that are **publicly visible** on GitHub. Many users hide their email addresses, and this tool respects those privacy settings.

3. **Rate Limiting** - The tool implements rate limiting to respect GitHub's API limits. Using this tool responsibly helps maintain access for all developers.

**Please read `usage_policy.md` before using this tool.**

## Features

- 🔍 Search GitHub users by location and/or programming languages
- 📧 Extract emails from multiple sources:
  - User profile (email field, bio)
  - Repository commits (author/committer emails)
  - README files
  - Repository homepage URLs
- ✅ Email validation and normalization
- 🚫 Automatic filtering of GitHub noreply addresses
- 📊 Multiple output formats: TXT, JSON, CSV
- ⚡ Rate limiting and exponential backoff for API resilience
- 🔒 Respects GitHub API rate limits and privacy settings

## Requirements

- Python 3.10 or higher
- GitHub Personal Access Token (optional but recommended for higher rate limits)

## Installation

### Option 1: Install from source

1. Clone or download this repository:
```bash
git clone <repository-url>
cd github-email-harvester
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Option 2: Install as a package

```bash
pip install -e .
```

This will install the package and make the `gh-email-harvest` command available globally.

## Usage

### Basic Usage

Search for developers in a specific location:
```bash
python gh_email_harvest.py --location "San Francisco" --max-results 10
```

Search by programming language:
```bash
python gh_email_harvest.py --languages "Python,JavaScript" --max-results 20
```

Combine filters:
```bash
python gh_email_harvest.py --location "New York" --languages "Python" --min-followers 100 --max-results 50
```

### With GitHub Token (Recommended)

Using a Personal Access Token increases your rate limit from 60 to 5,000 requests per hour:
```bash
python gh_email_harvest.py --location "London" --token YOUR_GITHUB_TOKEN --max-results 100
```

### Advanced Options

```bash
python gh_email_harvest.py \
  --location "San Francisco" \
  --languages "Python,JavaScript" \
  --min-followers 50 \
  --max-results 200 \
  --token YOUR_GITHUB_TOKEN \
  --output ./results \
  --rate 30 \
  --concurrency 1
```

### Dry Run

Test your query without writing files:
```bash
python gh_email_harvest.py --location "Boston" --max-results 5 --dry-run
```

## Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--location` | Location to search for developers | Required* |
| `--languages` | Comma-separated programming languages | Required* |
| `--min-followers` | Minimum number of followers | 0 |
| `--max-results` | Maximum users to process | 100 |
| `--token` | GitHub Personal Access Token | None |
| `--output` | Output directory path | ./output |
| `--dry-run` | Perform dry run without writing files | False |
| `--rate` | Maximum requests per minute | 30 |
| `--concurrency` | Number of concurrent requests | 1 |

*At least one of `--location` or `--languages` must be provided.

## Getting a GitHub Personal Access Token

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Select scopes: `public_repo` (for public repository access)
4. Copy the token and use it with the `--token` argument

**⚠️ Security Note:** Never commit your token to version control. Use environment variables or secure storage.

## Output Files

The tool generates three output files in the specified output directory:

### `emails.txt`
Plain text file with one email address per line:
```
user1@example.com
user2@example.org
developer@company.com
```

### `emails.json`
JSON array with full metadata:
```json
[
  {
    "username": "developer1",
    "email": "user1@example.com",
    "source": "profile",
    "repo": "",
    "commit_sha": "",
    "collected_at": "2024-01-15T10:30:00Z"
  },
  {
    "username": "developer2",
    "email": "user2@example.org",
    "source": "commit",
    "repo": "owner/repo",
    "commit_sha": "abc123",
    "collected_at": "2024-01-15T10:31:00Z"
  }
]
```

### `emails.csv`
CSV file with columns: `username`, `email`, `source`, `repo`, `commit_sha`, `collected_at`

## How It Works

1. **User Search**: Uses GitHub's Search API to find users matching your criteria

2. **Profile Extraction**: Fetches user profile data and extracts emails from:
   - Public email field
   - Bio text
   - Blog/homepage URL

3. **Repository Scanning**: For each user, scans their repositories:

   - Reads README.md files for contact information
   - Checks repository homepage URLs
   - Examines commit history for author/committer emails

4. **Email Processing**:

   - Normalizes email addresses (lowercase, trim whitespace)
   - Validates email format
   - Filters out GitHub noreply addresses
   - Deduplicates emails
   
5. **Output Generation**: Writes results to TXT, JSON, and CSV formats

## Limitations and Caveats

### Email Availability
- **Many users hide their email addresses** - GitHub allows users to hide their email from public view. This tool only collects what is publicly visible.
- **Commit emails may be noreply** - Many users use GitHub's noreply email addresses (`username@users.noreply.github.com`) in commits. These are automatically filtered out.
- **Email may not be current** - Some emails found in commits or README files may be outdated.

### API Rate Limits
- **Unauthenticated requests**: 60 requests/hour
- **Authenticated requests**: 5,000 requests/hour
- **Secondary rate limits**: GitHub may apply additional limits for aggressive API usage
- The tool implements exponential backoff and respects rate limit headers

### Privacy Considerations
- This tool only accesses **publicly available** information
- It does not attempt to bypass privacy settings
- Users who have hidden their emails will not appear in results

## Testing

Run the test suite:
```bash
python -m pytest tests/
```

Or using unittest:
```bash
python -m unittest discover tests
```

## Example Output

```
GitHub Email Harvester
==================================================
Search query: location:"San Francisco" (language:Python OR language:JavaScript) type:user
Max results: 10
Output directory: ./output
Dry run: False
==================================================

Found 10 users to process

[1/10] Processing user: developer1
  ✓ Found email: dev1@example.com (source: profile)
[2/10] Processing user: developer2
  ✓ Found email: dev2@company.com (source: commit)
[3/10] Processing user: developer3
  ✗ No emails found
...

Writing output files...
✓ Output files written to ./output

==================================================
Summary:
  Users processed: 10
  Unique emails found: 7
==================================================
```

## Contributing

Contributions are welcome! Please ensure that:
- Code follows PEP 8 style guidelines
- Tests pass for new features
- Documentation is updated
- Ethical considerations are maintained

## License

This project is provided as-is for educational and legitimate business purposes. Users are responsible for complying with all applicable laws and GitHub's Terms of Service.

## Disclaimer

This tool is provided "as is" without warranty of any kind. The authors are not responsible for:
- Misuse of extracted email addresses
- Violations of GitHub's Terms of Service
- Violations of applicable laws (CAN-SPAM, GDPR, etc.)
- Any consequences resulting from use of this tool

**Use responsibly and ethically.**

## References

- [GitHub REST API Documentation](https://docs.github.com/en/rest)
- [GitHub Terms of Service](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service)
- [GitHub Acceptable Use Policy](https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies)

