# Using the LinkedIn Job MCP Server

The LinkedIn Job MCP Server provides AI assistants with tools to search LinkedIn jobs and manage Google Sheets. Here's how to use it:

## 🚀 Starting the MCP Server

### Method 1: Direct MCP Server
```bash
# Start the MCP server (listens on stdio)
python -m linkedin_job_mcp.server
```

### Method 2: Using Python directly
```python
import asyncio
from linkedin_job_mcp.server import main

# Run the MCP server
asyncio.run(main())
```

## 🔧 Connecting AI Assistants

### Claude Desktop Configuration

Add this to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "linkedin-job-search": {
      "command": "python",
      "args": ["-m", "linkedin_job_mcp.server"],
      "cwd": "/path/to/your/linkedin_job_mcp"
    }
  }
}
```

### Other MCP Clients

For other MCP-compatible clients, use:
- **Command**: `python -m linkedin_job_mcp.server`
- **Working Directory**: Your project directory
- **Protocol**: stdio

## 🛠️ Available MCP Tools

### 1. `search_linkedin_jobs`

Search for jobs on LinkedIn and optionally add them to Google Sheets.

**Parameters:**
```json
{
  "keywords": "Python developer",
  "location": "San Francisco, CA", 
  "requirements": ["Python", "Django", "REST API"],
  "max_jobs": 25,
  "experience_level": "mid",
  "employment_type": "full-time",
  "date_posted": "past week",
  "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
  "filter_duplicates": true
}
```

**Example Usage with Claude:**
```
Please search for Python developer jobs in San Francisco. 
I need positions that require Python, Django, and REST API experience.
Add the results to my Google Sheet: 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
```

### 2. `create_spreadsheet`

Create a new Google Spreadsheet for storing job search results.

**Parameters:**
```json
{
  "title": "Python Developer Jobs - 2024"
}
```

**Example Usage with Claude:**
```
Create a new Google Spreadsheet called "Python Developer Jobs - 2024" 
for storing my job search results.
```

### 3. `get_spreadsheet_info`

Get information about an existing Google Spreadsheet.

**Parameters:**
```json
{
  "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
}
```

**Example Usage with Claude:**
```
Show me information about my job spreadsheet: 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
```

## 💬 Example Conversations with AI Assistants

### Job Search Example
```
User: I'm looking for senior Python developer jobs in New York. 
      I need positions that require Python, FastAPI, and PostgreSQL. 
      Please search for up to 30 jobs and add them to my spreadsheet.Assistant: I'll help you search for senior Python developer jobs in New York. 
          Let me use the search_linkedin_jobs tool with your requirements.

[The assistant would then call the search_linkedin_jobs tool with parameters:
{
  "keywords": "senior Python developer",
  "location": "New York, NY",
  "requirements": ["Python", "FastAPI", "PostgreSQL"],
  "max_jobs": 30,
  "experience_level": "director",
  "spreadsheet_id": "your_spreadsheet_id"
}]

Result: Found 28 matching jobs and added them to your spreadsheet!
```

### Creating a New Spreadsheet Example
```
User: Create a new spreadsheet for my data science job search.
Assistant: I'll create a new Google Spreadsheet for your data science job search.

[The assistant calls create_spreadsheet with:
{
  "title": "Data Science Jobs - 2024"
}]

Result: Created spreadsheet "Data Science Jobs - 2024" 
        ID: 1NewSpreadsheetId123456789
        URL: https://docs.google.com/spreadsheets/d/1NewSpreadsheetId123456789
```

## 🔧 Testing the MCP Server

### Test MCP Server Directly
```bash
# Start the server
python -m linkedin_job_mcp.server

# In another terminal, test with MCP client tools
# (You'll need an MCP client to test this)
```

### Test with Python Script
```python
import asyncio
import json
from linkedin_job_mcp.server import server

async def test_search():
    # This would be called by an MCP client
    result = await server.call_tool(
        "search_linkedin_jobs",
        {
            "keywords": "Python developer",
            "location": "Remote",
            "max_jobs": 5
        }
    )
    print(json.dumps(result, indent=2))

# Run test
asyncio.run(test_search())
```

## 🚨 Important Notes

1. **Google Sheets Setup Required**: Make sure you have `credentials.json` configured for Google Sheets integration.

2. **Chrome Browser**: The server needs Chrome browser installed for LinkedIn scraping.

3. **Rate Limiting**: The server includes built-in delays to respect LinkedIn's servers.

4. **MCP Client Required**: You need an MCP-compatible client (like Claude Desktop) to use the server.

5. **Environment Variables**: Set up your `.env` file with necessary configurations.

## 🔍 Troubleshooting MCP Connection

### Common Issues:

1. **Server not starting**: Check Python path and dependencies
2. **Tools not available**: Verify MCP client configuration
3. **Google Sheets errors**: Check credentials.json file
4. **LinkedIn scraping fails**: Ensure Chrome is installed

### Debug Mode:
```bash
# Run with debug logging
PYTHONPATH=. python -m linkedin_job_mcp.server --debug
```

## 📚 Additional Resources

- [Model Context Protocol Documentation](https://modelcontextprotocol.io/)
- [Claude Desktop MCP Setup](https://claude.ai/docs/mcp)
- [Google Sheets API Setup](https://developers.google.com/sheets/api/quickstart/python)
