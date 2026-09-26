from decimal import Decimal
from starlette.testclient import TestClient


def create_sample_trip(client: TestClient) -> tuple[str, list[dict]]:
    payload = {
        "name": "Mountain Trek",
        "destination": "Manali",
        "start_date": "2026-11-01",
        "end_date": "2026-11-05",
        "members": [{"name": "Alice"}, {"name": "Bob"}, {"name": "Charlie"}],
    }
    trip = client.post("/api/v1/trips", json=payload).json()["data"]
    return trip["id"], trip["members"]


def test_create_expense_exact_split(client: TestClient):
    trip_id, members = create_sample_trip(client)
    alice_id = members[0]["id"]
    bob_id = members[1]["id"]
    charlie_id = members[2]["id"]

    expense_payload = {
        "title": "Dinner Buffet",
        "amount": "100.00",
        "category": "Food",
        "paid_by": alice_id,
        "shared_by": [alice_id, bob_id, charlie_id],
        "description": "Welcome dinner",
    }

    res = client.post(f"/api/v1/trips/{trip_id}/expenses", json=expense_payload)
    assert res.status_code == 201
    data = res.json()["data"]

    assert data["title"] == "Dinner Buffet"
    assert data["amount"] == "100.00"
    assert data["category"] == "Food"

    # Verify split shares sum exactly to 100.00
    shares = data["split_shares"]
    assert len(shares) == 3
    shares_sum = sum(Decimal(s["share"]) for s in shares)
    assert shares_sum == Decimal("100.00")
    # First share should have the cent remainder
    assert Decimal(shares[0]["share"]) == Decimal("33.34")
    assert Decimal(shares[1]["share"]) == Decimal("33.33")
    assert Decimal(shares[2]["share"]) == Decimal("33.33")


def test_expense_invalid_members(client: TestClient):
    trip_id, members = create_sample_trip(client)
    alice_id = members[0]["id"]

    # Invalid payer
    res_bad_payer = client.post(
        f"/api/v1/trips/{trip_id}/expenses",
        json={
            "title": "Taxi",
            "amount": "50.00",
            "category": "Travel",
            "paid_by": "unknown_id_999",
            "shared_by": [alice_id],
        },
    )
    assert res_bad_payer.status_code == 400
    assert res_bad_payer.json()["error"]["code"] == "INVALID_MEMBER"

    # Invalid shared member
    res_bad_sharer = client.post(
        f"/api/v1/trips/{trip_id}/expenses",
        json={
            "title": "Snacks",
            "amount": "20.00",
            "category": "Food",
            "paid_by": alice_id,
            "shared_by": [alice_id, "ghost_member"],
        },
    )
    assert res_bad_sharer.status_code == 400
    assert res_bad_sharer.json()["error"]["code"] == "INVALID_MEMBER"


def test_update_expense_recalculates_splits(client: TestClient):
    trip_id, members = create_sample_trip(client)
    alice_id = members[0]["id"]
    bob_id = members[1]["id"]

    create_res = client.post(
        f"/api/v1/trips/{trip_id}/expenses",
        json={
            "title": "Hotel Room",
            "amount": "100.00",
            "category": "Accommodation",
            "paid_by": alice_id,
            "shared_by": [alice_id, bob_id],
        },
    )
    exp_id = create_res.json()["data"]["id"]

    # Update amount to 150.00
    update_res = client.put(
        f"/api/v1/trips/{trip_id}/expenses/{exp_id}",
        json={"amount": "150.00"},
    )
    assert update_res.status_code == 200
    updated_exp = update_res.json()["data"]
    assert updated_exp["amount"] == "150.00"
    assert len(updated_exp["split_shares"]) == 2
    for s in updated_exp["split_shares"]:
        assert Decimal(s["share"]) == Decimal("75.00")


def test_cannot_remove_member_with_expenses(client: TestClient):
    trip_id, members = create_sample_trip(client)
    alice_id = members[0]["id"]
    bob_id = members[1]["id"]

    client.post(
        f"/api/v1/trips/{trip_id}/expenses",
        json={
            "title": "Lunch",
            "amount": "60.00",
            "category": "Food",
            "paid_by": alice_id,
            "shared_by": [alice_id, bob_id],
        },
    )

    # Attempt to remove payer Alice
    rem_alice = client.delete(f"/api/v1/trips/{trip_id}/members/{alice_id}")
    assert rem_alice.status_code == 400

    # Attempt to remove sharer Bob
    rem_bob = client.delete(f"/api/v1/trips/{trip_id}/members/{bob_id}")
    assert rem_bob.status_code == 400


def test_list_expenses_with_filtering_and_pagination(client: TestClient):
    trip_id, members = create_sample_trip(client)
    alice_id = members[0]["id"]

    # Add 3 expenses in different categories
    client.post(
        f"/api/v1/trips/{trip_id}/expenses",
        json={"title": "Burgers", "amount": "30.00", "category": "Food", "paid_by": alice_id, "shared_by": [alice_id]},
    )
    client.post(
        f"/api/v1/trips/{trip_id}/expenses",
        json={"title": "Subway Pass", "amount": "15.00", "category": "Travel", "paid_by": alice_id, "shared_by": [alice_id]},
    )
    client.post(
        f"/api/v1/trips/{trip_id}/expenses",
        json={"title": "Pizza", "amount": "45.00", "category": "Food", "paid_by": alice_id, "shared_by": [alice_id]},
    )

    # Filter category Food
    food_res = client.get(f"/api/v1/trips/{trip_id}/expenses?category=Food")
    assert food_res.status_code == 200
    food_data = food_res.json()["data"]
    assert food_data["pagination"]["total"] == 2
    for item in food_data["items"]:
        assert item["category"] == "Food"

    # Pagination: limit=1
    page1 = client.get(f"/api/v1/trips/{trip_id}/expenses?limit=1&page=1")
    assert page1.status_code == 200
    assert len(page1.json()["data"]["items"]) == 1
    assert page1.json()["data"]["pagination"]["pages"] == 3
