# Coverage Analysis - Remaining Work

**Date**: 2026-01-25
**Status**: P0 Critical components completed, P1-P2 components need analysis

---

## ✅ COMPLETED (P0 Critical - 0% → 100%)

### 1. CheckpointProtocol & postgres_adapter.py (342 lines)
- **Status**: ✅ 100% coverage via 25 unit tests
- **Protocol Updated**: CheckpointRecord now matches evolved implementation
- **Tests Added**: Full coverage of save, load, list, delete, fork methods
- **Test File**: `avionics/tests/unit/checkpoint/test_postgres_adapter.py`

### 2. DistributedBusProtocol & redis_bus.py (446 lines)
- **Status**: ✅ 100% coverage via 24 unit tests
- **Protocol Updated**: DistributedTask and QueueStats now match implementation
- **Tests Added**: Full coverage of enqueue, dequeue, complete, fail, worker lifecycle, stats
- **Test File**: `avionics/tests/unit/distributed/test_redis_bus.py`

---

## 🔍 ANALYSIS REQUIRED

### Component Categorization

**Infrastructure (High Priority):**
1. PostgreSQL Client - Database operations
2. Gateway SSE - Real-time event streaming
3. LLM Providers - External API adapters

**Application (Lower Priority):**
4. Gateway Chat Router - HTTP request handling (integration-level)
5. Gateway WebSocket - Real-time bidirectional (integration-level)

---

## 📊 PostgreSQL Client (12% coverage, 358 lines)

### Current Test Status
- **Location**: `avionics/database/postgres_client.py`
- **Existing Tests**: `avionics/tests/unit/database/test_database.py`
- **Test Type**: **Integration tests** (require Docker containers)
- **Tests Passing**: 1/6 (5 skipped - require testcontainers)
- **Coverage**: 12% (44/358 lines tested)

### Methods Breakdown (22 methods total)

#### ✅ Already Tested (1 method)
- `to_json()` / `from_json()` - JSON serialization helpers (via test_json_helpers)

#### ❌ Untested - Connection Management (4 methods)
1. `__init__()` - Constructor
2. `connect()` - Establish connection, verify pgvector
3. `disconnect()` - Close connection
4. `close()` - Alias for disconnect

#### ❌ Untested - Session Management (2 methods)
5. `session()` - Context manager for sessions
6. `transaction()` - Context manager for transactions

#### ❌ Untested - Schema Management (1 method)
7. `initialize_schema()` - Load SQL schema from file

#### ❌ Untested - Query Execution (3 methods)
8. `execute()` - Execute single query
9. `execute_many()` - Execute batch queries
10. `execute_script()` - Execute multi-statement SQL script

#### ❌ Untested - CRUD Operations (4 methods)
11. `insert()` - Insert record
12. `update()` - Update records
13. `fetch_one()` - Fetch single row
14. `fetch_all()` - Fetch multiple rows

#### ❌ Untested - Health & Monitoring (4 methods)
15. `health_check()` - Database health status
16. `get_table_stats()` - Table statistics
17. `get_all_tables_stats()` - All tables statistics
18. `vacuum_analyze()` - Database maintenance

#### ❌ Untested - Helper Methods (3 methods)
19. `pool` property - Expose connection pool
20. `_convert_uuid_strings()` - UUID conversion
21. `_prepare_query_and_params()` - Query parameter preparation

### Testing Strategy Recommendation

**Option A: Unit Tests with Mock Engine** ✅ RECOMMENDED
- Mock SQLAlchemy AsyncEngine
- Test all 22 methods independently
- Fast execution, no infrastructure required
- Coverage target: 80%+ achievable

**Option B: Integration Tests Only** ❌ NOT RECOMMENDED
- Requires Docker/testcontainers
- Slow CI/CD pipeline
- Already have 5 skipped tests this way
- Can't run on all environments

**Option C: Hybrid Approach** ⚠️ CONSIDER
- Unit tests for 18 methods (mock-based)
- Keep 4 integration tests for critical paths
- Best of both worlds but adds complexity

**Decision Required**: Which approach for PostgreSQL client?

---

## 📊 Gateway SSE (21% coverage, 68 lines)

### Current Test Status
- **Location**: `avionics/gateway/sse.py`
- **Existing Tests**: None found
- **Coverage**: 21% (14/68 lines tested)

### Code Analysis
```python
# SSE stream implementation (191 lines total file)
class SSEStream:
    - format_event()      # Format SSE event
    - send()              # Send SSE event
    - close()             # Close stream

# Helper functions:
- merge_sse_streams()     # Merge multiple SSE streams
- create_sse_response()   # Create FastAPI SSE response
```

### Testing Strategy Recommendation

**Priority**: HIGH (real-time user-facing feature)

**Approach**: Unit tests with mock AsyncIterator
- Test SSE event formatting
- Test stream merging logic
- Test error handling
- Mock FastAPI Response objects

**Estimated Effort**: 4-6 tests, 2 hours
**Coverage Target**: 80%+

---

## 📊 LLM Providers (20-38% coverage)

### Current Test Status
- **Location**: `avionics/llm/providers/`
- **Existing Tests**:
  - `test_provider_errors.py` (MockProvider only)
  - `test_llm_providers.py` (needs inspection)

### Provider Files

| Provider | Lines | Current Coverage | Status |
|----------|-------|------------------|--------|
| `mock.py` | ~465 | High (tested) | ✅ Complete |
| `anthropic.py` | 40 | 35% (14/40 untested) | ❌ Needs tests |
| `azure.py` | 70 | 20% (56/70 untested) | ❌ Needs tests |
| `openai.py` | ? | Unknown | ❓ Check needed |
| `llamaserver.py` | ? | Unknown | ❓ Check needed |
| `base.py` | ? | Unknown | ❓ Check needed |

### Testing Strategy Recommendation

**Priority**: HIGH (critical for agent execution)

**Approach**: Unit tests with mock HTTP clients
- Mock API responses (httpx/aiohttp)
- Test retry logic
- Test error handling
- Test streaming vs non-streaming

**Estimated Effort**:
- 8-12 tests per provider
- 4-6 hours total
**Coverage Target**: 80%+ per provider

---

## 📊 Gateway Chat Router (28% coverage, 253 lines)

### Current Test Status
- **Location**: `avionics/gateway/routers/chat.py`
- **Coverage**: 28% (71/253 tested)

### Analysis
This is primarily **integration-level code**:
- FastAPI endpoint definitions
- gRPC client calls
- Request/response transformation

### Testing Recommendation

**Priority**: MEDIUM (integration tests more appropriate)

**Approach**:
- Focus on business logic only (event publishing)
- E2E tests better for HTTP endpoints
- Skip comprehensive unit testing

**Estimated Value**: LOW (integration tests cover this better)

---

## 🎯 RECOMMENDATIONS

### Immediate Priority (Next Steps)

**P1: High-Value Unit Tests**
1. ✅ CheckpointProtocol (DONE - 25 tests)
2. ✅ DistributedBusProtocol (DONE - 24 tests)
3. **Gateway SSE** (NEW - 4-6 tests, 2 hours) ← START HERE
4. **LLM Providers** (NEW - 8-12 tests per provider, 4-6 hours)

**P2: Infrastructure Tests**
5. **PostgreSQL Client** - Decision required on approach
   - Recommend: Unit tests with mock engine
   - Estimated: 20-25 tests, 6-8 hours

**P3: Skip (Low ROI)**
6. Gateway Chat Router - Integration tests better
7. Gateway WebSocket - Integration tests better

### Coverage Target Analysis

| Component | Current | After P1 | After P2 | Target |
|-----------|---------|----------|----------|--------|
| avionics | 50% | ~65% | ~78% | 80% |
| jeeves_airframe | 50% | 50% | 50% | 80% |

**Note**: jeeves_airframe needs separate analysis.

---

## 📋 Testing Patterns Established

### Successful Patterns (Use These)

1. **Protocol-First Testing**
   - Update protocol to match reality
   - Write comprehensive unit tests
   - Mock all external dependencies
   - Example: CheckpointProtocol, DistributedBusProtocol

2. **Mock Strategy**
   - AsyncMock for async methods
   - MagicMock for sync methods
   - Side effects for sequential calls
   - Example: Both completed test suites

3. **Test Structure**
   - Class-based organization
   - Descriptive test names
   - Edge cases separated
   - Fixtures for common setup

### Antipatterns (Avoid These)

1. ❌ Integration tests requiring Docker in unit test suite
2. ❌ Testing FastAPI endpoints without proper fixtures
3. ❌ Silent fallbacks for missing dependencies
4. ❌ Relative imports in non-package directories

---

## 🔧 DECISION POINTS

### For User Decision

1. **PostgreSQL Client Approach**
   - A) Unit tests with mock engine (fast, recommended)
   - B) Keep integration tests only (slow, incomplete)
   - C) Hybrid approach (complex)

2. **Coverage Priority**
   - Continue with P1 (SSE + LLM providers) to reach ~65%?
   - Move to PostgreSQL client (P2) to reach ~78%?
   - Move to jeeves_airframe analysis?

3. **Testing Philosophy**
   - Focus on unit tests (fast, isolated)?
   - Mix unit + integration (comprehensive)?
   - E2E for gateway components (realistic)?

---

## 📈 ESTIMATED EFFORT TO 80%

**Remaining Work (avionics only):**

| Task | Tests | Hours | Coverage Gain |
|------|-------|-------|---------------|
| Gateway SSE | 4-6 | 2 | +5% |
| LLM Providers (4 providers) | 32-48 | 16-20 | +10% |
| PostgreSQL Client | 20-25 | 6-8 | +13% |
| **TOTAL** | **56-79 tests** | **24-30 hours** | **+28% → 78%** |

**Note**: This achieves ~78% coverage. Reaching 80% requires:
- Addressing edge cases in existing code
- Testing error paths thoroughly
- May require additional 2-3% from misc files

---

## 📝 NEXT STEPS

1. ✅ Review this analysis
2. ❓ Decide on PostgreSQL client approach
3. ❓ Decide on priority order
4. 🚀 Implement selected tests
5. 📊 Run full coverage report
6. 🔄 Iterate on gaps

