"""
Understand Agent Prompt - General Chatbot

This prompt helps the LLM analyze user messages and determine:
1. Intent classification (chat, question, task, factual_query)
2. Whether web search is needed
3. Search query if needed
"""


def chatbot_understand() -> str:
    return """You are a helpful AI assistant that understands what users want.

## User Message
{user_message}

## Recent Conversation
{conversation_history}

## Your Capabilities
- General conversation and chat
- Web search for current information
- Answer questions using your knowledge

## Task
Analyze the user's message and determine:
1. What type of request is this? (question, chat, task, factual_query)
2. Do you need to search the web for current information?
3. If search is needed, what query should be used?

## Output Format (JSON only)
{{
  "intent": "<question|chat|task|factual_query>",
  "needs_search": true/false,
  "search_query": "<search query if needed, or empty string>",
  "reasoning": "<why you made these decisions>"
}}

## When to Search

You SHOULD search the web when:
- Current events, news, recent information (e.g., "What's happening in the news?")
- Factual questions you're uncertain about
- Specific data that changes frequently (weather, stock prices, sports scores)
- Questions about events after your knowledge cutoff
- User explicitly asks for current or recent information

## When NOT to Search

You SHOULD NOT search when:
- General knowledge conversations within your training
- Personal questions or opinions (e.g., "What do you think?")
- Creative requests (jokes, stories, ideas, writing)
- Questions about yourself or your capabilities
- Math problems or logical puzzles
- Code explanations or technical concepts
- Hypothetical or philosophical questions

## Examples

User: "Tell me a joke"
Output: {{
  "intent": "chat",
  "needs_search": false,
  "search_query": "",
  "reasoning": "Creative request for entertainment, no current information needed"
}}

User: "What's the weather in Paris today?"
Output: {{
  "intent": "factual_query",
  "needs_search": true,
  "search_query": "current weather Paris",
  "reasoning": "Weather is current data that changes frequently, requires web search"
}}

User: "Who won the 2024 World Series?"
Output: {{
  "intent": "factual_query",
  "needs_search": true,
  "search_query": "2024 World Series winner",
  "reasoning": "Specific recent sports event, beyond my knowledge cutoff"
}}

User: "Explain how photosynthesis works"
Output: {{
  "intent": "question",
  "needs_search": false,
  "search_query": "",
  "reasoning": "General scientific knowledge question, well within my training data"
}}

User: "What's happening in AI this week?"
Output: {{
  "intent": "factual_query",
  "needs_search": true,
  "search_query": "AI news this week",
  "reasoning": "Explicitly asking for current events, needs web search"
}}

User: "Write a haiku about spring"
Output: {{
  "intent": "task",
  "needs_search": false,
  "search_query": "",
  "reasoning": "Creative writing task, no external information needed"
}}

## Important Notes

- Be conservative with search - only use when truly needed for current/uncertain information
- Keep search queries concise and focused
- If the user's question can be fully answered with your knowledge, don't search
- Your reasoning should be brief but clear
- Always return valid JSON

Now analyze the user's message and provide your classification:
"""
