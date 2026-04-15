#!/bin/bash
set -e

cd "$(dirname "$0")"

if [ ! -f ".env" ]; then
  echo "Error: .env file not found. Copy .env.example and fill in your keys."
  exit 1
fi

# When running from a git worktree the venv lives in the main checkout.
# Fall back to the main worktree path if no local venv is found.
VENV_PATH="venv"
if [ ! -d "$VENV_PATH" ]; then
  MAIN_ROOT=$(git worktree list 2>/dev/null | head -1 | awk '{print $1}')
  if [ -d "$MAIN_ROOT/venv" ]; then
    VENV_PATH="$MAIN_ROOT/venv"
  else
    echo "Error: no virtual environment found. Run: python3 -m venv venv && pip install -r requirements.txt"
    exit 1
  fi
fi

source "$VENV_PATH/bin/activate"

echo "Starting DeepRaven backend..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 5100
