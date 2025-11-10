#!/usr/bin/env python3
"""Example usage of the LinkedIn Job MCP Server components."""

import asyncio
import logging
import json
from pathlib import Path
import sys

# Add the project directory to Python path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from linkedin_job_mcp.linkedin_scraper import search_linkedin_jobs
from linkedin_job_mcp.sheets_client import GoogleSheetsClient, add_jobs_to_sheets

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_job_search():
    """Example: Search for jobs without adding to sheets."""
    logger.info("🔍 Example: Searching for Python developer jobs")
    
    try:
        jobs = await search_linkedin_jobs(
            keywords="Python developer",
            location="Remote",
            requirements=["Python", "Django", "REST API"],
            max_jobs=5  # Small number for testing
        )
        
        logger.info(f"Found {len(jobs)} jobs")
        
        for i, job in enumerate(jobs, 1):
            logger.info(f"\n{i}. {job['title']} at {job['company']}")
            logger.info(f"   Location: {job['location']}")
            logger.info(f"   URL: {job['job_url']}")
            if job.get('match_score'):
                logger.info(f"   Match Score: {job['match_score']:.1%}")
            if job.get('matches'):
                logger.info(f"   Matches: {', '.join(job['matches'])}")
        
        return jobs
        
    except Exception as e:
        logger.error(f"Error in job search: {e}")
        return []


async def example_create_spreadsheet():
    """Example: Create a new spreadsheet."""
    logger.info("📊 Example: Creating a new spreadsheet")
    
    try:
        client = GoogleSheetsClient()
        spreadsheet_id = client.create_spreadsheet("LinkedIn Jobs - Example")
        
        info = client.get_spreadsheet_info(spreadsheet_id)
        logger.info(f"Created spreadsheet: {info['title']}")
        logger.info(f"URL: {info['url']}")
        
        return spreadsheet_id
        
    except Exception as e:
        logger.error(f"Error creating spreadsheet: {e}")
        return None


async def example_add_jobs_to_sheets(jobs, spreadsheet_id):
    """Example: Add jobs to a spreadsheet."""
    logger.info("📝 Example: Adding jobs to spreadsheet")
    
    try:
        result = await add_jobs_to_sheets(
            jobs=jobs,
            spreadsheet_id=spreadsheet_id,
            filter_duplicates=True
        )
        
        if result['success']:
            logger.info(f"Successfully added {result['jobs_added']} jobs")
            logger.info(f"Spreadsheet URL: {result.get('spreadsheet_url', 'N/A')}")
        else:
            logger.error(f"Failed to add jobs: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error adding jobs to sheets: {e}")
        return {"success": False, "error": str(e)}


async def example_full_workflow():
    """Example: Complete workflow from search to spreadsheet."""
    logger.info("🚀 Example: Complete workflow")
    logger.info("=" * 50)
    
    # Step 1: Search for jobs
    logger.info("Step 1: Searching for jobs...")
    jobs = await example_job_search()
    
    if not jobs:
        logger.warning("No jobs found, skipping spreadsheet steps")
        return
    
    # Step 2: Create spreadsheet
    logger.info("\nStep 2: Creating spreadsheet...")
    spreadsheet_id = await example_create_spreadsheet()
    
    if not spreadsheet_id:
        logger.warning("Failed to create spreadsheet, skipping job addition")
        return
    
    # Step 3: Add jobs to spreadsheet
    logger.info("\nStep 3: Adding jobs to spreadsheet...")
    result = await example_add_jobs_to_sheets(jobs, spreadsheet_id)
    
    if result['success']:
        logger.info("\n🎉 Complete workflow successful!")
        logger.info(f"Jobs found: {len(jobs)}")
        logger.info(f"Jobs added: {result['jobs_added']}")
        logger.info(f"Spreadsheet: {result.get('spreadsheet_url', 'N/A')}")
    else:
        logger.error("\n❌ Workflow failed at spreadsheet step")


async def example_job_matching():
    """Example: Demonstrate job requirement matching."""
    logger.info("🎯 Example: Job requirement matching")
    
    # Sample job data
    sample_job = {
        "title": "Senior Python Developer",
        "company": "Tech Corp",
        "location": "San Francisco, CA",
        "description": "We are looking for a Senior Python Developer with experience in Django, REST APIs, PostgreSQL, and AWS. The ideal candidate should have 5+ years of experience building scalable web applications.",
        "job_url": "https://linkedin.com/jobs/123456"
    }
    
    requirements = ["Python", "Django", "REST API", "PostgreSQL", "AWS", "React"]
    
    # Simulate matching logic
    job_text = f"{sample_job['title']} {sample_job['description']}".lower()
    matches = [req for req in requirements if req.lower() in job_text]
    match_score = len(matches) / len(requirements)
    
    logger.info(f"Job: {sample_job['title']} at {sample_job['company']}")
    logger.info(f"Requirements: {', '.join(requirements)}")
    logger.info(f"Matches: {', '.join(matches)}")
    logger.info(f"Match Score: {match_score:.1%}")
    logger.info(f"Is Match: {'Yes' if match_score >= 0.5 else 'No'}")


def example_mcp_tool_call():
    """Example: Simulate MCP tool call."""
    logger.info("🔧 Example: MCP tool call simulation")
    
    # Simulate tool call arguments
    tool_args = {
        "keywords": "Data Scientist",
        "location": "New York, NY",
        "requirements": ["Python", "Machine Learning", "SQL", "Pandas"],
        "max_jobs": 10,
        "experience_level": "mid",
        "employment_type": "full-time"
    }
    
    logger.info("Tool: search_linkedin_jobs")
    logger.info(f"Arguments: {json.dumps(tool_args, indent=2)}")
    
    # This would normally be handled by the MCP server
    logger.info("This would trigger a LinkedIn job search with the specified parameters")


async def main():
    """Run examples based on command line arguments."""
    import sys
    
    if len(sys.argv) < 2:
        logger.info("Available examples:")
        logger.info("  search     - Search for jobs (no spreadsheet)")
        logger.info("  sheets     - Create spreadsheet")
        logger.info("  workflow   - Complete workflow")
        logger.info("  matching   - Job requirement matching demo")
        logger.info("  mcp        - MCP tool call simulation")
        logger.info("  all        - Run all examples")
        logger.info("\nUsage: python example_usage.py <example_name>")
        return
    
    example = sys.argv[1].lower()
    
    if example == "search":
        await example_job_search()
    elif example == "sheets":
        await example_create_spreadsheet()
    elif example == "workflow":
        await example_full_workflow()
    elif example == "matching":
        await example_job_matching()
    elif example == "mcp":
        example_mcp_tool_call()
    elif example == "all":
        await example_job_matching()
        example_mcp_tool_call()
        logger.info("\n" + "="*50)
        logger.info("Note: Skipping live examples (search, sheets, workflow)")
        logger.info("To run live examples, make sure you have:")
        logger.info("1. Google Sheets API credentials set up")
        logger.info("2. Chrome browser installed")
        logger.info("3. Stable internet connection")
    else:
        logger.error(f"Unknown example: {example}")


if __name__ == "__main__":
    asyncio.run(main())