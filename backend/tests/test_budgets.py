from decimal import Decimal

import pytest


def put_budget(client, month="2026-09", amount=1000):
    return client.put(f"/api/v1/budgets/{month}", json={"amount": amount})


def test_get_without_budget_is_404(client):
    assert client.get("/api/v1/budgets/2026-09").status_code == 404


def test_set_then_get(client):
    response = put_budget(client, amount="1500.50")
    assert response.status_code == 200
    # The month is returned in the same YYYY-MM format used in the URL, not as 2026-09-01.
    assert response.json()["month"] == "2026-09"
    assert Decimal(response.json()["amount"]) == Decimal("1500.50")

    fetched = client.get("/api/v1/budgets/2026-09").json()
    assert fetched == {"month": "2026-09", "amount": fetched["amount"]}
    assert Decimal(fetched["amount"]) == Decimal("1500.50")


def test_put_again_updates_instead_of_duplicating(client):
    put_budget(client, amount=1000)
    response = put_budget(client, amount=2000)
    assert response.status_code == 200
    assert Decimal(client.get("/api/v1/budgets/2026-09").json()["amount"]) == 2000


def test_budgets_are_independent_per_month(client):
    put_budget(client, "2026-09", 1000)
    put_budget(client, "2026-10", 500)
    assert Decimal(client.get("/api/v1/budgets/2026-09").json()["amount"]) == 1000
    assert Decimal(client.get("/api/v1/budgets/2026-10").json()["amount"]) == 500
    assert client.get("/api/v1/budgets/2026-11").status_code == 404


@pytest.mark.parametrize("amount", [0, -10, "12.345"])
def test_invalid_amount_rejected(client, amount):
    assert put_budget(client, amount=amount).status_code == 422


@pytest.mark.parametrize("month", ["2026-13", "2026-9", "2026-00", "sept"])
def test_bad_month_format_rejected(client, month):
    assert client.get(f"/api/v1/budgets/{month}").status_code == 422
    assert put_budget(client, month=month).status_code == 422
