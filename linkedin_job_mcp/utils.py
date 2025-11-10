"""Utility functions for the LinkedIn Job MCP Server."""

import logging
import sys
from typing import Any, Dict, List, Optional
from functools import wraps
import asyncio
from datetime import datetime


def setup_logging(level: str = "INFO", log_file: Optional[str] = None):
    """Set up logging configuration."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Suppress noisy third-party loggers
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('googleapiclient').setLevel(logging.WARNING)


def retry_async(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator for retrying async functions with exponential backoff."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt == max_retries:
                        break
                    
                    logging.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                        f"Retrying in {current_delay} seconds..."
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            
            raise last_exception
        return wrapper
    return decorator


def validate_url(url: str) -> bool:
    """Validate if a string is a valid URL."""
    import re
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None


def sanitize_filename(filename: str) -> str:
    """Sanitize a string to be safe for use as a filename."""
    import re
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing whitespace and dots
    filename = filename.strip(' .')
    # Limit length
    if len(filename) > 255:
        filename = filename[:255]
    return filename


def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """Truncate text to a maximum length."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_job_for_display(job: Dict[str, Any], include_description: bool = True) -> str:
    """Format a job dictionary for human-readable display."""
    lines = []
    
    # Title and company
    lines.append(f"**{job.get('title', 'Unknown Title')}** at **{job.get('company', 'Unknown Company')}**")
    
    # Location
    if job.get('location'):
        lines.append(f"📍 {job['location']}")
    
    # URL
    if job.get('job_url'):
        lines.append(f"🔗 {job['job_url']}")
    
    # Posted date
    if job.get('posted_date'):
        lines.append(f"📅 Posted: {job['posted_date']}")
    
    # Employment details
    details = []
    if job.get('employment_type'):
        details.append(job['employment_type'])
    if job.get('experience_level'):
        details.append(job['experience_level'])
    if job.get('salary_range'):
        details.append(job['salary_range'])
    
    if details:
        lines.append(f"💼 {' | '.join(details)}")
    
    # Match information
    if job.get('match_score') is not None:
        lines.append(f"✅ Match Score: {job['match_score']:.1%}")
    
    if job.get('matches'):
        lines.append(f"🎯 Matching Requirements: {', '.join(job['matches'])}")
    
    # Description
    if include_description and job.get('description'):
        description = truncate_text(job['description'], 300)
        lines.append(f"📝 {description}")
    
    return '\n'.join(lines)


def validate_spreadsheet_id(spreadsheet_id: str) -> bool:
    """Validate Google Spreadsheet ID format."""
    import re
    # Google Spreadsheet IDs are typically 44 characters long and contain letters, numbers, hyphens, and underscores
    pattern = r'^[a-zA-Z0-9-_]{44}$'
    return bool(re.match(pattern, spreadsheet_id))


def parse_job_requirements(requirements_text: str) -> List[str]:
    """Parse job requirements from text input."""
    if not requirements_text:
        return []
    
    # Split by common delimiters
    import re
    requirements = re.split(r'[,;\n]', requirements_text)
    
    # Clean up each requirement
    cleaned_requirements = []
    for req in requirements:
        req = req.strip()
        if req:
            cleaned_requirements.append(req)
    
    return cleaned_requirements


def calculate_match_score(job_text: str, requirements: List[str]) -> Dict[str, Any]:
    """Calculate how well a job matches the given requirements."""
    if not requirements:
        return {
            "matches": [],
            "match_score": 1.0,
            "is_match": True
        }
    
    job_text_lower = job_text.lower()
    matches = []
    
    for requirement in requirements:
        if requirement.lower() in job_text_lower:
            matches.append(requirement)
    
    match_score = len(matches) / len(requirements)
    
    return {
        "matches": matches,
        "match_score": match_score,
        "is_match": match_score >= 0.5  # At least 50% match required
    }


def get_current_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now().isoformat()


class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, max_calls: int, time_window: float):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
    
    async def acquire(self):
        """Acquire permission to make a call."""
        now = asyncio.get_event_loop().time()
        
        # Remove old calls outside the time window
        self.calls = [call_time for call_time in self.calls if now - call_time < self.time_window]
        
        # Check if we can make a new call
        if len(self.calls) >= self.max_calls:
            # Calculate how long to wait
            oldest_call = min(self.calls)
            wait_time = self.time_window - (now - oldest_call)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        
        # Record this call
        self.calls.append(now)


def create_error_response(error: Exception, context: str = "") -> Dict[str, Any]:
    """Create a standardized error response."""
    return {
        "success": False,
        "error": str(error),
        "error_type": type(error).__name__,
        "context": context,
        "timestamp": get_current_timestamp()
    }


def create_success_response(data: Any, message: str = "") -> Dict[str, Any]:
    """Create a standardized success response."""
    return {
        "success": True,
        "data": data,
        "message": message,
        "timestamp": get_current_timestamp()
    }