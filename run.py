"""
Startup script for hello-world onboarding chatbot.

Configures and starts the Rust kernel with:
  - MCP tool server (stdio transport — kernel spawns mcp_server.py)
  - Agent registration (2 LLM + 2 MCP-delegating agents)
  - Prompt directory

Usage:
    # Start kernel + MCP server + Gradio UI
    python run.py

    # Kernel only (for manual testing with curl)
    python run.py --kernel-only

Environment variables:
    OPENAI_API_KEY      — LLM API key (required for LLM agents)
    OPENAI_BASE_URL     — LLM endpoint (default: https://api.openai.com)
    OPENAI_MODEL        — Model name (default: gpt-4o-mini)
    JEEVES_KERNEL_PORT  — Kernel HTTP port (default: 8080)
    GRADIO_SERVER_PORT  — Gradio UI port (default: 8001)
"""

import json
import os
import subprocess
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    kernel_only = "--kernel-only" in sys.argv
    kernel_port = os.getenv("JEEVES_KERNEL_PORT", "8080")

    # MCP server config — kernel spawns mcp_server.py via stdio
    mcp_servers = [
        {
            "name": "hello_tools",
            "transport": "stdio",
            "command": sys.executable,
            "args": [os.path.join(SCRIPT_DIR, "mcp_server.py")],
        }
    ]

    # Agent config — 2 LLM agents + 2 MCP-delegating agents
    agents = [
        {
            "name": "understand",
            "type": "llm",
            "prompt_key": "chatbot.understand",
            "temperature": 0.3,
            "max_tokens": 4000,
        },
        {
            "name": "think_knowledge",
            "type": "mcp_delegate",
            "tool_name": "think_knowledge",
        },
        {
            "name": "think_tools",
            "type": "mcp_delegate",
            "tool_name": "think_tools",
        },
        {
            "name": "respond",
            "type": "llm",
            "prompt_key": "chatbot.respond",
            "temperature": 0.5,
            "max_tokens": 4000,
        },
    ]

    # Set environment for kernel
    env = os.environ.copy()
    env["JEEVES_MCP_SERVERS"] = json.dumps(mcp_servers)
    env["JEEVES_AGENTS"] = json.dumps(agents)
    env["JEEVES_PROMPTS_DIR"] = os.path.join(SCRIPT_DIR, "prompts")

    print(f"Starting Jeeves kernel on port {kernel_port}...")
    print(f"  MCP servers: {[s['name'] for s in mcp_servers]}")
    print(f"  Agents: {[a['name'] for a in agents]}")
    print(f"  Prompts dir: {env['JEEVES_PROMPTS_DIR']}")

    # Start kernel
    kernel_proc = subprocess.Popen(
        ["cargo", "run", "--", "run", "--http-addr", f"0.0.0.0:{kernel_port}"],
        cwd=os.path.join(SCRIPT_DIR, "..", "jeeves-core"),
        env=env,
    )

    if kernel_only:
        print("Kernel started. Press Ctrl+C to stop.")
        try:
            kernel_proc.wait()
        except KeyboardInterrupt:
            kernel_proc.terminate()
        return

    # Wait for kernel to be ready
    print("Waiting for kernel to be ready...")
    for _ in range(30):
        try:
            import requests
            resp = requests.get(f"http://localhost:{kernel_port}/health", timeout=2)
            if resp.status_code == 200:
                print("Kernel is ready!")
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        print("Warning: Kernel may not be ready yet.")

    # Start Gradio UI
    print(f"Starting Gradio UI...")
    gradio_env = os.environ.copy()
    gradio_env["JEEVES_KERNEL_URL"] = f"http://localhost:{kernel_port}"

    gradio_proc = subprocess.Popen(
        [sys.executable, os.path.join(SCRIPT_DIR, "gradio_app.py")],
        env=gradio_env,
    )

    try:
        kernel_proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        gradio_proc.terminate()
        kernel_proc.terminate()


if __name__ == "__main__":
    main()
