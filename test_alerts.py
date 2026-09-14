from alert_dispatcher import CatalogAlertDispatcher


def test_payload_builder_structures_correctly():
    dispatcher = CatalogAlertDispatcher()
    deltas = [
        {"event_type": "PRICE_CHANGE", "title": "Jeans", "detail": "Price drop"},
        {"event_type": "STOCKOUT", "title": "Shirt", "detail": "Out of stock"}
    ]
    payload = dispatcher.build_payload(deltas)
    
    assert "Catalog Telemetry Alert" in payload["content"]
    assert len(payload["embeds"]) == 1
    assert payload["embeds"][0]["fields"][0]["value"] == "1"  # 1 price change
    assert payload["embeds"][0]["fields"][1]["value"] == "1"  # 1 stockout