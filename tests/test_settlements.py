from decimal import Decimal
from starlette.testclient import TestClient


def test_financial_summary_and_debt_settlement(client: TestClient):
    # Create trip with Alice, Bob, and Charlie
    trip_payload = {
        "name": "Euro Trip",
        "destination": "Amsterdam",
        "start_date": "2026-10-01",
        "end_date": "2026-10-08",
        "members": [{"name": "Alice"}, {"name": "Bob"}, {"name": "Charlie"}],
    }
    trip_res = client.post("/api/v1/trips", json=trip_payload)
    trip = trip_res.json()["data"]
    trip_id = trip["id"]
    alice_id = next(m["id"] for m in trip["members"] if m["name"] == "Alice")
    bob_id = next(m["id"] for m in trip["members"] if m["name"] == "Bob")
    charlie_id = next(m["id"] for m in trip["members"] if m["name"] == "Charlie")

    # Expense 1: Alice pays 120.00 for Alice, Bob, Charlie (Food)
    client.post(
        f"/api/v1/trips/{trip_id}/expenses",
        json={
            "title": "Fancy Dinner",
            "amount": "120.00",
            "category": "Food",
            "paid_by": alice_id,
            "shared_by": [alice_id, bob_id, charlie_id],
        },
    )

    # Expense 2: Bob pays 30.00 for Bob, Charlie (Travel)
    client.post(
        f"/api/v1/trips/{trip_id}/expenses",
        json={
            "title": "Train Tickets",
            "amount": "30.00",
            "category": "Travel",
            "paid_by": bob_id,
            "shared_by": [bob_id, charlie_id],
        },
    )

    # 1. Test Summary Endpoint
    summary_res = client.get(f"/api/v1/trips/{trip_id}/summary")
    assert summary_res.status_code == 200
    summary = summary_res.json()["data"]

    assert Decimal(summary["total_trip_expenses"]) == Decimal("150.00")
    assert summary["total_expenses_count"] == 2

    # Check category breakdown: Food (120/150 = 80%), Travel (30/150 = 20%)
    categories = {c["category"]: c for c in summary["category_breakdown"]}
    assert Decimal(categories["Food"]["total_amount"]) == Decimal("120.00")
    assert Decimal(categories["Food"]["percentage"]) == Decimal("80.00")
    assert Decimal(categories["Travel"]["total_amount"]) == Decimal("30.00")
    assert Decimal(categories["Travel"]["percentage"]) == Decimal("20.00")

    # Check members balances:
    # Alice: paid 120, share 40 -> balance +80 (receives 80, owes 0)
    # Bob: paid 30, share 55 -> balance -25 (owes 25, receives 0)
    # Charlie: paid 0, share 55 -> balance -55 (owes 55, receives 0)
    members_by_id = {m["member_id"]: m for m in summary["members_summary"]}
    assert Decimal(members_by_id[alice_id]["total_paid"]) == Decimal("120.00")
    assert Decimal(members_by_id[alice_id]["total_share"]) == Decimal("40.00")
    assert Decimal(members_by_id[alice_id]["balance"]) == Decimal("80.00")
    assert Decimal(members_by_id[alice_id]["receives"]) == Decimal("80.00")

    assert Decimal(members_by_id[bob_id]["total_paid"]) == Decimal("30.00")
    assert Decimal(members_by_id[bob_id]["total_share"]) == Decimal("55.00")
    assert Decimal(members_by_id[bob_id]["balance"]) == Decimal("-25.00")
    assert Decimal(members_by_id[bob_id]["owes"]) == Decimal("25.00")

    assert Decimal(members_by_id[charlie_id]["balance"]) == Decimal("-55.00")
    assert Decimal(members_by_id[charlie_id]["owes"]) == Decimal("55.00")

    # 2. Test Settlement Endpoint
    settlement_res = client.get(f"/api/v1/trips/{trip_id}/settlement")
    assert settlement_res.status_code == 200
    settlement = settlement_res.json()["data"]

    # Exactly 2 transactions needed: Charlie pays Alice 55, Bob pays Alice 25
    assert settlement["total_transactions"] == 2
    txs = settlement["transactions"]

    total_transferred = sum(Decimal(t["amount"]) for t in txs)
    assert total_transferred == Decimal("80.00")

    all_creditors = {t["creditor_name"] for t in txs}
    all_debtors = {t["debtor_name"] for t in txs}
    assert all_creditors == {"Alice"}
    assert all_debtors == {"Charlie", "Bob"}
