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
INSTALL_DIR="unmessit-ai"
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

echo "This installer will set up UnmessIt.AI with standard defaults."
read -p "Press [Enter] to continue with defaults, or type 'advanced' to customize ports and secrets: " MODE

if [ "$MODE" = "advanced" ]; then
    echo ""
    read -p "Enter Server Port (default: 2317): " input_sp
    SERVER_PORT=${input_sp:-2317}
    
    read -p "Enter Web Port (default: 2831): " input_wp
    WEB_PORT=${input_wp:-2831}
    
    read -p "Enter a secure JWT Secret (leave blank to auto-generate): " input_jwt
    JWT_SECRET=$input_jwt
fi

if [ -z "$JWT_SECRET" ]; then
    # Auto generate a random 32 character hex string
    if command -v openssl >/dev/null 2>&1; then
        JWT_SECRET=$(openssl rand -hex 32)
    else
        JWT_SECRET=$(cat /dev/urandom | LC_ALL=C tr -dc 'a-zA-Z0-9' | fold -w 64 | head -n 1)
    fi
fi

echo ""
echo -e "${BLUE}Downloading docker-compose.prod.yml...${NC}"
curl -s -O https://raw.githubusercontent.com/kuchuk-borom-debbarma/UnmessIt.AI/staging/docker-compose.prod.yml

echo "Generating .env file..."
cat > .env << EOL
SERVER_PORT=${SERVER_PORT}
WEB_PORT=${WEB_PORT}
JWT_SECRET=${JWT_SECRET}
UNMESSIT_DATA_DIR=./data
EOL

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
