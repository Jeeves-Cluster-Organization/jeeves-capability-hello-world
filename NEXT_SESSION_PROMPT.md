# Next Session: Complexity Refactoring Implementation

## Current Status

**Phase 1:** ✅ COMPLETE (2/2 tasks done)
**Phase 2:** 🔄 READY TO START (0/5 sub-tasks done)
**Last Updated:** 2026-01-25

## Context

We've completed a comprehensive Root Cause Analysis (RCA) of the three highest-complexity functions in the jeeves-core codebase. The analysis is documented in [COMPLEXITY_RCA_ANALYSIS.md](COMPLEXITY_RCA_ANALYSIS.md).

**Phase 1 has been completed successfully:**
- ✅ Task 1.1: Documented `_split_sql_statements` (CCN 28 justified)
- ✅ Task 1.2: Refactored `_publish_unified_event` (CCN 17→3)
- ✅ Results: 2 commits, 17 new tests, 61/61 tests passing

See [PHASE1_REVIEW_AND_PHASE2_AUDIT.md](PHASE1_REVIEW_AND_PHASE2_AUDIT.md) for detailed review.

## Objective

Implement Phase 2 refactoring: Extract helpers from `send_message` function and implement Strategy Pattern to reduce complexity from CCN 26 → 5.

## Tasks to Complete

### Phase 1: Quick Wins ✅ COMPLETE

#### Task 1.1: Document `_split_sql_statements` Function ✅
**File:** `jeeves-core/jeeves_avionics/database/postgres_client.py:304-420`
**Status:** ✅ COMPLETE
**Commit:** `70a983a` - docs(database): document _split_sql_statements complexity justification

**Completed:**
- ✅ Added 85-line comprehensive docstring explaining CCN 28 justification
- ✅ Documented 5 PostgreSQL syntax features handled (dollar quotes, comments, etc.)
- ✅ Documented test coverage (15 unit tests, 100% coverage, 0 bugs in 12 months)
- ✅ Added "Acceptance Criteria for Refactoring" section
- ✅ Included example edge cases (semicolons in strings, nested quotes, etc.)
- ✅ Documented trade-offs vs sqlparse library (7-dimension table)

**Result:** CCN 28 accepted and documented (not reduced)

#### Task 1.2: Refactor `_publish_unified_event` Function ✅
**File:** `jeeves-core/jeeves_avionics/gateway/routers/chat.py:40-112`
**Status:** ✅ COMPLETE
**Commit:** `ef6acad` - refactor(gateway): simplify _publish_unified_event with lookup table

**Completed:**
- ✅ Created `EVENT_CATEGORY_MAP` dictionary (19 event type mappings)
- ✅ Extracted `_classify_event_category(event_type: str) -> EventCategory` helper
- ✅ Implemented exact match lookup + prefix matching fallback for backward compatibility
- ✅ Updated `_publish_unified_event` to use the new helper
- ✅ Added 17 unit tests for `_classify_event_category` covering all event types
- ✅ Verified backward compatibility with existing event type strings
- ✅ Ran all existing tests - 61/61 passing (no regressions)

**Result:** CCN reduced from 17 → 3 (82% reduction)

### Phase 2: Major Refactoring 🔄 READY TO START

**Important:** See [PHASE1_REVIEW_AND_PHASE2_AUDIT.md](PHASE1_REVIEW_AND_PHASE2_AUDIT.md) for detailed implementation specs, code examples, and test templates.

#### Task 2.1: Refactor `send_message` Function
**File:** `jeeves-core/jeeves_avionics/gateway/routers/chat.py:268-427`
**Current State:** CCN 26, 160 lines, 6 responsibilities in one function
**Target:** CCN 5, ~45 lines, with 4 handlers + 3 helpers
**Action:** Implement Section 1.6 Option A from RCA

**Sub-tasks (follow in order):**

**2.1a: Extract gRPC Request Builder (30 min)**
- [ ] Create `_build_grpc_request(user_id: str, body: MessageSend) -> jeeves_pb2.FlowRequest`
- [ ] Move lines 214-225 to new function
- [ ] Add docstring
- [ ] Add unit test

**2.1b: Extract Event Classifier (15 min)**
- [ ] Create `_is_internal_event(event_type: jeeves_pb2.FlowEvent) -> bool`
- [ ] Move lines 250-262 (internal_event_types set) to new function
- [ ] Add docstring
- [ ] Add unit test

**2.1c: Implement Event Handler Strategy Pattern (2 hours)**
- [ ] Create abstract `EventHandler` base class with `handle()` method
- [ ] Implement `ResponseReadyHandler` (handles RESPONSE_READY events)
- [ ] Implement `ClarificationHandler` (handles CLARIFICATION events)
- [ ] Implement `ConfirmationHandler` (handles CONFIRMATION events)
- [ ] Implement `ErrorHandler` (handles ERROR events)
- [ ] Create `EVENT_HANDLERS` registry dictionary
- [ ] Add unit tests for each handler class (test mode_config field injection)
- [ ] Ensure constitutional compliance: Avionics R1 (Adapter Pattern)

**2.1d: Extract Stream Processor (1 hour)**
- [ ] Create `_process_event_stream()` async function
- [ ] Move stream consumption logic (lines 234-329) to new function
- [ ] Use `_is_internal_event()` for event filtering
- [ ] Use `EVENT_HANDLERS` for terminal event handling
- [ ] Return tuple: `(final_response, request_id, session_id)`
- [ ] Add integration test with mock gRPC stream

**2.1e: Simplify Main Function (30 min)**
- [ ] Refactor `send_message()` to orchestrate helpers
- [ ] Keep structure: build request → get mode config → process stream → return response
- [ ] Target: ~40 lines, CCN ~5
- [ ] Ensure readability: function should read like documentation

**2.1f: Testing & Validation (1-2 hours)**
- [ ] Run all existing integration tests
- [ ] Add unit tests for all new helper functions
- [ ] Verify no performance regression (measure response times before/after)
- [ ] Test error handling paths
- [ ] Test with different mode configurations
- [ ] Test with all event types (RESPONSE_READY, CLARIFICATION, CONFIRMATION, ERROR)

**Success Criteria:**
- Main function CCN reduced from 26 to ~5
- All helper functions have CCN ≤ 3
- 100% backward compatibility (all existing tests pass)
- Each helper has single responsibility
- No performance regression
- Code review approved by team

## Constitutional Compliance Checklist

Ensure all refactored code complies with relevant constitutions:

### Avionics Constitution
- [ ] **R1 (Adapter Pattern):** Implement protocols, don't modify them ✅
- [ ] **R2 (Configuration Over Code):** Event mappings are configuration, not hardcoded ✅
- [ ] **R3 (No Domain Logic):** Functions remain infrastructure-focused ✅
- [ ] **R6 (Defensive Error Handling):** Proper try/catch, HTTPException raising ✅

### Mission System Constitution
- [ ] **R7 (Single Responsibility):** Each function has one job ✅

### Layer Boundaries
- [ ] All functions remain in Avionics layer ✅
- [ ] Import only from jeeves_protocols and jeeves_shared ✅
- [ ] No imports from Mission System or Capability layers ✅

## Testing Strategy

### Before Refactoring
1. Run full test suite and record results
2. Measure baseline metrics (response times, error rates)
3. Document current behavior for each function

### During Refactoring
1. Extract one helper at a time
2. Run tests after each extraction
3. Keep commits small and atomic (one helper per commit)
4. Write unit tests for each new function before moving to next

### After Refactoring
1. Verify all existing tests pass
2. Verify new unit tests cover all helpers
3. Compare metrics to baseline (no regressions)
4. Run complexity analysis to confirm CCN reductions

## Git Workflow

### Commit Strategy
```bash
# Phase 1, Task 1.1
git commit -m "docs(database): document _split_sql_statements complexity justification

- Add comprehensive docstring explaining CCN 28
- Document SQL parsing state machine requirements
- Document test coverage and stability
- Add refactoring acceptance criteria

Ref: COMPLEXITY_RCA_ANALYSIS.md Section 3.6"

# Phase 1, Task 1.2
git commit -m "refactor(gateway): simplify _publish_unified_event with lookup table

- Extract EVENT_CATEGORY_MAP configuration
- Create _classify_event_category helper (CCN 13 → 1)
- Reduce main function from CCN 17 to CCN 3
- Add unit tests for event type classification
- Maintain backward compatibility with string matching

Ref: COMPLEXITY_RCA_ANALYSIS.md Section 2.6"

# Phase 2, Task 2.1a
git commit -m "refactor(gateway): extract _build_grpc_request helper

- Extract gRPC request building logic
- Add unit test for request builder
- Reduces send_message complexity (1/6 responsibilities)

Ref: COMPLEXITY_RCA_ANALYSIS.md Section 1.6"

# ... continue for each sub-task
```

### Branch Strategy
```bash
# Create feature branch
git checkout -b refactor/complexity-reduction-phase1-2

# After Phase 1 complete
git tag phase1-complete

# After Phase 2 complete
git tag phase2-complete

# When ready for review
git push origin refactor/complexity-reduction-phase1-2
```

## Prompt for Next Session (PHASE 2)

**Status:** Phase 1 complete (2/2 tasks ✅). Ready to start Phase 2.

```
Continue the complexity refactoring from NEXT_SESSION_PROMPT.md:

Phase 1: ✅ COMPLETE
- Task 1.1: ✅ Documented _split_sql_statements (CCN 28 justified)
- Task 1.2: ✅ Refactored _publish_unified_event (CCN 17→3)
- Results: 2 commits, 17 new tests, 61/61 tests passing

Phase 2: START HERE - Refactor send_message function
File: jeeves-core/jeeves_avionics/gateway/routers/chat.py:268-427
Target: CCN 26 → 5 (81% reduction)

Implementation Plan (follow in order):
1. Task 2.1a: Extract _build_grpc_request helper (30 min)
2. Task 2.1b: Extract _is_internal_event helper (15 min)
3. Task 2.1c: Implement EventHandler Strategy Pattern - 4 handler classes (2 hours)
4. Task 2.1d: Extract _process_event_stream function (1 hour)
5. Task 2.1e: Simplify send_message to orchestrate helpers (30 min)

CRITICAL: Read PHASE1_REVIEW_AND_PHASE2_AUDIT.md first for:
- Complete code templates for each helper/handler
- Unit test templates (14 tests total)
- Expected CCN for each function
- Git commit message templates

Requirements:
- Follow PHASE1_REVIEW_AND_PHASE2_AUDIT.md implementation specs exactly
- Run tests after each sub-task (atomic commits)
- Maintain 100% backward compatibility
- Follow constitutional compliance (Avionics R1, R2, R3, R6)

Success Criteria:
- send_message: CCN 26 → 5 (target met)
- All new unit tests pass (~14 tests)
- All existing integration tests pass (0 regressions)
- 5 atomic commits (one per sub-task)
```

## Expected Deliverables

### Files Modified
1. `jeeves-core/jeeves_avionics/database/postgres_client.py` (documentation only)
2. `jeeves-core/jeeves_avionics/gateway/routers/chat.py` (refactored)

### Files Created (if needed)
1. Test files for new helper functions (if not already covered)

### Documentation Updated
1. This file (NEXT_SESSION_PROMPT.md) - mark tasks complete
2. COMPLEXITY_RCA_ANALYSIS.md - update with actual results
3. complexity_summary.csv - regenerate after refactoring

### Metrics to Track
- CCN before/after for each function
- Test coverage percentage
- Response time (before/after)
- Lines of code (before/after)
- Number of functions (before: 3, after: ~15 with helpers)

## Risk Mitigation

### Low-Risk Changes (Phase 1)
- Documentation-only changes have zero risk
- Lookup table refactoring is simple and well-tested

### Medium-Risk Changes (Phase 2)
- send_message refactoring is larger but:
  - Each extraction is small and testable
  - Existing integration tests provide safety net
  - Backward compatibility is preserved
  - Can be reverted easily if issues arise

### Rollback Plan
If issues are discovered after deployment:
1. Revert to previous commit (tagged as pre-refactor)
2. All changes are in one feature branch
3. Original behavior is preserved in git history
4. No database schema changes, so rollback is safe

## Questions to Address During Implementation

1. **Event Type Standardization:** Should we standardize event type strings now (e.g., "agent.perception" vs "perception") or maintain backward compatibility indefinitely?

2. **Error Handling for _split_sql_statements:** Should we add validation for unclosed quotes/comments (Section 3.6 Option B) or defer until bugs emerge?

3. **gRPC Adapter Layer:** Should we create a dedicated `GrpcFlowAdapter` class (Section 1.6 Option B) or defer to future if more endpoints need gRPC?

4. **Testing Isolation:** Should we mock the gRPC client for unit tests or rely on integration tests?

5. **Documentation Location:** Should complex function documentation go in docstrings or separate docs? (Current: docstrings per RCA)

## Success Metrics

### Quantitative
- [ ] send_message: CCN 26 → 5 (81% reduction) - **IN PROGRESS (Phase 2)**
- [✅] _publish_unified_event: CCN 17 → 3 (82% reduction) - **COMPLETE**
- [✅] _split_sql_statements: CCN 28 → 28 (accepted, documented) - **COMPLETE**
- [✅] Phase 1 tests pass (61/61 = 100%) - **COMPLETE**
- [ ] Phase 2 new unit tests: ~14 tests added - **PENDING**
- [ ] Phase 2: Zero performance regression - **PENDING**

### Qualitative
- [ ] Code reads like documentation (high-level orchestration)
- [ ] Each function has single, clear responsibility
- [ ] Adding new features requires minimal changes (Open/Closed Principle)
- [ ] Team code review approval
- [ ] Constitutional compliance verified

## Timeline

**Phase 1:** 3-4 hours (can complete in one focused session)
**Phase 2:** 4-6 hours (may require 1-2 sessions depending on test writing)
**Total:** 7-10 hours

**Suggested Schedule:**
- **Session 1 (3-4 hours):** Complete Phase 1 (both tasks)
- **Session 2 (2-3 hours):** Phase 2 Tasks 2.1a-c (extract helpers, implement handlers)
- **Session 3 (2-3 hours):** Phase 2 Tasks 2.1d-f (stream processor, simplify main, full testing)

## References

1. [COMPLEXITY_RCA_ANALYSIS.md](COMPLEXITY_RCA_ANALYSIS.md) - Complete RCA with code examples
2. [COMPLEXITY_ACTION_PLAN.md](COMPLEXITY_ACTION_PLAN.md) - Original action plan
3. [CODE_COMPLEXITY_ANALYSIS.md](CODE_COMPLEXITY_ANALYSIS.md) - Full complexity analysis
4. All 8 CONSTITUTION.md files (architectural guidelines)

---

**Document Status:** Ready for implementation
**Last Updated:** 2026-01-25
**Prepared By:** Claude Sonnet 4.5
**Review Status:** Awaiting implementation kickoff
