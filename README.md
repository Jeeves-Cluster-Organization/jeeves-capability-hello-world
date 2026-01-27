# Jeeves Hello World - General Chatbot Capability

**A 3-agent template demonstrating multi-agent orchestration patterns**

## Overview

This is `jeeves-capability-hello-world`, a simplified general-purpose chatbot capability that demonstrates the core multi-agent orchestration pattern using jeeves-core infrastructure.

**This is NOT code-search specific** - it's a universal chatbot template (like ChatGPT lite) that anyone can customize for their domain.

**Key Features:**
- 3-agent pipeline (Understand → Think → Respond)
- Real LLM inference (llama.cpp local or API providers)
- General-purpose capabilities (conversation + web search)
- Minimal, reusable template for building custom multi-agent capabilities
- Single-machine deployment (Docker Compose, no K8s complexity)
- Gradio chat interface with streaming support
- Constitution R7 compliant architecture

**Status:** ✅ Complete and ready for deployment

**For the advanced version**, see the `main` branch for more complex capability examples.

## Architecture

### 3-Agent Pipeline: Universal Chatbot Pattern

```
User Message (via Gradio)
    ↓
UNDERSTAND (LLM)      ← Real LLM inference
  ├─ Analyzes user intent
  ├─ Determines if web search needed
  ├─ Extracts key entities/questions
  └─ Plans approach
    ↓
THINK (Tools)
  ├─ Executes web search (if needed)
  ├─ OR pure reasoning (if no tools needed)
  └─ Gathers information
    ↓
RESPOND (LLM)         ← Real LLM inference
  ├─ Synthesizes information
  ├─ Crafts helpful response
  └─ Includes citations (if web search used)
    ↓
Response to user (Gradio)
```

### Agent Responsibilities

**1. Understand** (LLM Agent)
- **Has LLM**: ✅ YES (uses real model)
- **Role**: Analyze user message and plan approach
- **Output**: `{intent, needs_search, search_query, reasoning}`
- **Examples**:
  - "What's the weather?" → `needs_search: true, search_query: "current weather"`
  - "Tell me a joke" → `needs_search: false`

**2. Think** (Tool Agent)
- **Has LLM**: ❌ NO (pure tool execution)
- **Role**: Execute tools OR pass through
- **Output**: `{information, sources[], has_data}`
- **Examples**:
  - Search query → Execute web_search → `{information: "...", sources: [...]}`
  - No search → `{information: null, sources: []}`

**3. Respond** (LLM Agent)
- **Has LLM**: ✅ YES (uses real model)
- **Role**: Synthesize information and craft response
- **Output**: `{response, citations[], confidence}`
- **Examples**:
  - With search: "Based on recent news [source], the weather is..."
  - Pure chat: "Here's a joke: Why did the chicken..."

### Project Structure

```
jeeves-capability-hello-world/
├── jeeves_capability_hello_world/      # Main capability package
│   ├── __init__.py                     # Package exports, register_capability
│   ├── registration.py                 # Constitution R7 capability registration
│   ├── pipeline_config.py              # 3-agent pipeline configuration
│   ├── CONSTITUTION.md                 # Capability rules and boundaries
│   │
│   ├── prompts/                        # LLM prompts
│   │   ├── __init__.py
│   │   └── chatbot/                    # General chatbot prompts
│   │       ├── __init__.py
│   │       ├── understand.py           # Understand agent prompt
│   │       ├── respond.py              # Respond agent prompt
│   │       └── respond_streaming.py    # Streaming response prompt
│   │
│   ├── tools/                          # General-purpose tools
│   │   ├── __init__.py                 # initialize_all_tools()
│   │   ├── catalog.py                  # Tool catalog with metadata
│   │   ├── registration.py             # Tool registration
│   │   └── hello_world_tools.py        # 3 minimal tools
│   │
│   └── orchestration/                  # Service layer
│       ├── __init__.py
│       ├── chatbot_service.py          # ChatbotService wrapper
│       ├── wiring.py                   # Dependency injection factory
│       └── types.py                    # Domain type definitions
│
├── jeeves-core/                        # Core infrastructure (git submodule)
│
├── gradio_app.py                       # Gradio chat UI with streaming
├── docker/                             # Docker deployment
│   ├── Dockerfile.hello-world          # Chatbot app container
│   ├── docker-compose.hello-world.yml  # 3-service deployment
│   ├── setup_hello_world.sh            # Setup script (Linux/macOS)
│   └── setup_hello_world.ps1           # Setup script (Windows)
└── README.md                           # This file
```

**What's Included:**
- ✅ 3-agent pipeline configuration with real LLM support
- ✅ Prompts for Understand and Respond agents (including streaming)
- ✅ 3 minimal general-purpose tools (web_search, get_time, list_tools)
- ✅ Gradio entry point with true token-level streaming
- ✅ ChatbotService wrapper for 3-agent pipeline
- ✅ Constitution R7 compliant registration and wiring
- ✅ Tool catalog with metadata (categories, risk levels)
- ✅ Docker deployment (3 services: postgres, llama-server, chatbot)
- ✅ Setup scripts for Linux/macOS and Windows

### What Makes Hello World Special

| Aspect | Hello World (This Branch) |
|--------|---------------------------|
| **Domain** | General purpose (chat, Q&A, web search) |
| **Agents** | 3 (Understand → Think → Respond) |
| **LLM Calls** | 2 (Understand + Respond) |
| **Tools** | 3 (web_search, get_time, list_tools) |
| **Iterations** | Max 2 |
| **Deployment** | Docker Compose (3 services) |
| **LLM Backend** | llama.cpp (local) or API providers |
| **Response Time** | ~3-8 sec |
| **Use Case** | Learning, general chatbot template |
| **Complexity** | Beginner-friendly |

## Dependencies

This capability depends on jeeves-core (git submodule) and LiteLLM (pip package).

**`jeeves-core`** - Core infrastructure:
- `protocols` - Protocol definitions and type bridge
- `mission_system` - Orchestration primitives and contracts
- `avionics` - Infrastructure adapters (LLM, database, gateway)
- `control_tower` - Kernel layer (lifecycle, resources)
- `shared` - Shared utilities (logging, serialization)

### Initializing the Submodule

```bash
git submodule update --init --recursive
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (for full deployment)
- PostgreSQL 15+ (for conversation history - included in Docker setup)
- Optional: Web search API key (Google Custom Search, Serper, or use DuckDuckGo)

### Development Setup

```bash
# 1. Clone and initialize submodules
git clone <repository-url>
cd jeeves-capability-hello-world
git checkout jeeves-capability-hello-world
git submodule update --init --recursive

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements/all.txt

# 3. (Optional) Set up web search API
# Option A: Google Custom Search
export GOOGLE_API_KEY=your_key_here
export GOOGLE_CX=your_cx_here

# Option B: Serper API
export SERPER_API_KEY=your_key_here

# Option C: Use DuckDuckGo (no API key needed)
# Just use the default implementation
```

### Current Status

**✅ Fully Implemented:**
- ✅ 3-agent pipeline configuration (Understand → Think → Respond)
- ✅ LLM prompts for Understand and Respond agents (with streaming)
- ✅ 3 general-purpose tools (web_search, get_time, list_tools)
- ✅ ChatbotService wrapper for pipeline execution
- ✅ Gradio UI with true token-level streaming
- ✅ Docker Compose deployment (3 services)
- ✅ Setup scripts (Linux/macOS/Windows)
- ✅ Constitution R7 compliant architecture
- ✅ Complete documentation

**Ready for:**
- Local development with any LLM provider (llama.cpp, OpenAI, Anthropic)
- Docker deployment with real LLM inference
- Customization for any domain (see Customization section)
- End-to-end testing

### Quick Deploy

**Option 1: Docker Deployment (Recommended)**

```bash
# 1. Run setup script (downloads 2GB LLM model)
bash docker/setup_hello_world.sh --build

# 2. Start all services
docker compose -f docker/docker-compose.hello-world.yml up -d

# 3. Wait for services to be healthy (~60 seconds)
docker compose -f docker/docker-compose.hello-world.yml ps

# 4. Open browser to http://localhost:8000
```

**Option 2: Local Development**

```bash
# 1. Install dependencies
pip install -r requirements/all.txt
pip install gradio structlog

# 2. Set up LLM provider
export LLM_PROVIDER=openai
export OPENAI_API_KEY=your_key

# 3. Start Gradio app
python gradio_app.py

# Open browser: http://localhost:8000
```

## Available Tools

The hello-world capability includes 3 minimal general-purpose tools:

| Tool | Description | Async |
|------|-------------|-------|
| `web_search` | Search the web for current information | ✅ Yes |
| `get_time` | Get current date and time (UTC) | ❌ No |
| `list_tools` | List all available tools (introspection) | ❌ No |

### Tool Details

**`web_search(query: str, max_results: int = 5)`**
- Purpose: Search the web for current information
- Input: Search query string
- Output: `{status, results[], sources[], query}`
- Usage: When Understand agent determines `needs_search: true`
- Note: Requires API key (Google Custom Search, Serper) or uses DuckDuckGo

**`get_time()`**
- Purpose: Get current date/time (demonstrates stateless tool pattern)
- Input: None
- Output: `{status, datetime, date, time, timezone}`
- Usage: Simple example of deterministic tool

**`list_tools()`**
- Purpose: Tool introspection and discovery
- Input: None
- Output: `{status, tools[], count}`
- Usage: Helps agents understand available capabilities

## Docker Deployment

The hello-world chatbot includes a complete Docker Compose setup with 3 services:

### Services

1. **PostgreSQL** - Conversation history and state storage
   - Image: `pgvector/pgvector:pg16`
   - Port: 5432
   - Volume: `postgres-data` (persistent)

2. **llama.cpp Server** - Real LLM inference
   - Image: `ghcr.io/ggerganov/llama.cpp:server-cuda`
   - Model: Qwen 2.5 3B Instruct (Q4 quantized, ~2GB)
   - Port: 8080
   - GPU: NVIDIA GPU support (falls back to CPU if unavailable)
   - Volume: `llama-models` (persistent, populated by setup script)

3. **Chatbot Application** - 3-agent pipeline + Gradio UI
   - Built from: `docker/Dockerfile.hello-world`
   - Port: 8000 (Gradio web interface with streaming)
   - Depends on: postgres, llama-server

### Setup and Deployment

**Linux/macOS:**
```bash
# 1. Run setup (downloads model, creates .env)
bash docker/setup_hello_world.sh --build

# 2. Start services
docker compose -f docker/docker-compose.hello-world.yml up -d

# 3. Check status
docker compose -f docker/docker-compose.hello-world.yml ps

# 4. View logs
docker compose -f docker/docker-compose.hello-world.yml logs -f chatbot

# 5. Stop services
docker compose -f docker/docker-compose.hello-world.yml down
```

**Windows (PowerShell):**
```powershell
# 1. Run setup
.\docker\setup_hello_world.ps1 -Build

# 2. Start services
docker compose -f docker/docker-compose.hello-world.yml up -d

# 3. Check status
docker compose -f docker/docker-compose.hello-world.yml ps
```

### Accessing the Application

Once all services are healthy (check with `docker compose ps`):

- **Gradio UI**: http://localhost:8000
- **LLM API**: http://localhost:8080 (internal)
- **PostgreSQL**: localhost:5432 (internal)

### Troubleshooting

**Services not starting:**
```bash
# Check logs for specific service
docker compose -f docker/docker-compose.hello-world.yml logs llama-server
docker compose -f docker/docker-compose.hello-world.yml logs chatbot

# Rebuild images
docker compose -f docker/docker-compose.hello-world.yml build --no-cache
```

**Model not found:**
```bash
# Re-run setup to download model
bash docker/setup_hello_world.sh

# Verify model in volume
docker run --rm -v llama-models:/models alpine ls -lh /models/
```

**Out of memory:**
- Reduce llama-server memory limit in `docker-compose.hello-world.yml`
- Use CPU-only mode (remove GPU configuration)
- Reduce `--n-gpu-layers` to offload less to GPU

## LLM Configuration

The hello-world capability uses **real LLM inference** (not mocks):

### Default: llama.cpp (Local, Free)

```yaml
# Recommended for hello-world
LLM_PROVIDER: llamaserver
LLAMASERVER_HOST: http://localhost:8080
DEFAULT_MODEL: qwen2.5-3b-instruct-q4_k_m
```

- Model: Qwen 2.5 3B Instruct (Q4 quantized)
- Size: ~2GB
- Speed: ~10-20 tokens/sec on GPU
- Cost: Free (runs locally)

### Alternative: OpenAI

```yaml
LLM_PROVIDER: openai
OPENAI_API_KEY: your_key_here
```

### Alternative: Anthropic Claude

```yaml
LLM_PROVIDER: anthropic
ANTHROPIC_API_KEY: your_key_here
```

### Environment Variables

Key configuration for hello-world deployment:

```bash
# Pipeline mode
PIPELINE_MODE=general_chatbot

# LLM Configuration
LLM_PROVIDER=llamaserver
LLAMASERVER_HOST=http://localhost:8080
DEFAULT_MODEL=qwen2.5-3b-instruct-q4_k_m

# Database (conversation history)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=chatbot
POSTGRES_USER=user
POSTGRES_PASSWORD=dev_password

# Web Search API (choose one)
GOOGLE_API_KEY=your_key_here        # Option A: Google Custom Search
GOOGLE_CX=your_cx_here
# OR
SERPER_API_KEY=your_key_here        # Option B: Serper API

# Gradio UI
GRADIO_PORT=8000

# Logging
LOG_LEVEL=INFO
```

## Customization for Your Domain

This hello-world chatbot is a **universal template** that can be customized for any domain:

### Step 1: Define Your Tools

Add domain-specific tools in `tools/hello_world_tools.py`:
```python
# Example: Customer support domain
async def search_knowledge_base(query: str) -> Dict[str, Any]:
    """Search internal knowledge base for customer support."""
    # Your implementation here
    pass

async def get_customer_info(customer_id: str) -> Dict[str, Any]:
    """Retrieve customer information."""
    # Your implementation here
    pass
```

### Step 2: Register Tools in Catalog

Update `tools/catalog.py` to add your tool IDs and metadata:
```python
class ToolId(str, Enum):
    WEB_SEARCH = "web_search"
    SEARCH_KNOWLEDGE_BASE = "search_knowledge_base"  # Add new tool
    GET_CUSTOMER_INFO = "get_customer_info"  # Add new tool
```

Update `tools/registration.py` to register your tools:
```python
tool_catalog.register(
    tool_id=ToolId.SEARCH_KNOWLEDGE_BASE.value,
    func=search_knowledge_base,
    description="Search internal knowledge base",
    category=ToolCategory.SEARCH.value,
    risk_level=RiskLevel.READ_ONLY.value,
    is_async=True,
)
```

### Step 3: Update Prompts

Modify `prompts/chatbot/understand.py` and `respond.py` to match your domain:
```python
def chatbot_understand() -> str:
    return """You are a customer support assistant analyzing user requests.

## Your Capabilities
- Search knowledge base for solutions
- Access customer account information
- Create support tickets
...
```

### Step 4: Adjust Agent Configuration (Optional)

Update `pipeline_config.py` if needed (usually no changes required):
- Same 3-agent pattern works for most domains
- Adjust `max_tokens`, `temperature` for your use case

That's it! The 3-agent pattern (Understand → Think → Respond) works for:
- **Customer support bots** - Help desk automation
- **Research assistants** - Literature search and summarization
- **E-commerce assistants** - Product recommendations
- **HR bots** - Employee onboarding
- **Legal assistants** - Document analysis
- **Any domain** that needs understanding → action → response

## Learning Path: From Hello World to Advanced

This hello-world branch is the **first step** in understanding multi-agent orchestration:

1. **Start here** (jeeves-capability-hello-world): 3 agents, general chatbot, ~2000 lines of code
2. **Then explore** (main branch): More advanced capability patterns

### What You'll Learn

**In Hello World (this branch):**
- Basic 3-agent pipeline pattern
- Constitution R7 compliant capability registration
- Tool catalog with metadata (categories, risk levels)
- Dependency injection via wiring.py
- LLM integration via mission_system.adapters
- Tool execution without LLM in middle agent
- Configuration-driven agent architecture
- Simple hook functions (pre_process, post_process)

**Advanced Patterns (main branch):**
- More complex multi-agent pipelines
- Additional tool orchestration patterns
- Production-grade error handling
- Kubernetes deployment options

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request with clear description

## License

See LICENSE.txt for license information.
