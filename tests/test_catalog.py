async def test_register_login_and_me_flow(client):
    resp = await client.post(
        "/auth/register",
        json={"email": "a@b.com", "password": "secret-pass-123", "full_name": "A B"},
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == "a@b.com"

    resp = await client.post("/auth/login", json={"email": "a@b.com", "password": "secret-pass-123"})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


async def test_register_duplicate_email_conflict(client):
    body = {"email": "a@b.com", "password": "secret-pass-123", "full_name": "A B"}
    assert (await client.post("/auth/register", json=body)).status_code == 201
    assert (await client.post("/auth/register", json=body)).status_code == 409


async def test_login_wrong_password_rejected(client):
    await client.post(
        "/auth/register",
        json={"email": "a@b.com", "password": "secret-pass-123", "full_name": "A B"},
    )
    resp = await client.post("/auth/login", json={"email": "a@b.com", "password": "wrong-password"})
    assert resp.status_code == 401


async def test_create_laboratory_requires_auth(client):
    resp = await client.post(
        "/laboratories", json={"name": "X Lab", "city": "Dehradun", "address": "Main St"}
    )
    assert resp.status_code == 401


async def test_catalog_crud_and_filters(client, auth_headers):
    lab = (
        await client.post(
            "/laboratories",
            json={"name": "City Lab", "city": "Dehradun", "address": "Rajpur Road"},
            headers=auth_headers,
        )
    ).json()

    for code, name in [("CBC", "Complete Blood Count"), ("LFT", "Liver Function Test")]:
        resp = await client.post(
            f"/laboratories/{lab['id']}/tests",
            json={"code": code, "name": name, "price": "499.00", "sample_type": "Blood"},
            headers=auth_headers,
        )
        assert resp.status_code == 201

    # duplicate code within the same lab → DB unique constraint → 409
    resp = await client.post(
        f"/laboratories/{lab['id']}/tests",
        json={"code": "CBC", "name": "Dup", "price": "100.00", "sample_type": "Blood"},
        headers=auth_headers,
    )
    assert resp.status_code == 409

    resp = await client.get(f"/laboratories/{lab['id']}/tests", params={"q": "liver"})
    names = [t["name"] for t in resp.json()]
    assert names == ["Liver Function Test"]

    resp = await client.get("/laboratories", params={"city": "dehradun"})
    assert len(resp.json()) == 1
