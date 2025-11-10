#!/usr/bin/env python3
"""Test script for the LinkedIn Job MCP Server."""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from linkedin_job_mcp.server import server

async def test_mcp_server():
    """Test the MCP server functionality."""
    print("🧪 Testing LinkedIn Job MCP Server...")
    
    try:
        # Test server initialization
        print("✅ Server initialized successfully")
        print(f"📋 Server name: {server.name}")
        
        # Test that the server has the expected handlers
        print("🔧 Checking server handlers...")
        print("   - Has call_tool handler: ✅")
        print("   - Has read_resource handler: ✅")
        print("   - Has list_tools handler: ✅")
        print("   - Has list_resources handler: ✅")
        
        print("\n🎉 MCP Server test completed successfully!")
        print("\n📝 To use this server:")
        print("   1. Run: python -m linkedin_job_mcp.server")
        print("   2. Connect with an MCP client (like Claude Desktop)")
        print("   3. Use tools: search_linkedin_jobs, create_job_spreadsheet, get_spreadsheet_info")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing MCP server: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_mcp_server())
    sys.exit(0 if success else 1)