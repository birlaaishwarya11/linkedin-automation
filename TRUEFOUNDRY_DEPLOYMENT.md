# TrueFoundry Deployment Guide for LinkedIn Job Search MCP Server

This guide shows you how to deploy the LinkedIn Job Search MCP Server on TrueFoundry using FastMCP.

## 🚀 Quick Deployment Steps

### 1. Prerequisites

- TrueFoundry account on `https://demo.truefoundry.cloud`
- TrueFoundry CLI installed: `pip install -U "truefoundry"`
- Login: `tfy login --host "https://demo.truefoundry.cloud"`

### 2. Deployment Configuration

Use these settings when deploying on TrueFoundry:

**Application Type:** Service  
**Runtime:** Python  
**Main File:** `fastmcp_server.py`  
**Command:** `python fastmcp_server.py`  
**Port:** `8000`  
**Health Check Path:** `/health`  

### 3. Environment Variables

Set these environment variables in TrueFoundry:

```bash
# Google Sheets API (Required)
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json

# Optional: LinkedIn scraping settings
LINKEDIN_EMAIL=your_email@example.com
LINKEDIN_PASSWORD=your_password
HEADLESS_BROWSER=true
```

### 4. Files to Upload

Make sure these files are included in your deployment:

```
fastmcp_server.py          # Main FastMCP server
linkedin_job_mcp/          # Core package
├── __init__.py
├── server.py
├── linkedin_scraper.py
├── sheets_client.py
├── config.py
└── utils.py
requirements.txt           # Dependencies
credentials.json           # Google Sheets credentials (if using)
.env                      # Environment variables (optional)
```

## 🔧 MCP Server Endpoints

Once deployed, your MCP server will be available at:

### Health Check
```
GET https://your-deployment-url/health
```
Response:
```json
{
  "status": "healthy",
  "service": "linkedin-job-search-mcp"
}
```

### MCP Information
```
GET https://your-deployment-url/mcp
```
Response:
```json
{
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
```

### MCP Protocol Endpoint
```
WebSocket: wss://your-deployment-url/mcp/ws
HTTP: https://your-deployment-url/mcp/http
```

## 🛠️ Available MCP Tools

### 1. `search_linkedin_jobs_tool`

Search LinkedIn jobs and optionally add to Google Sheets.

**Parameters:**
- `keywords` (string, required): Job search keywords
- `location` (string, optional): Job location
- `requirements` (array, optional): List of job requirements
- `max_jobs` (integer, optional): Maximum jobs to search (default: 25)
- `experience_level` (string, optional): Experience level filter
- `employment_type` (string, optional): Employment type filter
- `date_posted` (string, optional): Date posted filter
- `spreadsheet_id` (string, optional): Google Sheets ID
- `filter_duplicates` (boolean, optional): Filter duplicates (default: true)

**Example Usage:**
```json
{
  "tool": "search_linkedin_jobs_tool",
  "arguments": {
    "keywords": "Python developer",
    "location": "San Francisco, CA",
    "requirements": ["Python", "Django", "REST API"],
    "max_jobs": 25,
    "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
  }
}
```

### 2. `create_job_spreadsheet`

Create a new Google Spreadsheet for job storage.

**Parameters:**
- `title` (string, required): Spreadsheet title

**Example Usage:**
```json
{
  "tool": "create_job_spreadsheet",
  "arguments": {
    "title": "Python Developer Jobs - 2024"
  }
}
```

### 3. `get_spreadsheet_info`

Get information about an existing spreadsheet.

**Parameters:**
- `spreadsheet_id` (string, required): Google Sheets ID

**Example Usage:**
```json
{
  "tool": "get_spreadsheet_info",
  "arguments": {
    "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
  }
}
```

## 🔌 Connecting AI Clients

### Claude Desktop Configuration

Add this to your Claude Desktop config:

```json
{
  "mcpServers": {
    "linkedin-job-search": {
      "url": "https://your-deployment-url/mcp"
    }
  }
}
```

### Other MCP Clients

Use these connection details:
- **Server URL:** `https://your-deployment-url/mcp`
- **Protocol:** HTTP or WebSocket
- **Authentication:** None (for demo deployment)

## 🧪 Testing Your Deployment

### 1. Test Health Check
```bash
curl https://your-deployment-url/health
```

### 2. Test MCP Info
```bash
curl https://your-deployment-url/mcp
```

### 3. Test with MCP Inspector
```bash
npx @modelcontextprotocol/inspector https://your-deployment-url/mcp
```

### 4. Test Tools with AI Client

Connect Claude Desktop or another MCP client and try:

```
"Search for Python developer jobs in New York and add them to a new spreadsheet"
```

## 🚨 Troubleshooting

### Common Issues

1. **Tools not visible in AI client**
   - Check that `/mcp` endpoint returns tool information
   - Verify MCP client configuration
   - Ensure deployment is accessible

2. **Google Sheets errors**
   - Upload `credentials.json` file
   - Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable
   - Check Google Sheets API is enabled

3. **LinkedIn scraping fails**
   - Ensure Chrome is installed in container
   - Set `HEADLESS_BROWSER=true`
   - Check rate limiting

4. **Health check fails**
   - Verify `/health` endpoint responds
   - Check server logs in TrueFoundry dashboard
   - Ensure port 8000 is exposed

### Debug Mode

Add this environment variable for detailed logging:
```bash
LOG_LEVEL=DEBUG
```

## 📊 Monitoring

Monitor your deployment using:

1. **TrueFoundry Dashboard:** Check logs, metrics, and health status
2. **Health Endpoint:** Regular health checks at `/health`
3. **MCP Endpoint:** Verify tools are available at `/mcp`

## 🔒 Security Notes

This deployment uses **no authentication** for simplicity. For production:

1. Enable TrueFoundry MCP Gateway Authentication
2. Use secure environment variable storage
3. Implement rate limiting
4. Add input validation

## 📚 Additional Resources

- [TrueFoundry MCP Documentation](https://docs.truefoundry.com/gateway/mcp-gateway-auth-security)
- [FastMCP Documentation](https://gofastmcp.com/)
- [Model Context Protocol](https://modelcontextprotocol.io/)

## 🎯 Next Steps

1. Deploy the server on TrueFoundry
2. Test the `/health` and `/mcp` endpoints
3. Connect your AI client (Claude Desktop, etc.)
4. Start searching for jobs with natural language commands!

Example conversation with AI client:
```
User: "Find senior Python developer jobs in San Francisco that require Django and PostgreSQL. Create a new spreadsheet and add the top 20 matches."

AI: I'll help you search for senior Python developer jobs in San Francisco. Let me create a spreadsheet first and then search for jobs matching your requirements.

[AI uses create_job_spreadsheet and search_linkedin_jobs_tool]

Result: Created spreadsheet "Senior Python Jobs - SF" and found 18 matching jobs!
```