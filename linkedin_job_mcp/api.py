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


# Global state for background tasks
background_tasks_status = {}


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
        "default_spreadsheet_configured": bool(config.google_spreadsheet_id)
    }


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