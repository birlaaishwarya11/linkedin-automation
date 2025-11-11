"""Configuration management for LinkedIn Job MCP Server."""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Config(BaseSettings):
    """Configuration settings for the LinkedIn Job MCP Server."""
    
    # Google Sheets API Configuration
    google_credentials_path: str = Field(
        default="credentials.json",
        description="Path to Google service account credentials JSON file"
    )
    google_spreadsheet_id: Optional[str] = Field(
        default=None,
        description="Google Spreadsheet ID where jobs will be added"
    )
    
    # LinkedIn Configuration
    linkedin_email: Optional[str] = Field(
        default=None,
        description="LinkedIn email for authenticated searches (optional)"
    )
    linkedin_password: Optional[str] = Field(
        default=None,
        description="LinkedIn password for authenticated searches (optional)"
    )
    
    # LinkedIn OAuth Configuration
    linkedin_client_id: Optional[str] = Field(
        default=None,
        description="LinkedIn OAuth Client ID"
    )
    linkedin_client_secret: Optional[str] = Field(
        default=None,
        description="LinkedIn OAuth Client Secret"
    )
    linkedin_redirect_uri: str = Field(
        default="http://localhost:8000/auth/linkedin/callback",
        description="LinkedIn OAuth Redirect URI"
    )
    linkedin_oauth_scopes: str = Field(
        default="r_liteprofile,r_emailaddress,w_member_social",
        description="LinkedIn OAuth scopes (comma-separated)"
    )
    
    # OAuth Token Storage
    oauth_secret_key: str = Field(
        default="your-secret-key-change-this-in-production",
        description="Secret key for encrypting OAuth tokens"
    )
    
    # Chrome WebDriver Configuration
    chrome_headless: bool = Field(
        default=True,
        description="Run Chrome in headless mode"
    )
    chrome_user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        description="User agent string for Chrome"
    )
    
    # Rate Limiting
    search_delay_seconds: float = Field(
        default=2.0,
        description="Delay between searches to avoid rate limiting"
    )
    max_concurrent_searches: int = Field(
        default=3,
        description="Maximum number of concurrent search operations"
    )
    
    # Job Search Configuration
    max_jobs_per_search: int = Field(
        default=25,
        description="Maximum number of jobs to extract per search"
    )
    job_search_timeout: int = Field(
        default=30,
        description="Timeout for job search operations in seconds"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global configuration instance
config = Config()