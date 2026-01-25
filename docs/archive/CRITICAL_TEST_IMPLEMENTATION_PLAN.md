# Critical Test Implementation Plan
**Date:** 2026-01-25
**Focus:** Zero and Low Coverage Critical Modules
**Goal:** Implement comprehensive tests for the 6 most critical untested paths

---

## 📊 Module Analysis Summary

| Module | Coverage | Lines | Risk | Complexity | Priority |
|--------|----------|-------|------|------------|----------|
| flow_service.py | 0% | 369 | CRITICAL | Medium | P1 |
| governance_service.py | 0% | 292 | CRITICAL | Medium | P1 |
| pgvector_repository.py | 9% | 530 | CRITICAL | High | P1 |
| sql_adapter.py | 13% | 378 | CRITICAL | Medium | P1 |
| embedding_service.py | 13% | 284 | CRITICAL | Medium | P1 |
| rate_limiter.py | 18% | 424 | HIGH | High | P2 |

---

## 1. flow_service.py - gRPC Flow Servicer (0% → 75%)

### Module Overview
- **Path:** `mission_system/orchestrator/flow_service.py`
- **Lines:** 369
- **Class:** `FlowServicer` (gRPC servicer)
- **Purpose:** Capability invocation via gRPC, session management

### Methods to Test (6 methods)
1. `StartFlow` - Stream events from capability servicer
2. `GetSession` - Retrieve session details
3. `ListSessions` - List user sessions with pagination
4. `CreateSession` - Create new session with default title
5. `DeleteSession` - Soft delete session
6. `GetSessionMessages` - Retrieve session message history

### Test Strategy
**Mocking Requirements:**
- Mock `DatabaseClientProtocol` for SQL operations
- Mock `CapabilityServicerProtocol` for process_request
- Mock `grpc.aio.ServicerContext` for gRPC context
- Mock `jeeves_pb2` protobuf messages
- Mock `get_capability_resource_registry()` for default titles

**Test Cases (15-18 tests):**

#### StartFlow Tests (3 tests)
```python
@pytest.mark.asyncio
async def test_start_flow_success(mock_db, mock_servicer, mock_context):
    """Test successful flow start with event streaming"""

@pytest.mark.asyncio
async def test_start_flow_with_new_session(mock_db, mock_servicer, mock_context):
    """Test flow start creates new session when session_id is None"""

@pytest.mark.asyncio
async def test_start_flow_delegates_to_servicer(mock_db, mock_servicer, mock_context):
    """Test that StartFlow properly delegates to capability servicer"""
```

#### GetSession Tests (3 tests)
```python
@pytest.mark.asyncio
async def test_get_session_success(mock_db, mock_context):
    """Test successful session retrieval"""

@pytest.mark.asyncio
async def test_get_session_not_found(mock_db, mock_context):
    """Test session not found returns NOT_FOUND status"""

@pytest.mark.asyncio
async def test_get_session_with_message_count(mock_db, mock_context):
    """Test session includes accurate message count"""
```

#### ListSessions Tests (4 tests)
```python
@pytest.mark.asyncio
async def test_list_sessions_success(mock_db, mock_context):
    """Test listing sessions with pagination"""

@pytest.mark.asyncio
async def test_list_sessions_pagination(mock_db, mock_context):
    """Test offset and limit work correctly"""

@pytest.mark.asyncio
async def test_list_sessions_include_deleted(mock_db, mock_context):
    """Test include_deleted flag includes soft-deleted sessions"""

@pytest.mark.asyncio
async def test_list_sessions_empty_result(mock_db, mock_context):
    """Test empty session list for new user"""
```

#### CreateSession Tests (3 tests)
```python
@pytest.mark.asyncio
async def test_create_session_success(mock_db, mock_context):
    """Test session creation with generated ID"""

@pytest.mark.asyncio
async def test_create_session_default_title(mock_db, mock_context):
    """Test default title from capability registry"""

@pytest.mark.asyncio
async def test_create_session_custom_title(mock_db, mock_context):
    """Test custom title is used when provided"""
```

#### DeleteSession Tests (2 tests)
```python
@pytest.mark.asyncio
async def test_delete_session_success(mock_db, mock_context):
    """Test soft delete session"""

@pytest.mark.asyncio
async def test_delete_session_already_deleted(mock_db, mock_context):
    """Test deleting already deleted session returns success=False"""
```

#### GetSessionMessages Tests (3 tests)
```python
@pytest.mark.asyncio
async def test_get_session_messages_success(mock_db, mock_context):
    """Test retrieving messages for session"""

@pytest.mark.asyncio
async def test_get_session_messages_session_not_found(mock_db, mock_context):
    """Test session not found returns NOT_FOUND"""

@pytest.mark.asyncio
async def test_get_session_messages_pagination(mock_db, mock_context):
    """Test message pagination with offset/limit"""
```

**Fixtures Needed:**
```python
@pytest.fixture
def mock_db():
    """Mock DatabaseClientProtocol"""

@pytest.fixture
def mock_servicer():
    """Mock CapabilityServicerProtocol"""

@pytest.fixture
def mock_context():
    """Mock grpc.aio.ServicerContext"""

@pytest.fixture
def flow_servicer(mock_db, mock_servicer):
    """FlowServicer instance with mocked dependencies"""
```

**Estimated Effort:** 5-7 hours
**Expected Coverage:** 0% → 75%+

---

## 2. governance_service.py - Health & Governance (0% → 75%)

### Module Overview
- **Path:** `mission_system/orchestrator/governance_service.py`
- **Lines:** 292
- **Class:** `HealthServicer` (gRPC servicer)
- **Purpose:** System health monitoring, agent status, memory layer introspection

### Methods to Test (5 methods)
1. `GetHealthSummary` - Overall system health with tool status
2. `GetToolHealth` - Detailed health for specific tool
3. `GetAgents` - List all agents from registry
4. `GetMemoryLayers` - List L1-L7 memory layers with status
5. `_check_layer_status` - Helper to probe layer tables

### Test Strategy
**Mocking Requirements:**
- Mock `tool_health_service` for health data
- Mock `DatabaseClientProtocol` for layer status checks
- Mock `grpc.aio.ServicerContext`
- Mock `get_capability_resource_registry()` for agent definitions

**Test Cases (12-15 tests):**

#### GetHealthSummary Tests (3 tests)
```python
@pytest.mark.asyncio
async def test_get_health_summary_all_healthy(mock_health_service, mock_context):
    """Test health summary when all tools healthy"""

@pytest.mark.asyncio
async def test_get_health_summary_degraded(mock_health_service, mock_context):
    """Test health summary with some degraded tools"""

@pytest.mark.asyncio
async def test_get_health_summary_unhealthy(mock_health_service, mock_context):
    """Test health summary with unhealthy tools"""
```

#### GetToolHealth Tests (3 tests)
```python
@pytest.mark.asyncio
async def test_get_tool_health_success(mock_health_service, mock_context):
    """Test retrieving tool health details"""

@pytest.mark.asyncio
async def test_get_tool_health_not_found(mock_health_service, mock_context):
    """Test tool not found returns NOT_FOUND status"""

@pytest.mark.asyncio
async def test_get_tool_health_metrics(mock_health_service, mock_context):
    """Test tool health includes all metrics"""
```

#### GetAgents Tests (3 tests)
```python
@pytest.mark.asyncio
async def test_get_agents_from_registry(mock_context, mock_registry):
    """Test agents retrieved from capability registry"""

@pytest.mark.asyncio
async def test_get_agents_empty_registry(mock_context, mock_registry):
    """Test empty agent list when registry has no agents"""

@pytest.mark.asyncio
async def test_get_agents_includes_metadata(mock_context, mock_registry):
    """Test agent info includes layer and tools"""
```

#### GetMemoryLayers Tests (4 tests)
```python
@pytest.mark.asyncio
async def test_get_memory_layers_all_active(mock_db, mock_context):
    """Test all memory layers active"""

@pytest.mark.asyncio
async def test_get_memory_layers_l6_inactive(mock_db, mock_context):
    """Test L6 always returns inactive (deferred)"""

@pytest.mark.asyncio
async def test_get_memory_layers_degraded(mock_db, mock_context):
    """Test degraded layer when some tables inaccessible"""

@pytest.mark.asyncio
async def test_get_memory_layers_no_db(mock_context):
    """Test unknown status when no db connection"""
```

#### _check_layer_status Tests (3 tests)
```python
@pytest.mark.asyncio
async def test_check_layer_status_active(servicer, mock_db):
    """Test layer status active when all tables accessible"""

@pytest.mark.asyncio
async def test_check_layer_status_degraded(servicer, mock_db):
    """Test degraded status when some tables missing"""

@pytest.mark.asyncio
async def test_check_layer_status_inactive(servicer, mock_db):
    """Test inactive status when no tables accessible"""
```

**Estimated Effort:** 4-6 hours
**Expected Coverage:** 0% → 75%+

---

## 3. pgvector_repository.py - Vector Search (9% → 70%)

### Module Overview
- **Path:** `memory_module/repositories/pgvector_repository.py`
- **Lines:** 530
- **Class:** `PgVectorRepository`
- **Purpose:** Semantic search via pgvector, embedding storage

### Methods to Test (8 methods)
1. `upsert` - Store embeddings in PostgreSQL
2. `search` - Semantic search across collections
3. `delete` - Remove embedding (set to NULL)
4. `get` - Retrieve specific item embedding
5. `get_collection_stats` - Collection statistics
6. `rebuild_index` - Rebuild IVFFlat index
7. `batch_upsert` - Batch embedding storage
8. `_validate_collection` - Collection validation

### Test Strategy
**Mocking Requirements:**
- Mock `PostgreSQLClient` with async session support
- Mock `EmbeddingService` for embed() calls
- Mock SQLAlchemy `text()` and `session.execute()`
- Use `pytest-asyncio` for async tests

**Test Cases (18-20 tests):**

#### upsert Tests (4 tests)
```python
@pytest.mark.asyncio
async def test_upsert_success(repo, mock_db, mock_embeddings):
    """Test successful embedding upsert"""

@pytest.mark.asyncio
async def test_upsert_invalid_collection(repo):
    """Test upsert with invalid collection raises ValueError"""

@pytest.mark.asyncio
async def test_upsert_no_match(repo, mock_db, mock_embeddings):
    """Test upsert returns False when item_id not found"""

@pytest.mark.asyncio
async def test_upsert_numpy_array_conversion(repo, mock_db, mock_embeddings):
    """Test numpy array embedding converted to list"""
```

#### search Tests (5 tests)
```python
@pytest.mark.asyncio
async def test_search_success(repo, mock_db, mock_embeddings):
    """Test semantic search returns ranked results"""

@pytest.mark.asyncio
async def test_search_empty_query(repo, mock_db, mock_embeddings):
    """Test empty query returns empty list"""

@pytest.mark.asyncio
async def test_search_with_filters(repo, mock_db, mock_embeddings):
    """Test search with metadata filters"""

@pytest.mark.asyncio
async def test_search_min_similarity_threshold(repo, mock_db, mock_embeddings):
    """Test min_similarity filters low-scoring results"""

@pytest.mark.asyncio
async def test_search_multiple_collections(repo, mock_db, mock_embeddings):
    """Test searching across multiple collections"""
```

#### delete Tests (2 tests)
```python
@pytest.mark.asyncio
async def test_delete_success(repo, mock_db):
    """Test embedding deletion (sets to NULL)"""

@pytest.mark.asyncio
async def test_delete_no_match(repo, mock_db):
    """Test delete returns False when item not found"""
```

#### get Tests (2 tests)
```python
@pytest.mark.asyncio
async def test_get_success(repo, mock_db):
    """Test retrieving item with embedding"""

@pytest.mark.asyncio
async def test_get_not_found(repo, mock_db):
    """Test get returns None when item not found"""
```

#### Remaining Tests (5 tests)
```python
@pytest.mark.asyncio
async def test_get_collection_stats(repo, mock_db):
    """Test collection statistics"""

@pytest.mark.asyncio
async def test_rebuild_index(repo, mock_db):
    """Test index rebuild"""

@pytest.mark.asyncio
async def test_batch_upsert_success(repo, mock_db, mock_embeddings):
    """Test batch upsert"""

@pytest.mark.asyncio
async def test_validate_collection_valid(repo):
    """Test valid collection returns config"""

@pytest.mark.asyncio
async def test_validate_collection_invalid(repo):
    """Test invalid collection raises ValueError"""
```

**Estimated Effort:** 6-8 hours
**Expected Coverage:** 9% → 70%+

---

## 4. sql_adapter.py - SQL Data Layer (13% → 75%)

### Module Overview
- **Path:** `memory_module/adapters/sql_adapter.py`
- **Lines:** 378
- **Class:** `SQLAdapter`
- **Purpose:** CRUD operations for facts and messages

### Methods to Test (6 methods)
1. `write_fact` - Insert/update knowledge_facts
2. `write_message` - Insert message with RETURNING
3. `read_by_id` - Read single item by ID
4. `read_by_filter` - Query items with filters
5. `update_item` - Update item fields
6. `delete_item` - Soft/hard delete

### Test Cases (15-18 tests):**

#### write_fact Tests (3 tests)
```python
@pytest.mark.asyncio
async def test_write_fact_new(adapter, mock_db):
    """Test writing new fact"""

@pytest.mark.asyncio
async def test_write_fact_upsert(adapter, mock_db):
    """Test upsert on conflict updates existing fact"""

@pytest.mark.asyncio
async def test_write_fact_legacy_store_param(adapter, mock_db):
    """Test 'store' param mapped to 'domain' for backward compat"""
```

#### write_message Tests (2 tests)
```python
@pytest.mark.asyncio
async def test_write_message_success(adapter, mock_db):
    """Test message write with RETURNING clause"""

@pytest.mark.asyncio
async def test_write_message_default_role(adapter, mock_db):
    """Test default role is 'user'"""
```

#### read_by_id Tests (4 tests)
```python
@pytest.mark.asyncio
async def test_read_fact_by_id(adapter, mock_db):
    """Test reading fact by UUID"""

@pytest.mark.asyncio
async def test_read_message_by_id(adapter, mock_db):
    """Test reading message by INTEGER id"""

@pytest.mark.asyncio
async def test_read_by_id_not_found(adapter, mock_db):
    """Test returns None when item not found"""

@pytest.mark.asyncio
async def test_read_by_id_invalid_type(adapter, mock_db):
    """Test raises ValueError for invalid item_type"""
```

#### read_by_filter Tests (3 tests)
```python
@pytest.mark.asyncio
async def test_read_by_filter_facts(adapter, mock_db):
    """Test filtering facts by domain"""

@pytest.mark.asyncio
async def test_read_by_filter_messages(adapter, mock_db):
    """Test filtering messages (no user_id filter)"""

@pytest.mark.asyncio
async def test_read_by_filter_limit(adapter, mock_db):
    """Test limit parameter works"""
```

#### update_item Tests (2 tests)
```python
@pytest.mark.asyncio
async def test_update_fact(adapter, mock_db):
    """Test updating fact fields"""

@pytest.mark.asyncio
async def test_update_message(adapter, mock_db):
    """Test updating message sets edited_at"""
```

#### delete_item Tests (4 tests)
```python
@pytest.mark.asyncio
async def test_delete_message_soft(adapter, mock_db):
    """Test soft delete sets deleted_at"""

@pytest.mark.asyncio
async def test_delete_message_hard(adapter, mock_db):
    """Test hard delete removes row"""

@pytest.mark.asyncio
async def test_delete_fact_hard(adapter, mock_db):
    """Test fact deletion (no soft delete support)"""

@pytest.mark.asyncio
async def test_delete_invalid_type(adapter, mock_db):
    """Test raises ValueError for invalid type"""
```

**Estimated Effort:** 5-6 hours
**Expected Coverage:** 13% → 75%+

---

## 5. embedding_service.py - AI Embeddings (13% → 70%)

### Module Overview
- **Path:** `memory_module/services/embedding_service.py`
- **Lines:** 284
- **Class:** `EmbeddingService`
- **Purpose:** Text embedding generation with caching

### Methods to Test (7 methods)
1. `__init__` - Initialize with sentence-transformers
2. `embed` - Single text embedding with cache
3. `embed_batch` - Batch embeddings
4. `similarity` - Cosine similarity calculation
5. `get_cache_stats` - Cache statistics
6. `clear_cache` - Cache clearing
7. `_get_cache_key` - SHA-256 hash generation

### Test Strategy
**Mocking Requirements:**
- Mock `SentenceTransformer` model
- Mock model.encode() to return fake embeddings
- Use deterministic embeddings for testing

**Test Cases (15-18 tests):**

#### Initialization Tests (3 tests)
```python
def test_init_success(mock_sentence_transformer):
    """Test successful initialization"""

def test_init_permission_error(mock_sentence_transformer):
    """Test PermissionError with actionable message"""

def test_init_generic_error(mock_sentence_transformer):
    """Test RuntimeError on model load failure"""
```

#### embed Tests (4 tests)
```python
def test_embed_success(service, mock_model):
    """Test embedding generation"""

def test_embed_empty_text(service):
    """Test empty text returns zero vector"""

def test_embed_cache_hit(service, mock_model):
    """Test cache hit returns cached embedding"""

def test_embed_cache_eviction(service, mock_model):
    """Test LRU eviction when cache full"""
```

#### embed_batch Tests (4 tests)
```python
def test_embed_batch_success(service, mock_model):
    """Test batch embedding generation"""

def test_embed_batch_empty_texts(service):
    """Test batch with empty texts returns zero vectors"""

def test_embed_batch_cache_hits(service, mock_model):
    """Test batch uses cached embeddings"""

def test_embed_batch_mixed_cached_uncached(service, mock_model):
    """Test batch with mix of cached and new texts"""
```

#### similarity Tests (3 tests)
```python
def test_similarity_identical_texts(service):
    """Test similarity of identical texts is 1.0"""

def test_similarity_different_texts(service):
    """Test similarity calculation"""

def test_similarity_empty_text(service):
    """Test similarity with empty text returns 0.0"""
```

#### Cache Tests (3 tests)
```python
def test_get_cache_stats(service):
    """Test cache statistics"""

def test_clear_cache(service):
    """Test cache clearing"""

def test_cache_key_generation(service):
    """Test SHA-256 hash generation"""
```

**Estimated Effort:** 4-5 hours
**Expected Coverage:** 13% → 70%+

---

## 6. rate_limiter.py - Rate Limiting (18% → 75%)

### Module Overview
- **Path:** `control_tower/resources/rate_limiter.py`
- **Lines:** 424
- **Classes:** `SlidingWindow`, `RateLimiter`
- **Purpose:** Sliding window rate limiting

### Methods to Test (11 methods)
**SlidingWindow:**
1. `record` - Record request and return count
2. `get_count` - Get current window count
3. `time_until_slot_available` - Calculate retry time

**RateLimiter:**
4. `check_rate_limit` - Check if request allowed
5. `set_user_limits` - Configure user limits
6. `set_endpoint_limits` - Configure endpoint limits
7. `get_config` - Get effective config
8. `get_usage` - Get usage statistics
9. `reset_user` - Reset user windows
10. `cleanup_expired` - Clean up old data

### Test Strategy
**Mocking Requirements:**
- Mock `time.time()` for deterministic testing
- Use `freezegun` or manual time mocking

**Test Cases (20-25 tests):**

#### SlidingWindow Tests (6 tests)
```python
def test_sliding_window_record(mock_time):
    """Test recording request in window"""

def test_sliding_window_get_count(mock_time):
    """Test getting current count"""

def test_sliding_window_bucket_cleanup(mock_time):
    """Test old buckets are cleaned up"""

def test_sliding_window_accurate_sliding(mock_time):
    """Test accurate sliding window calculation"""

def test_sliding_window_time_until_slot(mock_time):
    """Test retry time calculation"""

def test_sliding_window_multiple_buckets(mock_time):
    """Test sub-bucket distribution"""
```

#### RateLimiter Tests (15-18 tests)
```python
def test_check_rate_limit_allowed(limiter, mock_time):
    """Test request allowed when under limit"""

def test_check_rate_limit_exceeded_minute(limiter, mock_time):
    """Test minute limit exceeded"""

def test_check_rate_limit_exceeded_hour(limiter, mock_time):
    """Test hour limit exceeded"""

def test_check_rate_limit_exceeded_day(limiter, mock_time):
    """Test day limit exceeded"""

def test_check_rate_limit_burst(limiter, mock_time):
    """Test burst allowance"""

def test_set_user_limits(limiter):
    """Test setting custom user limits"""

def test_set_endpoint_limits(limiter):
    """Test endpoint-specific limits"""

def test_get_config_precedence(limiter):
    """Test endpoint > user > default precedence"""

def test_get_usage(limiter, mock_time):
    """Test usage statistics"""

def test_reset_user(limiter, mock_time):
    """Test resetting user windows"""

def test_cleanup_expired(limiter, mock_time):
    """Test cleaning up expired windows"""

def test_rate_limit_thread_safety(limiter):
    """Test thread-safe operation"""

def test_rate_limit_dry_run(limiter, mock_time):
    """Test record=False doesn't record request"""
```

**Estimated Effort:** 6-8 hours
**Expected Coverage:** 18% → 75%+

---

## 📋 Implementation Order

Based on business impact and difficulty:

### Phase 1: Core Services (2-3 days)
1. **sql_adapter.py** (5-6 hours) - Foundation for data layer
2. **embedding_service.py** (4-5 hours) - Critical for AI features
3. **rate_limiter.py** (6-8 hours) - Resource protection

**Expected Gain:** +12-15% overall coverage

### Phase 2: Orchestration (2-3 days)
4. **flow_service.py** (5-7 hours) - Core session management
5. **governance_service.py** (4-6 hours) - System health

**Expected Gain:** +8-10% overall coverage

### Phase 3: Advanced Features (1-2 days)
6. **pgvector_repository.py** (6-8 hours) - Semantic search

**Expected Gain:** +5-7% overall coverage

---

## 🛠️ Test Infrastructure Setup

### Required Fixtures (Create in conftest.py)

```python
# Database mocks
@pytest.fixture
def mock_db():
    """Mock DatabaseClientProtocol"""

@pytest.fixture
def mock_postgres_session():
    """Mock PostgreSQL async session"""

# Service mocks
@pytest.fixture
def mock_embedding_service():
    """Mock EmbeddingService"""

@pytest.fixture
def mock_sentence_transformer():
    """Mock SentenceTransformer model"""

@pytest.fixture
def mock_health_service():
    """Mock ToolHealthService"""

# gRPC mocks
@pytest.fixture
def mock_grpc_context():
    """Mock grpc.aio.ServicerContext"""

@pytest.fixture
def mock_grpc_request():
    """Mock gRPC request messages"""

# Time mocking
@pytest.fixture
def mock_time(monkeypatch):
    """Mock time.time() for deterministic tests"""
```

### Required Dependencies
```txt
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-mock>=3.12.0
pytest-cov>=4.1.0
freezegun>=1.2.0  # For time mocking
```

---

## 📊 Expected Outcomes

### Coverage Improvement
- **Current:** 60%
- **After Phase 1:** 72-75%
- **After Phase 2:** 80-85%
- **After Phase 3:** 85-90%

### Total Effort
- **Phase 1:** 15-19 hours (2-3 days)
- **Phase 2:** 9-13 hours (2-3 days)
- **Phase 3:** 6-8 hours (1-2 days)
- **Total:** 30-40 hours (5-8 days)

### Risk Reduction
- ✅ Zero-coverage critical modules eliminated
- ✅ Core data layer protected (sql_adapter, pgvector)
- ✅ AI features validated (embeddings)
- ✅ Resource protection verified (rate_limiter)
- ✅ Orchestration layer tested (flow, governance)

---

## Next Steps

1. **Review and approve this plan**
2. **Set up test infrastructure (fixtures, mocks)**
3. **Begin Phase 1 implementation**
4. **Run coverage after each phase to track progress**
5. **Adjust priorities based on results**

**Ready to begin implementation?**
