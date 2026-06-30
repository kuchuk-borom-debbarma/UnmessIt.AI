#!/usr/bin/env bash
set -e

# Change to the root directory of the project
cd "$(dirname "$0")/.."

echo -e "\033[0;34mBuilding and starting UnmessIt.AI locally from source...\033[0m"

# We use the default docker-compose.yml, which uses the local build context
docker compose up -d --build

echo ""
echo -e "\033[0;32m==============================================\033[0m"
echo -e "\033[0;32m    UnmessIt.AI is now running from source!   \033[0m"
echo -e "\033[0;32m==============================================\033[0m"
echo ""
echo -e "\033[0;34mWeb UI:\033[0m http://localhost:2831"
echo -e "\033[0;34mAPI:\033[0m    http://localhost:2317"
echo ""
echo "To stop, run: docker compose down"
