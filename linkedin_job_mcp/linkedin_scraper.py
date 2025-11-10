"""LinkedIn job scraper module."""

import asyncio
import time
import logging
from typing import List, Dict, Optional, Any
from urllib.parse import urlencode, quote
from dataclasses import dataclass
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re

from .config import config

logger = logging.getLogger(__name__)


@dataclass
class JobListing:
    """Represents a job listing from LinkedIn."""
    title: str
    company: str
    location: str
    description: str
    job_url: str
    posted_date: Optional[str] = None
    employment_type: Optional[str] = None
    experience_level: Optional[str] = None
    salary_range: Optional[str] = None


class LinkedInScraper:
    """LinkedIn job scraper using Selenium."""
    
    def __init__(self):
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        
    def _setup_driver(self) -> webdriver.Chrome:
        """Set up Chrome WebDriver with appropriate options."""
        chrome_options = Options()
        
        if config.chrome_headless:
            chrome_options.add_argument("--headless")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(f"--user-agent={config.chrome_user_agent}")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Install ChromeDriver automatically
        service = Service(ChromeDriverManager().install())
        
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    
    async def initialize(self):
        """Initialize the scraper."""
        try:
            self.driver = self._setup_driver()
            self.wait = WebDriverWait(self.driver, config.job_search_timeout)
            logger.info("LinkedIn scraper initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize LinkedIn scraper: {e}")
            raise
    
    async def close(self):
        """Close the scraper and clean up resources."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("LinkedIn scraper closed successfully")
            except Exception as e:
                logger.error(f"Error closing LinkedIn scraper: {e}")
    
    def _build_search_url(self, keywords: str, location: str = "", experience_level: str = "", 
                         employment_type: str = "", date_posted: str = "") -> str:
        """Build LinkedIn job search URL with parameters."""
        base_url = "https://www.linkedin.com/jobs/search"
        
        params = {
            "keywords": keywords,
            "location": location,
            "trk": "public_jobs_jobs-search-bar_search-submit",
            "position": "1",
            "pageNum": "0"
        }
        
        # Add optional filters
        filters = []
        if experience_level:
            exp_map = {
                "internship": "1",
                "entry": "2", 
                "associate": "3",
                "mid": "4",
                "director": "5",
                "executive": "6"
            }
            if experience_level.lower() in exp_map:
                filters.append(f"f_E={exp_map[experience_level.lower()]}")
        
        if employment_type:
            type_map = {
                "full-time": "F",
                "part-time": "P",
                "contract": "C",
                "temporary": "T",
                "internship": "I"
            }
            if employment_type.lower() in type_map:
                filters.append(f"f_JT={type_map[employment_type.lower()]}")
        
        if date_posted:
            date_map = {
                "past 24 hours": "r86400",
                "past week": "r604800",
                "past month": "r2592000"
            }
            if date_posted.lower() in date_map:
                filters.append(f"f_TPR={date_map[date_posted.lower()]}")
        
        if filters:
            params["f_LF"] = "f_AL"  # Easy Apply filter
            for filter_param in filters:
                key, value = filter_param.split("=")
                params[key] = value
        
        return f"{base_url}?{urlencode(params)}"
    
    def _extract_job_details(self, job_element) -> Optional[JobListing]:
        """Extract job details from a job listing element."""
        try:
            # Extract basic information
            title_element = job_element.find_element(By.CSS_SELECTOR, "h3.base-search-card__title a")
            title = title_element.text.strip()
            job_url = title_element.get_attribute("href")
            
            company_element = job_element.find_element(By.CSS_SELECTOR, "h4.base-search-card__subtitle a")
            company = company_element.text.strip()
            
            location_element = job_element.find_element(By.CSS_SELECTOR, "span.job-search-card__location")
            location = location_element.text.strip()
            
            # Try to extract posted date
            posted_date = None
            try:
                date_element = job_element.find_element(By.CSS_SELECTOR, "time.job-search-card__listdate")
                posted_date = date_element.get_attribute("datetime") or date_element.text.strip()
            except NoSuchElementException:
                pass
            
            # Get job description (this requires clicking on the job)
            description = self._get_job_description(job_url)
            
            return JobListing(
                title=title,
                company=company,
                location=location,
                description=description,
                job_url=job_url,
                posted_date=posted_date
            )
            
        except Exception as e:
            logger.error(f"Error extracting job details: {e}")
            return None
    
    def _get_job_description(self, job_url: str) -> str:
        """Get detailed job description by visiting the job page."""
        try:
            # Open job page in a new tab
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[1])
            self.driver.get(job_url)
            
            # Wait for job description to load
            try:
                description_element = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.show-more-less-html__markup"))
                )
                description = description_element.text.strip()
            except TimeoutException:
                # Fallback to other possible selectors
                try:
                    description_element = self.driver.find_element(By.CSS_SELECTOR, "div.description__text")
                    description = description_element.text.strip()
                except NoSuchElementException:
                    description = "Description not available"
            
            # Close the tab and switch back
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            
            return description
            
        except Exception as e:
            logger.error(f"Error getting job description: {e}")
            # Make sure we're back on the main tab
            if len(self.driver.window_handles) > 1:
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])
            return "Description not available"
    
    async def search_jobs(self, keywords: str, location: str = "", 
                         max_jobs: int = None, **filters) -> List[JobListing]:
        """Search for jobs on LinkedIn."""
        if not self.driver:
            await self.initialize()
        
        max_jobs = max_jobs or config.max_jobs_per_search
        jobs = []
        
        try:
            # Build search URL
            search_url = self._build_search_url(keywords, location, **filters)
            logger.info(f"Searching LinkedIn jobs: {search_url}")
            
            # Navigate to search page
            self.driver.get(search_url)
            
            # Wait for job listings to load
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.jobs-search__results-list"))
                )
            except TimeoutException:
                logger.warning("Job listings did not load within timeout")
                return jobs
            
            # Scroll to load more jobs
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            jobs_loaded = 0
            
            while jobs_loaded < max_jobs:
                # Scroll down
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                # Wait for new content to load
                await asyncio.sleep(2)
                
                # Check if more content loaded
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
                
                # Count current jobs
                job_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.base-card.relative.w-full.hover\\:no-underline.focus\\:no-underline.base-card--link.base-search-card.base-search-card--link.job-search-card")
                jobs_loaded = len(job_elements)
                
                logger.info(f"Loaded {jobs_loaded} job listings")
            
            # Extract job details
            job_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.base-card.relative.w-full.hover\\:no-underline.focus\\:no-underline.base-card--link.base-search-card.base-search-card--link.job-search-card")
            
            for i, job_element in enumerate(job_elements[:max_jobs]):
                if i > 0:
                    await asyncio.sleep(config.search_delay_seconds)
                
                job_listing = self._extract_job_details(job_element)
                if job_listing:
                    jobs.append(job_listing)
                    logger.info(f"Extracted job: {job_listing.title} at {job_listing.company}")
            
            logger.info(f"Successfully extracted {len(jobs)} job listings")
            return jobs
            
        except Exception as e:
            logger.error(f"Error searching LinkedIn jobs: {e}")
            raise
    
    def match_job_requirements(self, job: JobListing, requirements: List[str]) -> Dict[str, Any]:
        """Check if a job matches the given requirements."""
        job_text = f"{job.title} {job.description}".lower()
        
        matches = []
        for requirement in requirements:
            if requirement.lower() in job_text:
                matches.append(requirement)
        
        match_score = len(matches) / len(requirements) if requirements else 0
        
        return {
            "matches": matches,
            "match_score": match_score,
            "is_match": match_score >= 0.5  # At least 50% of requirements must match
        }


async def search_linkedin_jobs(keywords: str, location: str = "", 
                              requirements: List[str] = None, 
                              max_jobs: int = None, **filters) -> List[Dict[str, Any]]:
    """High-level function to search LinkedIn jobs and return matching results."""
    scraper = LinkedInScraper()
    
    try:
        await scraper.initialize()
        jobs = await scraper.search_jobs(keywords, location, max_jobs, **filters)
        
        results = []
        for job in jobs:
            job_data = {
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "description": job.description,
                "job_url": job.job_url,
                "posted_date": job.posted_date,
                "employment_type": job.employment_type,
                "experience_level": job.experience_level,
                "salary_range": job.salary_range
            }
            
            if requirements:
                match_info = scraper.match_job_requirements(job, requirements)
                job_data.update(match_info)
                
                # Only include jobs that match requirements
                if match_info["is_match"]:
                    results.append(job_data)
            else:
                results.append(job_data)
        
        return results
        
    finally:
        await scraper.close()