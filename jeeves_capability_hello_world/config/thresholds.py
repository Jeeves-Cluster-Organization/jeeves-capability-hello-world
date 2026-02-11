"""Agent-specific thresholds for hello-world capability.

Moved from jeeves_infra/thresholds.py — these constants are tuning knobs
for the specific agents in this capability (planner, critic, meta-validator).
Infrastructure thresholds remain in jeeves_infra/thresholds.py.
"""

# =============================================================================
# CONFIRMATION SYSTEM
# =============================================================================

CONFIRMATION_DETECTION_CONFIDENCE = 0.7
CONFIRMATION_INTERPRETATION_CONFIDENCE = 0.7

# =============================================================================
# PLANNING & EXECUTION
# =============================================================================

# Below this confidence, planner should request clarification
# Tuned for Qwen 7B local LLM (smaller models produce lower confidence scores)
PLAN_MIN_CONFIDENCE = 0.70

# Above this confidence, skip optional validation steps
PLAN_HIGH_CONFIDENCE = 0.85


# =============================================================================
# CRITIC & VALIDATION
# =============================================================================

CRITIC_APPROVAL_THRESHOLD = 0.80
CRITIC_HIGH_CONFIDENCE = 0.85
CRITIC_MEDIUM_CONFIDENCE = 0.75
CRITIC_LOW_CONFIDENCE = 0.6
CRITIC_DEFAULT_CONFIDENCE = 0.5

META_VALIDATOR_PASS_THRESHOLD = 0.9
META_VALIDATOR_APPROVED_CONFIDENCE = 0.95
META_VALIDATOR_REJECTED_CONFIDENCE = 0.35

USER_CONFIRMED_CONFIDENCE = 0.9


# =============================================================================
# SEARCH & MATCHING
# =============================================================================

FUZZY_MATCH_MIN_SCORE = 0.5
SEMANTIC_SEARCH_MIN_SIMILARITY = 0.5
HYBRID_SEARCH_FUZZY_WEIGHT = 0.4
HYBRID_SEARCH_SEMANTIC_WEIGHT = 0.6


# =============================================================================
# WORKING MEMORY / SESSION
# =============================================================================

SESSION_SUMMARIZATION_TURN_THRESHOLD = 8
SESSION_TOKEN_BUDGET_THRESHOLD = 6000
SESSION_IDLE_TIMEOUT_MINUTES = 30
OPEN_LOOP_STALE_DAYS = 7
