# Agents

HCAI OPS agents run on edge nodes to collect telemetry and execute safe actions.

## Capabilities
- Heartbeats
- Metrics collection
- Log forwarding
- Safe command execution

## Lifecycle
- Install agent package
- Register with `/agent/ping`
- Send periodic reports via `/agent/report`
