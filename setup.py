"""
Setup script for GitHub Email Harvester.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="github-email-harvester",
    version="1.0.0",
    description="Extract publicly available email addresses from GitHub profiles",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="GitHub Email Harvester Contributors",
    py_modules=[
        "gh_email_harvest",
        "github_client",
        "email_utils",
        "output_writer"
    ],
    install_requires=[
        "requests>=2.31.0"
    ],
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "gh-email-harvest=gh_email_harvest:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="github, email, scraping, api, cli",
)

