"""
E-Commerce Telemetry Alerts: Dispatcher Module
Processes catalog deltas and dispatches alerts on critical changes.
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("AlertDispatcher")


class AnomalyAlertDispatcher:
    """Evaluates catalog snapshot discrepancies and dispatches operational alerts."""

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")

    def analyze_deltas(self, delta_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Scans delta records for out-of-stock events and abnormal price fluctuations."""
        alerts = []
        if delta_df.empty:
            return alerts

        for _, row in delta_df.iterrows():
            title = row.get("title", "Unknown Product")
            sku = row.get("sku", "N/A")
            price = row.get("price", 0.0)
            available = row.get("available", True)

            # Flag stockouts
            if not available:
                alerts.append({
                    "event_type": "STOCKOUT",
                    "type": "STOCKOUT",
                    "severity": "CRITICAL",
                    "sku": sku,
                    "title": title,
                    "detail": f"Out of stock detected: {title} (SKU: {sku})"
                })

            # Flag zero-pricing or abnormal cost drops
            if float(price) <= 0.0:
                alerts.append({
                    "event_type": "PRICE_CHANGE",
                    "type": "PRICE_ANOMALY",
                    "severity": "CRITICAL",
                    "sku": sku,
                    "title": title,
                    "detail": f"Zero or negative price detected for: {title} (Price: {price})"
                })

        return alerts

    def build_payload(self, deltas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Constructs Discord-compliant embed payload matching pipeline schema."""
        price_changes = sum(
            1 for item in deltas
            if "PRICE" in str(item.get("event_type", "")).upper()
            or "PRICE" in str(item.get("type", "")).upper()
        )
        stockouts = sum(
            1 for item in deltas
            if "STOCKOUT" in str(item.get("event_type", "")).upper()
            or "STOCKOUT" in str(item.get("type", "")).upper()
        )

        return {
            "content": f"🚨 Catalog Telemetry Alert: {len(deltas)} deltas detected",
            "source": "ecom-telemetry-alerts",
            "total_alerts": len(deltas),
            "embeds": [
                {
                    "title": "Catalog Delta Breakdown",
                    "fields": [
                        {
                            "name": "Price Changes",
                            "value": str(price_changes),
                            "inline": True
                        },
                        {
                            "name": "Stockouts",
                            "value": str(stockouts),
                            "inline": True
                        }
                    ]
                }
            ]
        }

    def dispatch(self, delta_csv: str, dry_run: bool = True) -> bool:
        """Loads deltas, evaluates anomalies, and pushes telemetry payload."""
        path = Path(delta_csv)
        if not path.exists():
            logger.error("Delta file not found: %s", delta_csv)
            return False

        try:
            df = pd.read_csv(path)
        except Exception as exc:
            logger.error("Failed to parse CSV snapshot: %s", exc)
            return False

        alerts = self.analyze_deltas(df)
        logger.info("Evaluation complete: %d anomalies flagged across %d rows.", len(alerts), len(df))

        if not alerts:
            logger.info("No actionable alerts detected. Pipeline clean.")
            return True

        payload = self.build_payload(alerts)

        if dry_run or not self.webhook_url:
            logger.info("Dry-run execution enabled. Payload staged locally:\n%s", json.dumps(payload, indent=2))
            return True

        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            if resp.status_code in (200, 204):
                logger.info("Alert payload successfully dispatched via webhook.")
                return True
            logger.error("Webhook endpoint rejected payload. Status: %d", resp.status_code)
            return False
        except requests.RequestException as exc:
            logger.error("Failed to transmit telemetry to webhook: %s", exc)
            return False


# Module-level alias for test runner compatibility
CatalogAlertDispatcher = AnomalyAlertDispatcher


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="E-Commerce Catalog Anomaly Alert Dispatcher")
    parser.add_argument("--deltas", required=True, type=str, help="Path to delta or snapshot CSV")
    parser.add_argument("--webhook", default=None, type=str, help="Webhook destination URL")
    parser.add_argument("--send", action="store_true", help="Execute live dispatch instead of dry-run")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dispatcher = AnomalyAlertDispatcher(webhook_url=args.webhook)
    success = dispatcher.dispatch(delta_csv=args.deltas, dry_run=not args.send)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()