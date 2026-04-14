#!/bin/bash
set -e

cd "$(dirname "$0")"

if [ ! -f ".env" ]; then
  echo "Error: .env file not found. Copy .env.example and fill in your keys."
  exit 1
fi

source venv/bin/activate

echo "Starting DeepRaven backend..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 5100
