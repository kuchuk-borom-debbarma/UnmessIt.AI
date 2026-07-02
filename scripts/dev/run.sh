#!/usr/bin/env bash
set -e

# Change to the root directory of the project
cd "$(dirname "$0")/../.."

echo -e "\033[0;34mStarting UnmessIt.AI Development Environment...\033[0m"

REDIS_CONTAINER="unmessit-dev-redis"
REDIS_PORT="${UNMESSIT_DEV_REDIS_PORT:-6381}"
STARTED_REDIS=0
SERVER_PID=""
WEB_PID=""
LOG_DIR=".dev-logs"
mkdir -p "$LOG_DIR"

kill_tree() {
    local pid="$1"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        pkill -TERM -P "$pid" 2>/dev/null || true
        kill "$pid" 2>/dev/null || true
    fi
}

cleanup() {
    echo -e "\n\033[0;31mStopping services...\033[0m"
    kill_tree "$SERVER_PID"
    kill_tree "$WEB_PID"
    if [ "$STARTED_REDIS" = "1" ]; then
        docker stop "$REDIS_CONTAINER" >/dev/null 2>&1 || true
    fi
}

port_in_use() {
    "${PYTHON_BIN:-python3}" - "$1" <<'PY'
import socket
import sys

with socket.socket() as s:
    s.settimeout(0.2)
    raise SystemExit(0 if s.connect_ex(("127.0.0.1", int(sys.argv[1]))) == 0 else 1)
PY
}

if port_in_use 2831; then
    echo "Port 2831 is already in use. Stop the existing web dev server first."
    exit 1
fi

if port_in_use 2317; then
    echo "Port 2317 is already in use. Stop the existing backend server first."
    exit 1
fi

if [ -z "${REDIS_URL:-}" ]; then
    if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
        if ! docker ps --format '{{.Names}}' | grep -qx "$REDIS_CONTAINER"; then
            if port_in_use "$REDIS_PORT"; then
                echo "Port $REDIS_PORT is already in use. Set UNMESSIT_DEV_REDIS_PORT to another free port."
                exit 1
            fi
            docker rm -f "$REDIS_CONTAINER" >/dev/null 2>&1 || true
            echo "Starting Redis on redis://localhost:$REDIS_PORT/0"
            docker run --rm -d --name "$REDIS_CONTAINER" -p "$REDIS_PORT:6379" redis:7-alpine >/dev/null
            STARTED_REDIS=1
        else
            echo "Using existing Redis container $REDIS_CONTAINER"
        fi
        export REDIS_URL="redis://localhost:$REDIS_PORT/0"
        for _ in {1..30}; do
            if port_in_use "$REDIS_PORT"; then
                break
            fi
            sleep 0.2
        done
        if ! port_in_use "$REDIS_PORT"; then
            echo "Redis did not become reachable on port $REDIS_PORT."
            exit 1
        fi
    else
        echo "Docker is unavailable; backend will use in-memory events/SSE."
    fi
else
    echo "Using REDIS_URL=$REDIS_URL"
fi

# Trap to ensure background processes are killed when this script exits.
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

echo "Starting web client on http://localhost:2831 (logs: $LOG_DIR/web.log)"
cd web
npm run dev > "../$LOG_DIR/web.log" 2>&1 &
WEB_PID=$!
cd ..
sleep 1
if ! kill -0 "$WEB_PID" 2>/dev/null; then
    echo "Web client failed to start. Port 2831 may already be in use."
    tail -n 40 "$LOG_DIR/web.log" 2>/dev/null || true
    exit 1
fi

# Start backend server with visible logs.
echo "Starting backend server on http://localhost:2317"
echo "Server logs will appear below:"
echo "----------------------------------------"
cd server
source .venv/bin/activate 2>/dev/null || true
uvicorn src.main:create_app --reload --port 2317 &
SERVER_PID=$!
cd ..
sleep 1
if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "Backend server failed to start. Port 2317 may already be in use."
    exit 1
fi

while kill -0 "$SERVER_PID" 2>/dev/null && kill -0 "$WEB_PID" 2>/dev/null; do
    sleep 1
done

if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "Backend server stopped."
fi

if ! kill -0 "$WEB_PID" 2>/dev/null; then
    echo "Web client stopped. Last web log lines:"
    tail -n 40 "$LOG_DIR/web.log" 2>/dev/null || true
fi

exit 1
