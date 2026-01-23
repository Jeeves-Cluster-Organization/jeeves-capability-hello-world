"""TraversalState for code analysis - extends WorkingMemory.

This is the code-analysis specific state model that extends the generic
WorkingMemory from jeeves_protocols with code-specific fields.

Part of the code_analysis vertical - NOT part of core.

Updated for jeeves-core v4.0:
- WorkingMemory is now a dataclass (not Pydantic)
- TraversalState uses composition rather than inheritance for better compatibility
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

# Constitutional imports - from jeeves_protocols (canonical location)
from jeeves_protocols import WorkingMemory, Finding


@dataclass
class CodeSnippet:
    """A relevant code snippet found during traversal."""
    file: str
    start_line: int
    end_line: int
    content: str
    relevance: str
    tokens: int = 0

    def __post_init__(self):
        if self.tokens == 0:
            self.tokens = len(self.content) // 4

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "content": self.content,
            "relevance": self.relevance,
            "tokens": self.tokens,
        }


@dataclass
class CallChainEntry:
    """An entry in the call chain being traced."""
    caller: str
    callee: str
    file: str
    line: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "caller": self.caller,
            "callee": self.callee,
            "file": self.file,
            "line": self.line,
        }


# Default bounds for code analysis (can be overridden via injection)
DEFAULT_CODE_BOUNDS = {
    "max_explored_files": 100,
    "max_explored_symbols": 200,
    "max_pending_files": 50,
    "max_relevant_snippets": 50,
    "max_call_chain_length": 20,
}


@dataclass
class TraversalState:
    """Working memory state for code traversal.

    Composes WorkingMemory with code-analysis specific fields:
    - explored_files, explored_symbols (code-specific exploration tracking)
    - relevant_snippets, call_chain (code-specific findings)
    - detected_languages, repo_patterns (code-specific metadata)

    Bounds are injected via constructor or passed to add_* methods,
    NOT imported from config modules.

    Updated for jeeves-core v4.0:
    - Uses composition with WorkingMemory instead of inheritance
    - WorkingMemory is now a dataclass from jeeves_protocols
    """

    # Core identity
    session_id: str
    user_id: str = "anonymous"

    # Composed WorkingMemory for base memory operations
    _working_memory: Optional[WorkingMemory] = field(default=None, repr=False)

    # ─── Code-Specific Exploration Tracking ───
    explored_files: List[str] = field(default_factory=list)
    explored_symbols: List[str] = field(default_factory=list)
    pending_files: List[str] = field(default_factory=list)
    pending_symbols: List[str] = field(default_factory=list)

    # ─── Code-Specific Findings ───
    relevant_snippets: List[Dict[str, Any]] = field(default_factory=list)
    call_chain: List[Dict[str, Any]] = field(default_factory=list)

    # ─── Code-Specific Metadata ───
    detected_languages: List[str] = field(default_factory=list)
    repo_patterns: Dict[str, Any] = field(default_factory=dict)
    scope_path: Optional[str] = None

    # ─── Token and Loop Tracking ───
    tokens_used: int = 0
    current_loop: int = 0
    query_intent: str = ""

    # ─── Timestamps ───
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Injected bounds (not serialized)
    _bounds: Dict[str, int] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        """Initialize bounds and working memory after construction."""
        if not self._bounds:
            self._bounds = DEFAULT_CODE_BOUNDS.copy()

        # Initialize composed WorkingMemory
        if self._working_memory is None:
            from jeeves_protocols import create_working_memory
            self._working_memory = create_working_memory(
                session_id=self.session_id,
                user_id=self.user_id,
            )

        # Set timestamps if not provided
        if self.created_at is None:
            from jeeves_protocols import utc_now
            self.created_at = utc_now()
        if self.updated_at is None:
            self.updated_at = self.created_at

    @property
    def working_memory(self) -> WorkingMemory:
        """Access the composed WorkingMemory."""
        return self._working_memory

    def add_explored_file(self, file_path: str, max_files: Optional[int] = None) -> None:
        """Mark a file as explored.

        Args:
            file_path: File to mark as explored
            max_files: Override for max files (uses injected bounds if not provided)
        """
        max_items = max_files or self._bounds.get("max_explored_files", 100)

        if file_path not in self.explored_files:
            while len(self.explored_files) >= max_items:
                self.explored_files.pop(0)
            self.explored_files.append(file_path)

        # Remove from pending if present
        if file_path in self.pending_files:
            self.pending_files.remove(file_path)

    def add_explored_symbol(self, symbol: str, max_symbols: Optional[int] = None) -> None:
        """Mark a symbol as explored.

        Args:
            symbol: Symbol to mark as explored
            max_symbols: Override for max symbols
        """
        max_items = max_symbols or self._bounds.get("max_explored_symbols", 200)

        if symbol not in self.explored_symbols:
            while len(self.explored_symbols) >= max_items:
                self.explored_symbols.pop(0)
            self.explored_symbols.append(symbol)

        # Remove from pending if present
        if symbol in self.pending_symbols:
            self.pending_symbols.remove(symbol)

    def add_pending_file(self, file_path: str, max_pending: Optional[int] = None) -> None:
        """Add file to exploration queue.

        Args:
            file_path: File to queue
            max_pending: Override for max pending files
        """
        max_items = max_pending or self._bounds.get("max_pending_files", 50)

        if file_path not in self.explored_files and file_path not in self.pending_files:
            while len(self.pending_files) >= max_items:
                self.pending_files.pop(0)
            self.pending_files.append(file_path)

    def add_pending_symbol(self, symbol: str) -> None:
        """Add symbol to lookup queue."""
        if symbol not in self.explored_symbols and symbol not in self.pending_symbols:
            self.pending_symbols.append(symbol)

    def add_snippet(
        self,
        file: str,
        start_line: int,
        end_line: int,
        content: str,
        relevance: str,
        max_snippets: Optional[int] = None,
    ) -> None:
        """Add a relevant code snippet.

        Args:
            file: File path
            start_line: Starting line number
            end_line: Ending line number
            content: Code content
            relevance: Why this snippet is relevant
            max_snippets: Override for max snippets
        """
        max_items = max_snippets or self._bounds.get("max_relevant_snippets", 50)

        snippet = {
            "file": file,
            "start_line": start_line,
            "end_line": end_line,
            "content": content,
            "relevance": relevance,
            "tokens": len(content) // 4,
        }

        while len(self.relevant_snippets) >= max_items:
            removed = self.relevant_snippets.pop(0)
            self.tokens_used -= removed.get("tokens", 0)

        self.relevant_snippets.append(snippet)
        self.tokens_used += snippet["tokens"]

        # Also add as Finding in composed WorkingMemory
        finding = Finding(
            finding_id=f"{file}:{start_line}-{end_line}",
            finding_type="code_snippet",
            title=f"Snippet from {file}",
            description=relevance,
            location=f"{file}:{start_line}-{end_line}",
            evidence=[{"content": content[:500]}],  # Truncate for storage
        )
        self._working_memory.add_finding(finding)

    def add_call_chain_entry(
        self,
        caller: str,
        callee: str,
        file: str,
        line: int,
        max_chain: Optional[int] = None,
    ) -> None:
        """Add an entry to the call chain.

        Args:
            caller: Caller function/method name
            callee: Called function/method name
            file: File where call occurs
            line: Line number of call
            max_chain: Override for max chain length
        """
        max_items = max_chain or self._bounds.get("max_call_chain_length", 20)

        entry = {
            "caller": caller,
            "callee": callee,
            "file": file,
            "line": line,
        }

        while len(self.call_chain) >= max_items:
            self.call_chain.pop(0)

        self.call_chain.append(entry)

    def get_exploration_summary(self) -> str:
        """Get a summary of exploration progress."""
        return (
            f"Explored: {len(self.explored_files)} files, {len(self.explored_symbols)} symbols. "
            f"Pending: {len(self.pending_files)} files, {len(self.pending_symbols)} symbols. "
            f"Found: {len(self.relevant_snippets)} snippets, {len(self.call_chain)} call chain entries. "
            f"Tokens: ~{self.tokens_used}. Loop: {self.current_loop}."
        )

    def reset_for_new_query(self, query_intent: str = "") -> None:
        """Reset state for a new query while keeping session context."""
        self.query_intent = query_intent
        self.pending_files = []
        self.pending_symbols = []
        self.relevant_snippets = []
        self.call_chain = []
        self.current_loop = 0
        self.tokens_used = 0

        # Reset composed WorkingMemory findings
        self._working_memory.findings = []

        # Update timestamp
        from jeeves_protocols import utc_now
        self.updated_at = utc_now()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize state to dictionary."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "explored_files": self.explored_files,
            "explored_symbols": self.explored_symbols,
            "pending_files": self.pending_files,
            "pending_symbols": self.pending_symbols,
            "relevant_snippets": self.relevant_snippets,
            "call_chain": self.call_chain,
            "detected_languages": self.detected_languages,
            "repo_patterns": self.repo_patterns,
            "scope_path": self.scope_path,
            "tokens_used": self.tokens_used,
            "current_loop": self.current_loop,
            "query_intent": self.query_intent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        bounds: Optional[Dict[str, int]] = None
    ) -> "TraversalState":
        """Create from dictionary.

        Args:
            data: State data
            bounds: Optional bounds to inject

        Returns:
            TraversalState instance
        """
        # Parse timestamps if present
        created_at = data.get("created_at")
        updated_at = data.get("updated_at")
        if isinstance(created_at, str):
            from jeeves_protocols import parse_datetime
            created_at = parse_datetime(created_at)
        if isinstance(updated_at, str):
            from jeeves_protocols import parse_datetime
            updated_at = parse_datetime(updated_at)

        return cls(
            session_id=data.get("session_id", ""),
            user_id=data.get("user_id", "anonymous"),
            explored_files=data.get("explored_files", []),
            explored_symbols=data.get("explored_symbols", []),
            pending_files=data.get("pending_files", []),
            pending_symbols=data.get("pending_symbols", []),
            relevant_snippets=data.get("relevant_snippets", []),
            call_chain=data.get("call_chain", []),
            detected_languages=data.get("detected_languages", []),
            repo_patterns=data.get("repo_patterns", {}),
            scope_path=data.get("scope_path"),
            tokens_used=data.get("tokens_used", 0),
            current_loop=data.get("current_loop", 0),
            query_intent=data.get("query_intent", ""),
            created_at=created_at,
            updated_at=updated_at,
            _bounds=bounds or DEFAULT_CODE_BOUNDS.copy(),
        )


# Factory function for creating TraversalState
def create_traversal_state(
    session_id: str,
    user_id: str = "anonymous",
    bounds: Optional[Dict[str, int]] = None,
) -> TraversalState:
    """Factory function to create a new TraversalState.

    Args:
        session_id: Session identifier
        user_id: User identifier
        bounds: Optional bounds configuration

    Returns:
        New TraversalState instance
    """
    return TraversalState(
        session_id=session_id,
        user_id=user_id,
        _bounds=bounds or DEFAULT_CODE_BOUNDS.copy(),
    )


__all__ = [
    "TraversalState",
    "CodeSnippet",
    "CallChainEntry",
    "DEFAULT_CODE_BOUNDS",
    "create_traversal_state",
]
