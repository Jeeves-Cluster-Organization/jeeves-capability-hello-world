# Jeeves Hello World - General Chatbot Capability

**A 3-agent template demonstrating multi-agent orchestration patterns**

## Overview

This is `jeeves-capability-hello-world`, a simplified general-purpose chatbot capability that demonstrates the core multi-agent orchestration pattern using jeeves-core and airframe infrastructure.

**This is NOT code-search specific** - it's a universal chatbot template (like ChatGPT lite) that anyone can customize for their domain.

**Key Features:**
- 3-agent pipeline (Understand → Think → Respond)
- Real LLM inference (llama.cpp local or API providers)
- General-purpose capabilities (conversation + web search)
- Minimal, reusable template for building custom multi-agent capabilities
- Single-machine deployment (Docker Compose, no K8s complexity)
- Chainlit chat interface

**Status:** 🚧 Foundation complete, integration in progress

**For the advanced version**, see the `main` branch: 7-agent code analysis capability with 30+ tools.

## Architecture

### 3-Agent Pipeline: Universal Chatbot Pattern

```
User Message (via Chainlit)
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
Response to user (Chainlit)
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
jeeves-capability-code-analysis/
├── jeeves-capability-code-analyser/    # Main capability package
│   ├── __init__.py                     # Package metadata (hello-world)
│   ├── pipeline_config.py              # 3-agent pipeline configuration
│   │
│   ├── prompts/                        # LLM prompts
│   │   ├── __init__.py
│   │   └── chatbot/                    # General chatbot prompts
│   │       ├── __init__.py
│   │       ├── understand.py           # Understand agent prompt
│   │       └── respond.py              # Respond agent prompt
│   │
│   ├── tools/                          # General-purpose tools
│   │   ├── __init__.py
│   │   └── hello_world_tools.py        # 3 minimal tools
│   │
│   └── orchestration/                  # Service wrapper
│       ├── __init__.py
│       └── service.py                  # ChatbotService (to be adapted)
│
├── airframe/                           # LLM adapter infrastructure (git submodule)
├── jeeves-core/                        # Core infrastructure (git submodule)
│
├── chainlit_app.py                     # Chainlit chat UI (to be created)
├── docker/                             # Docker deployment (to be created)
│   ├── Dockerfile
│   └── docker-compose.yml
└── README.md                           # This file
```

**What's Included:**
- ✅ 3-agent pipeline configuration with real LLM support
- ✅ Prompts for Understand and Respond agents
- ✅ 3 minimal general-purpose tools (web_search, get_time, list_tools)
- 🚧 Chainlit entry point (pending)
- 🚧 ChatbotService wrapper (pending adaptation)
- 🚧 Docker deployment configuration (pending)

### Comparison: Hello World vs Code Analysis

| Aspect | Hello World (This Branch) | Code Analysis (main Branch) |
|--------|---------------------------|------------------------------|
| **Domain** | General purpose (chat, Q&A, web search) | Code understanding |
| **Agents** | 3 (Understand → Think → Respond) | 7 (Perception → Intent → Planner → Traverser → Synthesizer → Critic → Integration) |
| **LLM Calls** | 2 (Understand + Respond) | 5 (Intent + Planner + Synthesizer + Critic + Integration) |
| **Tools** | 3 (web_search, get_time, list_tools) | 30+ (search_code, read_code, git tools, semantic search, etc.) |
| **Iterations** | Max 2 | Max 5 |
| **Deployment** | Docker Compose (3 services) | K8s (distributed) |
| **LLM Backend** | llama.cpp (local, 3B model) | llama.cpp (larger model) or API |
| **Response Time** | ~3-8 sec | ~10-30 sec |
| **Use Case** | Learning, general chatbot template | Production code analysis |
| **Complexity** | Beginner-friendly | Advanced patterns |

## Dependencies

This capability depends on two git submodules:

**`airframe`** - LLM adapter infrastructure:
- Endpoint management and backend adapters
- Health monitoring and observability hooks
- Stream-first inference contract

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
cd jeeves-capability-code-analysis
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

**✅ Completed:**
- 3-agent pipeline configuration
- LLM prompts for Understand and Respond agents
- Minimal tool implementations

**🚧 Pending:**
- Chainlit entry point (`chainlit_app.py`)
- ChatbotService adaptation
- Docker deployment configuration
- End-to-end testing

### Next Steps for Completion

To complete the hello-world chatbot:

1. **Create Chainlit entry point** - Chat UI integration
2. **Adapt ChatbotService** - Simple service wrapper in `orchestration/service.py`
3. **Create Docker setup** - 3-service deployment (postgres, llama-server, chatbot)
4. **Test end-to-end** - Full conversation flow

See the implementation plan at [`C:\Users\shaik\.claude\plans\zesty-mapping-panda.md`](C:\Users\shaik\.claude\plans\zesty-mapping-panda.md) for detailed next steps.

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

# Chainlit UI
CHAINLIT_PORT=8000

# Logging
LOG_LEVEL=INFO
```

## Customization for Your Domain

This hello-world chatbot is a **universal template** that can be customized for any domain:

### Step 1: Define Your Tools
Replace the 3 general tools with domain-specific tools in `tools/hello_world_tools.py`:
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

### Step 2: Update Prompts
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

### Step 3: Adjust Agent Configuration
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
2. **Then explore** (main branch): 7 agents, code analysis, ~15000+ lines of code

### What You'll Learn

**In Hello World (this branch):**
- Basic 3-agent pipeline pattern
- LLM integration with jeeves-core
- Tool execution without LLM in middle agent
- Configuration-driven agent architecture
- Simple hook functions (pre_process, post_process)

**In Code Analysis (main branch):**
- Advanced 7-agent pipeline with critic loop
- Complex tool orchestration (30+ tools)
- Bounded context management
- Citation validation and anti-hallucination
- Production-grade error handling
- Kubernetes deployment

### Switching to Advanced Version

```bash
# View current branch
git branch

# Switch to main (code analysis)
git checkout main

# Compare the two
git diff jeeves-capability-hello-world main
```

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request with clear description

## License

See LICENSE.txt for license information.
