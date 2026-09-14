"""
E-Commerce Catalog Alerting & Webhook Dispatcher
Parses detected catalog delta events and posts formatted alert payloads
to external monitoring webhooks (Discord / Slack / generic HTTP receivers).
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("AlertEngine")


class CatalogAlertDispatcher:
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url

    def build_payload(self, delta_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Constructs a structured JSON alert payload from delta events.
        """
        summary = {
            "total_events": len(delta_records),
            "price_changes": sum(1 for r in delta_records if r.get("event_type") == "PRICE_CHANGE"),
            "stockouts": sum(1 for r in delta_records if r.get("event_type") == "STOCKOUT"),
            "restocks": sum(1 for r in delta_records if r.get("event_type") == "RESTOCK"),
            "products_added": sum(1 for r in delta_records if r.get("event_type") == "PRODUCT_ADDED"),
            "products_removed": sum(1 for r in delta_records if r.get("event_type") == "PRODUCT_REMOVED"),
        }

        # Format top 5 sample events for notification preview
        preview = [
            f"[{r.get('event_type')}] {r.get('title', 'Unknown')} - {r.get('detail', '')}"
            for r in delta_records[:5]
        ]

        payload = {
            "content": f"🚨 **Catalog Telemetry Alert**: {summary['total_events']} state transitions detected.",
            "embeds": [
                {
                    "title": "Catalog Delta Summary",
                    "color": 15158332 if summary["stockouts"] > 0 else 3066993,
                    "fields": [
                        {"name": "Price Changes", "value": str(summary["price_changes"]), "inline": True},
                        {"name": "Stockouts", "value": str(summary["stockouts"]), "inline": True},
                        {"name": "Restocks", "value": str(summary["restocks"]), "inline": True},
                        {"name": "New Products", "value": str(summary["products_added"]), "inline": True},
                        {"name": "Delisted Products", "value": str(summary["products_removed"]), "inline": True},
                    ],
                    "description": "**Event Previews:**\n" + "\n".join(preview) if preview else "No events."
                }
            ]
        }
        return payload

    def dispatch(self, payload: Dict[str, Any]) -> bool:
        if not self.webhook_url:
            logger.warning("No webhook URL configured. Outputting payload to stdout.")
            print(json.dumps(payload, indent=2))
            return True

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
            logger.info("Webhook payload dispatched successfully.")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to deliver webhook payload: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="Dispatch notifications for catalog delta events.")
    parser.add_argument("--input", "-i", required=True, help="Path to delta_results.csv")
    parser.add_argument("--webhook", "-w", default=None, help="Target Discord/Slack/HTTP webhook URL")

    args = parser.parse_args()
    input_path = Path(args.input)

    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    df = pd.read_csv(input_path)
    if df.empty:
        logger.info("Delta input is empty. No notifications to send.")
        sys.exit(0)

    records = df.to_dict(orient="records")
    dispatcher = CatalogAlertDispatcher(webhook_url=args.webhook)
    payload = dispatcher.build_payload(records)
    success = dispatcher.dispatch(payload)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()