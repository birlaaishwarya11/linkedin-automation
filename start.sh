#!/bin/bash

# LinkedIn Job Search API Startup Script
# Usage: ./start.sh [port] [--reload]

PORT=${1:-8000}
RELOAD_FLAG=""

# Check if --reload flag is passed
if [[ "$*" == *"--reload"* ]]; then
    RELOAD_FLAG="--reload"
fi

echo "🚀 Starting LinkedIn Job Search API..."
echo "📍 Server will be available at: http://localhost:$PORT"
echo "📚 API Documentation: http://localhost:$PORT/docs"
echo "🔍 Web Interface: http://localhost:$PORT"
echo ""

# Start the server
uvicorn main:app --host 0.0.0.0 --port $PORT $RELOAD_FLAG