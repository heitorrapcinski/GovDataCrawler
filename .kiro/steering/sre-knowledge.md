# SRE Knowledge Base

## Overview

This project incorporates **Site Reliability Engineering (SRE)** principles as defined by Google and widely adopted across the industry. All agents working on this project must understand SRE concepts to correctly design, implement, and extend features that bridge ITSM and modern reliability practices.

---

## Core SRE Principles

### Embrace Risk

- 100% reliability is neither realistic nor desirable — pursuing it has diminishing returns
- Every service must define an acceptable level of unreliability (error budget)
- Risk tolerance is a business decision, not a purely technical one

### Eliminate Toil

- **Toil** is manual, repetitive, automatable, tactical work with no enduring value
- SRE teams aim to spend no more than 50% of their time on toil
- Automation is the primary weapon against toil
- If a human is doing something a machine could do, it should be automated

### Monitor and Measure Everything

- Decisions must be driven by data, not intuition
- Monitoring provides the foundation for understanding system behavior
- Alerting must be actionable — every alert should require human intervention

### Automate Progressively

- Start with manual processes, document them as runbooks, then automate incrementally
- Automation reduces human error and improves consistency
- Self-healing systems are the ultimate goal

---

## Key SRE Concepts

### Service Level Indicators (SLIs)

| Concept | Description |
|---|---|
| **SLI** | A quantitative measure of a specific aspect of the level of service provided |
| **Common SLIs** | Availability, latency, throughput, error rate, durability |
| **Measurement** | SLIs are derived from monitoring data (metrics, logs, traces) |

Examples:
- **Availability SLI**: Proportion of successful requests over total requests
- **Latency SLI**: Proportion of requests served faster than a threshold (e.g., < 200ms)
- **Error Rate SLI**: Proportion of requests that result in errors

### Service Level Objectives (SLOs)

| Concept | Description |
|---|---|
| **SLO** | A target value or range for an SLI over a time window |
| **Purpose** | Defines the reliability goal for a service |
| **Time Window** | Typically 30 days (rolling) or calendar month |

Examples:
- Availability SLO: 99.9% of requests succeed over 30 days
- Latency SLO: 95% of requests complete in < 200ms over 30 days
- Error Rate SLO: < 0.1% of requests return 5xx errors

### Service Level Agreements (SLAs)

| Concept | Description |
|---|---|
| **SLA** | A formal contract with consequences for missing the SLO |
| **Relationship** | SLA ⊇ SLO ⊇ SLI |
| **Consequences** | Financial penalties, service credits, contract termination |

Rule: SLOs should always be stricter than SLAs to provide a safety margin.

### Error Budgets

| Concept | Description |
|---|---|
| **Error Budget** | The allowed amount of unreliability within an SLO window |
| **Calculation** | `Error Budget = 1 - SLO target` |
| **Purpose** | Balances reliability with feature velocity |

Examples:
- SLO = 99.9% → Error Budget = 0.1% (43.2 minutes/month of downtime)
- SLO = 99.95% → Error Budget = 0.05% (21.6 minutes/month)
- SLO = 99.99% → Error Budget = 0.01% (4.32 minutes/month)

Error Budget Policy:
- When budget is healthy → teams can ship features and take risks
- When budget is depleted → freeze deployments, focus on reliability improvements
- Error budget burn rate indicates how fast reliability is degrading

---

## SRE Practices

### Incident Management

| Phase | Description |
|---|---|
| **Detection** | Automated alerting based on SLI/SLO breaches |
| **Triage** | Assess severity, assign incident commander |
| **Mitigation** | Restore service as quickly as possible (not root cause) |
| **Resolution** | Fix the underlying issue |
| **Postmortem** | Blameless analysis of what happened and how to prevent recurrence |

Severity Levels:
- **SEV-1**: Critical — major user-facing impact, all hands on deck
- **SEV-2**: High — significant impact, dedicated responders
- **SEV-3**: Medium — limited impact, normal priority
- **SEV-4**: Low — minimal impact, tracked but not urgent

### Postmortems (Blameless)

Every significant incident must produce a postmortem containing:
- **Summary**: What happened, when, and impact
- **Timeline**: Chronological sequence of events
- **Root Cause**: Technical root cause analysis (5 Whys, Fishbone, etc.)
- **Impact**: Users affected, duration, error budget consumed
- **Action Items**: Concrete, assigned, and time-bound improvements
- **Lessons Learned**: What went well, what went poorly, where we got lucky

Rules:
- Postmortems are **blameless** — focus on systems, not individuals
- Action items must be tracked to completion
- Postmortems are shared openly to spread learning

### On-Call

| Concept | Description |
|---|---|
| **On-Call Rotation** | Scheduled responsibility for responding to incidents |
| **Escalation Policy** | Defined chain of escalation when primary responder is unavailable |
| **Handoff** | Structured transfer of context between on-call shifts |
| **Compensation** | On-call work must be recognized and compensated |

Rules:
- On-call engineers must have the authority and tools to mitigate incidents
- Maximum on-call shift: 12 hours for high-severity services
- Post-incident rest period must be respected

### Capacity Planning

| Concept | Description |
|---|---|
| **Demand Forecasting** | Predicting future resource needs based on growth trends |
| **Load Testing** | Validating system behavior under expected and peak loads |
| **Provisioning** | Ensuring sufficient resources are available ahead of demand |
| **Headroom** | Maintaining buffer capacity for unexpected spikes |

---

## Observability (The Three Pillars)

### Metrics

- Numeric measurements collected over time (time series)
- Used for dashboards, alerting, and trend analysis
- Key metric types: counters, gauges, histograms, summaries
- Follow the **USE Method** for resources: Utilization, Saturation, Errors
- Follow the **RED Method** for services: Rate, Errors, Duration

### Logs

- Discrete events with structured or unstructured data
- Must be structured (JSON) for machine parsing
- Include correlation IDs for request tracing
- Log levels: DEBUG, INFO, WARN, ERROR, FATAL

### Traces

- End-to-end request flow across distributed services
- Each trace contains spans representing individual operations
- Essential for debugging latency and understanding service dependencies
- Implement distributed tracing with context propagation

---

## Reliability Patterns

### Graceful Degradation

- Services should degrade gracefully under load rather than fail completely
- Implement fallbacks for non-critical dependencies
- Serve cached or stale data when upstream services are unavailable

### Circuit Breaker

- Prevent cascading failures by stopping requests to unhealthy dependencies
- States: Closed (normal) → Open (failing) → Half-Open (testing recovery)
- Configure thresholds for failure rate and recovery timeout

### Retry with Backoff

- Retry transient failures with exponential backoff and jitter
- Set maximum retry limits to prevent retry storms
- Distinguish between retryable and non-retryable errors

### Rate Limiting and Throttling

- Protect services from being overwhelmed by excessive requests
- Implement at API gateway and service level
- Return appropriate HTTP status codes (429 Too Many Requests)

### Bulkhead Pattern

- Isolate critical resources to prevent one component from consuming all capacity
- Use separate thread pools, connection pools, or service instances
- Limit blast radius of failures

### Health Checks

- Implement liveness probes (is the process running?)
- Implement readiness probes (is the service ready to accept traffic?)
- Health checks should verify critical dependencies

---

## Automation Hierarchy

```
Level 0: No automation — manual process documented in a runbook
Level 1: Operator-triggered automation — human initiates, machine executes
Level 2: Operator-supervised automation — machine initiates, human approves
Level 3: Fully automated — machine initiates and executes, human is notified
Level 4: Autonomous — machine handles everything, human is informed only on anomalies
```

Goal: Progressively move operational tasks up the automation hierarchy.

---

## SRE Metrics for Opsly

When implementing features, consider these operational metrics:

| Metric | Description |
|---|---|
| **MTTR** (Mean Time to Recovery) | Average time to restore service after an incident |
| **MTTD** (Mean Time to Detect) | Average time to detect an incident after it begins |
| **MTTA** (Mean Time to Acknowledge) | Average time for a responder to acknowledge an incident |
| **MTBF** (Mean Time Between Failures) | Average time between service failures |
| **Change Failure Rate** | Percentage of changes that result in incidents |
| **Deployment Frequency** | How often code is deployed to production |
| **Toil Ratio** | Percentage of time spent on toil vs. engineering work |
| **Error Budget Burn Rate** | How fast the error budget is being consumed |

---

## Rules for Agents

- When implementing incident-related features, always consider the **SLI → SLO → SLA → Error Budget** chain
- Automation features must follow the **automation hierarchy** — start with runbooks, progress to full automation
- Monitoring and alerting features must produce **actionable alerts** — no alert fatigue
- Incident workflows must support **blameless postmortems** with structured action items
- Reliability patterns (circuit breaker, retry, bulkhead) must be considered in all service-to-service communication
- Observability features must address all three pillars: **metrics, logs, and traces**
- Capacity and performance features must account for **headroom and graceful degradation**
- Error budget tracking must be a first-class feature — it drives the balance between velocity and reliability
- All operational metrics (MTTR, MTTD, MTTA, etc.) must be measurable and reportable
- Toil reduction must be a measurable goal — track automation coverage over time
