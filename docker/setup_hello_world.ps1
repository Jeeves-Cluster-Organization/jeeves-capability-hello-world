# Setup script for Jeeves Hello World deployment (Windows PowerShell)
#
# This script:
# 1. Creates Docker volume for LLM models
# 2. Downloads Qwen 2.5 3B Instruct model (~2GB)
# 3. Creates .env file if not exists
# 4. Optionally builds Docker images
#
# Usage:
#   .\docker\setup_hello_world.ps1 [-Build]
#
# Options:
#   -Build    Build Docker images after setup

param(
    [switch]$Build
)

$ErrorActionPreference = "Stop"

Write-Host "=============================================="
Write-Host "Jeeves Hello World - Setup Script"
Write-Host "=============================================="
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir

# Step 1: Create model volume
Write-Host "[1/4] Creating Docker volume for LLM models..."
$volumeExists = docker volume inspect llama-models 2>$null
if ($volumeExists) {
    Write-Host "  [OK] Volume 'llama-models' already exists" -ForegroundColor Green
} else {
    docker volume create llama-models | Out-Null
    Write-Host "  [OK] Created volume 'llama-models'" -ForegroundColor Green
}
Write-Host ""

# Step 2: Download model
Write-Host "[2/4] Downloading Qwen 2.5 3B Instruct model (~2GB)..."
Write-Host "  This may take a few minutes depending on your internet speed..."
Write-Host ""

# Check if model already exists in volume
$modelExists = docker run --rm -v llama-models:/models alpine sh -c "[ -f /models/qwen2.5-3b-instruct-q4_k_m.gguf ] && echo 'yes' || echo 'no'"

if ($modelExists -match "yes") {
    Write-Host "  [OK] Model already downloaded" -ForegroundColor Green
} else {
    # Download model using sh command (single line for PowerShell compatibility)
    $downloadCmd = "apk add --no-cache wget && cd /models && wget -O qwen2.5-3b-instruct-q4_k_m.gguf https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf && echo 'Model downloaded successfully'"
    docker run --rm -v llama-models:/models alpine sh -c $downloadCmd
    Write-Host "  [OK] Model downloaded to volume" -ForegroundColor Green
}
Write-Host ""

# Step 3: Create .env file
Write-Host "[3/4] Creating .env file..."
Set-Location $projectRoot

$envPath = Join-Path $projectRoot ".env"
if (Test-Path $envPath) {
    Write-Host "  [OK] .env file already exists" -ForegroundColor Green
} else {
    $envContent = @"
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

# Database (PostgreSQL)
POSTGRES_DATABASE=chatbot
POSTGRES_USER=user
POSTGRES_PASSWORD=dev_password

# Web Search API (optional - choose one)
# Google Custom Search
# GOOGLE_API_KEY=your_google_api_key
# GOOGLE_CX=your_google_cx

# Serper API
# SERPER_API_KEY=your_serper_key

# Chainlit
CHAINLIT_PORT=8000
"@
    Set-Content -Path $envPath -Value $envContent
    Write-Host "  [OK] Created .env file with default configuration" -ForegroundColor Green
    Write-Host "  --> Edit .env to configure web search API keys (optional)" -ForegroundColor Yellow
}
Write-Host ""

# Step 4: Build images (optional)
if ($Build) {
    Write-Host "[4/4] Building Docker images..."
    Set-Location $projectRoot
    docker compose -f docker/docker-compose.hello-world.yml build
    Write-Host "  [OK] Docker images built" -ForegroundColor Green
} else {
    Write-Host "[4/4] Skipping Docker build (use -Build to build images)"
}
Write-Host ""

Write-Host "=============================================="
Write-Host "[SUCCESS] Setup Complete!" -ForegroundColor Green
Write-Host "=============================================="
Write-Host ""
Write-Host "Next steps:"
Write-Host ""
Write-Host "1. (Optional) Configure web search API in .env:"
Write-Host "   - Google Custom Search: GOOGLE_API_KEY, GOOGLE_CX"
Write-Host "   - Serper API: SERPER_API_KEY"
Write-Host ""
Write-Host "2. Start services:"
Write-Host "   cd $projectRoot"
Write-Host "   docker compose -f docker/docker-compose.hello-world.yml up -d"
Write-Host ""
Write-Host "3. Wait for services to be healthy (~30-60 seconds):"
Write-Host "   docker compose -f docker/docker-compose.hello-world.yml ps"
Write-Host ""
Write-Host "4. Open Chainlit UI in browser:"
Write-Host "   http://localhost:8000" -ForegroundColor Cyan
Write-Host ""
Write-Host "5. View logs:"
Write-Host "   docker compose -f docker/docker-compose.hello-world.yml logs -f chatbot"
Write-Host ""
Write-Host "6. Stop services:"
Write-Host "   docker compose -f docker/docker-compose.hello-world.yml down"
Write-Host ""
