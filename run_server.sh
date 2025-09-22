#!/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
  export $(cat .env | sed 's/#.*//g' | xargs)
fi

# Activate virtual environment
source venv/bin/activate

# Start the FastAPI server
echo "Starting FastAPI server on http://127.0.0.1:8000"
uvicorn src.main:app --host 127.0.0.1 --port 8000
