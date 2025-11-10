#!/usr/bin/env python3
"""Test script to verify the LinkedIn Job MCP Server setup."""

import sys
import os
import asyncio
import logging
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from linkedin_job_mcp.config import config
from linkedin_job_mcp.linkedin_scraper import LinkedInScraper
from linkedin_job_mcp.sheets_client import GoogleSheetsClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_imports():
    """Test that all modules can be imported."""
    try:
        from linkedin_job_mcp import server, linkedin_scraper, sheets_client, config, utils
        logger.info("✅ All modules imported successfully")
        return True
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        return False


def test_config():
    """Test configuration loading."""
    try:
        logger.info(f"Chrome headless: {config.chrome_headless}")
        logger.info(f"Search delay: {config.search_delay_seconds}")
        logger.info(f"Max jobs per search: {config.max_jobs_per_search}")
        logger.info(f"Google credentials path: {config.google_credentials_path}")
        logger.info("✅ Configuration loaded successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Configuration error: {e}")
        return False


def test_chrome_driver():
    """Test Chrome WebDriver setup."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        
        # Test ChromeDriver installation
        driver_path = ChromeDriverManager().install()
        logger.info(f"ChromeDriver installed at: {driver_path}")
        
        # Test Chrome options
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        logger.info("✅ Chrome WebDriver setup successful")
        return True
    except Exception as e:
        logger.error(f"❌ Chrome WebDriver error: {e}")
        return False


def test_google_credentials():
    """Test Google Sheets credentials."""
    try:
        credentials_path = config.google_credentials_path
        if os.path.exists(credentials_path):
            logger.info(f"✅ Google credentials file found: {credentials_path}")
            
            # Try to initialize the client (without making API calls)
            client = GoogleSheetsClient()
            logger.info("✅ Google Sheets client can be initialized")
            return True
        else:
            logger.warning(f"⚠️  Google credentials file not found: {credentials_path}")
            logger.info("This is expected if you haven't set up Google Sheets API yet")
            return True
    except Exception as e:
        logger.error(f"❌ Google credentials error: {e}")
        return False


async def test_linkedin_scraper_init():
    """Test LinkedIn scraper initialization."""
    try:
        scraper = LinkedInScraper()
        logger.info("✅ LinkedIn scraper can be created")
        
        # Test URL building
        url = scraper._build_search_url("python developer", "New York")
        logger.info(f"Sample search URL: {url}")
        logger.info("✅ LinkedIn scraper URL building works")
        
        return True
    except Exception as e:
        logger.error(f"❌ LinkedIn scraper error: {e}")
        return False


def test_mcp_server():
    """Test MCP server components."""
    try:
        from linkedin_job_mcp.server import server, handle_list_tools, handle_list_resources
        
        logger.info("✅ MCP server components imported successfully")
        return True
    except Exception as e:
        logger.error(f"❌ MCP server error: {e}")
        return False


async def main():
    """Run all tests."""
    logger.info("🚀 Starting LinkedIn Job MCP Server setup test")
    logger.info("=" * 50)
    
    tests = [
        ("Module Imports", test_imports),
        ("Configuration", test_config),
        ("Chrome WebDriver", test_chrome_driver),
        ("Google Credentials", test_google_credentials),
        ("LinkedIn Scraper", test_linkedin_scraper_init),
        ("MCP Server", test_mcp_server),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n🧪 Testing: {test_name}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"❌ Test {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("📊 TEST SUMMARY")
    logger.info("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
        if result:
            passed += 1
    
    logger.info(f"\nTests passed: {passed}/{len(results)}")
    
    if passed == len(results):
        logger.info("🎉 All tests passed! Your setup looks good.")
        logger.info("\nNext steps:")
        logger.info("1. Set up Google Sheets API credentials if you haven't already")
        logger.info("2. Create a .env file with your configuration")
        logger.info("3. Run the MCP server: python -m linkedin_job_mcp.server")
    else:
        logger.warning("⚠️  Some tests failed. Please check the errors above.")
        logger.info("\nFor help, see the README.md file or check the troubleshooting section.")
    
    return passed == len(results)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)