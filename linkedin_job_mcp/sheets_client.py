"""Google Sheets integration module."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .config import config

logger = logging.getLogger(__name__)

# Google Sheets API scope
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


class GoogleSheetsClient:
    """Google Sheets API client for managing job data."""
    
    def __init__(self, spreadsheet_id: Optional[str] = None):
        self.spreadsheet_id = spreadsheet_id or config.google_spreadsheet_id
        self.service = None
        self.credentials = None
        
    def _authenticate(self):
        """Authenticate with Google Sheets API."""
        creds = None
        
        # Check if service account credentials file exists
        if os.path.exists(config.google_credentials_path):
            try:
                creds = ServiceAccountCredentials.from_service_account_file(
                    config.google_credentials_path, scopes=SCOPES
                )
                logger.info("Authenticated using service account credentials")
            except Exception as e:
                logger.error(f"Failed to load service account credentials: {e}")
                raise
        else:
            # Fallback to OAuth flow (for user credentials)
            token_path = "token.json"
            
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(config.google_credentials_path):
                        raise FileNotFoundError(
                            f"Google credentials file not found: {config.google_credentials_path}. "
                            "Please download your credentials from Google Cloud Console."
                        )
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        config.google_credentials_path, SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                
                # Save credentials for next run
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
        
        self.credentials = creds
        self.service = build('sheets', 'v4', credentials=creds)
        logger.info("Google Sheets API client initialized successfully")
    
    def initialize(self):
        """Initialize the Google Sheets client."""
        if not self.service:
            self._authenticate()
    
    def create_spreadsheet(self, title: str) -> str:
        """Create a new spreadsheet and return its ID."""
        self.initialize()
        
        try:
            spreadsheet = {
                'properties': {
                    'title': title
                },
                'sheets': [{
                    'properties': {
                        'title': 'Job Listings',
                        'gridProperties': {
                            'rowCount': 1000,
                            'columnCount': 20
                        }
                    }
                }]
            }
            
            result = self.service.spreadsheets().create(body=spreadsheet).execute()
            spreadsheet_id = result.get('spreadsheetId')
            
            # Set up headers
            self._setup_headers(spreadsheet_id)
            
            logger.info(f"Created new spreadsheet: {title} (ID: {spreadsheet_id})")
            return spreadsheet_id
            
        except HttpError as e:
            logger.error(f"Failed to create spreadsheet: {e}")
            raise
    
    def _setup_headers(self, spreadsheet_id: str = None):
        """Set up column headers in the spreadsheet."""
        spreadsheet_id = spreadsheet_id or self.spreadsheet_id
        
        headers = [
            "Job Title",
            "Company",
            "Location", 
            "Job URL",
            "Posted Date",
            "Employment Type",
            "Experience Level",
            "Salary Range",
            "Match Score",
            "Matching Requirements",
            "Description",
            "Date Added"
        ]
        
        try:
            # Clear existing headers and add new ones
            range_name = "Job Listings!A1:L1"
            body = {
                'values': [headers]
            }
            
            self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            # Format headers (bold)
            format_body = {
                "requests": [{
                    "repeatCell": {
                        "range": {
                            "sheetId": 0,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": len(headers)
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "textFormat": {
                                    "bold": True
                                },
                                "backgroundColor": {
                                    "red": 0.9,
                                    "green": 0.9,
                                    "blue": 0.9
                                }
                            }
                        },
                        "fields": "userEnteredFormat(textFormat,backgroundColor)"
                    }
                }]
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=format_body
            ).execute()
            
            logger.info("Headers set up successfully")
            
        except HttpError as e:
            logger.error(f"Failed to set up headers: {e}")
            raise
    
    def add_jobs(self, jobs: List[Dict[str, Any]], spreadsheet_id: str = None) -> int:
        """Add job listings to the spreadsheet."""
        self.initialize()
        spreadsheet_id = spreadsheet_id or self.spreadsheet_id
        
        if not spreadsheet_id:
            raise ValueError("No spreadsheet ID provided")
        
        if not jobs:
            logger.warning("No jobs to add")
            return 0
        
        try:
            # Get current data to find next empty row
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range="Job Listings!A:A"
            ).execute()
            
            values = result.get('values', [])
            next_row = len(values) + 1
            
            # Prepare job data for insertion
            job_rows = []
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            for job in jobs:
                row = [
                    job.get('title', ''),
                    job.get('company', ''),
                    job.get('location', ''),
                    job.get('job_url', ''),
                    job.get('posted_date', ''),
                    job.get('employment_type', ''),
                    job.get('experience_level', ''),
                    job.get('salary_range', ''),
                    job.get('match_score', ''),
                    ', '.join(job.get('matches', [])),
                    job.get('description', '')[:1000] + '...' if len(job.get('description', '')) > 1000 else job.get('description', ''),  # Truncate long descriptions
                    current_time
                ]
                job_rows.append(row)
            
            # Insert data
            range_name = f"Job Listings!A{next_row}:L{next_row + len(job_rows) - 1}"
            body = {
                'values': job_rows
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            updated_cells = result.get('updatedCells', 0)
            logger.info(f"Added {len(job_rows)} jobs to spreadsheet ({updated_cells} cells updated)")
            
            return len(job_rows)
            
        except HttpError as e:
            logger.error(f"Failed to add jobs to spreadsheet: {e}")
            raise
    
    def get_existing_jobs(self, spreadsheet_id: str = None) -> List[str]:
        """Get list of existing job URLs to avoid duplicates."""
        self.initialize()
        spreadsheet_id = spreadsheet_id or self.spreadsheet_id
        
        if not spreadsheet_id:
            return []
        
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range="Job Listings!D:D"  # Job URL column
            ).execute()
            
            values = result.get('values', [])
            # Skip header row and extract URLs
            existing_urls = [row[0] for row in values[1:] if row]
            
            logger.info(f"Found {len(existing_urls)} existing job URLs")
            return existing_urls
            
        except HttpError as e:
            logger.error(f"Failed to get existing jobs: {e}")
            return []
    
    def filter_new_jobs(self, jobs: List[Dict[str, Any]], spreadsheet_id: str = None) -> List[Dict[str, Any]]:
        """Filter out jobs that already exist in the spreadsheet."""
        existing_urls = set(self.get_existing_jobs(spreadsheet_id))
        
        new_jobs = []
        for job in jobs:
            if job.get('job_url') not in existing_urls:
                new_jobs.append(job)
        
        logger.info(f"Filtered {len(jobs)} jobs down to {len(new_jobs)} new jobs")
        return new_jobs
    
    def get_spreadsheet_info(self, spreadsheet_id: str = None) -> Dict[str, Any]:
        """Get information about the spreadsheet."""
        self.initialize()
        spreadsheet_id = spreadsheet_id or self.spreadsheet_id
        
        if not spreadsheet_id:
            raise ValueError("No spreadsheet ID provided")
        
        try:
            result = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            return {
                'title': result.get('properties', {}).get('title', ''),
                'url': f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
                'sheets': [sheet.get('properties', {}).get('title', '') for sheet in result.get('sheets', [])]
            }
            
        except HttpError as e:
            logger.error(f"Failed to get spreadsheet info: {e}")
            raise


async def add_jobs_to_sheets(jobs: List[Dict[str, Any]], spreadsheet_id: str = None, 
                           filter_duplicates: bool = True) -> Dict[str, Any]:
    """High-level function to add jobs to Google Sheets."""
    client = GoogleSheetsClient(spreadsheet_id)
    
    try:
        client.initialize()
        
        if filter_duplicates:
            jobs = client.filter_new_jobs(jobs, spreadsheet_id)
        
        if not jobs:
            return {
                'success': True,
                'jobs_added': 0,
                'message': 'No new jobs to add'
            }
        
        jobs_added = client.add_jobs(jobs, spreadsheet_id)
        spreadsheet_info = client.get_spreadsheet_info(spreadsheet_id)
        
        return {
            'success': True,
            'jobs_added': jobs_added,
            'spreadsheet_url': spreadsheet_info['url'],
            'message': f'Successfully added {jobs_added} jobs to spreadsheet'
        }
        
    except Exception as e:
        logger.error(f"Failed to add jobs to sheets: {e}")
        return {
            'success': False,
            'jobs_added': 0,
            'error': str(e),
            'message': f'Failed to add jobs to spreadsheet: {e}'
        }