# IRIS DevTools Roadmap

**Current Version**: Development (pre-v1.0.0)
**Last Updated**: 2025-10-18

---

## v1.0.0 (In Progress - Target: 2025-10-25)

### Phase 2: Complete Missing Features ✅
- [x] ObjectScript support for IRISContainer
- [x] Production patterns from rag-templates
- [x] Port auto-discovery
- [x] Schema reset utilities
- [ ] Update 53 integration tests
- [ ] Run all integration tests with real IRIS

### Phase 3: Package Preparation
- [ ] Fix pyproject.toml (dependencies, metadata)
- [ ] Uncomment working imports in __init__.py
- [ ] Add CLI entry point
- [ ] Create comprehensive README
- [ ] Create CHANGELOG.md
- [ ] Add examples directory

### Phase 4: PyPI Release
- [ ] Final testing (unit + integration)
- [ ] Version bump to 1.0.0
- [ ] Build package (python -m build)
- [ ] Upload to PyPI (twine upload)

---

## v1.1.0 (Post-Release Enhancements)

### Schema Introspection Improvements

**Priority**: High
**Complexity**: Medium
**Estimated**: 2 weeks

#### Problem: VECTOR Datatype Visibility

**Context**:
- IRIS VECTOR datatype appears as VARCHAR to DBAPI/SQL clients
- INFORMATION_SCHEMA shows VARCHAR instead of VECTOR
- This mismatch causes coding assistants to generate incorrect schema code
- Developers expect INFORMATION_SCHEMA to show true column types

**Impact**:
- Coding assistants (Claude, Copilot, etc.) continuously generate wrong code
- Schema introspection tools show incorrect types
- Type validation fails because VARCHAR != VECTOR
- Manual workarounds required for every VECTOR column

**Proposed Solution**:

Create `iris_devtester.schema.introspection` module with:

1. **Audit Trail DDL Parser**
   - Query IRIS audit trail for DDL commands
   - Parse CREATE TABLE / ALTER TABLE statements
   - Extract TRUE column definitions (including VECTOR)
   - Cache results for performance

2. **Enhanced Schema Inspector**
   - Combine INFORMATION_SCHEMA + audit trail data
   - Return accurate column types (VECTOR, not VARCHAR)
   - Support for all IRIS-specific types
   - Compatible with SQLAlchemy introspection

3. **SQLAlchemy Dialect Extension**
   - Custom IRIS dialect with VECTOR type awareness
   - Automatic type mapping (VECTOR <-> Python types)
   - Schema reflection with correct types
   - Type validation and coercion

**Implementation Plan**:

```python
# Example API:
from iris_devtester.schema import get_true_schema

# Get schema with real VECTOR types (not VARCHAR)
schema = get_true_schema(conn, table="Embeddings")

# Returns:
# {
#   "columns": [
#     {"name": "id", "type": "INT", "source": "INFORMATION_SCHEMA"},
#     {"name": "embedding", "type": "VECTOR(DOUBLE, 768)", "source": "AUDIT_TRAIL"},
#     {"name": "text", "type": "VARCHAR(5000)", "source": "INFORMATION_SCHEMA"}
#   ]
# }

# SQLAlchemy integration:
from iris_devtester.schema import IRISIntrospector
from sqlalchemy import create_engine

engine = create_engine("iris://localhost:1972/USER")
inspector = IRISIntrospector(engine)

# Reflects with correct VECTOR types
columns = inspector.get_columns("Embeddings")
# [
#   {"name": "embedding", "type": VECTOR(DOUBLE, 768)},  # Not VARCHAR!
#   ...
# ]
```

**Technical Approach**:

1. **Audit Trail Queries**:
   ```sql
   -- Find DDL for specific table
   SELECT Event, Description, SQLStatement
   FROM %SYS.Audit
   WHERE Event IN ('DDL:CREATE TABLE', 'DDL:ALTER TABLE')
     AND Description LIKE '%Embeddings%'
   ORDER BY UTCTimeStamp DESC
   ```

2. **DDL Parsing**:
   - Use regex/parser to extract column definitions
   - Handle VECTOR(DOUBLE, 768), VECTOR(STRING, 1536), etc.
   - Preserve all IRIS-specific type info

3. **Caching Strategy**:
   - Cache parsed schemas per table
   - Invalidate on DDL changes (listen for audit events)
   - Configurable TTL (default: 5 minutes)

4. **SQLAlchemy Integration**:
   - Extend `sqlalchemy.dialects.iris` (if exists) or create custom dialect
   - Override `get_columns()` to use audit trail
   - Define VECTOR type class for Python

**Benefits**:

- ✅ Coding assistants see correct VECTOR types
- ✅ Schema introspection matches reality
- ✅ Type validation works correctly
- ✅ No more VARCHAR confusion
- ✅ Production-ready schema management

**Risks**:

- Audit trail may not be enabled on all IRIS instances
- Performance impact of audit queries (mitigated by caching)
- DDL parsing complexity (handle edge cases)

**Acceptance Criteria**:

1. Can query true schema for tables with VECTOR columns
2. Returns VECTOR(DOUBLE, 768) instead of VARCHAR
3. Works with audit trail enabled/disabled (graceful degradation)
4. SQLAlchemy reflection shows correct types
5. Performance overhead < 100ms per table (with caching)
6. Comprehensive tests with various VECTOR configurations

**References**:
- IRIS VECTOR documentation
- IRIS Audit Trail documentation
- SQLAlchemy custom types guide
- User pain point: "coding assistants CONTINUALLY screw up on this issue!"

---

## v1.2.0 (Advanced Features)

### Connection Pooling
- Production-grade connection pool (from rag-templates Pattern 3)
- Thread-safe with statistics
- Health checks and validation
- Min/max sizing

### Performance Monitoring
- Query performance tracking
- Connection metrics
- Resource usage monitoring
- Slow query detection

### Advanced Testing
- DAT fixture versioning
- Incremental fixture updates
- Fixture dependency management
- Performance benchmarking

---

## v2.0.0 (Future - Major Features)

### Multi-Instance Support
- Connect to multiple IRIS instances
- Instance discovery and registration
- Cross-instance operations
- Instance health monitoring

### Mirror Configuration Support
- Automatic mirror detection
- Failover handling
- Primary/backup awareness
- Mirror synchronization utilities

### Enterprise Features
- Sharding support
- Advanced security (Kerberos, LDAP)
- ECP (Enterprise Cache Protocol) support
- Production monitoring integration

---

## Backlog (Unprioritized)

### Documentation
- Video tutorials
- Interactive examples
- Best practices guide
- Performance tuning guide

### Tooling
- CLI for common operations
- Schema migration tools
- Data migration utilities
- Health check dashboard

### Integrations
- Django ORM support
- FastAPI utilities
- Pandas integration
- Jupyter notebook helpers

---

## User Feedback Integration

**Submit Feedback**:
- GitHub Issues: https://github.com/anthropics/iris-devtester/issues
- Discussions: https://github.com/anthropics/iris-devtester/discussions

**Priority Process**:
1. User reports pain point
2. Validate with production usage
3. Add to roadmap with priority
4. Implement in next minor/major release

---

## Notes

- **Constitutional Compliance**: All features must follow the 8 core principles in CONSTITUTION.md
- **Battle-Testing**: New features should be extracted from production use when possible
- **Documentation**: Every feature requires comprehensive documentation with examples
- **Zero Config**: Maintain "pip install && pytest" simplicity

---

**Current Focus**: Complete v1.0.0 release (Phases 2-4)

**Reminder Set**: VECTOR datatype introspection for v1.1.0 🔔
