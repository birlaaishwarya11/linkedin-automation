#!/usr/bin/env python3
"""LinkedIn Job Search FastMCP Server for TrueFoundry deployment."""

import asyncio
import logging
import json
from typing import List, Optional, Dict, Any
from fastmcp import FastMCP
from linkedin_job_mcp.linkedin_scraper import search_linkedin_jobs
from linkedin_job_mcp.sheets_client import add_jobs_to_sheets, GoogleSheetsClient
from linkedin_job_mcp.config import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("linkedin-job-search")

@mcp.tool()
def search_linkedin_jobs_tool(
    keywords: str,
    location: str = "",
    requirements: List[str] = None,
    max_jobs: int = 25,
    experience_level: str = "",
    employment_type: str = "",
    date_posted: str = "",
    spreadsheet_id: Optional[str] = None,
    filter_duplicates: bool = True
) -> str:
    """
    Search for jobs on LinkedIn and optionally add them to Google Sheets.
    
    Args:
        keywords: Job search keywords (e.g., 'Python developer', 'Data scientist')
        location: Job location (e.g., 'New York, NY', 'Remote')
        requirements: List of job requirements to match against
        max_jobs: Maximum number of jobs to search for (default: 25)
        experience_level: Experience level filter (internship, entry, associate, mid, director, executive)
        employment_type: Employment type filter (full-time, part-time, contract, temporary, internship)
        date_posted: Date posted filter (past 24 hours, past week, past month)
        spreadsheet_id: Google Spreadsheet ID to add jobs to (optional)
        filter_duplicates: Filter out duplicate jobs already in spreadsheet
    
    Returns:
        JSON string with search results and summary
    """
    try:
        if requirements is None:
            requirements = []
            
        logger.info(f"Searching LinkedIn jobs: {keywords} in {location}")
        
        # Run the async search function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            jobs = loop.run_until_complete(search_linkedin_jobs(
                keywords=keywords,
                location=location,
                requirements=requirements,
                max_jobs=max_jobs,
                experience_level=experience_level,
                employment_type=employment_type,
                date_posted=date_posted
            ))
        finally:
            loop.close()
        
        if not jobs:
            return json.dumps({
                "status": "success",
                "message": "No jobs found matching your criteria.",
                "search_summary": {
                    "keywords": keywords,
                    "location": location,
                    "requirements": requirements,
                    "jobs_found": 0,
                    "matching_jobs": 0
                },
                "jobs": []
            })
        
        # Prepare response
        response_data = {
            "status": "success",
            "search_summary": {
                "keywords": keywords,
                "location": location,
                "requirements": requirements,
                "jobs_found": len(jobs),
                "matching_jobs": len([job for job in jobs if job.get('is_match', True)])
            },
            "jobs": jobs
        }
        
        # Add to Google Sheets if spreadsheet_id is provided
        if spreadsheet_id:
            try:
                logger.info(f"Adding jobs to Google Sheets: {spreadsheet_id}")
                
                # Run the async sheets function
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    sheets_result = loop.run_until_complete(add_jobs_to_sheets(
                        jobs=jobs,
                        spreadsheet_id=spreadsheet_id,
                        filter_duplicates=filter_duplicates
                    ))
                    response_data["sheets_result"] = sheets_result
                finally:
                    loop.close()
                    
            except Exception as e:
                logger.error(f"Error adding jobs to sheets: {e}")
                response_data["sheets_error"] = str(e)
        
        return json.dumps(response_data, indent=2)
        
    except Exception as e:
        logger.error(f"Error in search_linkedin_jobs_tool: {e}")
        return json.dumps({
            "status": "error",
            "message": f"Error searching for jobs: {str(e)}"
        })

@mcp.tool()
def create_job_spreadsheet(title: str) -> str:
    """
    Create a new Google Spreadsheet for storing job listings.
    
    Args:
        title: Title for the new spreadsheet
    
    Returns:
        JSON string with spreadsheet information
    """
    try:
        logger.info(f"Creating new spreadsheet: {title}")
        
        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            sheets_client = GoogleSheetsClient()
            spreadsheet = loop.run_until_complete(sheets_client.create_job_spreadsheet(title))
        finally:
            loop.close()
        
        return json.dumps({
            "status": "success",
            "message": f"Created spreadsheet '{title}' successfully",
            "spreadsheet": {
                "id": spreadsheet["spreadsheetId"],
                "title": title,
                "url": f"https://docs.google.com/spreadsheets/d/{spreadsheet['spreadsheetId']}"
            }
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error creating spreadsheet: {e}")
        return json.dumps({
            "status": "error",
            "message": f"Error creating spreadsheet: {str(e)}"
        })

@mcp.tool()
def get_spreadsheet_info(spreadsheet_id: str) -> str:
    """
    Get information about a Google Spreadsheet.
    
    Args:
        spreadsheet_id: Google Spreadsheet ID
    
    Returns:
        JSON string with spreadsheet information
    """
    try:
        logger.info(f"Getting spreadsheet info: {spreadsheet_id}")
        
        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            sheets_client = GoogleSheetsClient()
            info = loop.run_until_complete(sheets_client.get_spreadsheet_info(spreadsheet_id))
        finally:
            loop.close()
        
        return json.dumps({
            "status": "success",
            "spreadsheet": info
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error getting spreadsheet info: {e}")
        return json.dumps({
            "status": "error",
            "message": f"Error getting spreadsheet info: {str(e)}"
        })

# Add health check endpoint for TrueFoundry
@mcp.custom_route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for TrueFoundry deployment."""
    return {"status": "healthy", "service": "linkedin-job-search-mcp"}

# Add MCP endpoint for TrueFoundry
@mcp.custom_route("/mcp", methods=["GET"])
def mcp_endpoint():
    """MCP endpoint information."""
    return {
        "name": "linkedin-job-search",
        "version": "1.0.0",
        "tools": [
            {
                "name": "search_linkedin_jobs_tool",
                "description": "Search for jobs on LinkedIn and optionally add them to Google Sheets"
            },
            {
                "name": "create_job_spreadsheet", 
                "description": "Create a new Google Spreadsheet for storing job listings"
            },
            {
                "name": "get_spreadsheet_info",
                "description": "Get information about a Google Spreadsheet"
            }
        ]
    }

if __name__ == "__main__":
    # Configure for TrueFoundry deployment
    import uvicorn
    
    # Get the FastMCP HTTP app
    app = mcp.http_app()
    
    # Run with uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )