#!/usr/bin/env bash

# ==================== Parameter Configuration ====================
# Read environment variables or use default values
DOCKER_USERNAME="${DOCKER_USERNAME:-handsonsecurity}"   # Docker Hub username
DOCKER_IMAGE="${DOCKER_IMAGE:-seedemu-internetmap}"     # Image name (backend service name)
DOCKER_TAG="${DOCKER_TAG:-2.0}"                         # Image tag
REMOTE_REPO="${REMOTE_REPO:-seedemu-internetmap}"       # Docker Hub repository name
TARGET_TAG="${TARGET_TAG:-2.0}"                         # Tag to push to remote

# ==================== Help Function ====================
print_help() {
    cat <<EOF
Usage: $0 [options]

Options:
  -u, --username   Docker Hub username (can be set via environment variable DOCKER_USERNAME)
  -p, --password   Docker Hub password (can be set via environment variable DOCKER_PASSWORD)
  -i, --image      Image name (corresponds to service name in docker-compose.yml), default: $DOCKER_IMAGE
  -t, --tag        Image tag, default: $DOCKER_TAG
  -r, --repo       Remote repository name, default: $REMOTE_REPO
  -g, --gtag       Tag to push to remote, default: $TARGET_TAG
  -h, --help       Display this help message

Examples:
  # Set via environment variables:
  export DOCKER_USERNAME=myuser
  export DOCKER_PASSWORD=mypass
  export DOCKER_IMAGE=backend
  export REMOTE_REPO=backend-repo
  ./docker-compose-push.sh

  # Via command line arguments:
  ./docker-compose-push.sh -u myuser -p mypass -i backend -r backend-repo -g latest
EOF
}

# ==================== Argument Parsing ====================
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--username) DOCKER_USERNAME="$2"; shift 2 ;;
        -p|--password) DOCKER_PASSWORD="$2"; shift 2 ;;
        -i|--image) DOCKER_IMAGE="$2"; shift 2 ;;
        -t|--tag) DOCKER_TAG="$2"; shift 2 ;;
        -r|--repo) REMOTE_REPO="$2"; shift 2 ;;
        -g|--gtag) TARGET_TAG="$2"; shift 2 ;;
        -h|--help) print_help; exit 0 ;;
        *) echo "Unknown parameter: $1"; print_help; exit 1 ;;
    esac
done

# ==================== Core Logic ====================

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker command not found. Please install Docker first." >&2
    exit 1
fi

# Check if Docker Compose v2 is installed
if ! docker compose version &> /dev/null; then
    echo "Error: Docker Compose v2 not found. Please install it first." >&2
    exit 1
fi

# -------------------- Step 1: Build Image --------------------
echo "Building image using docker compose..."
docker compose build --quiet "$DOCKER_IMAGE"
if [ $? -ne 0 ]; then
    echo "Error: Image build failed." >&2
    exit 1
fi

# -------------------- Step 2: Login to Docker Hub --------------------
# If password is not set, prompt user for input
if [ -z "$DOCKER_PASSWORD" ]; then
    read -sp "Please enter Docker Hub password: " DOCKER_PASSWORD
    echo
fi

echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
if [ $? -ne 0 ]; then
    echo "Error: Docker login failed." >&2
    exit 1
fi

# -------------------- Step 3: Check Image --------------------
FULL_REMOTE_IMAGE="${DOCKER_USERNAME}/${REMOTE_REPO}:${TARGET_TAG}"
if ! docker images -q "$FULL_REMOTE_IMAGE" &> /dev/null; then
    echo "Error: Local image $FULL_REMOTE_IMAGE not found. Build may have failed." >&2
    exit 1
fi

# -------------------- Step 4: Push Image --------------------
echo "Pushing image to Docker Hub..."
docker push "$FULL_REMOTE_IMAGE"
if [ $? -ne 0 ]; then
    echo "Error: Image push failed." >&2
    exit 1
fi

echo "Image pushed successfully! Visit https://hub.docker.com/r/${DOCKER_USERNAME}/${REMOTE_REPO} to view."

# ==================== Exit ====================
exit 0