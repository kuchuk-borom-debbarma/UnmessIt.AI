#!/usr/bin/env bash
set -e

# Change to the root directory of the project
cd "$(dirname "$0")/.."

echo -e "\033[0;34mBuilding and starting UnmessIt.AI locally from source...\033[0m"

# If the user previously used the installer, grab their existing .env
ENV_ARGS=""
if [ -f "unmessit-ai/.env" ]; then
    echo -e "\033[0;33mDetected existing staging installation. Linking to existing database and config...\033[0m"
    ENV_ARGS="--env-file unmessit-ai/.env"
fi

# We force the project name to 'unmessit-ai' so it seamlessly shares the database volume 
# and replaces the staging containers without port conflicts.
docker compose $ENV_ARGS -p unmessit-ai up -d --build

echo ""
echo -e "\033[0;32m==============================================\033[0m"
echo -e "\033[0;32m    UnmessIt.AI is now running from source!   \033[0m"
echo -e "\033[0;32m==============================================\033[0m"
echo ""
echo -e "\033[0;34mWeb UI:\033[0m http://localhost:2831"
echo -e "\033[0;34mAPI:\033[0m    http://localhost:2317"
echo ""
echo "To stop, run: docker compose down"
