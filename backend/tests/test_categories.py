def make_category(client, name="Food", monthly_limit=300):
    return client.post("/api/v1/categories", json={"name": name, "monthly_limit": monthly_limit})


def test_create_and_list(client):
    response = make_category(client)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Food"
    assert float(body["monthly_limit"]) == 300

    listed = client.get("/api/v1/categories").json()
    assert [c["name"] for c in listed] == ["Food"]


def test_limit_is_optional(client):
    response = client.post("/api/v1/categories", json={"name": "Misc"})
    assert response.status_code == 201
    assert response.json()["monthly_limit"] is None


def test_duplicate_name_conflicts(client):
    make_category(client)
    assert make_category(client).status_code == 409


def test_name_is_trimmed_before_duplicate_check(client):
    make_category(client, "Food")
    assert make_category(client, "  Food  ").status_code == 409


def test_invalid_limit_rejected(client):
    assert make_category(client, monthly_limit=-5).status_code == 422
    assert make_category(client, monthly_limit=0).status_code == 422


def test_update_can_clear_limit(client):
    category_id = make_category(client).json()["id"]
    response = client.put(
        f"/api/v1/categories/{category_id}", json={"name": "Groceries", "monthly_limit": None}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Groceries"
    assert response.json()["monthly_limit"] is None


def test_update_to_existing_name_conflicts(client):
    make_category(client, "Food")
    other_id = make_category(client, "Travel").json()["id"]
    response = client.put(f"/api/v1/categories/{other_id}", json={"name": "Food"})
    assert response.status_code == 409


def test_missing_category_is_404(client):
    assert client.get("/api/v1/categories/999").status_code == 404
    assert client.delete("/api/v1/categories/999").status_code == 404


def test_delete_category(client):
    category_id = make_category(client).json()["id"]
    assert client.delete(f"/api/v1/categories/{category_id}").status_code == 204
    assert client.get(f"/api/v1/categories/{category_id}").status_code == 404


def test_cannot_delete_category_with_expenses(client):
    category_id = make_category(client).json()["id"]
    client.post(
        "/api/v1/expenses",
        json={"amount": 10, "expense_date": "2026-09-01", "category_id": category_id},
    )
    response = client.delete(f"/api/v1/categories/{category_id}")
    assert response.status_code == 409
    assert client.get(f"/api/v1/categories/{category_id}").status_code == 200
