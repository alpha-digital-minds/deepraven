#!/bin/bash
set -e

cd "$(dirname "$0")"

if [ ! -f ".env" ]; then
  echo "Error: .env file not found. Copy .env.example and fill in your keys."
  exit 1
fi

# Locate or create the virtual environment.
# git rev-parse --git-common-dir returns ".git" in the main checkout (relative)
# and the absolute path to the shared .git dir when inside a worktree — so
# $GIT_COMMON/../venv always resolves to the main checkout's venv.
VENV_PATH="venv"

if [ ! -d "$VENV_PATH" ]; then
  GIT_COMMON=$(git rev-parse --git-common-dir 2>/dev/null || echo "")
  MAIN_VENV="$GIT_COMMON/../venv"
  if [ -n "$GIT_COMMON" ] && [ -d "$MAIN_VENV" ]; then
    VENV_PATH="$MAIN_VENV"
  else
    echo "No virtual environment found — creating one and installing dependencies..."
    python3 -m venv venv
    venv/bin/pip install -r requirements.txt
  fi
fi

source "$VENV_PATH/bin/activate"

echo "Starting DeepRaven backend..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 5100
