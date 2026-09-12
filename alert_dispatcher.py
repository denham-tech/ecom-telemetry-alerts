import json
import sqlite3
from datetime import datetime
import pandas as pd

class AnomalyAlertDispatcher:
    def __init__(self, db_path: str = "delta_warehouse.db"):
        self.db_path = db_path

    def fetch_unreported_anomalies(self, limit: int = 5) -> list:
        """
        Extracts recent price drops and stockouts for priority dispatch.
        Simulates an ingestion query against historical delta tables.
        """
        # Structured operational test payload
        simulated_events = [
            {
                "event_type": "PRICE_DROP",
                "severity": "HIGH",
                "sku": "CRW-BLK-M",
                "item": "Core Crewneck - Black",
                "previous_price": 95.0,
                "current_price": 85.0,
                "variance_pct": -10.53,
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "event_type": "STOCKOUT",
                "severity": "CRITICAL",
                "sku": "DNM-RAW-32",
                "item": "Denim Trouser - Raw",
                "previous_state": "IN_STOCK",
                "current_state": "OUT_OF_STOCK",
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
        return simulated_events

    def format_webhook_payload(self, event: dict) -> dict:
        """
        Constructs a structured, production-standard JSON webhook card.
        Compatible with Slack, Discord, or enterprise CRM webhook endpoints.
        """
        color = 0xE02424 if event["severity"] == "CRITICAL" else 0xF59E0B
        
        payload = {
            "channel": "#market-telemetry",
            "username": "DeltaGuard Engine",
            "embeds": [
                {
                    "title": f"[{event['severity']}] {event['event_type']} Detected",
                    "color": color,
                    "fields": [
                        {"name": "Item", "value": event["item"], "inline": True},
                        {"name": "SKU", "value": f"`{event['sku']}`", "inline": True},
                    ],
                    "footer": {"text": f"Telemetry Sync • {event['timestamp']}"}
                }
            ]
        }

        if event["event_type"] == "PRICE_DROP":
            payload["embeds"][0]["fields"].append(
                {"name": "Price Shift", "value": f"${event['previous_price']} → **${event['current_price']}** ({event['variance_pct']}%)", "inline": False}
            )
        elif event["event_type"] == "STOCKOUT":
            payload["embeds"][0]["fields"].append(
                {"name": "Inventory Event", "value": "Status transitioned to **OUT_OF_STOCK**", "inline": False}
            )

        return payload

    def dispatch_simulation(self):
        """
        Validates pipeline formatting and generates client-facing JSON deliverable.
        """
        events = self.fetch_unreported_anomalies()
        dispatched_logs = []

        for ev in events:
            card = self.format_webhook_payload(ev)
            dispatched_logs.append(card)
            print(f"[✓] Formatted {ev['severity']} alert for SKU: {ev['sku']}")

        # Persist output artifact
        with open("webhook_payload_sample.json", "w") as f:
            json.dump(dispatched_logs, f, indent=2)

        print("[✓] Generated 'webhook_payload_sample.json' for integration audits.")

if __name__ == "__main__":
    dispatcher = AnomalyAlertDispatcher()
    dispatcher.dispatch_simulation()