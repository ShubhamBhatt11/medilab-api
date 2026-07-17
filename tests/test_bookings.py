"""Booking state machine: capacity enforcement, cancellation, cross-lab guard."""


async def _setup_lab_test_slot(client, headers, capacity=2):
    lab = (
        await client.post(
            "/laboratories",
            json={"name": "City Lab", "city": "Dehradun", "address": "Rajpur Road"},
            headers=headers,
        )
    ).json()
    test = (
        await client.post(
            f"/laboratories/{lab['id']}/tests",
            json={"code": "CBC", "name": "Complete Blood Count", "price": "499.00", "sample_type": "Blood"},
            headers=headers,
        )
    ).json()
    slot = (
        await client.post(
            f"/laboratories/{lab['id']}/slots",
            json={"starts_at": "2026-08-01T09:00:00Z", "capacity": capacity},
            headers=headers,
        )
    ).json()
    return lab, test, slot


async def test_booking_fills_slot_to_capacity_then_409(client, auth_headers):
    _, test, slot = await _setup_lab_test_slot(client, auth_headers, capacity=2)
    body = {"slot_id": slot["id"], "lab_test_id": test["id"], "collection_mode": "home"}

    first = await client.post("/bookings", json=body, headers=auth_headers)
    assert first.status_code == 201
    assert first.json()["status"] == "confirmed"

    assert (await client.post("/bookings", json=body, headers=auth_headers)).status_code == 201

    # capacity=2 exhausted — third booking must be rejected, not overbooked
    third = await client.post("/bookings", json=body, headers=auth_headers)
    assert third.status_code == 409


async def test_cancel_frees_capacity_and_is_idempotent_guarded(client, auth_headers):
    lab, test, slot = await _setup_lab_test_slot(client, auth_headers, capacity=1)
    body = {"slot_id": slot["id"], "lab_test_id": test["id"], "collection_mode": "lab"}

    booking = (await client.post("/bookings", json=body, headers=auth_headers)).json()
    assert (await client.post("/bookings", json=body, headers=auth_headers)).status_code == 409

    resp = await client.post(f"/bookings/{booking['id']}/cancel", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"

    # cancelling twice is a state-machine violation
    resp = await client.post(f"/bookings/{booking['id']}/cancel", headers=auth_headers)
    assert resp.status_code == 409

    # capacity was released — booking works again
    assert (await client.post("/bookings", json=body, headers=auth_headers)).status_code == 201

    slots = (await client.get(f"/laboratories/{lab['id']}/slots")).json()
    assert slots[0]["booked_count"] == 1


async def test_cannot_book_test_from_another_lab(client, auth_headers):
    _, _, slot = await _setup_lab_test_slot(client, auth_headers)

    other_lab = (
        await client.post(
            "/laboratories",
            json={"name": "Other Lab", "city": "Delhi", "address": "CP"},
            headers=auth_headers,
        )
    ).json()
    other_test = (
        await client.post(
            f"/laboratories/{other_lab['id']}/tests",
            json={"code": "TSH", "name": "Thyroid Panel", "price": "299.00", "sample_type": "Blood"},
            headers=auth_headers,
        )
    ).json()

    resp = await client.post(
        "/bookings",
        json={"slot_id": slot["id"], "lab_test_id": other_test["id"], "collection_mode": "home"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_my_bookings_requires_auth(client):
    assert (await client.get("/bookings/me")).status_code == 401
