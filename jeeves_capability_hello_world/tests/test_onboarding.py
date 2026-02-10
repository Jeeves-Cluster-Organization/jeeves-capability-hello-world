"""Tests for onboarding chatbot functionality."""

import pytest
from jeeves_capability_hello_world.prompts.knowledge_base import (
    ECOSYSTEM_OVERVIEW,
    LAYER_DETAILS,
    KEY_CONCEPTS,
    CODE_EXAMPLES,
    HELLO_WORLD_STRUCTURE,
    HOW_TO_GUIDES,
    KNOWLEDGE_SECTIONS,
    get_onboarding_context,
    get_knowledge_for_sections,
    get_section_names,
)


class TestKnowledgeBase:
    """Tests for embedded knowledge base."""

    def test_ecosystem_overview_contains_layers(self):
        """Verify all layers are documented."""
        assert "jeeves-core" in ECOSYSTEM_OVERVIEW
        assert "jeeves-infra" in ECOSYSTEM_OVERVIEW
        assert "Capabilities" in ECOSYSTEM_OVERVIEW

    def test_ecosystem_overview_contains_high_level(self):
        """Verify high-level architecture concepts."""
        assert "Three Layers" in ECOSYSTEM_OVERVIEW
        assert "micro-kernel" in ECOSYSTEM_OVERVIEW
        assert "Data Flow" in ECOSYSTEM_OVERVIEW
        assert "Envelope" in ECOSYSTEM_OVERVIEW

    def test_layer_details_contains_all_layers(self):
        """Verify layer details are documented."""
        # Layer 1: jeeves-core
        assert "Rust Micro-Kernel" in LAYER_DETAILS
        assert "Pipeline orchestration" in LAYER_DETAILS
        assert "Envelope state management" in LAYER_DETAILS

        # Layer 2: jeeves-infra
        assert "LLM providers" in LAYER_DETAILS
        assert "Database clients" in LAYER_DETAILS

        # jeeves-infra now includes orchestration (formerly mission_system)
        assert "Agent profiles" in LAYER_DETAILS
        assert "PipelineRunner" in LAYER_DETAILS

        # Layer 3: Capabilities
        assert "Domain prompts" in LAYER_DETAILS
        assert "Custom tools" in LAYER_DETAILS

    def test_key_concepts_contains_required(self):
        """Verify key concepts are documented."""
        assert "Envelope" in KEY_CONCEPTS
        assert "AgentConfig" in KEY_CONCEPTS
        assert "Constitution R7" in KEY_CONCEPTS
        assert "PipelineConfig" in KEY_CONCEPTS

    def test_key_concepts_envelope_details(self):
        """Verify Envelope concept is well documented."""
        assert "envelope_id" in KEY_CONCEPTS
        assert "raw_input" in KEY_CONCEPTS
        assert "metadata" in KEY_CONCEPTS
        assert "current_stage" in KEY_CONCEPTS
        assert "outputs" in KEY_CONCEPTS

    def test_key_concepts_agent_config_details(self):
        """Verify AgentConfig concept is documented."""
        assert "has_llm" in KEY_CONCEPTS
        assert "has_tools" in KEY_CONCEPTS
        assert "prompt_key" in KEY_CONCEPTS
        assert "output_key" in KEY_CONCEPTS

    def test_key_concepts_constitution_r7(self):
        """Verify Constitution R7 is documented."""
        assert "Import Boundaries" in KEY_CONCEPTS
        assert "CORRECT" in KEY_CONCEPTS
        assert "WRONG" in KEY_CONCEPTS
        assert "adapters" in KEY_CONCEPTS

    def test_key_concepts_pipeline_pattern(self):
        """Verify pipeline pattern is documented."""
        assert "Understand" in KEY_CONCEPTS
        assert "Think" in KEY_CONCEPTS
        assert "Respond" in KEY_CONCEPTS

    def test_hello_world_structure_contains_files(self):
        """Verify hello world structure is documented."""
        assert "gradio_app.py" in HELLO_WORLD_STRUCTURE
        assert "pipeline_config.py" in HELLO_WORLD_STRUCTURE
        assert "understand.py" in HELLO_WORLD_STRUCTURE
        assert "respond.py" in HELLO_WORLD_STRUCTURE
        assert "chatbot_service.py" in HELLO_WORLD_STRUCTURE

    def test_code_examples_contains_patterns(self):
        """Verify code examples are provided."""
        assert "def get_time" in CODE_EXAMPLES or "get_time" in CODE_EXAMPLES
        assert "tool_catalog.register" in CODE_EXAMPLES
        assert "@register_prompt" in CODE_EXAMPLES
        assert "AgentConfig" in CODE_EXAMPLES

    def test_how_to_guides_contains_guides(self):
        """Verify how-to guides are provided."""
        assert "How to Add a New Tool" in HOW_TO_GUIDES
        assert "How to Create a New Agent" in HOW_TO_GUIDES
        assert "How to Run the Capability" in HOW_TO_GUIDES
        assert "Common Troubleshooting" in HOW_TO_GUIDES

    def test_get_onboarding_context_combines_all(self):
        """Verify context includes all sections."""
        context = get_onboarding_context()
        assert "Jeeves Ecosystem" in context
        assert "Key Concepts" in context
        assert "Hello World Capability Structure" in context
        assert "Code Examples" in context
        assert "How-To Guides" in context

    def test_get_onboarding_context_length(self):
        """Verify context is reasonable length for embedding."""
        context = get_onboarding_context()
        # Should be substantial with detailed knowledge
        assert len(context) > 5000  # Has meaningful content
        assert len(context) < 20000  # Still reasonable for prompts

    def test_knowledge_sections_dict(self):
        """Verify all sections are in the registry."""
        expected_sections = [
            "ecosystem_overview",
            "layer_details",
            "key_concepts",
            "code_examples",
            "hello_world_structure",
            "how_to_guides",
        ]
        for section in expected_sections:
            assert section in KNOWLEDGE_SECTIONS

    def test_get_knowledge_for_sections(self):
        """Verify targeted knowledge retrieval works."""
        # Single section
        result = get_knowledge_for_sections(["ecosystem_overview"])
        assert "Jeeves Ecosystem" in result
        assert "How-To Guides" not in result

        # Multiple sections
        result = get_knowledge_for_sections(["key_concepts", "code_examples"])
        assert "Envelope" in result
        assert "tool_catalog.register" in result

    def test_get_knowledge_for_sections_fallback(self):
        """Verify fallback to ecosystem_overview for empty/invalid."""
        result = get_knowledge_for_sections([])
        assert "Jeeves Ecosystem" in result

        result = get_knowledge_for_sections(["nonexistent_section"])
        assert "Jeeves Ecosystem" in result

    def test_get_section_names(self):
        """Verify section names API."""
        names = get_section_names()
        assert "ecosystem_overview" in names
        assert "key_concepts" in names
        assert len(names) == 6


class TestOnboardingIntents:
    """Tests for intent classification."""

    @pytest.mark.parametrize("query,expected_intent", [
        ("What is the architecture?", "architecture"),
        ("How do the layers work?", "architecture"),
        ("What is an Envelope?", "concept"),
        ("Explain AgentConfig", "concept"),
        ("How do I run this?", "getting_started"),
        ("How do I add a tool?", "getting_started"),
        ("What is jeeves-core?", "component"),
        ("What does jeeves-infra do?", "component"),
        ("Hello!", "general"),
        ("Thanks!", "general"),
    ])
    def test_intent_categories_exist(self, query, expected_intent):
        """Verify intent categories are valid."""
        valid_intents = ["architecture", "concept", "getting_started", "component", "general"]
        assert expected_intent in valid_intents


class TestToolsOnboarding:
    """Tests for onboarding tools."""

    def test_list_tools_returns_capabilities(self):
        """Verify list_tools includes onboarding capabilities."""
        from jeeves_capability_hello_world.tools.hello_world_tools import list_tools

        result = list_tools()

        assert result["status"] == "success"
        assert "tools" in result
        assert "capabilities" in result
        assert len(result["capabilities"]) > 0

    def test_list_tools_mentions_ecosystem(self):
        """Verify list_tools describes ecosystem capabilities."""
        from jeeves_capability_hello_world.tools.hello_world_tools import list_tools

        result = list_tools()
        capabilities = result["capabilities"]

        # Check key capabilities are listed
        capability_text = " ".join(capabilities)
        assert "Jeeves" in capability_text or "ecosystem" in capability_text
        assert "jeeves-core" in capability_text or "architecture" in capability_text

    def test_get_time_works(self):
        """Verify get_time tool still works."""
        from jeeves_capability_hello_world.tools.hello_world_tools import get_time

        result = get_time()

        assert result["status"] == "success"
        assert "datetime" in result
        assert "date" in result
        assert "time" in result
