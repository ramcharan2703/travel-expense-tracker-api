from decimal import Decimal
from starlette.testclient import TestClient


def test_root_and_health_endpoints(client: TestClient):
    # Root endpoint
    root_res = client.get("/")
    assert root_res.status_code == 200
    root_data = root_res.json()
    assert root_data["status"] == "online"
    assert "api_v1" in root_data

    # Health endpoint
    health_res = client.get("/health")
    assert health_res.status_code == 200
    health_data = health_res.json()
    assert health_data["status"] == "healthy"
    assert health_data["database"]["connected"] is True


def test_empty_trip_summary_and_settlement(client: TestClient):
    trip_payload = {
        "name": "Empty Trip",
        "destination": "Nowhere",
        "start_date": "2026-10-01",
        "end_date": "2026-10-05",
        "members": [{"name": "Solo Traveler"}],
    }
    trip_id = client.post("/api/v1/trips", json=trip_payload).json()["data"]["id"]

    # Summary of trip with 0 expenses
    sum_res = client.get(f"/api/v1/trips/{trip_id}/summary")
    assert sum_res.status_code == 200
    sum_data = sum_res.json()["data"]
    assert Decimal(sum_data["total_trip_expenses"]) == Decimal("0.00")
    assert sum_data["total_expenses_count"] == 0
    assert len(sum_data["category_breakdown"]) == 0
    assert len(sum_data["members_summary"]) == 1
    assert Decimal(sum_data["members_summary"][0]["balance"]) == Decimal("0.00")

    # Settlement of trip with 0 expenses
    settle_res = client.get(f"/api/v1/trips/{trip_id}/settlement")
    assert settle_res.status_code == 200
    settle_data = settle_res.json()["data"]
    assert settle_data["total_transactions"] == 0
    assert len(settle_data["transactions"]) == 0


def test_complex_multi_member_settlement(client: TestClient):
    # 4 members: Alice, Bob, Charlie, Dana
    trip_payload = {
        "name": "Skiing Trip",
        "destination": "Swiss Alps",
        "start_date": "2026-12-10",
        "end_date": "2026-12-17",
        "members": [
            {"name": "Alice"},
            {"name": "Bob"},
            {"name": "Charlie"},
            {"name": "Dana"},
        ],
    }
    trip = client.post("/api/v1/trips", json=trip_payload).json()["data"]
    trip_id = trip["id"]
    m = {member["name"]: member["id"] for member in trip["members"]}

    # Alice pays 200.00 for all 4 (each owes 50.00)
    client.post(
        f"/api/v1/trips/{trip_id}/expenses",
        json={
            "title": "Chalet Booking",
            "amount": "200.00",
            "category": "Accommodation",
            "paid_by": m["Alice"],
            "shared_by": [m["Alice"], m["Bob"], m["Charlie"], m["Dana"]],
        },
    )

    # Bob pays 80.00 for Charlie and Dana (each owes 40.00)
    client.post(
        f"/api/v1/trips/{trip_id}/expenses",
        json={
            "title": "Ski Passes",
            "amount": "80.00",
            "category": "Entertainment",
            "paid_by": m["Bob"],
            "shared_by": [m["Charlie"], m["Dana"]],
        },
    )

    # Dana pays 40.00 for Alice and Bob (each owes 20.00)
    client.post(
        f"/api/v1/trips/{trip_id}/expenses",
        json={
            "title": "Groceries",
            "amount": "40.00",
            "category": "Food",
            "paid_by": m["Dana"],
            "shared_by": [m["Alice"], m["Bob"]],
        },
    )

    # Balances:
    # Alice: Paid 200. Share: 50 + 20 = 70. Net: +130 (receives 130)
    # Bob: Paid 80. Share: 50 + 20 = 70. Net: +10 (receives 10)
    # Charlie: Paid 0. Share: 50 + 40 = 90. Net: -90 (owes 90)
    # Dana: Paid 40. Share: 50 + 40 = 90. Net: -50 (owes 50)
    # Sum of debts = 90 + 50 = 140. Sum of credits = 130 + 10 = 140.

    settle_res = client.get(f"/api/v1/trips/{trip_id}/settlement")
    assert settle_res.status_code == 200
    settle_data = settle_res.json()["data"]

    txs = settle_data["transactions"]
    total_amount = sum(Decimal(t["amount"]) for t in txs)
    assert total_amount == Decimal("140.00")

    # Minimized: should be at most 3 transactions (N-1 = 3)
    assert len(txs) <= 3


def test_sorting_and_amount_filters(client: TestClient):
    trip_payload = {
        "name": "Beach Trip",
        "destination": "Goa",
        "start_date": "2026-10-01",
        "end_date": "2026-10-05",
        "members": [{"name": "A"}],
    }
    trip_id = client.post("/api/v1/trips", json=trip_payload).json()["data"]["id"]
    a_id = client.get(f"/api/v1/trips/{trip_id}").json()["data"]["members"][0]["id"]

    client.post(
        f"/api/v1/trips/{trip_id}/expenses",
        json={"title": "Small Snack", "amount": "10.00", "paid_by": a_id, "shared_by": [a_id]},
    )
    client.post(
        f"/api/v1/trips/{trip_id}/expenses",
        json={"title": "Medium Meal", "amount": "50.00", "paid_by": a_id, "shared_by": [a_id]},
    )
    client.post(
        f"/api/v1/trips/{trip_id}/expenses",
        json={"title": "Big Dinner", "amount": "120.00", "paid_by": a_id, "shared_by": [a_id]},
    )

    # Sort by amount desc
    desc_res = client.get(f"/api/v1/trips/{trip_id}/expenses?sort_by=amount&sort_order=desc")
    items = desc_res.json()["data"]["items"]
    assert Decimal(items[0]["amount"]) == Decimal("120.00")
    assert Decimal(items[1]["amount"]) == Decimal("50.00")
    assert Decimal(items[2]["amount"]) == Decimal("10.00")

    # Sort by amount asc
    asc_res = client.get(f"/api/v1/trips/{trip_id}/expenses?sort_by=amount&sort_order=asc")
    items_asc = asc_res.json()["data"]["items"]
    assert Decimal(items_asc[0]["amount"]) == Decimal("10.00")
    assert Decimal(items_asc[2]["amount"]) == Decimal("120.00")
