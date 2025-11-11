"""LinkedIn Job MCP Server - Main server implementation."""

import asyncio
import logging
from typing import Any, Dict, List, Optional
import json

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)
from pydantic import BaseModel, Field

from .linkedin_scraper import search_linkedin_jobs
from .sheets_client import add_jobs_to_sheets, GoogleSheetsClient
from .config import config
from .linkedin_oauth import (
    get_linkedin_oauth_client, 
    get_linkedin_api_client,
    LinkedInOAuthError
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize MCP server
server = Server("linkedin-job-mcp")


class JobSearchRequest(BaseModel):
    """Request model for job search."""
    keywords: str = Field(description="Job search keywords (e.g., 'Python developer', 'Data scientist')")
    location: str = Field(default="", description="Job location (e.g., 'New York, NY', 'Remote')")
    requirements: List[str] = Field(default=[], description="List of job requirements to match against")
    max_jobs: int = Field(default=25, description="Maximum number of jobs to search for")
    experience_level: str = Field(default="", description="Experience level filter (internship, entry, associate, mid, director, executive)")
    employment_type: str = Field(default="", description="Employment type filter (full-time, part-time, contract, temporary, internship)")
    date_posted: str = Field(default="", description="Date posted filter (past 24 hours, past week, past month)")
    spreadsheet_id: Optional[str] = Field(default=None, description="Google Spreadsheet ID to add jobs to")
    filter_duplicates: bool = Field(default=True, description="Filter out duplicate jobs already in spreadsheet")


class CreateSpreadsheetRequest(BaseModel):
    """Request model for creating a new spreadsheet."""
    title: str = Field(description="Title for the new spreadsheet")


@server.list_resources()
async def handle_list_resources() -> List[Resource]:
    """List available resources."""
    return [
        Resource(
            uri="linkedin://jobs/search",
            name="LinkedIn Job Search",
            description="Search for jobs on LinkedIn and optionally add them to Google Sheets",
            mimeType="application/json"
        ),
        Resource(
            uri="sheets://spreadsheet/create",
            name="Create Google Spreadsheet",
            description="Create a new Google Spreadsheet for job listings",
            mimeType="application/json"
        )
    ]


@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read a resource."""
    if uri == "linkedin://jobs/search":
        return json.dumps({
            "description": "Search for jobs on LinkedIn",
            "parameters": {
                "keywords": "Job search keywords (required)",
                "location": "Job location (optional)",
                "requirements": "List of job requirements to match (optional)",
                "max_jobs": "Maximum number of jobs to search (default: 25)",
                "experience_level": "Experience level filter (optional)",
                "employment_type": "Employment type filter (optional)",
                "date_posted": "Date posted filter (optional)",
                "spreadsheet_id": "Google Spreadsheet ID to add jobs to (optional)",
                "filter_duplicates": "Filter out duplicate jobs (default: true)"
            }
        })
    elif uri == "sheets://spreadsheet/create":
        return json.dumps({
            "description": "Create a new Google Spreadsheet for job listings",
            "parameters": {
                "title": "Title for the new spreadsheet (required)"
            }
        })
    else:
        raise ValueError(f"Unknown resource: {uri}")


@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available tools."""
    return [
        Tool(
            name="search_linkedin_jobs",
            description="Search for jobs on LinkedIn based on keywords and requirements, optionally add matching jobs to Google Sheets",
            inputSchema={
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "string",
                        "description": "Job search keywords (e.g., 'Python developer', 'Data scientist')"
                    },
                    "location": {
                        "type": "string",
                        "description": "Job location (e.g., 'New York, NY', 'Remote')",
                        "default": ""
                    },
                    "requirements": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of job requirements to match against",
                        "default": []
                    },
                    "max_jobs": {
                        "type": "integer",
                        "description": "Maximum number of jobs to search for",
                        "default": 25,
                        "minimum": 1,
                        "maximum": 100
                    },
                    "experience_level": {
                        "type": "string",
                        "description": "Experience level filter",
                        "enum": ["", "internship", "entry", "associate", "mid", "director", "executive"],
                        "default": ""
                    },
                    "employment_type": {
                        "type": "string",
                        "description": "Employment type filter",
                        "enum": ["", "full-time", "part-time", "contract", "temporary", "internship"],
                        "default": ""
                    },
                    "date_posted": {
                        "type": "string",
                        "description": "Date posted filter",
                        "enum": ["", "past 24 hours", "past week", "past month"],
                        "default": ""
                    },
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "Google Spreadsheet ID to add jobs to (optional)"
                    },
                    "filter_duplicates": {
                        "type": "boolean",
                        "description": "Filter out duplicate jobs already in spreadsheet",
                        "default": True
                    }
                },
                "required": ["keywords"]
            }
        ),
        Tool(
            name="create_job_spreadsheet",
            description="Create a new Google Spreadsheet for storing job listings",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title for the new spreadsheet"
                    }
                },
                "required": ["title"]
            }
        ),
        Tool(
            name="get_spreadsheet_info",
            description="Get information about a Google Spreadsheet",
            inputSchema={
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "Google Spreadsheet ID"
                    }
                },
                "required": ["spreadsheet_id"]
            }
        ),
        Tool(
            name="linkedin_oauth_authorize",
            description="Generate LinkedIn OAuth authorization URL for user authentication",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="linkedin_oauth_status",
            description="Check LinkedIn OAuth authentication status for a user",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID to check authentication status for"
                    }
                },
                "required": ["user_id"]
            }
        ),
        Tool(
            name="linkedin_get_profile",
            description="Get LinkedIn profile information for authenticated user",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "Authenticated user ID"
                    }
                },
                "required": ["user_id"]
            }
        ),
        Tool(
            name="linkedin_post_update",
            description="Post an update to LinkedIn for authenticated user",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "Authenticated user ID"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to post to LinkedIn"
                    }
                },
                "required": ["user_id", "content"]
            }
        ),
        Tool(
            name="linkedin_get_connections",
            description="Get LinkedIn connections for authenticated user",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "Authenticated user ID"
                    }
                },
                "required": ["user_id"]
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls."""
    try:
        if name == "search_linkedin_jobs":
            return await handle_search_linkedin_jobs(arguments)
        elif name == "create_job_spreadsheet":
            return await handle_create_job_spreadsheet(arguments)
        elif name == "get_spreadsheet_info":
            return await handle_get_spreadsheet_info(arguments)
        elif name == "linkedin_oauth_authorize":
            return await handle_linkedin_oauth_authorize(arguments)
        elif name == "linkedin_oauth_status":
            return await handle_linkedin_oauth_status(arguments)
        elif name == "linkedin_get_profile":
            return await handle_linkedin_get_profile(arguments)
        elif name == "linkedin_post_update":
            return await handle_linkedin_post_update(arguments)
        elif name == "linkedin_get_connections":
            return await handle_linkedin_get_connections(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
    except Exception as e:
        logger.error(f"Error handling tool call {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_search_linkedin_jobs(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle LinkedIn job search requests."""
    try:
        # Validate and parse arguments
        request = JobSearchRequest(**arguments)
        
        logger.info(f"Searching LinkedIn jobs: {request.keywords} in {request.location}")
        
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
        
        if not jobs:
            return [TextContent(
                type="text",
                text="No jobs found matching your criteria."
            )]
        
        # Prepare response
        response_data = {
            "search_summary": {
                "keywords": request.keywords,
                "location": request.location,
                "requirements": request.requirements,
                "jobs_found": len(jobs),
                "matching_jobs": len([job for job in jobs if job.get('is_match', True)])
            },
            "jobs": jobs
        }
        
        # Add to Google Sheets if spreadsheet_id is provided
        if request.spreadsheet_id:
            logger.info(f"Adding jobs to Google Sheets: {request.spreadsheet_id}")
            
            sheets_result = await add_jobs_to_sheets(
                jobs=jobs,
                spreadsheet_id=request.spreadsheet_id,
                filter_duplicates=request.filter_duplicates
            )
            
            response_data["sheets_result"] = sheets_result
            
            if sheets_result["success"]:
                message = f"Successfully found {len(jobs)} jobs and added {sheets_result['jobs_added']} new jobs to Google Sheets."
                if sheets_result.get('spreadsheet_url'):
                    message += f"\n\nSpreadsheet URL: {sheets_result['spreadsheet_url']}"
            else:
                message = f"Found {len(jobs)} jobs but failed to add them to Google Sheets: {sheets_result.get('error', 'Unknown error')}"
        else:
            message = f"Successfully found {len(jobs)} jobs matching your criteria."
        
        # Format job listings for display
        job_summaries = []
        for i, job in enumerate(jobs[:10], 1):  # Show first 10 jobs in summary
            summary = f"{i}. **{job['title']}** at **{job['company']}**\n"
            summary += f"   📍 {job['location']}\n"
            summary += f"   🔗 {job['job_url']}\n"
            
            if job.get('match_score'):
                summary += f"   ✅ Match Score: {job['match_score']:.1%}\n"
            
            if job.get('matches'):
                summary += f"   🎯 Matches: {', '.join(job['matches'])}\n"
            
            summary += f"   📝 {job['description'][:200]}...\n"
            job_summaries.append(summary)
        
        if len(jobs) > 10:
            job_summaries.append(f"\n... and {len(jobs) - 10} more jobs")
        
        formatted_response = f"{message}\n\n## Job Listings:\n\n" + "\n".join(job_summaries)
        
        return [
            TextContent(type="text", text=formatted_response),
            TextContent(type="text", text=f"\n\n## Full Data (JSON):\n```json\n{json.dumps(response_data, indent=2)}\n```")
        ]
        
    except Exception as e:
        logger.error(f"Error in LinkedIn job search: {e}")
        return [TextContent(type="text", text=f"Error searching LinkedIn jobs: {str(e)}")]


async def handle_create_job_spreadsheet(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle creating a new job spreadsheet."""
    try:
        request = CreateSpreadsheetRequest(**arguments)
        
        logger.info(f"Creating new spreadsheet: {request.title}")
        
        client = GoogleSheetsClient()
        spreadsheet_id = client.create_spreadsheet(request.title)
        spreadsheet_info = client.get_spreadsheet_info(spreadsheet_id)
        
        response = f"Successfully created new spreadsheet: **{request.title}**\n\n"
        response += f"📊 Spreadsheet ID: `{spreadsheet_id}`\n"
        response += f"🔗 URL: {spreadsheet_info['url']}\n\n"
        response += "The spreadsheet has been set up with appropriate headers for job listings. "
        response += "You can now use this spreadsheet ID in job search requests to automatically add matching jobs."
        
        return [TextContent(type="text", text=response)]
        
    except Exception as e:
        logger.error(f"Error creating spreadsheet: {e}")
        return [TextContent(type="text", text=f"Error creating spreadsheet: {str(e)}")]


async def handle_get_spreadsheet_info(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle getting spreadsheet information."""
    try:
        spreadsheet_id = arguments.get("spreadsheet_id")
        if not spreadsheet_id:
            return [TextContent(type="text", text="Error: spreadsheet_id is required")]
        
        logger.info(f"Getting spreadsheet info: {spreadsheet_id}")
        
        client = GoogleSheetsClient(spreadsheet_id)
        info = client.get_spreadsheet_info()
        existing_jobs = client.get_existing_jobs()
        
        response = f"## Spreadsheet Information\n\n"
        response += f"📊 **Title:** {info['title']}\n"
        response += f"🆔 **ID:** `{spreadsheet_id}`\n"
        response += f"🔗 **URL:** {info['url']}\n"
        response += f"📋 **Sheets:** {', '.join(info['sheets'])}\n"
        response += f"💼 **Existing Jobs:** {len(existing_jobs)} job listings\n"
        
        return [TextContent(type="text", text=response)]
        
    except Exception as e:
        logger.error(f"Error getting spreadsheet info: {e}")
        return [TextContent(type="text", text=f"Error getting spreadsheet info: {str(e)}")]


# LinkedIn OAuth Tool Handlers

async def handle_linkedin_oauth_authorize(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle LinkedIn OAuth authorization request."""
    try:
        oauth_client = get_linkedin_oauth_client()
        if not oauth_client:
            return [TextContent(type="text", text="❌ LinkedIn OAuth is not configured. Please set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET in your environment variables.")]

        auth_url, state = oauth_client.get_authorization_url()
        
        response = f"## 🔗 LinkedIn OAuth Authorization\n\n"
        response += f"To connect your LinkedIn account, please visit the following URL:\n\n"
        response += f"**Authorization URL:** {auth_url}\n\n"
        response += f"**State:** `{state}`\n\n"
        response += f"After authorizing, you'll be redirected back with an authorization code. "
        response += f"Use the authorization code with the callback endpoint to complete the authentication process.\n\n"
        response += f"**Note:** Keep the state value safe as it's used for security validation."

        return [TextContent(type="text", text=response)]

    except LinkedInOAuthError as e:
        logger.error(f"LinkedIn OAuth authorization error: {e}")
        return [TextContent(type="text", text=f"❌ LinkedIn OAuth error: {str(e)}")]
    except Exception as e:
        logger.error(f"Error generating LinkedIn OAuth URL: {e}")
        return [TextContent(type="text", text=f"❌ Error generating LinkedIn OAuth URL: {str(e)}")]


async def handle_linkedin_oauth_status(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle LinkedIn OAuth status check."""
    try:
        user_id = arguments.get("user_id")
        if not user_id:
            return [TextContent(type="text", text="❌ Error: user_id is required")]

        oauth_client = get_linkedin_oauth_client()
        if not oauth_client:
            return [TextContent(type="text", text="❌ LinkedIn OAuth is not configured.")]

        is_authenticated = oauth_client.is_user_authenticated(user_id)
        
        if is_authenticated:
            try:
                token_data = oauth_client.get_user_token(user_id)
                profile = await oauth_client.get_user_profile(token_data['access_token'])
                
                name = "LinkedIn User"
                if profile.get('localizedFirstName') and profile.get('localizedLastName'):
                    name = f"{profile['localizedFirstName']} {profile['localizedLastName']}"
                
                response = f"## ✅ LinkedIn Authentication Status\n\n"
                response += f"**Status:** Authenticated\n"
                response += f"**User ID:** `{user_id}`\n"
                response += f"**Name:** {name}\n"
                if profile.get('email'):
                    response += f"**Email:** {profile['email']}\n"
                response += f"**LinkedIn ID:** {profile.get('id', 'N/A')}\n"
                
                return [TextContent(type="text", text=response)]
                
            except LinkedInOAuthError:
                # Token expired
                oauth_client.remove_user_token(user_id)
                return [TextContent(type="text", text=f"❌ **Authentication Status:** Token expired for user `{user_id}`. Please re-authenticate.")]
        else:
            return [TextContent(type="text", text=f"❌ **Authentication Status:** User `{user_id}` is not authenticated with LinkedIn.")]

    except Exception as e:
        logger.error(f"Error checking LinkedIn OAuth status: {e}")
        return [TextContent(type="text", text=f"❌ Error checking LinkedIn OAuth status: {str(e)}")]


async def handle_linkedin_get_profile(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle getting LinkedIn profile."""
    try:
        user_id = arguments.get("user_id")
        if not user_id:
            return [TextContent(type="text", text="❌ Error: user_id is required")]

        oauth_client = get_linkedin_oauth_client()
        if not oauth_client:
            return [TextContent(type="text", text="❌ LinkedIn OAuth is not configured.")]

        if not oauth_client.is_user_authenticated(user_id):
            return [TextContent(type="text", text=f"❌ User `{user_id}` is not authenticated with LinkedIn. Please authenticate first.")]

        token_data = oauth_client.get_user_token(user_id)
        profile = await oauth_client.get_user_profile(token_data['access_token'])
        
        name = "LinkedIn User"
        if profile.get('localizedFirstName') and profile.get('localizedLastName'):
            name = f"{profile['localizedFirstName']} {profile['localizedLastName']}"
        
        response = f"## 👤 LinkedIn Profile Information\n\n"
        response += f"**Name:** {name}\n"
        response += f"**LinkedIn ID:** {profile.get('id', 'N/A')}\n"
        if profile.get('email'):
            response += f"**Email:** {profile['email']}\n"
        
        # Add any additional profile fields that are available
        if profile.get('headline'):
            response += f"**Headline:** {profile['headline']}\n"
        if profile.get('summary'):
            response += f"**Summary:** {profile['summary'][:200]}{'...' if len(profile.get('summary', '')) > 200 else ''}\n"
        
        return [TextContent(type="text", text=response)]

    except LinkedInOAuthError as e:
        logger.error(f"LinkedIn API error: {e}")
        return [TextContent(type="text", text=f"❌ LinkedIn API error: {str(e)}")]
    except Exception as e:
        logger.error(f"Error getting LinkedIn profile: {e}")
        return [TextContent(type="text", text=f"❌ Error getting LinkedIn profile: {str(e)}")]


async def handle_linkedin_post_update(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle posting update to LinkedIn."""
    try:
        user_id = arguments.get("user_id")
        content = arguments.get("content")
        
        if not user_id:
            return [TextContent(type="text", text="❌ Error: user_id is required")]
        if not content:
            return [TextContent(type="text", text="❌ Error: content is required")]

        api_client = get_linkedin_api_client()
        if not api_client:
            return [TextContent(type="text", text="❌ LinkedIn OAuth is not configured.")]

        oauth_client = get_linkedin_oauth_client()
        if not oauth_client.is_user_authenticated(user_id):
            return [TextContent(type="text", text=f"❌ User `{user_id}` is not authenticated with LinkedIn. Please authenticate first.")]

        result = await api_client.post_update(user_id, content)
        
        if result["success"]:
            response = f"## ✅ LinkedIn Post Successful\n\n"
            response += f"**Content:** {content[:100]}{'...' if len(content) > 100 else ''}\n"
            if result.get("post_id"):
                response += f"**Post ID:** `{result['post_id']}`\n"
            response += f"**Status:** Successfully posted to LinkedIn\n"
            
            return [TextContent(type="text", text=response)]
        else:
            return [TextContent(type="text", text=f"❌ Failed to post to LinkedIn: {result.get('error', 'Unknown error')}")]

    except LinkedInOAuthError as e:
        logger.error(f"LinkedIn API error: {e}")
        return [TextContent(type="text", text=f"❌ LinkedIn API error: {str(e)}")]
    except Exception as e:
        logger.error(f"Error posting to LinkedIn: {e}")
        return [TextContent(type="text", text=f"❌ Error posting to LinkedIn: {str(e)}")]


async def handle_linkedin_get_connections(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle getting LinkedIn connections."""
    try:
        user_id = arguments.get("user_id")
        if not user_id:
            return [TextContent(type="text", text="❌ Error: user_id is required")]

        api_client = get_linkedin_api_client()
        if not api_client:
            return [TextContent(type="text", text="❌ LinkedIn OAuth is not configured.")]

        oauth_client = get_linkedin_oauth_client()
        if not oauth_client.is_user_authenticated(user_id):
            return [TextContent(type="text", text=f"❌ User `{user_id}` is not authenticated with LinkedIn. Please authenticate first.")]

        result = await api_client.get_user_connections(user_id)
        
        if result.get("success"):
            connections = result.get("connections", {})
            response = f"## 🤝 LinkedIn Connections\n\n"
            response += f"**Total Connections:** {connections.get('total', 'N/A')}\n"
            
            if connections.get('elements'):
                response += f"**Recent Connections:**\n"
                for conn in connections['elements'][:5]:  # Show first 5
                    response += f"- {conn.get('name', 'Unknown')}\n"
            
            return [TextContent(type="text", text=response)]
        else:
            return [TextContent(type="text", text=f"❌ Failed to get LinkedIn connections: {result.get('error', 'Unknown error')}")]

    except LinkedInOAuthError as e:
        logger.error(f"LinkedIn API error: {e}")
        return [TextContent(type="text", text=f"❌ LinkedIn API error: {str(e)}")]
    except Exception as e:
        logger.error(f"Error getting LinkedIn connections: {e}")
        return [TextContent(type="text", text=f"❌ Error getting LinkedIn connections: {str(e)}")]


async def main():
    """Main entry point for the MCP server."""
    logger.info("Starting LinkedIn Job MCP Server")
    
    # Initialize server options
    options = InitializationOptions(
        server_name="linkedin-job-mcp",
        server_version="0.1.0",
        capabilities={
            "resources": {},
            "tools": {},
            "logging": {}
        }
    )
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            options
        )


if __name__ == "__main__":
    asyncio.run(main())