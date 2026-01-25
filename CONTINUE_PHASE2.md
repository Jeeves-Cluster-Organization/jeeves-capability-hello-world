# Continue Phase 2: Succinct Prompt

Copy this prompt to continue the refactoring work:

---

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

---

## Quick Reference

**Key Documents:**
1. [PHASE1_REVIEW_AND_PHASE2_AUDIT.md](PHASE1_REVIEW_AND_PHASE2_AUDIT.md) - Implementation specs, code templates, tests
2. [NEXT_SESSION_PROMPT.md](NEXT_SESSION_PROMPT.md) - Full task list and status
3. [COMPLEXITY_RCA_ANALYSIS.md](COMPLEXITY_RCA_ANALYSIS.md) - Original analysis

**Phase 1 Commits:**
- `70a983a` - docs(database): document _split_sql_statements
- `ef6acad` - refactor(gateway): simplify _publish_unified_event

**Test Status:**
- 61/61 gateway tests passing
- 17 new unit tests added in Phase 1
- 0 regressions

**Next Action:**
Start with Task 2.1a: Extract `_build_grpc_request` helper from lines 288-300
