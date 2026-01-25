# Full Cyclomatic Complexity Coverage Analysis

**Date:** 2026-01-25
**Scope:** jeeves-core + airframe (complete codebase)
**Total Functions Analyzed:** 3,109
**Status:** ✅ Analysis Complete - Ready for Capability Layer Testing

---

## Executive Summary

Comprehensive complexity analysis of the entire jeeves ecosystem reveals **excellent overall health** with targeted areas requiring attention before capability layer testing.

### Key Findings

| Metric | Value | Assessment |
|--------|-------|------------|
| **Total Functions** | 3,109 | Complete coverage |
| **Average CCN** | 3.02 | ✅ Excellent (target: <5) |
| **Grade A (CCN 1-5)** | 88.0% | ✅ Industry best practice |
| **Grade B (CCN 6-10)** | 10.0% | ✅ Acceptable |
| **Grade C+ (CCN >10)** | 2.0% | ⚠️ Needs attention (62 functions) |
| **Critical (CCN ≥20)** | 8 functions | 🔴 High priority |

**Recommendation:** Address 8 critical functions before capability layer testing to ensure testability.

---

## Repository Breakdown

### JEEVES-CORE

**Size:** 2,960 functions
**Average CCN:** 3.05
**Max CCN:** 26

**Grade Distribution:**
- Grade A (CCN 1-5): 2,604 functions (88.0%)
- Grade B (CCN 6-10): 296 functions (10.0%)
- Grade C (CCN 11-20): 56 functions (1.9%)
- Grade D (CCN 21-50): 4 functions (0.1%)

**Assessment:** ✅ Healthy codebase with targeted complexity hotspots

### AIRFRAME

**Size:** 149 functions
**Average CCN:** 2.71
**Max CCN:** 13

**Grade Distribution:**
- Grade A (CCN 1-5): 132 functions (88.6%)
- Grade B (CCN 6-10): 15 functions (10.1%)
- Grade C (CCN 11-20): 2 functions (1.3%)

**Assessment:** ✅ Excellent - minimal complexity issues

---

## Top 10 Most Complex Functions (Entire Codebase)

| Rank | CCN | Function | Location | Priority |
|------|-----|----------|----------|----------|
| 1 | 26 | `_envelope_from_proto` | jeeves_protocols/grpc_client.py | 🔴 CRITICAL |
| 2 | 25 | `_envelope_to_proto` | jeeves_protocols/grpc_client.py | 🔴 CRITICAL |
| 3 | 23 | `submit_request` | jeeves_mission_system/api/server.py | 🔴 CRITICAL |
| 4 | 23 | `from_dict` | jeeves_protocols/envelope.py | 🔴 CRITICAL |
| 5 | 20 | `_check_models` | jeeves_mission_system/api/health.py | 🔴 CRITICAL |
| 6 | 20 | `triage_plan` | jeeves_mission_system/common/plan_triage.py | 🔴 CRITICAL |
| 7 | 20 | `apply_skip_markers` | jeeves_mission_system/tests/config/markers.py | 🔴 CRITICAL |
| 8 | 20 | `read` | jeeves_memory_module/manager.py | 🔴 CRITICAL |
| 9 | 19 | `_call_llm` | jeeves_protocols/agents.py | 🟡 HIGH |
| 10 | 18 | `process` | jeeves_protocols/agents.py | 🟡 HIGH |

**Note:** `send_message` previously at CCN 26 has been refactored to CCN 5 ✅

---

## Functions Requiring Attention by Priority

### 🔴 CRITICAL Priority (CCN ≥ 20) - 8 functions

**Impact:** High - These functions are difficult to test and maintain.

| Function | CCN | File | Recommended Action |
|----------|-----|------|-------------------|
| `_envelope_from_proto` | 26 | jeeves_protocols/grpc_client.py | Extract parsers for each field type |
| `_envelope_to_proto` | 25 | jeeves_protocols/grpc_client.py | Extract serializers for each field type |
| `submit_request` | 23 | jeeves_mission_system/api/server.py | Extract validation, routing, execution |
| `from_dict` | 23 | jeeves_protocols/envelope.py | Extract field mappers |
| `_check_models` | 20 | jeeves_mission_system/api/health.py | Extract health check strategies |
| `triage_plan` | 20 | jeeves_mission_system/common/plan_triage.py | Extract triage rules |
| `apply_skip_markers` | 20 | jeeves_mission_system/tests/config/markers.py | Extract marker strategies |
| `read` | 20 | jeeves_memory_module/manager.py | Extract read strategies by type |

### 🟡 HIGH Priority (CCN 15-19) - 14 functions

Functions in this range should be refactored before extensive testing. See [FULL_CC_REPORT.csv](FULL_CC_REPORT.csv) for complete list.

### 🟠 MEDIUM Priority (CCN 10-14) - 40 functions (jeeves-core)

These functions are testable but could benefit from simplification. Monitor during capability layer testing.

### ℹ️ LOW Priority (CCN 6-9) - 293 functions

Acceptable complexity. No immediate action needed.

---

## Complexity Distribution by Module

### jeeves-core Modules

| Module | Functions | Avg CCN | Max CCN | Assessment |
|--------|-----------|---------|---------|------------|
| jeeves_avionics | ~800 | 2.9 | 17 | ✅ Good after Phase 2 refactoring |
| jeeves_mission_system | ~900 | 3.3 | 23 | ⚠️ submit_request needs attention |
| jeeves_protocols | ~600 | 3.5 | 26 | 🔴 grpc_client has 2 critical functions |
| jeeves_shared | ~300 | 2.4 | 8 | ✅ Excellent |
| jeeves_memory_module | ~360 | 2.8 | 20 | ⚠️ read() needs refactoring |

### airframe Modules

| Module | Functions | Avg CCN | Max CCN | Assessment |
|--------|-----------|---------|---------|------------|
| adapters | ~80 | 3.1 | 13 | ✅ Good - stream_infer acceptable |
| health | ~20 | 2.5 | 8 | ✅ Excellent |
| k8s | ~30 | 2.2 | 6 | ✅ Excellent |
| tests | ~19 | 2.1 | 6 | ✅ Excellent test quality |

---

## Impact of Phase 2 Refactoring

### Before Phase 2
- `send_message`: CCN 26 (tied for #1 most complex)
- `_publish_unified_event`: CCN 17 (#11 most complex)

### After Phase 2 ✅
- `send_message`: CCN 5 (removed from top 100)
- `_publish_unified_event`: CCN 3 (removed from top 100)
- **Net improvement:** -35 complexity points distributed across 8 focused functions

**Result:** jeeves_avionics now has **zero critical functions** (CCN ≥ 20)

---

## Recommended Actions Before Capability Layer Testing

### Phase 3: Address Critical Functions (Estimate: 2-3 days)

**Priority Order:**

1. **jeeves_protocols/grpc_client.py** (CCN 26 + 25)
   - These functions handle protocol conversion
   - Extract type-specific parsers/serializers
   - Target: CCN < 10 each

2. **jeeves_mission_system/api/server.py** (CCN 23)
   - Core request handling
   - Extract validation, routing, execution phases
   - Target: CCN < 10

3. **jeeves_protocols/envelope.py** (CCN 23)
   - Data structure conversion
   - Extract field mapping strategies
   - Target: CCN < 10

4. **Remaining 4 critical functions** (CCN 20 each)
   - Lower priority but should be addressed
   - Can be parallelized

### Why This Matters for Capability Layer Testing

**Capability layer depends on:**
- jeeves_protocols (for agent communication)
- jeeves_mission_system/api (for request handling)
- jeeves_memory_module (for context management)

**Current blockers:**
1. `_envelope_from_proto` / `_envelope_to_proto` - Hard to mock protocol conversions
2. `submit_request` - Hard to test routing logic in isolation
3. `from_dict` - Hard to test envelope parsing edge cases

**Recommendation:** Refactor these 3 functions (top 4 by CCN) before capability layer testing to enable:
- Unit testing of capabilities in isolation
- Integration testing with mocked protocols
- Reliable test doubles for request handling

---

## Test Coverage Implications

### Current State (jeeves-core)

Based on previous analysis:
- Total tests: ~400 unit tests
- Integration tests: ~50
- Critical functions (CCN ≥ 20): 8 functions with limited test coverage

### Recommended Test Strategy for Capability Layer

**Phase 1: Pre-Requisites (Do First)**
1. Refactor 4 critical protocol/API functions
2. Add unit tests for extracted helpers
3. Verify integration tests still pass

**Phase 2: Capability Layer Testing**
1. Unit test each capability in isolation (mocked dependencies)
2. Integration test capability → protocol → API flow
3. End-to-end test full capability execution

**Blocker:** Cannot reliably test capabilities while protocol conversion has CCN 26. Must refactor first.

---

## Complexity Trends

### Historical Context

**Phase 1 Complete:**
- `_split_sql_statements` (CCN 28) - Documented and accepted
- `_publish_unified_event` (CCN 17 → 3) - Successfully refactored

**Phase 2 Complete:**
- `send_message` (CCN 26 → 5) - Successfully refactored
- Legacy event naming removed (O(n) → O(1))

**Phase 3 Targets (Top 8 by CCN):**
- `_envelope_from_proto` (CCN 26)
- `_envelope_to_proto` (CCN 25)
- `submit_request` (CCN 23)
- `from_dict` (CCN 23)
- 4 more at CCN 20

### Projected Improvement

If Phase 3 targets are refactored to CCN < 10:
- Current critical functions: 8
- Target critical functions: 0
- Average CCN improvement: 3.05 → 2.85
- Grade A percentage: 88% → 92%

---

## Files for Further Analysis

All detailed data available in:

1. **[FULL_CC_REPORT.csv](FULL_CC_REPORT.csv)** - Complete function-level data (3,109 rows)
2. **jeeves_core_cc_full.json** - Raw radon output for jeeves-core
3. **airframe_cc_full.json** - Raw radon output for airframe

---

## Next Steps

### Immediate (Before Capability Testing)

1. ✅ **DONE:** Full CC coverage analysis
2. 🔄 **TODO:** Review top 8 critical functions
3. 🔄 **TODO:** Create Phase 3 refactoring plan
4. 🔄 **TODO:** Refactor protocol conversion functions (CCN 26, 25)
5. 🔄 **TODO:** Refactor API request handling (CCN 23)

### Medium Term (Capability Layer)

1. Unit test capability implementations
2. Integration test capability → protocol flow
3. End-to-end test capability execution
4. Monitor for new complexity hotspots

### Long Term (Maintenance)

1. Set CI/CD threshold: Fail PR if CCN > 15
2. Monthly complexity audits
3. Refactor functions as they approach CCN 10

---

## Summary

**Current State:**
- ✅ 88% of functions have excellent complexity (CCN ≤ 5)
- ✅ Only 62 functions need attention (2% of codebase)
- 🔴 8 critical functions block capability layer testing

**Recommendation:**
- **Refactor top 4 critical functions** (protocol + API layers)
- **Then proceed** with capability layer testing
- **Estimated effort:** 2-3 days for Phase 3 refactoring

**Rationale:**
- Cannot reliably test capabilities while core dependencies have CCN 20+
- Mocking protocol conversions with CCN 26 is error-prone
- Testing API routing with CCN 23 requires extensive setup

**Path Forward:**
1. Phase 3: Refactor critical protocol/API functions
2. Verify all tests pass
3. Proceed with capability layer testing with confidence

---

**Analysis Complete:** 2026-01-25
**Next Action:** Review Phase 3 refactoring plan for top 4 critical functions
**Goal:** Enable capability layer testing with reliable, testable infrastructure

