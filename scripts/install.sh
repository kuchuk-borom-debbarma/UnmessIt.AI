#!/usr/bin/env bash
set -e

# Colors for UI
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
cat << "EOF"
  _   _                                ___ _   _  _   ___ 
 | | | |                              |_ _| | | |/ | |_ _|
 | | | |_ __  _ __ ___   ___  ___ ___  | || |_| |/| |  | | 
 | |_| | '_ \| '_ ` _ \ / _ \/ __/ __| | ||  _  | | |  | | 
 |  _  | | | | | | | | |  __/\__ \__ \ | || | | | | |  | | 
 |_| |_|_| |_|_| |_| |_|\___||___/___/|___|_| |_| |_| |___|
                                                           
EOF
echo -e "${NC}"
echo -e "${GREEN}Welcome to the UnmessIt.AI interactive installer!${NC}"
echo ""

# Dependency checks
if ! command -v docker >/dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not installed. Please install Docker first: https://docs.docker.com/get-docker/${NC}"
    exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
    echo -e "${RED}Error: Docker Compose is not installed or not available as 'docker compose'. Please install it first.${NC}"
    exit 1
fi

# Directory setup
INSTALL_DIR="$HOME/unmessit-ai"
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Directory '$INSTALL_DIR' already exists. The installer will use it.${NC}"
else
    echo "Creating installation directory '$INSTALL_DIR'..."
    mkdir -p "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"
mkdir -p data

# Interaction
SERVER_PORT=2317
WEB_PORT=2831
JWT_SECRET=""
REDIS_URL="redis://redis:6379/0"
UNMESSIT_DATA_DIR="./data"
CORS_ORIGINS=""
ENABLE_DEV_ROUTES=0
LOG_LEVEL=INFO

# Load existing configuration if it exists to preserve secrets and custom ports across updates
if [ -f ".env" ]; then
    echo -e "${YELLOW}Existing .env file found. Loading current configuration...${NC}"
    get_env_value() {
        awk -F= -v key="$1" '$0 !~ /^[[:space:]]*#/ && $1 == key {sub(/^[^=]*=/, ""); print; exit}' .env
    }
    SERVER_PORT="$(get_env_value SERVER_PORT || true)"
    WEB_PORT="$(get_env_value WEB_PORT || true)"
    JWT_SECRET="$(get_env_value JWT_SECRET || true)"
    REDIS_URL="$(get_env_value REDIS_URL || true)"
    UNMESSIT_DATA_DIR="$(get_env_value UNMESSIT_DATA_DIR || true)"
    CORS_ORIGINS="$(get_env_value CORS_ORIGINS || true)"
    ENABLE_DEV_ROUTES="$(get_env_value ENABLE_DEV_ROUTES || true)"
    LOG_LEVEL="$(get_env_value LOG_LEVEL || true)"
fi

SERVER_PORT=${SERVER_PORT:-2317}
WEB_PORT=${WEB_PORT:-2831}
REDIS_URL=${REDIS_URL:-redis://redis:6379/0}
UNMESSIT_DATA_DIR=${UNMESSIT_DATA_DIR:-./data}
ENABLE_DEV_ROUTES=${ENABLE_DEV_ROUTES:-0}
LOG_LEVEL=${LOG_LEVEL:-INFO}

echo "This installer will set up UnmessIt.AI with standard defaults."
read -p "Press [Enter] to continue with defaults, or type 'advanced' to customize ports and secrets: " MODE

if [ "$MODE" = "advanced" ]; then
    echo ""
    read -p "Enter Server Port (default: ${SERVER_PORT}): " input_sp
    if [ -n "$input_sp" ]; then SERVER_PORT=$input_sp; fi
    
    read -p "Enter Web Port (default: ${WEB_PORT}): " input_wp
    if [ -n "$input_wp" ]; then WEB_PORT=$input_wp; fi
    
    read -p "Enter a secure JWT Secret (leave blank to keep existing or auto-generate): " input_jwt
    if [ -n "$input_jwt" ]; then JWT_SECRET=$input_jwt; fi
fi

if [ -z "$JWT_SECRET" ]; then
    # Auto generate a random 32 character hex string
    if command -v openssl >/dev/null 2>&1; then
        JWT_SECRET=$(openssl rand -hex 32)
    else
        JWT_SECRET=$(cat /dev/urandom | LC_ALL=C tr -dc 'a-zA-Z0-9' | fold -w 64 | head -n 1)
    fi
fi

CORS_ORIGINS=${CORS_ORIGINS:-http://localhost:${WEB_PORT},http://127.0.0.1:${WEB_PORT}}

echo ""
echo -e "${BLUE}Downloading docker-compose.prod.yml...${NC}"
curl -fsSL https://raw.githubusercontent.com/kuchuk-borom-debbarma/UnmessIt.AI/staging/docker-compose.prod.yml -o docker-compose.prod.yml

echo "Generating .env file..."
cat > .env << EOL
SERVER_PORT=${SERVER_PORT}
WEB_PORT=${WEB_PORT}
JWT_SECRET=${JWT_SECRET}
UNMESSIT_DATA_DIR=${UNMESSIT_DATA_DIR}
REDIS_URL=${REDIS_URL}
CORS_ORIGINS=${CORS_ORIGINS}
ENABLE_DEV_ROUTES=${ENABLE_DEV_ROUTES}
LOG_LEVEL=${LOG_LEVEL}
EOL

docker compose -f docker-compose.prod.yml config >/dev/null

echo -e "${BLUE}Preparing environment (stopping existing containers if any)...${NC}"
docker compose -f docker-compose.prod.yml down || true

echo -e "${BLUE}Starting UnmessIt.AI in the background...${NC}"
docker compose -f docker-compose.prod.yml up -d --pull always

echo ""
echo -e "${GREEN}==============================================${NC}"
echo -e "${GREEN}    UnmessIt.AI is now running successfully!   ${NC}"
echo -e "${GREEN}==============================================${NC}"
echo ""
echo -e "Access the web app at:  ${BLUE}http://localhost:${WEB_PORT}${NC}"
echo -e "Access the API at:      ${BLUE}http://localhost:${SERVER_PORT}${NC}"
echo ""
echo -e "Your configuration is saved in ${YELLOW}$(pwd)/.env${NC}"
echo -e "Your UnmessIt.AI data is stored in ${YELLOW}$(pwd)/data${NC}"
echo -e "To stop the app, run: ${YELLOW}cd $(pwd) && docker compose -f docker-compose.prod.yml down${NC}"
