#!/usr/bin/env bash
set -e

# Change to the root directory of the project
cd "$(dirname "$0")/../.."

echo -e "\033[0;34mStarting UnmessIt.AI Development Environment...\033[0m"

# Trap to ensure background processes are killed when this script exits
trap 'echo -e "\n\033[0;31mStopping services...\033[0m"; kill $SERVER_PID $WEB_PID 2>/dev/null || true' EXIT INT TERM

# Start web client in the background and discard its output (or pipe to a log file if needed)
echo "Starting web client on http://localhost:2831 (logs hidden)"
cd web
npm run dev > /dev/null 2>&1 &
WEB_PID=$!
cd ..

# Start backend server in the foreground so its logs are fully visible
echo "Starting backend server on http://localhost:2317"
echo "Server logs will appear below:"
echo "----------------------------------------"
cd server
source .venv/bin/activate 2>/dev/null || true
uvicorn src.main:create_app --reload --port 2317 &
SERVER_PID=$!
cd ..

# Wait for both to finish (which won't happen unless they crash or user presses Ctrl+C)
wait $SERVER_PID $WEB_PID
