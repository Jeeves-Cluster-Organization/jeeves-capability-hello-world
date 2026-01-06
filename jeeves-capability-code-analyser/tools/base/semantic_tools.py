"""Semantic code search tools - RAG-based file discovery.

Phase 2/4 Constitutional Compliance - No auto-registration at import time

These tools provide semantic search capabilities using embeddings stored in pgvector.
All tools are READ_ONLY risk level since they don't modify any files.

Tools:
- semantic_search: Find files by semantic similarity to a query
- find_similar_files: Find files similar to a given file

Prerequisites:
- Repository must be indexed using the CodeIndexer service
- pgvector extension enabled in PostgreSQL
- code_index table populated with embeddings

Decision 1:A/2:B Compliance:
- Uses contextvars instead of true global state
- Indexer is scoped per-request, not globally mutable
- Thread-safe and async-safe
"""

from contextvars import ContextVar
from typing import Any, Dict, List, Optional

from jeeves_protocols import LoggerProtocol
from jeeves_capability_code_analyser.logging import get_logger
from jeeves_protocols import RiskLevel
from tools.base.path_helpers import (
    get_repo_path,
    resolve_path,
    ensure_repo_path_valid,
    repo_path_error_response,
)

# Decision 1:A/2:B: Use contextvars instead of true global state
# Each async request gets its own context - no global mutable state
_code_indexer_context: ContextVar[Optional['CodeIndexer']] = ContextVar(
    'code_indexer', default=None
)


def set_code_indexer(indexer: 'CodeIndexer') -> None:
    """Set the code indexer instance for the current context.

    Decision 1:A/2:B: Uses contextvars for per-request scoping.
    This is NOT a true global - each async task has its own context.

    Args:
        indexer: CodeIndexer instance to use for semantic search

    Usage:
        # At request start (server.py)
        set_code_indexer(indexer)

        # Semantic tools automatically use this context
        result = await semantic_search("authentication")
    """
    _logger = get_logger()
    _code_indexer_context.set(indexer)
    _logger.info("semantic_tools_indexer_set_in_context")


def get_code_indexer() -> Optional['CodeIndexer']:
    """Get the code indexer instance from current context.

    Returns:
        CodeIndexer if set in current context, None otherwise
    """
    return _code_indexer_context.get()


async def semantic_search(
    query: str,
    limit: int = 10,
    languages: Optional[str] = None,
    min_similarity: float = 0.3,
    include_snippets: bool = False,
    path_prefix: Optional[str] = None,
) -> Dict[str, Any]:
    """Search for code files by semantic similarity.

    Args:
        query: Natural language query describing what to find
        limit: Maximum number of results (default: 10)
        languages: Comma-separated language filter (e.g., 'python,javascript')
        min_similarity: Minimum similarity threshold (default: 0.3)
        include_snippets: Include code snippets in results (default: False)
        path_prefix: Filter to files under this path prefix (optional)

    Returns:
        Dict with:
        - status: "success" or "error"
        - files: List of matching files with paths and scores
        - count: Number of matches
        - query: The search query used
    """
    # Validate repo path exists
    if not ensure_repo_path_valid():
        return repo_path_error_response()

    # Check if indexer is available
    indexer = get_code_indexer()
    if indexer is None:
        return {
            "status": "error",
            "error": "Semantic search not available. Repository may not be indexed. "
                     "Run the indexing script to enable semantic search.",
        }

    if not query or not query.strip():
        return {
            "status": "error",
            "error": "Query is required for semantic search",
        }

    try:
        # Parse languages filter - handle both string and list inputs
        lang_list = None
        if languages:
            if isinstance(languages, list):
                # Already a list, just normalize
                lang_list = [str(lang).strip().lower() for lang in languages]
            else:
                # String, split by comma
                lang_list = [lang.strip().lower() for lang in languages.split(",")]

        # Perform search (request extra if filtering by path)
        search_limit = limit * 2 if path_prefix else limit
        results = await indexer.search(
            query=query,
            limit=search_limit,
            min_similarity=min_similarity,
            languages=lang_list,
        )

        # Apply path prefix filter if specified
        if path_prefix:
            prefix = path_prefix.rstrip("/")
            results = [r for r in results if r["file_path"].startswith(prefix)][:limit]

        # Format results with optional snippets
        files = []
        for r in results:
            file_info = {
                "file": r["file_path"],
                "language": r["language"],
                "score": round(r["score"], 3),
                "lines": r["line_count"],
            }
            # Include snippet if requested and available
            if include_snippets and "snippet" in r:
                file_info["snippet"] = r["snippet"][:500]  # Limit snippet length
            files.append(file_info)

        return {
            "status": "success",
            "files": files,
            "count": len(files),
            "query": query,
            "path_prefix": path_prefix,
        }

    except Exception as e:
        _logger = get_logger()
        _logger.error("semantic_search_error", query=query, error=str(e))
        return {
            "status": "error",
            "error": f"Semantic search failed: {e}",
        }


async def find_similar_files(
    file_path: str,
    limit: int = 5,
    min_similarity: float = 0.4,
) -> Dict[str, Any]:
    """Find files similar to a given file.

    Args:
        file_path: Path to the reference file
        limit: Maximum number of similar files to return (default: 5)
        min_similarity: Minimum similarity threshold (default: 0.4)

    Returns:
        Dict with:
        - status: "success" or "error"
        - reference_file: The input file path
        - similar_files: List of similar files with paths and scores
        - count: Number of similar files found
    """
    # Validate repo path exists
    if not ensure_repo_path_valid():
        return repo_path_error_response()

    repo_path = get_repo_path()

    # Check if indexer is available
    indexer = get_code_indexer()
    if indexer is None:
        return {
            "status": "error",
            "error": "Semantic search not available. Repository may not be indexed.",
        }

    # Resolve and validate file path
    resolved = resolve_path(file_path, repo_path)
    if resolved is None:
        return {
            "status": "error",
            "error": f"Path '{file_path}' is outside repository bounds",
        }

    if not resolved.exists():
        return {
            "status": "error",
            "error": f"File not found: {file_path}",
        }

    if not resolved.is_file():
        return {
            "status": "error",
            "error": f"Not a file: {file_path}",
        }

    try:
        # Read file content for embedding
        content = resolved.read_text(encoding='utf-8', errors='replace')

        # Use file content as the query to find similar files
        # Limit content to avoid huge embeddings
        query_content = f"File: {file_path}\n\n{content[:6000]}"

        # Perform search (requesting limit+1 to exclude the reference file)
        results = await indexer.search(
            query=query_content,
            limit=limit + 1,
            min_similarity=min_similarity,
        )

        # Get relative path for comparison
        rel_path = str(resolved.relative_to(repo_path))

        # Filter out the reference file itself
        similar = [
            {
                "file": r["file_path"],
                "language": r["language"],
                "score": round(r["score"], 3),
                "lines": r["line_count"],
            }
            for r in results
            if r["file_path"] != rel_path and r["file_path"] != file_path
        ][:limit]

        return {
            "status": "success",
            "reference_file": rel_path,
            "similar_files": similar,
            "count": len(similar),
        }

    except Exception as e:
        _logger = get_logger()
        _logger.error("find_similar_files_error", file=file_path, error=str(e))
        return {
            "status": "error",
            "error": f"Failed to find similar files: {e}",
        }


async def get_index_stats() -> Dict[str, Any]:
    """Get statistics about the code index.

    Returns:
        Dict with:
        - status: "success" or "error"
        - stats: Index statistics including file counts, languages, etc.
    """
    # Check if indexer is available
    indexer = get_code_indexer()
    if indexer is None:
        return {
            "status": "error",
            "error": "Semantic search not available. Repository may not be indexed.",
        }

    try:
        stats = await indexer.get_stats()

        if "error" in stats:
            return {
                "status": "error",
                "error": stats["error"],
            }

        return {
            "status": "success",
            "stats": stats,
        }

    except Exception as e:
        _logger = get_logger()
        _logger.error("get_index_stats_error", error=str(e))
        return {
            "status": "error",
            "error": f"Failed to get index stats: {e}",
        }


def register_semantic_tools(
    code_indexer: Optional['CodeIndexer'] = None,
) -> Dict[str, Any]:
    """
    Register semantic tools and optionally set the code indexer.

    This function is called during tool initialization to:
    1. Ensure semantic tools are registered in the tool registry
    2. Optionally set the code indexer instance for actual search functionality

    Args:
        code_indexer: Optional CodeIndexer instance for semantic search

    Returns:
        Dict with registration status and tool count
    """
    # Set the indexer if provided
    if code_indexer is not None:
        set_code_indexer(code_indexer)

    # The tools are no longer auto-registered via decorators
    # They must be registered via the new registration system
    _logger = get_logger()
    semantic_tool_names = ["semantic_search", "find_similar_files", "get_index_stats"]

    _logger.info(
        "semantic_tools_setup",
        tools=semantic_tool_names,
        indexer_available=code_indexer is not None,
    )

    return {
        "count": len(semantic_tool_names),
        "tools": semantic_tool_names,
        "indexer_available": code_indexer is not None,
    }


__all__ = ["semantic_search", "find_similar_files", "get_index_stats", "set_code_indexer", "get_code_indexer", "register_semantic_tools"]
