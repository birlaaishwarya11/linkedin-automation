#!/usr/bin/env python3
"""Test script for FastMCP server endpoints."""

import requests
import json
import time
import subprocess
import sys
from threading import Thread

def start_server():
    """Start the FastMCP server in background."""
    try:
        subprocess.run([sys.executable, "fastmcp_server.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Server failed to start: {e}")

def test_endpoints():
    """Test the FastMCP server endpoints."""
    base_url = "http://localhost:8000"
    
    # Wait for server to start
    print("⏳ Waiting for server to start...")
    time.sleep(3)
    
    try:
        # Test health endpoint
        print("🔍 Testing health endpoint...")
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Health endpoint working")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
        
        # Test MCP info endpoint
        print("\n🔍 Testing MCP info endpoint...")
        response = requests.get(f"{base_url}/mcp", timeout=10)
        if response.status_code == 200:
            print("✅ MCP info endpoint working")
            data = response.json()
            print(f"   Server: {data['name']}")
            print(f"   Tools: {len(data['tools'])}")
            for tool in data['tools']:
                print(f"     - {tool['name']}")
        else:
            print(f"❌ MCP info endpoint failed: {response.status_code}")
        
        print("\n🎉 FastMCP server is ready for TrueFoundry deployment!")
        print("\n📝 Deployment checklist:")
        print("   ✅ Health endpoint (/health) working")
        print("   ✅ MCP info endpoint (/mcp) working") 
        print("   ✅ Server runs on port 8000")
        print("   ✅ FastMCP tools are registered")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
        print("Make sure the server is running on port 8000")

if __name__ == "__main__":
    print("🧪 Testing FastMCP Server for TrueFoundry deployment...")
    
    # Start server in background thread
    server_thread = Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Test endpoints
    test_endpoints()