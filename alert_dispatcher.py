"""
Alert Dispatcher
Consumes delta anomalies, bundles them into rate-limit-safe 
webhook digests, and delivers structured Discord/Slack embeds.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("AlertDispatcher")


class AnomalyAlertDispatcher:
    def __init__(self, webhook_url: str | None = None):
        # Fall back to system environment variable if CLI flag is absent
        self.webhook_url = webhook_url or os.getenv("ALERT_WEBHOOK_URL") or os.getenv("DISCORD_WEBHOOK_URL")

    def _sanitize_val(self, val: Any, fallback: str = "N/A") -> str:
        """Sanitize NaN, None, or empty float values from pandas rows."""
        if pd.isna(val) or val is None or str(val).strip().lower() in ("nan", "none", ""):
            return fallback
        return str(val)

    def load_deltas(self, delta_csv: str) -> list[dict[str, Any]]:
        path = Path(delta_csv)
        if not path.exists():
            logger.warning(f"No delta file found at: {delta_csv}")
            return []

        try:
            df = pd.read_csv(path)
        except Exception as e:
            logger.error(f"Failed to parse delta CSV: {e}")
            return []

        if df.empty:
            return []

        events = []
        for _, row in df.iterrows():
            events.append({
                "event_type": self._sanitize_val(row.get("event_type"), "UNKNOWN").upper(),
                "variant_id": self._sanitize_val(row.get("variant_id")),
                "title": self._sanitize_val(row.get("title")),
                "sku": self._sanitize_val(row.get("sku")),
                "price_delta": self._sanitize_val(row.get("price_delta"), "0.00"),
                "detail": self._sanitize_val(row.get("detail"), "No details provided."),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        return events

    def build_embed(self, event: dict[str, Any]) -> dict[str, Any]:
        """Format individual event into a Discord/Slack webhook embed."""
        is_critical = event["event_type"] in ("STOCKOUT", "PRODUCT_REMOVED")
        severity = "CRITICAL" if is_critical else "HIGH"
        color = 0xE02424 if is_critical else 0xF59E0B  # Red vs Amber

        return {
            "title": f"[{severity}] {event['event_type']}",
            "color": color,
            "fields": [
                {"name": "Item", "value": event["title"], "inline": True},
                {"name": "SKU", "value": f"`{event['sku']}`", "inline": True},
                {"name": "Delta", "value": f"`{event['price_delta']}`", "inline": True},
                {"name": "Detail", "value": event["detail"], "inline": False},
            ],
            "footer": {"text": f"Telemetry Pipeline • {event['timestamp']}"}
        }

    def send_batch(self, embeds: list[dict[str, Any]]) -> bool:
        """Transmit batched embeds (max 10 per Discord API spec)."""
        if not self.webhook_url:
            logger.warning("No webhook URL configured — skipping HTTP dispatch.")
            return False

        payload = {"embeds": embeds}
        try:
            resp = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            resp.raise_for_status()
            logger.info(f"✓ Dispatched batch of {len(embeds)} embeds successfully")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Webhook dispatch failed: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response status: {e.response.status_code} | Body: {e.response.text}")
            return False

    def dispatch(self, delta_csv: str, dry_run: bool = True) -> bool:
        events = self.load_deltas(delta_csv)
        if not events:
            logger.info("No anomalies found to dispatch.")
            return True

        logger.info(f"Processing {len(events)} delta event(s)...")

        all_embeds = [self.build_embed(e) for e in events]
        dispatch_success = True

        # Discord allows up to 10 embeds per single POST request
        batch_size = 10
        for i in range(0, len(all_embeds), batch_size):
            batch = all_embeds[i:i + batch_size]
            if dry_run:
                logger.info(f"[DRY-RUN] Would dispatch batch {i // batch_size + 1} ({len(batch)} alerts)")
            else:
                success = self.send_batch(batch)
                if not success:
                    dispatch_success = False

        # Persist audit record locally
        output_path = Path("last_dispatch.json")
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(all_embeds, f, indent=2)
            logger.info(f"Audit log saved to {output_path.resolve()}")
        except Exception as e:
            logger.warning(f"Could not write dispatch cache: {e}")

        return dispatch_success


def main():
    parser = argparse.ArgumentParser(description="Dispatch delta telemetry alerts")
    parser.add_argument("--deltas", default="delta_results.csv", help="Path to input delta CSV")
    parser.add_argument("--webhook", default=None, help="Webhook URL (or set ALERT_WEBHOOK_URL env var)")
    parser.add_argument("--send", action="store_true", help="Execute live network delivery (default is dry-run)")
    args = parser.parse_args()

    dispatcher = AnomalyAlertDispatcher(webhook_url=args.webhook)
    success = dispatcher.dispatch(delta_csv=args.deltas, dry_run=not args.send)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()