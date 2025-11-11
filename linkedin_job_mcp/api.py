"""FastAPI wrapper for LinkedIn Job MCP Server."""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import traceback

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn
from pathlib import Path

from .linkedin_scraper import search_linkedin_jobs
from .sheets_client import add_jobs_to_sheets, GoogleSheetsClient
from .config import config
from .utils import setup_logging, create_error_response, create_success_response
from .linkedin_oauth import (
    get_linkedin_oauth_client, 
    get_linkedin_api_client,
    LinkedInOAuthError
)

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="LinkedIn Job Search API",
    description="API for searching LinkedIn jobs and adding them to Google Sheets",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Request/Response Models
class JobSearchRequest(BaseModel):
    """Request model for job search."""
    keywords: str = Field(..., description="Job search keywords", example="Python developer")
    location: str = Field("", description="Job location", example="San Francisco, CA")
    requirements: List[str] = Field([], description="List of job requirements to match against", example=["Python", "Django", "REST API"])
    max_jobs: int = Field(25, ge=1, le=100, description="Maximum number of jobs to search for")
    experience_level: str = Field("", description="Experience level filter", example="mid")
    employment_type: str = Field("", description="Employment type filter", example="full-time")
    date_posted: str = Field("", description="Date posted filter", example="past week")
    spreadsheet_id: Optional[str] = Field(None, description="Google Spreadsheet ID to add jobs to")
    filter_duplicates: bool = Field(True, description="Filter out duplicate jobs already in spreadsheet")


class CreateSpreadsheetRequest(BaseModel):
    """Request model for creating a new spreadsheet."""
    title: str = Field(..., description="Title for the new spreadsheet", example="Python Developer Jobs - 2024")


class JobSearchResponse(BaseModel):
    """Response model for job search."""
    success: bool
    message: str
    jobs_found: int
    matching_jobs: int
    jobs_added_to_sheets: Optional[int] = None
    spreadsheet_url: Optional[str] = None
    jobs: List[Dict[str, Any]]
    search_params: Dict[str, Any]
    timestamp: str


class SpreadsheetResponse(BaseModel):
    """Response model for spreadsheet operations."""
    success: bool
    message: str
    spreadsheet_id: Optional[str] = None
    spreadsheet_url: Optional[str] = None
    title: Optional[str] = None
    timestamp: str


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    timestamp: str
    version: str
    services: Dict[str, str]


class OAuthAuthorizationResponse(BaseModel):
    """Response model for OAuth authorization."""
    success: bool
    authorization_url: str
    state: str
    message: str


class OAuthCallbackResponse(BaseModel):
    """Response model for OAuth callback."""
    success: bool
    message: str
    user_id: Optional[str] = None
    profile: Optional[Dict[str, Any]] = None


class OAuthStatusResponse(BaseModel):
    """Response model for OAuth status."""
    authenticated: bool
    user_id: Optional[str] = None
    profile: Optional[Dict[str, Any]] = None
    message: str


# Global state for background tasks
background_tasks_status = {}

# OAuth state storage (in production, use Redis or database)
oauth_states = {}


# LinkedIn OAuth Endpoints

@app.get("/auth/linkedin", response_model=OAuthAuthorizationResponse)
async def linkedin_oauth_authorize():
    """Initiate LinkedIn OAuth authorization."""
    try:
        oauth_client = get_linkedin_oauth_client()
        if not oauth_client:
            raise HTTPException(
                status_code=503, 
                detail="LinkedIn OAuth not configured. Please set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET."
            )
        
        auth_url, state = oauth_client.get_authorization_url()
        
        # Store state for validation (in production, use Redis or database)
        oauth_states[state] = {
            'created_at': datetime.now(),
            'used': False
        }
        
        return OAuthAuthorizationResponse(
            success=True,
            authorization_url=auth_url,
            state=state,
            message="Redirect user to authorization URL"
        )
        
    except LinkedInOAuthError as e:
        logger.error(f"OAuth authorization error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"Unexpected error in OAuth authorization: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/auth/linkedin/callback", response_model=OAuthCallbackResponse)
async def linkedin_oauth_callback(code: str = Query(...), state: str = Query(...)):
    """Handle LinkedIn OAuth callback."""
    try:
        oauth_client = get_linkedin_oauth_client()
        if not oauth_client:
            raise HTTPException(status_code=503, detail="LinkedIn OAuth not configured")
        
        # Validate state
        if state not in oauth_states or oauth_states[state]['used']:
            raise HTTPException(status_code=400, detail="Invalid or expired state parameter")
        
        # Mark state as used
        oauth_states[state]['used'] = True
        
        # Exchange code for token
        token_data = await oauth_client.exchange_code_for_token(code, state)
        
        # Get user profile
        profile = await oauth_client.get_user_profile(token_data['access_token'])
        
        # Generate user ID (in production, use proper user management)
        user_id = f"linkedin_{profile['id']}"
        
        # Store token
        oauth_client.store_user_token(user_id, token_data)
        
        logger.info(f"OAuth callback successful for user: {user_id}")
        
        return OAuthCallbackResponse(
            success=True,
            message="Successfully authenticated with LinkedIn",
            user_id=user_id,
            profile=profile
        )
        
    except LinkedInOAuthError as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in OAuth callback: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/auth/linkedin/status/{user_id}", response_model=OAuthStatusResponse)
async def linkedin_oauth_status(user_id: str):
    """Check LinkedIn OAuth authentication status for a user."""
    try:
        oauth_client = get_linkedin_oauth_client()
        if not oauth_client:
            return OAuthStatusResponse(
                authenticated=False,
                message="LinkedIn OAuth not configured"
            )
        
        is_authenticated = oauth_client.is_user_authenticated(user_id)
        
        if is_authenticated:
            # Get user profile from stored token
            token_data = oauth_client.get_user_token(user_id)
            try:
                profile = await oauth_client.get_user_profile(token_data['access_token'])
                return OAuthStatusResponse(
                    authenticated=True,
                    user_id=user_id,
                    profile=profile,
                    message="User is authenticated"
                )
            except LinkedInOAuthError:
                # Token might be expired
                oauth_client.remove_user_token(user_id)
                return OAuthStatusResponse(
                    authenticated=False,
                    message="Token expired, please re-authenticate"
                )
        else:
            return OAuthStatusResponse(
                authenticated=False,
                message="User is not authenticated"
            )
            
    except Exception as e:
        logger.error(f"Error checking OAuth status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/auth/linkedin/{user_id}")
async def linkedin_oauth_logout(user_id: str):
    """Logout user and remove OAuth token."""
    try:
        oauth_client = get_linkedin_oauth_client()
        if oauth_client:
            oauth_client.remove_user_token(user_id)
        
        return {
            "success": True,
            "message": f"Successfully logged out user: {user_id}"
        }
        
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/")
async def root():
    """Serve the main web interface."""
    static_path = Path(__file__).parent.parent / "static" / "index.html"
    if static_path.exists():
        return FileResponse(str(static_path))
    else:
        return {
            "name": "LinkedIn Job Search API",
            "version": "0.1.0",
            "description": "API for searching LinkedIn jobs and adding them to Google Sheets",
            "docs": "/docs",
            "health": "/health"
        }


@app.get("/api", response_model=Dict[str, str])
async def api_info():
    """API information endpoint."""
    return {
        "name": "LinkedIn Job Search API",
        "version": "0.1.0",
        "description": "API for searching LinkedIn jobs and adding them to Google Sheets",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    services = {}
    
    # Check Chrome WebDriver
    try:
        from selenium import webdriver
        from webdriver_manager.chrome import ChromeDriverManager
        ChromeDriverManager().install()
        services["chrome_driver"] = "available"
    except Exception as e:
        services["chrome_driver"] = f"error: {str(e)}"
    
    # Check Google Sheets credentials
    try:
        import os
        if os.path.exists(config.google_credentials_path):
            services["google_sheets"] = "credentials_found"
        else:
            services["google_sheets"] = "credentials_missing"
    except Exception as e:
        services["google_sheets"] = f"error: {str(e)}"
    
    # Check LinkedIn OAuth configuration
    try:
        oauth_client = get_linkedin_oauth_client()
        if oauth_client:
            services["linkedin_oauth"] = "configured"
        else:
            services["linkedin_oauth"] = "not_configured"
    except Exception as e:
        services["linkedin_oauth"] = f"error: {str(e)}"
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="0.1.0",
        services=services
    )


@app.post("/search", response_model=JobSearchResponse)
async def search_jobs(request: JobSearchRequest):
    """Search for jobs on LinkedIn and optionally add them to Google Sheets."""
    try:
        logger.info(f"Job search request: {request.keywords} in {request.location}")
        
        # Search for jobs
        jobs = await search_linkedin_jobs(
            keywords=request.keywords,
            location=request.location,
            requirements=request.requirements,
            max_jobs=request.max_jobs,
            experience_level=request.experience_level,
            employment_type=request.employment_type,
            date_posted=request.date_posted
        )
        
        matching_jobs = len([job for job in jobs if job.get('is_match', True)])
        jobs_added_to_sheets = None
        spreadsheet_url = None
        
        # Add to Google Sheets if spreadsheet_id is provided
        if request.spreadsheet_id:
            logger.info(f"Adding jobs to Google Sheets: {request.spreadsheet_id}")
            
            sheets_result = await add_jobs_to_sheets(
                jobs=jobs,
                spreadsheet_id=request.spreadsheet_id,
                filter_duplicates=request.filter_duplicates
            )
            
            if sheets_result["success"]:
                jobs_added_to_sheets = sheets_result["jobs_added"]
                spreadsheet_url = sheets_result.get("spreadsheet_url")
            else:
                logger.warning(f"Failed to add jobs to sheets: {sheets_result.get('error')}")
        
        message = f"Found {len(jobs)} jobs"
        if matching_jobs < len(jobs):
            message += f", {matching_jobs} matching your requirements"
        if jobs_added_to_sheets is not None:
            message += f", added {jobs_added_to_sheets} new jobs to spreadsheet"
        
        return JobSearchResponse(
            success=True,
            message=message,
            jobs_found=len(jobs),
            matching_jobs=matching_jobs,
            jobs_added_to_sheets=jobs_added_to_sheets,
            spreadsheet_url=spreadsheet_url,
            jobs=jobs,
            search_params=request.dict(),
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error in job search: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search/async")
async def search_jobs_async(request: JobSearchRequest, background_tasks: BackgroundTasks):
    """Start an asynchronous job search and return a task ID."""
    import uuid
    task_id = str(uuid.uuid4())
    
    background_tasks_status[task_id] = {
        "status": "started",
        "timestamp": datetime.now().isoformat(),
        "request": request.dict()
    }
    
    background_tasks.add_task(run_job_search_background, task_id, request)
    
    return {
        "task_id": task_id,
        "status": "started",
        "message": "Job search started in background",
        "status_url": f"/search/status/{task_id}"
    }


@app.get("/search/status/{task_id}")
async def get_search_status(task_id: str):
    """Get the status of an asynchronous job search."""
    if task_id not in background_tasks_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return background_tasks_status[task_id]


async def run_job_search_background(task_id: str, request: JobSearchRequest):
    """Run job search in background."""
    try:
        background_tasks_status[task_id]["status"] = "running"
        
        # Search for jobs
        jobs = await search_linkedin_jobs(
            keywords=request.keywords,
            location=request.location,
            requirements=request.requirements,
            max_jobs=request.max_jobs,
            experience_level=request.experience_level,
            employment_type=request.employment_type,
            date_posted=request.date_posted
        )
        
        matching_jobs = len([job for job in jobs if job.get('is_match', True)])
        jobs_added_to_sheets = None
        spreadsheet_url = None
        
        # Add to Google Sheets if spreadsheet_id is provided
        if request.spreadsheet_id:
            sheets_result = await add_jobs_to_sheets(
                jobs=jobs,
                spreadsheet_id=request.spreadsheet_id,
                filter_duplicates=request.filter_duplicates
            )
            
            if sheets_result["success"]:
                jobs_added_to_sheets = sheets_result["jobs_added"]
                spreadsheet_url = sheets_result.get("spreadsheet_url")
        
        background_tasks_status[task_id] = {
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "request": request.dict(),
            "result": {
                "jobs_found": len(jobs),
                "matching_jobs": matching_jobs,
                "jobs_added_to_sheets": jobs_added_to_sheets,
                "spreadsheet_url": spreadsheet_url,
                "jobs": jobs
            }
        }
        
    except Exception as e:
        background_tasks_status[task_id] = {
            "status": "failed",
            "timestamp": datetime.now().isoformat(),
            "request": request.dict(),
            "error": str(e)
        }


@app.post("/spreadsheet/create", response_model=SpreadsheetResponse)
async def create_spreadsheet(request: CreateSpreadsheetRequest):
    """Create a new Google Spreadsheet for job listings."""
    try:
        logger.info(f"Creating spreadsheet: {request.title}")
        
        client = GoogleSheetsClient()
        spreadsheet_id = client.create_spreadsheet(request.title)
        spreadsheet_info = client.get_spreadsheet_info(spreadsheet_id)
        
        return SpreadsheetResponse(
            success=True,
            message=f"Successfully created spreadsheet: {request.title}",
            spreadsheet_id=spreadsheet_id,
            spreadsheet_url=spreadsheet_info["url"],
            title=spreadsheet_info["title"],
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error creating spreadsheet: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/spreadsheet/{spreadsheet_id}/info")
async def get_spreadsheet_info(spreadsheet_id: str):
    """Get information about a Google Spreadsheet."""
    try:
        client = GoogleSheetsClient(spreadsheet_id)
        info = client.get_spreadsheet_info()
        existing_jobs = client.get_existing_jobs()
        
        return {
            "success": True,
            "spreadsheet_id": spreadsheet_id,
            "title": info["title"],
            "url": info["url"],
            "sheets": info["sheets"],
            "existing_jobs_count": len(existing_jobs),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting spreadsheet info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/filters")
async def get_job_filters():
    """Get available job search filters."""
    return {
        "experience_levels": [
            {"value": "", "label": "Any"},
            {"value": "internship", "label": "Internship"},
            {"value": "entry", "label": "Entry Level"},
            {"value": "associate", "label": "Associate"},
            {"value": "mid", "label": "Mid Level"},
            {"value": "director", "label": "Director"},
            {"value": "executive", "label": "Executive"}
        ],
        "employment_types": [
            {"value": "", "label": "Any"},
            {"value": "full-time", "label": "Full-time"},
            {"value": "part-time", "label": "Part-time"},
            {"value": "contract", "label": "Contract"},
            {"value": "temporary", "label": "Temporary"},
            {"value": "internship", "label": "Internship"}
        ],
        "date_posted": [
            {"value": "", "label": "Any time"},
            {"value": "past 24 hours", "label": "Past 24 hours"},
            {"value": "past week", "label": "Past week"},
            {"value": "past month", "label": "Past month"}
        ]
    }


@app.get("/config")
async def get_config():
    """Get current configuration (non-sensitive values only)."""
    return {
        "chrome_headless": config.chrome_headless,
        "search_delay_seconds": config.search_delay_seconds,
        "max_concurrent_searches": config.max_concurrent_searches,
        "max_jobs_per_search": config.max_jobs_per_search,
        "job_search_timeout": config.job_search_timeout,
        "google_credentials_configured": bool(config.google_credentials_path),
        "default_spreadsheet_configured": bool(config.google_spreadsheet_id),
        "linkedin_oauth_configured": bool(config.linkedin_client_id and config.linkedin_client_secret)
    }


# LinkedIn API Endpoints (OAuth-enabled)

@app.get("/linkedin/profile/{user_id}")
async def get_linkedin_profile(user_id: str):
    """Get LinkedIn profile for authenticated user."""
    try:
        oauth_client = get_linkedin_oauth_client()
        if not oauth_client:
            raise HTTPException(status_code=503, detail="LinkedIn OAuth not configured")
        
        if not oauth_client.is_user_authenticated(user_id):
            raise HTTPException(status_code=401, detail="User not authenticated with LinkedIn")
        
        token_data = oauth_client.get_user_token(user_id)
        profile = await oauth_client.get_user_profile(token_data['access_token'])
        
        return {
            "success": True,
            "profile": profile,
            "timestamp": datetime.now().isoformat()
        }
        
    except LinkedInOAuthError as e:
        logger.error(f"LinkedIn API error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting LinkedIn profile: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/linkedin/post/{user_id}")
async def post_to_linkedin(user_id: str, content: str = Body(..., embed=True)):
    """Post content to LinkedIn for authenticated user."""
    try:
        api_client = get_linkedin_api_client()
        if not api_client:
            raise HTTPException(status_code=503, detail="LinkedIn OAuth not configured")
        
        oauth_client = get_linkedin_oauth_client()
        if not oauth_client.is_user_authenticated(user_id):
            raise HTTPException(status_code=401, detail="User not authenticated with LinkedIn")
        
        result = await api_client.post_update(user_id, content)
        
        if result["success"]:
            return {
                "success": True,
                "message": "Successfully posted to LinkedIn",
                "post_id": result.get("post_id"),
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to post to LinkedIn"))
            
    except LinkedInOAuthError as e:
        logger.error(f"LinkedIn API error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error posting to LinkedIn: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/linkedin/connections/{user_id}")
async def get_linkedin_connections(user_id: str):
    """Get LinkedIn connections for authenticated user."""
    try:
        api_client = get_linkedin_api_client()
        if not api_client:
            raise HTTPException(status_code=503, detail="LinkedIn OAuth not configured")
        
        oauth_client = get_linkedin_oauth_client()
        if not oauth_client.is_user_authenticated(user_id):
            raise HTTPException(status_code=401, detail="User not authenticated with LinkedIn")
        
        result = await api_client.get_user_connections(user_id)
        
        return {
            "success": True,
            "connections": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except LinkedInOAuthError as e:
        logger.error(f"LinkedIn API error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting LinkedIn connections: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(exc, f"HTTP {exc.status_code}")
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content=create_error_response(exc, "Internal server error")
    )


def create_app():
    """Factory function to create the FastAPI app."""
    return app


def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Run the FastAPI server."""
    uvicorn.run(
        "linkedin_job_mcp.api:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


# For direct uvicorn usage
if __name__ == "__main__":
    import sys
    import os
    
    # Add project root to path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    
    run_server()