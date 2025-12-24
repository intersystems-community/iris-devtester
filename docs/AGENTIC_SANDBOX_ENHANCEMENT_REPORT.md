# IRIS Agentic Sandbox Enhancement Report

**Date**: 2025-11-23
**Version**: 1.0
**Status**: Research Complete → Design Phase

---

## Executive Summary

This report analyzes iris-devtester's current capabilities against modern agentic AI sandbox requirements and provides actionable recommendations to transform it into a production-grade "IRIS sandbox" system optimized for autonomous AI agents.

**Key Findings**:
- ✅ iris-devtester has strong foundations (isolation, auto-remediation, test fixtures)
- ⚠️ Missing critical agentic features (resource limits, monitoring, lifecycle management)
- 🎯 High ROI opportunity: 8 enhancements could position iris-devtester as the standard IRIS sandbox for AI agents

**Impact**: These enhancements would make iris-devtester the **de facto standard** for IRIS-based agentic systems, similar to how E2B and Firecracker dominate general code execution sandboxes.

---

## Research Findings: Agentic AI Sandbox Requirements (2024-2025)

### 1. Industry Standards for Agent Sandboxes

Based on research from Google Cloud, NVIDIA, OpenAI, and AWS:

#### **Core Requirements**
1. **Workload Isolation** - Each agent gets isolated execution environment
2. **Resource Limits** - CPU, memory, storage, network bandwidth limits
3. **Lifecycle Management** - Create, monitor, pause, resume, destroy sandboxes
4. **Security Boundaries** - Prevent cross-session data leakage
5. **Observability** - Real-time monitoring of all operations
6. **Fast Provisioning** - Sub-second latency for pre-warmed pools
7. **Cost Efficiency** - Ephemeral environments reduce infrastructure by 90%
8. **Stateful Workload Support** - Databases need special handling vs. stateless compute

#### **Key Technologies**
- **Kubernetes Agent Sandbox** (Google, Nov 2025): New K8s SIG standard for agent workloads
- **gVisor**: Kernel-level isolation without VM overhead
- **Kata Containers**: VM-based isolation for stronger security
- **Signadot**: Ephemeral K8s environments with database sandboxing
- **WebAssembly**: Lightweight sandboxing for LLM-generated code

### 2. Database-Specific Sandbox Patterns

Research from Kubernetes testing platforms (Signadot, Testkube, Qovery):

#### **Ephemeral Database Strategies**
1. **Temporary Schemas/Namespaces** - Create per-agent database namespaces
2. **Pre-warmed Pools** - Maintain ready-to-use database instances
3. **Snapshot-Based Reset** - Fast rollback to known-good state
4. **Transaction Isolation** - Atomic all-or-nothing operations
5. **Cross-Session Protection** - Prevent data leakage between agents

#### **Cost Reduction Techniques**
- **90% infrastructure cost reduction** with ephemeral environments
- **Shared stateful resources** with logical isolation (namespaces)
- **On-demand provisioning** instead of long-running instances
- **Automatic cleanup** after agent task completion

### 3. Security & Monitoring Best Practices

From OpenAI, AWS Security, McKinsey agentic AI playbooks:

#### **Security Controls**
1. **Least-privilege permissions** - Minimum required database access
2. **Network isolation** - Controlled ingress/egress
3. **Audit logging** - All queries, schema changes, data access logged
4. **Automatic sandboxing** - Default-deny, explicit allowlisting
5. **Runtime monitoring** - Detect anomalous behavior

#### **Monitoring Requirements**
1. **Resource utilization** - CPU, memory, disk I/O tracking
2. **Query performance** - Slow query detection, execution plans
3. **Connection health** - Validate database accessibility
4. **Error tracking** - Categorize failures (timeout, permission, corruption)
5. **SLA compliance** - Measure against performance targets

---

## Gap Analysis: iris-devtester vs. Agentic Requirements

### ✅ What iris-devtester Does Well

| Feature | Status | Notes |
|---------|--------|-------|
| Container isolation | ✅ Excellent | Testcontainers-based, automatic cleanup |
| Auto-remediation | ✅ Excellent | Password reset, CallIn enablement |
| Zero-config | ✅ Excellent | Works out of the box |
| DBAPI-first performance | ✅ Excellent | 3x faster than JDBC |
| Test fixtures (DAT) | ✅ Excellent | 10-100x faster data loading |
| Platform compatibility | ✅ Good | macOS, Linux, Windows (WSL2) |
| Defensive validation | ✅ Good | Container health checks |
| Medical-grade reliability | ✅ Good | 94% test coverage |

### ⚠️ Critical Gaps for Agentic Systems

| Requirement | Current State | Gap Severity | Impact |
|-------------|---------------|--------------|--------|
| **Resource limits** | ❌ None | 🔴 Critical | Agents can exhaust CPU/memory |
| **Lifecycle management** | ⚠️ Basic | 🟡 Medium | No pause/resume, limited pools |
| **Real-time monitoring** | ⚠️ Minimal | 🟡 Medium | No query tracking, no alerts |
| **Ephemeral namespaces** | ❌ None | 🔴 Critical | Agents pollute shared namespaces |
| **Multi-tenancy** | ❌ None | 🟠 High | No agent-to-agent isolation |
| **Pre-warmed pools** | ❌ None | 🟡 Medium | Cold start penalty (10-15s) |
| **Audit logging** | ❌ None | 🟠 High | No query history, no compliance |
| **Automatic cleanup** | ⚠️ Partial | 🟡 Medium | Manual namespace deletion required |

### 🎯 Opportunity Areas

1. **Resource Governance** - No CPU/memory limits, no disk quotas
2. **Observability** - No agent activity tracking, no performance metrics
3. **Multi-Agent Orchestration** - No session management, no workload queueing
4. **Compliance** - No audit logs, no data retention policies
5. **Developer Experience** - No sandbox UI, no cost dashboards

---

## Recommended Enhancements

### Phase 1: Foundation (Weeks 1-2)

#### Enhancement 1: Ephemeral Namespace Management
**Problem**: Agents currently share namespaces, causing data pollution and security risks.

**Solution**: Automatic ephemeral namespace per agent session.

```python
# NEW API
from iris_devtester.sandbox import AgentSandbox

with AgentSandbox.create(agent_id="assistant-123") as sandbox:
    # Isolated namespace: AGENT_ASSISTANT_123_20251123_1430
    conn = sandbox.get_connection()

    # Automatic cleanup on context exit
    # All data, schemas, globals deleted
```

**Benefits**:
- ✅ Complete data isolation between agents
- ✅ Automatic cleanup (no orphaned namespaces)
- ✅ Session-scoped transaction safety
- ✅ Compliance-friendly (no cross-agent data leakage)

**Implementation**:
- New `iris_devtester/sandbox/namespace_manager.py`
- Namespace naming: `AGENT_{agent_id}_{timestamp}`
- Cleanup via `##class(Config.Namespaces).Delete()`
- Integration with existing IRISContainer

---

#### Enhancement 2: Resource Limits & Quotas
**Problem**: Agents can consume unlimited CPU, memory, and disk, causing DoS.

**Solution**: Docker resource constraints + IRIS resource governors.

```python
# NEW API
with AgentSandbox.create(
    agent_id="assistant-123",
    limits={
        "cpu": "0.5",          # 50% of 1 core
        "memory": "512M",      # 512MB RAM
        "disk_quota_mb": 100,  # 100MB database storage
        "max_connections": 5,  # Concurrent connections
    }
) as sandbox:
    # Resource-constrained execution
    conn = sandbox.get_connection()
```

**Benefits**:
- ✅ Prevent runaway agent resource consumption
- ✅ Fair resource sharing across agents
- ✅ Predictable cost modeling
- ✅ Automatic termination on quota exceeded

**Implementation**:
- Docker: `container.with_resource_limits(cpus=0.5, memory="512M")`
- IRIS: `##class(%Library.ECP).SetMaxServers(5)` for connection limits
- Disk quota: Monitor namespace size via `##class(%Monitor.System.DiskSpace)`
- Auto-terminate on violation

---

#### Enhancement 3: Real-Time Monitoring & Alerts
**Problem**: No visibility into agent database activity, resource usage, or errors.

**Solution**: Built-in monitoring with configurable alerts.

```python
# NEW API
with AgentSandbox.create(
    agent_id="assistant-123",
    monitoring={
        "enabled": True,
        "alert_on_slow_query_ms": 1000,  # Alert if query > 1s
        "alert_on_cpu_percent": 80,       # Alert if CPU > 80%
        "log_all_queries": True,          # Audit trail
    }
) as sandbox:
    conn = sandbox.get_connection()

    # Access metrics
    metrics = sandbox.get_metrics()
    # {
    #   "queries_executed": 42,
    #   "slow_queries": 3,
    #   "avg_query_time_ms": 45,
    #   "cpu_percent": 23,
    #   "memory_used_mb": 128
    # }
```

**Benefits**:
- ✅ Real-time visibility into agent behavior
- ✅ Proactive alerts for anomalies
- ✅ Performance optimization insights
- ✅ Compliance audit trails

**Implementation**:
- New `iris_devtester/sandbox/monitor.py`
- IRIS SQL tracing: `##class(%Monitor.System.SQL).Enable()`
- Resource polling: Query `##class(%Monitor.System.Dashboard)` every 5s
- Webhook/callback for alerts

---

### Phase 2: Advanced Features (Weeks 3-4)

#### Enhancement 4: Pre-Warmed Sandbox Pools
**Problem**: Cold start penalty (10-15s on macOS) kills agent responsiveness.

**Solution**: Maintain pool of ready-to-use sandboxes.

```python
# NEW API
from iris_devtester.sandbox import SandboxPool

# Pre-warm 5 sandboxes
pool = SandboxPool(size=5, warmup=True)

# Instant allocation (< 100ms)
with pool.acquire(agent_id="assistant-123") as sandbox:
    conn = sandbox.get_connection()  # Already warm!

# Auto-replenished pool
```

**Benefits**:
- ✅ Sub-second sandbox provisioning (90% improvement)
- ✅ Predictable latency for agent operations
- ✅ Better user experience (no waiting)
- ✅ Cost-efficient (reuse containers)

**Implementation**:
- New `iris_devtester/sandbox/pool.py`
- Background thread maintains pool size
- Namespace reset via DAT fixture or DELETE
- Health checks on idle sandboxes

---

#### Enhancement 5: Snapshot-Based State Management
**Problem**: Agents need to rollback or restore known-good database state.

**Solution**: Fast snapshot/restore using DAT fixtures.

```python
# NEW API
with AgentSandbox.create(agent_id="assistant-123") as sandbox:
    # Load initial state
    sandbox.load_snapshot("golden-dataset-v1")

    # Agent modifies data
    conn = sandbox.get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO entities VALUES (...)")

    # Rollback to snapshot
    sandbox.restore_snapshot("golden-dataset-v1")

    # Or save new snapshot
    sandbox.create_snapshot("agent-checkpoint-1")
```

**Benefits**:
- ✅ Fast rollback (<10s for 10K rows)
- ✅ Reproducible agent testing
- ✅ Checkpoint/resume workflows
- ✅ A/B testing different agent strategies

**Implementation**:
- Leverage existing DAT fixture system
- Store snapshots in `.iris-sandbox/snapshots/`
- SHA256 checksums for integrity
- Lazy loading (only restore if needed)

---

#### Enhancement 6: Multi-Tenancy & Access Control
**Problem**: No way to isolate agents by tenant, organization, or project.

**Solution**: Hierarchical namespace management with access policies.

```python
# NEW API
with AgentSandbox.create(
    agent_id="assistant-123",
    tenant="acme-corp",           # Namespace: TENANT_ACME_CORP_AGENT_123
    access_policy={
        "read_only": False,
        "allowed_tables": ["Entities", "Documents"],
        "deny_tables": ["Admin", "Secrets"],
        "max_row_limit": 1000,
    }
) as sandbox:
    conn = sandbox.get_connection()
```

**Benefits**:
- ✅ SaaS-ready multi-tenancy
- ✅ Least-privilege access control
- ✅ Prevent accidental data exposure
- ✅ Compliance with data privacy regulations

**Implementation**:
- Namespace hierarchy: `TENANT_{tenant}_AGENT_{agent_id}`
- IRIS row-level security: `##class(Security.Roles)`
- SQL proxy to enforce table allowlists
- Query rewrite to inject `WHERE ROWNUM <= 1000`

---

### Phase 3: Production Hardening (Weeks 5-6)

#### Enhancement 7: Comprehensive Audit Logging
**Problem**: No audit trail of agent database activity for compliance.

**Solution**: Structured logging of all agent operations.

```python
# NEW API
with AgentSandbox.create(
    agent_id="assistant-123",
    audit_log={
        "enabled": True,
        "log_queries": True,
        "log_connections": True,
        "log_schema_changes": True,
        "export_format": "json",
        "retention_days": 90,
    }
) as sandbox:
    conn = sandbox.get_connection()

    # All activity logged
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM secrets")  # LOGGED + DENIED
```

**Audit Log Schema**:
```json
{
  "timestamp": "2025-11-23T14:30:00Z",
  "agent_id": "assistant-123",
  "tenant": "acme-corp",
  "event_type": "query",
  "query": "SELECT * FROM secrets",
  "status": "denied",
  "duration_ms": 5,
  "rows_affected": 0,
  "error": "Access denied: secrets not in allowed_tables"
}
```

**Benefits**:
- ✅ Complete audit trail for compliance (SOC2, HIPAA, GDPR)
- ✅ Security incident investigation
- ✅ Performance debugging (slow query detection)
- ✅ Usage analytics (cost allocation)

**Implementation**:
- New `iris_devtester/sandbox/audit.py`
- Hook into IRIS `%Monitor.System.SQL`
- Structured logging to JSON files or S3
- Retention policy enforcement

---

#### Enhancement 8: Kubernetes Integration (Optional)
**Problem**: Local Docker doesn't scale for production agentic workloads.

**Solution**: Deploy iris-devtester sandboxes on Kubernetes with Agent Sandbox API.

```yaml
# NEW: Kubernetes deployment
apiVersion: apps.kubernetes.io/v1
kind: SandboxTemplate
metadata:
  name: iris-agent-sandbox
spec:
  image: intersystemsdc/iris-community:latest
  resources:
    limits:
      cpu: "500m"
      memory: "512Mi"
  security:
    gvisor: true  # Kernel-level isolation
```

```python
# Python API (unchanged)
with AgentSandbox.create(agent_id="assistant-123") as sandbox:
    # Auto-deploys to K8s if available, else local Docker
    conn = sandbox.get_connection()
```

**Benefits**:
- ✅ Production-scale orchestration
- ✅ Auto-scaling based on demand
- ✅ Multi-region deployment
- ✅ Enterprise-grade security (gVisor, Kata)

**Implementation**:
- Detect K8s via `kubectl` availability
- Use Google's Kubernetes Agent Sandbox APIs
- Fallback to local Docker if K8s unavailable
- Pre-warmed pod pools for <1s provisioning

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2) - HIGH PRIORITY
- [ ] Enhancement 1: Ephemeral Namespace Management
- [ ] Enhancement 2: Resource Limits & Quotas
- [ ] Enhancement 3: Real-Time Monitoring & Alerts

**Deliverables**:
- `iris_devtester/sandbox/` module
- `AgentSandbox` class with namespace isolation
- Docker resource constraints
- Basic monitoring (CPU, memory, queries)
- 95%+ test coverage

**Success Criteria**:
- ✅ Agents get isolated namespaces
- ✅ Resource limits prevent DoS
- ✅ Monitoring detects slow queries

### Phase 2: Advanced Features (Weeks 3-4) - MEDIUM PRIORITY
- [ ] Enhancement 4: Pre-Warmed Sandbox Pools
- [ ] Enhancement 5: Snapshot-Based State Management
- [ ] Enhancement 6: Multi-Tenancy & Access Control

**Deliverables**:
- `SandboxPool` with warmup/acquire/release
- Snapshot save/restore via DAT fixtures
- Tenant-scoped namespaces
- Access policy enforcement

**Success Criteria**:
- ✅ <100ms sandbox allocation from pool
- ✅ <10s snapshot restore time
- ✅ Multi-tenant isolation verified

### Phase 3: Production Hardening (Weeks 5-6) - OPTIONAL
- [ ] Enhancement 7: Comprehensive Audit Logging
- [ ] Enhancement 8: Kubernetes Integration

**Deliverables**:
- Structured audit logs (JSON)
- K8s deployment manifests
- Agent Sandbox API integration
- Production deployment guide

**Success Criteria**:
- ✅ 100% audit coverage
- ✅ K8s sandboxes deploy successfully
- ✅ Production SLA: <1s provisioning, 99.9% uptime

---

## Cost-Benefit Analysis

### Development Investment
- **Phase 1**: ~40 hours (1 senior dev, 1 week)
- **Phase 2**: ~60 hours (1 senior dev, 1.5 weeks)
- **Phase 3**: ~40 hours (1 senior dev, 1 week)
- **Total**: ~140 hours (~3.5 weeks)

### Expected ROI
1. **Market Positioning**: iris-devtester becomes the **standard** IRIS sandbox for AI agents
2. **User Adoption**: 90% reduction in setup friction for agentic systems
3. **Infrastructure Savings**: 90% cost reduction (ephemeral environments vs. persistent)
4. **Security Posture**: Eliminate cross-agent data leakage, audit compliance
5. **Developer Velocity**: <1s sandbox provisioning (vs. 10-15s cold start)

### Competitive Advantage
- **E2B**: General code execution, no IRIS support
- **Firecracker**: VM-based, heavyweight for databases
- **Agent Sandbox (K8s)**: No IRIS integration
- **iris-devtester**: **Only IRIS-native agentic sandbox** (zero competition!)

---

## Adoption Strategy

### Target Audiences
1. **Agentic AI Developers**: Building autonomous systems on IRIS
2. **Enterprise AI Teams**: Multi-tenant SaaS platforms
3. **Research Labs**: Reproducible agent experiments
4. **CI/CD Platforms**: Automated IRIS testing infrastructure

### Go-To-Market
1. **Documentation**: Agentic quickstart guide (5 minutes to first agent)
2. **Blog Post**: "Building Production-Grade AI Agents on IRIS" (SEO: "IRIS agent sandbox")
3. **Example Projects**: RAG agent, SQL agent, workflow orchestrator
4. **Conference Talks**: InterSystems Global Summit, PyData, AI Engineer Summit

### Success Metrics
- **Adoption**: 100+ projects using AgentSandbox in 6 months
- **GitHub Stars**: 500+ (signal of community interest)
- **PyPI Downloads**: 10K/month (from current ~1K/month)
- **Enterprise Users**: 5+ companies in production

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| IRIS resource governors don't exist | Low | High | Use Docker limits + namespace deletion |
| K8s complexity delays adoption | Medium | Low | Keep K8s optional, local Docker default |
| Monitoring overhead impacts performance | Medium | Medium | Sampling (1 in 10 queries), async logging |
| Community doesn't need agentic features | Low | High | Survey users, validate hipporag2 use case |

---

## Next Steps

### Immediate (This Week)
1. ✅ **Research Complete** (this report)
2. **Stakeholder Review**: Share with iris-devtester maintainers
3. **User Validation**: Interview hipporag2-pipeline team about needs
4. **Prototype**: Build minimal AgentSandbox with namespace isolation

### Short-Term (Next 2 Weeks)
1. **Phase 1 Implementation**: Ephemeral namespaces, resource limits, monitoring
2. **Documentation**: Agentic quickstart guide
3. **Testing**: 95%+ coverage for new sandbox features
4. **Release**: v1.5.0 with AgentSandbox beta

### Medium-Term (Next 6 Weeks)
1. **Phase 2 Implementation**: Pools, snapshots, multi-tenancy
2. **Production Pilot**: hipporag2-pipeline migration
3. **Performance Tuning**: <100ms pool allocation, <10s snapshots
4. **Release**: v1.6.0 with production-ready AgentSandbox

---

## Conclusion

iris-devtester is **perfectly positioned** to become the standard IRIS sandbox for agentic AI systems. With 8 targeted enhancements (~3.5 weeks development), we can:

1. ✅ **Eliminate setup friction** for AI developers (zero-config agentic sandbox)
2. ✅ **Reduce infrastructure costs** by 90% (ephemeral environments)
3. ✅ **Improve security posture** (isolation, auditing, least-privilege)
4. ✅ **Enable production deployment** (K8s, monitoring, SLAs)
5. ✅ **Capture entire market** (no IRIS-native competitors)

**Recommendation**: Proceed with **Phase 1 implementation** immediately. The hipporag2-pipeline use case validates real demand, and the 2025 agentic AI boom creates massive market opportunity.

---

## References

### Agentic AI Sandbox Standards
- [Google: Unleashing Autonomous AI Agents on Kubernetes](https://opensource.googleblog.com/2025/11/unleashing-autonomous-ai-agents-why-kubernetes-needs-a-new-standard-for-agent-execution.html) - Kubernetes Agent Sandbox announcement (Nov 2025)
- [Google Cloud: Agentic AI on Kubernetes and GKE](https://cloud.google.com/blog/products/containers-kubernetes/agentic-ai-on-kubernetes-and-gke) - Production deployment patterns
- [NVIDIA: Sandboxing Agentic AI Workflows with WebAssembly](https://developer.nvidia.com/blog/sandboxing-agentic-ai-workflows-with-webassembly/) - Lightweight isolation techniques
- [OpenAI: Practices for Governing Agentic AI Systems](https://cdn.openai.com/papers/practices-for-governing-agentic-ai-systems.pdf) - Security and monitoring requirements
- [AWS: Agentic AI Security Scoping Matrix](https://aws.amazon.com/blogs/security/the-agentic-ai-security-scoping-matrix-a-framework-for-securing-autonomous-ai-systems/) - Security framework
- [McKinsey: Deploying Agentic AI with Safety and Security](https://www.mckinsey.com/capabilities/risk-and-resilience/our-insights/deploying-agentic-ai-with-safety-and-security-a-playbook-for-technology-leaders) - Enterprise playbook

### Database Sandbox Patterns
- [Signadot: Creating Scalable Sandboxes in Kubernetes](https://www.signadot.com/blog/creating-sandboxes-in-kubernetes-at-scale) - Ephemeral database environments
- [Testkube: Kubernetes Sandbox Environment](https://testkube.io/glossary/kubernetes-sandbox-environment) - Testing patterns
- [Signadot: Cut Testing Infrastructure Costs by 90%](https://www.signadot.com/articles/kubernetes-budget-rescue-trim-90-of-testing-infrastructure-costs) - Cost optimization
- [Kubernetes SIG: agent-sandbox](https://github.com/kubernetes-sigs/agent-sandbox) - Official K8s agent sandbox project

### Security & Isolation
- [Google Cloud: Isolate AI Code Execution with Agent Sandbox](https://docs.cloud.google.com/kubernetes-engine/docs/how-to/agent-sandbox) - gVisor-based isolation
- [Rippling: Agentic AI Security Guide](https://www.rippling.com/blog/agentic-ai-security) - Threats and defenses
- [arXiv: Agentic AI Security Research](https://arxiv.org/html/2510.23883v1) - Academic research
- [UserJot: Best Practices for Agentic AI Systems](https://userjot.com/blog/best-practices-building-agentic-ai-systems) - Production lessons

---

**Report prepared by**: Claude Code
**Review requested from**: iris-devtester maintainers, hipporag2-pipeline team
**Next review date**: 2025-11-30
