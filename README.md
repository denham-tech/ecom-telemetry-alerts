# E-Commerce Telemetry & Anomaly Webhook Dispatcher

Production-grade alerting module engineered in **Python** for real-time e-commerce intelligence. Consumes inventory delta streams and formats structured, rich JSON webhook payloads for automated dispatch to Slack, Discord, or enterprise endpoints.

## Core Architecture
- **Multi-Event Classification:** Evaluates severity profiles for catastrophic stockouts (`CRITICAL`) and competitor pricing shifts (`HIGH`).
- **Normalized Schema Payloads:** Constructs standardized embed objects containing variant SKUs, absolute price deltas, percentage variance, and UTC timestamps.
- **Integration Agnostic:** Plugs directly into existing delta monitoring pipelines and SQLite audit warehouses.

## Deliverables
- `alert_dispatcher.py` - Core telemetry formatting and routing engine.
- `webhook_payload_sample.json` - Sample formatted integration payload (untracked).