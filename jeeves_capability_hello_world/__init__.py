"""Jeeves Hello World - Onboarding Chatbot Capability

A 4-agent pipeline with conditional routing demonstrating kernel-driven orchestration.

Architecture:
    Understand (LLM) → Think-Knowledge | Think-Tools → Respond (LLM)
    Respond may loop back to Understand (bounded by max_llm_calls=7)

Usage:
    # Start Rust kernel + Gradio UI
    python run.py

    # Kernel only (for manual testing with curl)
    python run.py --kernel-only
"""

CAPABILITY_ID = "hello_world"
CAPABILITY_VERSION = "0.0.1"

__version__ = CAPABILITY_VERSION
__capability__ = CAPABILITY_ID
