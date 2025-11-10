# LinkedIn Job Search API & MCP Server

A comprehensive job search solution that provides both a FastAPI web service and Model Context Protocol (MCP) server for searching LinkedIn jobs based on your requirements and automatically adding matching jobs to Google Sheets.

## 🌟 Features

### Web Interface & API
- 🌐 **Beautiful Web UI**: Responsive interface for easy job searching
- 🚀 **FastAPI REST API**: Full-featured API with OpenAPI documentation
- 📱 **Mobile Friendly**: Works on desktop, tablet, and mobile devices
- ⚡ **Async Processing**: Background job processing for large searches
- 📊 **Real-time Stats**: Live job search statistics and progress

### Core Functionality
- 🔍 **LinkedIn Job Search**: Search LinkedIn jobs by keywords, location, and filters
- 🎯 **Smart Job Matching**: Match jobs against specific requirements with scoring
- 📊 **Google Sheets Integration**: Automatically add matching jobs to spreadsheets
- 🚫 **Duplicate Prevention**: Filter out jobs already in your spreadsheet
- ⚙️ **Flexible Filtering**: Filter by experience level, employment type, and posting date
- 🤖 **MCP Compatible**: Works with any MCP-compatible AI assistant

## Installation

### Prerequisites

- Python 3.8 or higher
- Chrome browser (for web scraping)
- Google Cloud Project with Sheets API enabled
- Google service account credentials

### Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd linkedin-job-mcp-server
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Google Sheets API**:
   
   a. Go to the [Google Cloud Console](https://console.cloud.google.com/)
   
   b. Create a new project or select an existing one
   
   c. Enable the Google Sheets API:
      - Go to "APIs & Services" > "Library"
      - Search for "Google Sheets API"
      - Click "Enable"
   
   d. Create service account credentials:
      - Go to "APIs & Services" > "Credentials"
      - Click "Create Credentials" > "Service Account"
      - Fill in the details and create
      - Click on the created service account
      - Go to "Keys" tab > "Add Key" > "Create New Key"
      - Choose JSON format and download
   
   e. Save the downloaded JSON file as `credentials.json` in the project root

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` file with your settings:
   ```env
   GOOGLE_CREDENTIALS_PATH=credentials.json
   GOOGLE_SPREADSHEET_ID=your_spreadsheet_id_here
   CHROME_HEADLESS=true
   SEARCH_DELAY_SECONDS=2
   MAX_CONCURRENT_SEARCHES=3
   ```

## Usage

### 🌐 Web Interface (Recommended)

1. **Start the FastAPI server:**
   ```bash
   python run_server.py
   ```
   
2. **Open your browser and go to:**
   - **Web Interface**: http://localhost:8000
   - **API Documentation**: http://localhost:8000/docs
   - **Health Check**: http://localhost:8000/health

3. **Use the web interface to:**
   - Fill out the job search form
   - Set your requirements and filters
   - Create or specify a Google Spreadsheet
   - Click "Search Jobs" to start the search
   - View results and statistics in real-time

### 🚀 FastAPI REST API

#### Start the Server
```bash
# Basic usage
python run_server.py

# Custom host and port
python run_server.py --host 0.0.0.0 --port 8080

# Development mode with auto-reload
python run_server.py --reload
```

#### API Endpoints

**Search for Jobs:**
```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": "Python developer",
    "location": "San Francisco, CA",
    "requirements": ["Python", "Django", "REST API"],
    "max_jobs": 25,
    "experience_level": "mid",
    "employment_type": "full-time"
  }'
```

**Create a New Spreadsheet:**
```bash
curl -X POST "http://localhost:8000/spreadsheet/create" \
  -H "Content-Type: application/json" \
  -d '{"title": "Python Developer Jobs - 2024"}'
```

**Get Available Filters:**
```bash
curl "http://localhost:8000/jobs/filters"
```

**Health Check:**
```bash
curl "http://localhost:8000/health"
```

### 🤖 MCP Server Mode

```bash
python -m linkedin_job_mcp.server
```

The server will start and listen for MCP requests via stdio.

### Available Tools

#### 1. `search_linkedin_jobs`

Search for jobs on LinkedIn and optionally add them to Google Sheets.

**Parameters**:
- `keywords` (required): Job search keywords (e.g., "Python developer", "Data scientist")
- `location` (optional): Job location (e.g., "New York, NY", "Remote")
- `requirements` (optional): List of job requirements to match against
- `max_jobs` (optional): Maximum number of jobs to search (default: 25)
- `experience_level` (optional): Filter by experience level
- `employment_type` (optional): Filter by employment type
- `date_posted` (optional): Filter by posting date
- `spreadsheet_id` (optional): Google Spreadsheet ID to add jobs to
- `filter_duplicates` (optional): Filter out duplicate jobs (default: true)

**Example**:
```json
{
  "keywords": "Python developer",
  "location": "San Francisco, CA",
  "requirements": ["Python", "Django", "PostgreSQL", "AWS"],
  "max_jobs": 20,
  "experience_level": "mid",
  "employment_type": "full-time",
  "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
}
```

#### 2. `create_job_spreadsheet`

Create a new Google Spreadsheet for storing job listings.

**Parameters**:
- `title` (required): Title for the new spreadsheet

**Example**:
```json
{
  "title": "Python Developer Jobs - 2024"
}
```

#### 3. `get_spreadsheet_info`

Get information about an existing Google Spreadsheet.

**Parameters**:
- `spreadsheet_id` (required): Google Spreadsheet ID

**Example**:
```json
{
  "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
}
```

### Integration with AI Assistants

This MCP server can be integrated with AI assistants that support the Model Context Protocol. Here are some examples:

#### Claude Desktop

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "linkedin-job-search": {
      "command": "python",
      "args": ["-m", "linkedin_job_mcp.server"],
      "cwd": "/path/to/linkedin-job-mcp-server"
    }
  }
}
```

#### Example Conversation

```
User: "Find Python developer jobs in New York that require Django and React experience, and add them to my job spreadsheet"
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_CREDENTIALS_PATH` | Path to Google service account JSON file | `credentials.json` |
| `GOOGLE_SPREADSHEET_ID` | Default spreadsheet ID for job listings | None |
| `LINKEDIN_EMAIL` | LinkedIn email (optional, for authenticated searches) | None |
| `LINKEDIN_PASSWORD` | LinkedIn password (optional) | None |
| `CHROME_HEADLESS` | Run Chrome in headless mode | `true` |
| `CHROME_USER_AGENT` | User agent string for Chrome | Default Chrome UA |
| `SEARCH_DELAY_SECONDS` | Delay between searches to avoid rate limiting | `2.0` |
| `MAX_CONCURRENT_SEARCHES` | Maximum concurrent search operations | `3` |
| `MAX_JOBS_PER_SEARCH` | Maximum jobs to extract per search | `25` |
| `JOB_SEARCH_TIMEOUT` | Timeout for job search operations (seconds) | `30` |

### Google Sheets Setup

1. **Create a Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one

2. **Enable Google Sheets API**:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Sheets API" and enable it

3. **Create Service Account**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Download the JSON key file

4. **Share Spreadsheet** (if using existing spreadsheet):
   - Open your Google Spreadsheet
   - Click "Share" and add the service account email with "Editor" permissions

## Spreadsheet Format

The server creates spreadsheets with the following columns:

| Column | Description |
|--------|-------------|
| Job Title | Position title |
| Company | Company name |
| Location | Job location |
| Job URL | Direct link to LinkedIn job posting |
| Posted Date | When the job was posted |
| Employment Type | Full-time, Part-time, Contract, etc. |
| Experience Level | Entry, Mid, Senior, etc. |
| Salary Range | Salary information (if available) |
| Match Score | Percentage match against requirements |
| Matching Requirements | Which requirements were found |
| Description | Job description (truncated) |
| Date Added | When job was added to spreadsheet |

## Rate Limiting and Best Practices

- **Respect LinkedIn's Terms**: This tool is for personal job searching only
- **Rate Limiting**: Built-in delays prevent overwhelming LinkedIn's servers
- **Headless Mode**: Runs Chrome in headless mode by default for efficiency
- **Error Handling**: Robust error handling with retry mechanisms
- **Duplicate Prevention**: Automatically filters out jobs already in your spreadsheet

## Troubleshooting

### Common Issues

1. **Chrome Driver Issues**:
   ```bash
   # The server automatically downloads ChromeDriver, but if you encounter issues:
   pip install --upgrade webdriver-manager
   ```

2. **Google Sheets Authentication**:
   ```bash
   # Ensure your credentials.json file is valid and the Sheets API is enabled
   # Check that the service account has access to your spreadsheet
   ```

3. **LinkedIn Blocking**:
   ```bash
   # If LinkedIn blocks requests, try:
   # - Increasing SEARCH_DELAY_SECONDS
   # - Using a different user agent
   # - Running searches during off-peak hours
   ```

4. **Memory Issues**:
   ```bash
   # For large job searches, consider:
   # - Reducing MAX_JOBS_PER_SEARCH
   # - Running searches in smaller batches
   ```

### Debug Mode

Enable debug logging by setting the log level:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Development

### Project Structure

```
linkedin_job_mcp/
├── __init__.py          # Package initialization
├── server.py            # Main MCP server implementation
├── linkedin_scraper.py  # LinkedIn job scraping logic
├── sheets_client.py     # Google Sheets integration
├── config.py           # Configuration management
└── utils.py            # Utility functions
```

### Running Tests

```bash
# Install development dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## Security Considerations

- **Credentials**: Never commit credentials files to version control
- **Rate Limiting**: Respect LinkedIn's rate limits to avoid IP blocking
- **Personal Use**: This tool is intended for personal job searching only
- **Data Privacy**: Job data is only stored in your Google Spreadsheet

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for educational and personal use only. Users are responsible for complying with LinkedIn's Terms of Service and robots.txt. The authors are not responsible for any misuse or violations of third-party terms of service.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Search existing GitHub issues
3. Create a new issue with detailed information about your problem

## 🚀 Deployment

### Production Deployment

For production deployment, consider these options:

#### Docker Deployment
```dockerfile
FROM python:3.11-slim

# Install Chrome dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "run_server.py", "--host", "0.0.0.0", "--port", "8000"]
```

#### Cloud Deployment
- **Heroku**: Use the included `Procfile` and buildpacks
- **Railway**: Deploy directly from GitHub
- **Google Cloud Run**: Use the Docker image
- **AWS ECS**: Deploy with container service

#### Environment Variables for Production
```bash
CHROME_HEADLESS=true
SEARCH_DELAY_SECONDS=3
MAX_CONCURRENT_SEARCHES=2
GOOGLE_CREDENTIALS_PATH=/app/credentials.json
```

### Scaling Considerations

- Use Redis for background task queuing in production
- Implement rate limiting to respect LinkedIn's servers
- Consider using a proxy service for large-scale scraping
- Monitor Chrome memory usage and restart containers as needed

## Changelog

### v0.1.0
- Initial release
- LinkedIn job search functionality
- Google Sheets integration
- MCP server implementation
- Job requirement matching
- Duplicate prevention
- FastAPI web interface
- OpenAPI documentation
- Background job processing
