# Feature Specification: IRIS Server-Side Performance Monitoring Configuration

**Feature Branch**: `002-set-default-stats`
**Created**: 2025-10-05
**Status**: Draft - Revised for IRIS Server-Side Monitoring
**Input**: User description: "set default stats and performance collection to run every 30 seconds and keep last hour of data for debugging ease"

## Clarifications

### Session 2025-10-05
- Q: Which IRIS monitoring facilities should iris-devtools configure automatically when containers start? → A: ^SystemPerformance scheduled via IRIS Task Manager to run continuously (30s sampling, 1-hour profile duration), opt-out via environment variable override
- Q: How should Yaspe/Yates integration be handled in iris-devtools? → A: Bundle Yaspe as optional dependency (install with `pip install 'iris-devtools[yaspe]'`)
- Q: What are the safe minimum and maximum intervals for ^SystemPerformance sampling? → A: 1 second minimum, 300 seconds (5 minutes) maximum
- Q: What are the safe minimum and maximum retention periods for performance data? → A: 5 minutes minimum, 24 hours maximum
- Q: Should monitoring auto-disable under resource constraints, or always run regardless of system load? → A: Auto-disable when CPU >90% or memory >95% (self-protecting)

---

## Execution Flow (main)
```
1. Parse user description from Input
   → Feature: Auto-configure IRIS server performance monitoring in containers
2. Extract key concepts from description
   → Actors: IRIS database server, developers debugging production issues
   → Actions: configure ^SystemPerformance policy, set retention policies
   → Data: IRIS internal metrics (CPU, disk, globals, SQL, cache stats)
   → Constraints: 30-second collection interval, 1-hour retention window
   → Context: InterSystems best practice, inspired by Yaspe/Yates tooling
3. For each unclear aspect:
   → [RESOLVED] Collection interval: 30 seconds
   → [RESOLVED] Retention period: 1 hour
   → [RESOLVED] Target: IRIS server-side monitoring (not client-side)
   → [RESOLVED] Monitoring facility: ^SystemPerformance with policy configuration
   → [NEEDS CLARIFICATION: CPF parameters to set?]
   → [NEEDS CLARIFICATION: Integration with Yaspe/Yates?]
4. Fill User Scenarios & Testing section
   → Primary: Container starts with monitoring policy pre-configured
   → Secondary: Developer executes ^SystemPerformance after crash
5. Generate Functional Requirements
   → Each requirement testable via container integration tests
6. Identify Key Entities
   → IRISContainer, MonitoringPolicy, CPFSettings
7. Run Review Checklist
   → WARN "Spec needs IRIS monitoring expertise clarification"
8. Return: SUCCESS (spec ready for planning with clarifications)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no tech stack, APIs, code structure)
- 👥 Written for business stakeholders, not developers

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story
As a developer using iris-devtools containers, when my IRIS instance crashes or experiences performance issues, I want ^SystemPerformance already running automatically (30-second intervals, 1-hour retention), so diagnostic data is immediately available for investigation without having to manually start monitoring or lose critical debugging information.

### Acceptance Scenarios

1. **Given** a developer starts an IRIS container using `IRISContainer.community()`
   **When** the container finishes initialization
   **Then** ^SystemPerformance is automatically started and actively collecting performance data every 30 seconds with 1-hour retention

2. **Given** ^SystemPerformance is running with 30-second intervals and 1-hour retention
   **When** 1 hour (120 collection cycles) has elapsed
   **Then** IRIS automatically retains only the most recent hour of performance data, discarding older samples

3. **Given** a developer encounters an IRIS crash or performance degradation
   **When** they connect to the IRIS instance to investigate
   **Then** the last hour of IRIS performance metrics (CPU, globals, SQL, cache stats) is already collected and immediately accessible

4. **Given** an IRIS container is started with default iris-devtools configuration
   **When** a developer accesses management portal or queries ^SystemPerformance
   **Then** they see monitoring actively running with 30-second intervals and 1-hour retention window, with data already collected since container start

5. **Given** IRIS performance data is being automatically collected via ^SystemPerformance
   **When** a developer needs to export data for analysis (e.g., with Yaspe/Yates)
   **Then** the data is accessible in standard IRIS monitoring formats compatible with visualization tools

6. **Given** a developer wants to disable automatic monitoring (e.g., for resource-constrained environment)
   **When** they set environment variable IRIS_DISABLE_MONITORING=true before container start
   **Then** ^SystemPerformance does not automatically start, and the container runs without monitoring overhead

### Edge Cases

- What happens when IRIS monitoring overhead impacts container performance?
  → Monitoring automatically disables when CPU exceeds 90% or memory exceeds 95% (self-protecting behavior)

- How does monitoring behave in multi-instance containers (e.g., sharded setups)?
  → [NEEDS CLARIFICATION: Per-instance or aggregated monitoring?]

- What happens when users manually modify IRIS monitoring settings after container start?
  → Policy configuration is persistent; user modifications override defaults until container restart

- How does this work with Enterprise Edition licensed containers?
  → [NEEDS CLARIFICATION: Different monitoring capabilities/requirements?]

- Can users opt-out of automatic monitoring configuration?
  → [NEEDS CLARIFICATION: Disable flag or environment variable?]

## Requirements *(mandatory)*

### Functional Requirements

**Core Configuration**
- **FR-001**: System MUST automatically configure ^SystemPerformance with a monitoring policy when containers start
- **FR-002**: System MUST set ^SystemPerformance policy collection interval to 30 seconds by default
- **FR-003**: System MUST configure ^SystemPerformance policy to retain exactly 1 hour of performance history (120 data points at 30-second intervals)
- **FR-004**: System MUST configure ^SystemPerformance policy to automatically discard performance data older than 1 hour using rolling window

**^SystemPerformance Configuration**
- **FR-005**: System MUST configure ^SystemPerformance to collect IRIS instance metrics (globals, SQL, cache statistics, process counts)
- **FR-006**: System MUST configure ^SystemPerformance to collect OS-level metrics (vmstat, iostat, CPU, memory, disk I/O)
- **FR-007**: System MUST create a named monitoring policy/profile with 30-second interval and 1-hour retention settings
- **FR-008**: System MUST timestamp all collected metrics with sub-second precision (IRIS standard)

**CPF Configuration**
- **FR-009**: System MUST set appropriate CPF parameters for ^SystemPerformance during container initialization [NEEDS CLARIFICATION: Specific CPF parameters and values?]
- **FR-010**: System MUST configure memory allocation for monitoring operations [NEEDS CLARIFICATION: Default memory allocation?]
- **FR-011**: System MUST ensure OS-level permissions are configured for vmstat/iostat collection

**Data Access & Integration**
- **FR-012**: Monitoring data MUST be accessible via ^SystemPerformance utility and Management Portal
- **FR-013**: System MUST provide Yaspe/Yates as optional dependency for visualization (install via `pip install 'iris-devtools[yaspe]'`)
- **FR-014**: System MUST provide helper utilities to invoke Yaspe visualization on ^SystemPerformance output data
- **FR-015**: System MUST export monitoring data in standard ^SystemPerformance HTML report format compatible with Yaspe

**Performance & Reliability**
- **FR-016**: Monitoring configuration MUST NOT prevent IRIS container from starting (graceful degradation)
- **FR-017**: System MUST automatically disable monitoring when CPU utilization exceeds 90% or memory utilization exceeds 95%
- **FR-018**: System MUST re-enable monitoring automatically when resource utilization drops below thresholds (CPU <85%, memory <90%)
- **FR-019**: Monitoring MUST work transparently for both Community and Enterprise editions

**Configuration Control**
- **FR-020**: Users MUST be able to disable automatic monitoring via IRIS_DISABLE_MONITORING environment variable
- **FR-021**: Users MUST be able to customize collection interval between 1 second (minimum) and 300 seconds/5 minutes (maximum)
- **FR-022**: Users MUST be able to customize retention period between 5 minutes (minimum) and 24 hours (maximum)
- **FR-023**: Users MUST be able to override auto-disable thresholds (CPU/memory limits)

### Key Entities *(data involved)*

- **MonitoringPolicy**: Pre-configured ^SystemPerformance policy/profile defining collection interval (30s), retention period (1 hour), enabled metrics, and report format

- **CPFParameters**: Specific iris.cpf configuration parameter file settings related to ^SystemPerformance monitoring (memory allocation, OS permissions, collection settings)

- **IRISContainer**: Enhanced with automatic ^SystemPerformance policy configuration during container initialization (extends existing iris_devtools.containers.IRISContainer)

- **PerformanceDataExport**: Mechanism for extracting ^SystemPerformance monitoring data in formats suitable for Yaspe/Yates or other analysis tools

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs (automatic debugging-ready IRIS)
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No critical [NEEDS CLARIFICATION] markers remain (5 answered, 4 deferred to planning)
- [x] Requirements are testable and unambiguous (Task Manager scheduling, auto-disable thresholds, interval/retention limits)
- [x] Success criteria are measurable (30s interval, 1-hour retention, CPU/memory thresholds)
- [x] Scope is clearly bounded (^SystemPerformance + Task Manager only, not ^PERFMON or Activity Volume)
- [x] Dependencies and assumptions identified (IRIS Task Manager, Yaspe as optional dependency)

**Outstanding Clarifications (Deferred to Planning):**

1. **Specific CPF parameters and values** - Technical implementation detail best resolved during `/plan` phase
2. **Default memory allocation** - System-dependent, will be determined during implementation
3. **Per-instance vs aggregated monitoring** - Low impact edge case, defer to planning
4. **Enterprise Edition differences** - Will test during implementation, expected to work transparently

**Resolved via Clarification Session:**
- ✅ Monitoring facility: ^SystemPerformance via Task Manager scheduling
- ✅ Yaspe integration: Optional dependency (`pip install 'iris-devtools[yaspe]'`)
- ✅ Sampling interval limits: 1s min, 300s max
- ✅ Retention period limits: 5 min, 24 hours max
- ✅ Resource protection: Auto-disable at CPU >90% or memory >95%

---

## Execution Status
*Updated by main() during processing*

- [x] User description parsed
- [x] Key concepts extracted (30s interval, 1-hour retention, IRIS server-side)
- [x] Research completed (^SystemPerformance, Yaspe/Yates, CPF)
- [x] Scope pivoted from client-side to server-side monitoring
- [x] Monitoring facility clarified: ^SystemPerformance with policy configuration
- [x] Ambiguities marked (8 NEEDS CLARIFICATION items remaining)
- [x] User scenarios defined (5 acceptance scenarios, 5 edge cases)
- [x] Requirements updated (20 functional requirements)
- [x] Entities identified (4 key entities)
- [ ] Review checklist passed (WARN: 8 clarifications need IRIS monitoring expertise)

---

## Research Summary

### IRIS Performance Monitoring Architecture

**^SystemPerformance Utility** (formerly ^pButtons):
- Primary tool for comprehensive performance data collection
- Collects both IRIS instance metrics and OS-level metrics (vmstat, iostat, Windows perf counters)
- Generates HTML reports with unique run identifiers (YYYYMMDD_HHMM_profile_name.log)
- Requires appropriate OS permissions (Windows: Performance Monitor Users group)
- Supports scheduled execution via Task Manager
- Supports predefined profiles/policies for collection parameters
- Standard diagnostic tool shared with InterSystems WRC

**^PERFMON Facility**:
- System-level performance data through event counting
- Pre-allocates memory slots for processes, routines, globals, network nodes
- Organizes metrics by process, routine, global, network categories
- Minimal overhead (uses kernel-collected data)
- Controlled via ^PERFMON utility
- **Not selected for this feature** (^SystemPerformance chosen as modern approach)

**Activity Volume Statistics**:
- Specialized for message-based/integration systems
- Short-term monitoring and long-term traffic reporting
- Real-time dashboard capabilities
- Centralized repository for message statistics (SQL/MDX analysis)
- Auto-enabled for Ens.BusinessService/Process/Operation classes
- **Not selected for this feature** (^SystemPerformance provides broader coverage)

**Yaspe/Yates Tool** (GitHub community project):
- Python-based wrapper around ^SystemPerformance
- Transforms raw performance data into visualizations (HTML, PNG)
- Designed for containerized deployment
- Charts all system metrics (mgstat, vmstat, iostat, IRIS cache stats)
- Minimal overhead (aggregates existing kernel data)

### CPF Configuration

- iris.cpf = Configuration Parameter File for IRIS instance
- Controls monitoring behavior, buffer sizes, collection intervals, resource allocation
- Directly impacts ^SystemPerformance effectiveness

### Best Practice Context

User mentioned this is based on work at InterSystems and represents best practice for "debugging success" - having ^SystemPerformance policy pre-configured so diagnostic data collection is immediately available when issues occur, rather than trying to configure monitoring after-the-fact.

---

## Next Steps for `/clarify`

The specification has been updated with first clarification:
- **Monitoring facility**: ^SystemPerformance with policy-based configuration (not ^PERFMON or Activity Volume)
- **Approach**: Policy/profile defines 30s interval and 1-hour retention, ready to execute when needed

**Remaining critical clarifications before `/plan`**:
1. **Technical specifics**: Which CPF parameters control ^SystemPerformance
2. **Yaspe integration**: Bundle it? Document compatibility? Ignore it?
3. **Resource boundaries**: When to disable, how much overhead acceptable
4. **Enterprise considerations**: Licensing or capability differences

Once clarified, this will enable iris-devtools to provide "batteries-included" IRIS containers that are automatically debugging-ready with ^SystemPerformance, following InterSystems best practices.
