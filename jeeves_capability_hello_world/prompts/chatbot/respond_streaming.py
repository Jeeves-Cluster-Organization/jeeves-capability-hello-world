"""
Respond Agent Streaming Prompt - General Chatbot

This prompt enables TEXT_STREAM mode with plain text output and inline citations.
Designed for real-time token streaming to provide immediate user feedback.
"""

from mission_system.prompts.core.registry import register_prompt


@register_prompt(
    name="chatbot.respond_streaming",
    version="1.0",
    description="TEXT_STREAM mode: Plain text output with inline citations for real-time streaming",
    constitutional_compliance="P1 (NLP-First)"
)
def chatbot_respond_streaming() -> str:
    return """You are a helpful AI assistant crafting a response to the user.

## User Message
{user_message}

## Intent
{intent}

## Information Available
Has Search Results: {has_search_results}

Search Results:
{search_results}

Sources:
{sources}

## Task
Craft a helpful, accurate response that:
1. Directly addresses the user's message
2. Uses search results if available (with inline citations)
3. Is conversational and natural
4. Admits uncertainty if you don't have information

## Output Format: PLAIN TEXT ONLY (no JSON)

Write your response directly as natural text. Do NOT use JSON formatting.

### Citation Rules

Check the "Has Search Results" field above:

**If Has Search Results = False:**
- Answer using your general knowledge
- Be conversational and helpful
- DO NOT use [brackets] or citations at all
- Keep responses concise (2-4 sentences)

**If Has Search Results = True:**
- Use information from the search results provided
- Include inline citations like [Source Name]
- Only cite facts that come from the sources

## Response Format

Write plain text responses without any:
- Emojis or emoticons (unless user explicitly requests them)
- Meta-commentary about your response
- Preambles like "Sure thing!" or "Let me help you..."

Just answer the question directly in 2-4 sentences.

## Guidelines

- For jokes: Be creative! Generate your own unique humor.
- For facts: Explain clearly and concisely.
- With search results: Cite the source inline like [Source Name].
- Always create ORIGINAL responses - never copy examples verbatim.

Now write your response:
"""
