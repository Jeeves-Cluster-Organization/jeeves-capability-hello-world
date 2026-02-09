#!/bin/bash
# Setup script for Jeeves Hello World deployment
#
# This script:
# 1. Creates Docker volume for LLM models
# 2. Downloads Qwen 2.5 3B Instruct model (~2GB)
# 3. Creates .env file if not exists
# 4. Optionally builds Docker images
#
# Usage:
#   bash docker/setup_hello_world.sh [--build]
#
# Options:
#   --build    Build Docker images after setup

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=============================================="
echo "Jeeves Hello World - Setup Script"
echo "=============================================="
echo ""

# Parse arguments
BUILD_IMAGES=false
if [[ "$1" == "--build" ]]; then
    BUILD_IMAGES=true
fi

# Step 1: Create model volume
echo "[1/4] Creating Docker volume for LLM models..."
if docker volume inspect llama-models >/dev/null 2>&1; then
    echo "  ✓ Volume 'llama-models' already exists"
else
    docker volume create llama-models
    echo "  ✓ Created volume 'llama-models'"
fi
echo ""

# Step 2: Download model
echo "[2/4] Downloading Qwen 2.5 3B Instruct model (~2GB)..."
echo "  This may take a few minutes depending on your internet speed..."
echo ""

# Check if model already exists in volume
MODEL_EXISTS=$(docker run --rm -v llama-models:/models alpine sh -c "[ -f /models/qwen2.5-3b-instruct-q4_k_m.gguf ] && echo 'yes' || echo 'no'")

if [[ "$MODEL_EXISTS" == "yes" ]]; then
    echo "  ✓ Model already downloaded"
else
    # Download model using wget in Alpine container
    docker run --rm -v llama-models:/models alpine sh -c "
        apk add --no-cache wget && \
        cd /models && \
        wget -O qwen2.5-3b-instruct-q4_k_m.gguf \
          https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf && \
        echo 'Model downloaded successfully'
    "
    echo "  ✓ Model downloaded to volume"
fi
echo ""

# Step 3: Create .env file
echo "[3/4] Creating .env file..."
cd "$PROJECT_ROOT"

if [[ -f .env ]]; then
    echo "  ✓ .env file already exists"
else
    cat > .env <<'EOF'
# Jeeves Hello World - Environment Configuration

# General
CODE_VERSION=hello-world
LOG_LEVEL=INFO

# LLM Provider (choose one)
LLM_PROVIDER=llamaserver
LLAMASERVER_HOST=http://llama-server:8080

# Uncomment to use OpenAI instead
# LLM_PROVIDER=openai
# OPENAI_API_KEY=your_openai_key_here

# Uncomment to use Anthropic instead
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=your_anthropic_key_here

# Database
DB_NAME=chatbot
DB_USER=user
DB_PASSWORD=dev_password

# Web Search API (optional - choose one)
# Google Custom Search
# GOOGLE_API_KEY=your_google_api_key
# GOOGLE_CX=your_google_cx

# Serper API
# SERPER_API_KEY=your_serper_key

# Chainlit
CHAINLIT_PORT=8000
EOF
    echo "  ✓ Created .env file with default configuration"
    echo "  → Edit .env to configure web search API keys (optional)"
fi
echo ""

# Step 4: Build images (optional)
if [[ "$BUILD_IMAGES" == true ]]; then
    echo "[4/4] Building Docker images..."
    cd "$PROJECT_ROOT"
    docker compose -f docker/docker-compose.hello-world.yml build
    echo "  ✓ Docker images built"
else
    echo "[4/4] Skipping Docker build (use --build to build images)"
fi
echo ""

echo "=============================================="
echo "✅ Setup Complete!"
echo "=============================================="
echo ""
echo "Next steps:"
echo ""
echo "1. (Optional) Configure web search API in .env:"
echo "   - Google Custom Search: GOOGLE_API_KEY, GOOGLE_CX"
echo "   - Serper API: SERPER_API_KEY"
echo ""
echo "2. Start services:"
echo "   cd $PROJECT_ROOT"
echo "   docker compose -f docker/docker-compose.hello-world.yml up -d"
echo ""
echo "3. Wait for services to be healthy (~30-60 seconds):"
echo "   docker compose -f docker/docker-compose.hello-world.yml ps"
echo ""
echo "4. Open Chainlit UI in browser:"
echo "   http://localhost:8000"
echo ""
echo "5. View logs:"
echo "   docker compose -f docker/docker-compose.hello-world.yml logs -f chatbot"
echo ""
echo "6. Stop services:"
echo "   docker compose -f docker/docker-compose.hello-world.yml down"
echo ""
