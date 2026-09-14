# E-Commerce Telemetry Alerts

Notification dispatch utility that translates catalog delta events into structured webhook payloads for team channels (Discord, Slack, or custom HTTP ingestion endpoints).

## Features
- **Delta Event Aggregation:** Groups price modifications, stockouts, restocks, and additions into a summary payload.
- **Webhook Integration:** Formats Discord/Slack embeds with status colors and event previews.
- **CLI Ready:** Ingests delta result CSV files and runs headless.

## Usage

```bash
# Output formatted JSON payload to stdout
python alert_dispatcher.py --input delta_results.csv

# Dispatch to a live Discord/Slack webhook
python alert_dispatcher.py --input delta_results.csv --webhook "[https://discord.com/api/webhooks/your/url](https://discord.com/api/webhooks/your/url)"