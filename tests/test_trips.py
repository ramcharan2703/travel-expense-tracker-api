from starlette.testclient import TestClient


def test_create_and_get_trip(client: TestClient):
    payload = {
        "name": "Paris Holiday",
        "destination": "Paris, France",
        "start_date": "2026-10-01",
        "end_date": "2026-10-07",
        "members": [
            {"name": "Alice", "email": "alice@example.com"},
            {"name": "Bob"},
        ],
    }

    res = client.post("/api/v1/trips", json=payload)
    assert res.status_code == 201
    body = res.json()
    assert body["success"] is True
    trip_data = body["data"]
    assert trip_data["name"] == "Paris Holiday"
    assert len(trip_data["members"]) == 2
    trip_id = trip_data["id"]

    # Get single trip
    res_get = client.get(f"/api/v1/trips/{trip_id}")
    assert res_get.status_code == 200
    assert res_get.json()["data"]["id"] == trip_id


def test_create_trip_invalid_dates(client: TestClient):
    payload = {
        "name": "Goa Retreat",
        "destination": "Goa, India",
        "start_date": "2026-10-10",
        "end_date": "2026-10-05",  # earlier than start date
        "members": [{"name": "Charlie"}],
    }
    res = client.post("/api/v1/trips", json=payload)
    assert res.status_code == 422


def test_create_trip_duplicate_members(client: TestClient):
    payload = {
        "name": "Road Trip",
        "destination": "Leh Ladakh",
        "start_date": "2026-11-01",
        "end_date": "2026-11-10",
        "members": [{"name": "David"}, {"name": "david"}],
    }
    res = client.post("/api/v1/trips", json=payload)
    assert res.status_code == 422


def test_update_trip(client: TestClient):
    # Create trip
    payload = {
        "name": "Original Name",
        "destination": "Original Place",
        "start_date": "2026-10-01",
        "end_date": "2026-10-05",
        "members": [{"name": "Alice"}],
    }
    trip_id = client.post("/api/v1/trips", json=payload).json()["data"]["id"]

    # Update name and destination
    update_res = client.put(f"/api/v1/trips/{trip_id}", json={"name": "Updated Name", "destination": "New Place"})
    assert update_res.status_code == 200
    assert update_res.json()["data"]["name"] == "Updated Name"
    assert update_res.json()["data"]["destination"] == "New Place"


def test_add_and_remove_member(client: TestClient):
    payload = {
        "name": "Camping",
        "destination": "Rishikesh",
        "start_date": "2026-12-01",
        "end_date": "2026-12-05",
        "members": [{"name": "Alice"}, {"name": "Bob"}],
    }
    trip = client.post("/api/v1/trips", json=payload).json()["data"]
    trip_id = trip["id"]
    bob_id = next(m["id"] for m in trip["members"] if m["name"] == "Bob")

    # Add member Charlie
    add_res = client.post(f"/api/v1/trips/{trip_id}/members", json={"name": "Charlie"})
    assert add_res.status_code == 200
    assert len(add_res.json()["data"]["members"]) == 3

    # Reject duplicate member name
    dup_res = client.post(f"/api/v1/trips/{trip_id}/members", json={"name": "charlie"})
    assert dup_res.status_code == 400

    # Remove Bob
    rem_res = client.delete(f"/api/v1/trips/{trip_id}/members/{bob_id}")
    assert rem_res.status_code == 200
    assert len(rem_res.json()["data"]["members"]) == 2


def test_delete_trip_cascades(client: TestClient):
    payload = {
        "name": "Tokyo Trip",
        "destination": "Tokyo, Japan",
        "start_date": "2026-10-01",
        "end_date": "2026-10-05",
        "members": [{"name": "Ken"}],
    }
    trip_id = client.post("/api/v1/trips", json=payload).json()["data"]["id"]

    del_res = client.delete(f"/api/v1/trips/{trip_id}")
    assert del_res.status_code == 200
    assert del_res.json()["data"]["deleted"] is True

    # Trip should now return 404
    get_res = client.get(f"/api/v1/trips/{trip_id}")
    assert get_res.status_code == 404
