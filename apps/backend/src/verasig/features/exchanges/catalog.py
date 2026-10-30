EXCHANGE_CATALOG = [
    {
        "id": "bybit",
        "name": "Bybit",
        "tint": "var(--viz-4)",
        "brand": "#F7A600",
        "initials": "BY",
        "status": "available",
        "kind": "Derivatives · Spot",
    }
]


def catalog_item(exchange_id: str) -> dict | None:
    return next(
        (exchange for exchange in EXCHANGE_CATALOG if exchange["id"] == exchange_id),
        None,
    )
