# D-carbN Operational Runbooks

Use these runbooks with the alert name, service, severity, correlation ID,
trace ID, deployment version, and incident start time.

## Incident roles

- Incident commander: owns decisions, communication, and timeline.
- Operations lead: investigates infrastructure and deployment state.
- Application lead: investigates code, data, and application behavior.
- Security lead: joins identity, access, exfiltration, or compromise incidents.
- Communications lead: updates affected internal and external stakeholders.

## Severity targets

| Severity | Acknowledge | Update cadence | Example |
|---|---:|---:|---|
| Critical | 10 minutes | 30 minutes | API unavailable, database loss, token reuse |
| Warning | 30 minutes | 60 minutes | Elevated latency, stale backup, disk pressure |

Preserve evidence before destructive remediation. Record commands, timestamps,
decisions, affected tenants, and validation results in the incident log.
