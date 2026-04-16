#!/bin/bash
set -e

cd "$(dirname "$0")"

if [ ! -f ".env" ]; then
  echo "Error: .env file not found. Copy .env.example and fill in your keys."
  exit 1
fi

if [ ! -d "venv" ]; then
  echo "No virtual environment found — creating one and installing dependencies..."
  python3 -m venv venv
  venv/bin/pip install -r requirements.txt
fi

source venv/bin/activate

echo "Starting DeepRaven backend..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 5100
