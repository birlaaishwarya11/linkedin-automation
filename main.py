"""Main entry point for the LinkedIn Job Search API."""

import sys
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

# Import the FastAPI app
from linkedin_job_mcp.api import app

# This allows uvicorn to find the app with: uvicorn main:app
__all__ = ["app"]