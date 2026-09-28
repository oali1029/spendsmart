import pytest


@pytest.fixture
def food_id(client):
    return client.post("/api/v1/categories", json={"name": "Food"}).json()["id"]


@pytest.fixture
def travel_id(client):
    return client.post("/api/v1/categories", json={"name": "Travel"}).json()["id"]


def add_expense(client, category_id, amount=10, expense_date="2026-09-15", description=None):
    return client.post(
        "/api/v1/expenses",
        json={
            "amount": amount,
            "expense_date": expense_date,
            "category_id": category_id,
            "description": description,
        },
    )


def test_create_and_get(client, food_id):
    response = add_expense(client, food_id, amount="12.50", description="Lunch")
    assert response.status_code == 201
    body = response.json()
    assert float(body["amount"]) == 12.50
    assert body["category_id"] == food_id

    fetched = client.get(f"/api/v1/expenses/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["description"] == "Lunch"


def test_unknown_category_is_404(client):
    assert add_expense(client, 999).status_code == 404


@pytest.mark.parametrize("amount", [0, -1, "12.345"])
def test_invalid_amount_rejected(client, food_id, amount):
    assert add_expense(client, food_id, amount=amount).status_code == 422


def test_invalid_date_rejected(client, food_id):
    assert add_expense(client, food_id, expense_date="not-a-date").status_code == 422


def test_update_expense_including_category(client, food_id, travel_id):
    expense_id = add_expense(client, food_id).json()["id"]
    response = client.put(
        f"/api/v1/expenses/{expense_id}",
        json={"amount": 99, "expense_date": "2026-09-20", "category_id": travel_id},
    )
    assert response.status_code == 200
    assert response.json()["category_id"] == travel_id
    assert float(response.json()["amount"]) == 99


def test_update_to_unknown_category_is_404(client, food_id):
    expense_id = add_expense(client, food_id).json()["id"]
    response = client.put(
        f"/api/v1/expenses/{expense_id}",
        json={"amount": 5, "expense_date": "2026-09-01", "category_id": 999},
    )
    assert response.status_code == 404


def test_delete_expense(client, food_id):
    expense_id = add_expense(client, food_id).json()["id"]
    assert client.delete(f"/api/v1/expenses/{expense_id}").status_code == 204
    assert client.get(f"/api/v1/expenses/{expense_id}").status_code == 404
    assert client.delete(f"/api/v1/expenses/{expense_id}").status_code == 404


def test_filter_by_month_uses_half_open_range(client, food_id):
    add_expense(client, food_id, expense_date="2026-08-31")
    add_expense(client, food_id, expense_date="2026-09-01")
    add_expense(client, food_id, expense_date="2026-09-30")
    add_expense(client, food_id, expense_date="2026-10-01")

    dates = [e["expense_date"] for e in client.get("/api/v1/expenses?month=2026-09").json()]
    assert dates == ["2026-09-30", "2026-09-01"]  # newest first


def test_december_rolls_over_to_next_year(client, food_id):
    add_expense(client, food_id, expense_date="2026-12-31")
    add_expense(client, food_id, expense_date="2027-01-01")
    result = client.get("/api/v1/expenses?month=2026-12").json()
    assert [e["expense_date"] for e in result] == ["2026-12-31"]


def test_filter_by_category(client, food_id, travel_id):
    add_expense(client, food_id)
    add_expense(client, travel_id)
    result = client.get(f"/api/v1/expenses?category_id={travel_id}").json()
    assert [e["category_id"] for e in result] == [travel_id]


def test_filter_by_month_and_category(client, food_id, travel_id):
    add_expense(client, food_id, expense_date="2026-09-10")
    add_expense(client, food_id, expense_date="2026-10-10")
    add_expense(client, travel_id, expense_date="2026-09-10")
    result = client.get(f"/api/v1/expenses?month=2026-09&category_id={food_id}").json()
    assert len(result) == 1


@pytest.mark.parametrize("month", ["2026-13", "2026-9", "sept"])
def test_bad_month_format_rejected(client, month):
    assert client.get(f"/api/v1/expenses?month={month}").status_code == 422
