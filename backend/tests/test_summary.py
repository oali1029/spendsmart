from decimal import Decimal

import pytest


def make_category(client, name, monthly_limit=None):
    return client.post(
        "/api/v1/categories", json={"name": name, "monthly_limit": monthly_limit}
    ).json()["id"]


def add_expense(client, category_id, amount, expense_date="2026-09-15"):
    response = client.post(
        "/api/v1/expenses",
        json={"amount": amount, "expense_date": expense_date, "category_id": category_id},
    )
    assert response.status_code == 201


def summary(client, month="2026-09"):
    response = client.get(f"/api/v1/summary?month={month}")
    assert response.status_code == 200
    return response.json()


def by_name(body):
    return {c["name"]: c for c in body["categories"]}


def test_empty_month(client):
    body = summary(client)
    assert body["month"] == "2026-09"
    assert body["budget"] is None
    assert body["remaining"] is None
    assert Decimal(body["total_spent"]) == 0
    assert body["categories"] == []


def test_totals_and_remaining(client):
    food = make_category(client, "Food", 300)
    travel = make_category(client, "Travel")
    add_expense(client, food, "40.25")
    add_expense(client, food, "9.75")
    add_expense(client, travel, "100")
    client.put("/api/v1/budgets/2026-09", json={"amount": 500})

    body = summary(client)
    assert Decimal(body["budget"]) == 500
    assert Decimal(body["total_spent"]) == 150
    assert Decimal(body["remaining"]) == 350

    cats = by_name(body)
    assert Decimal(cats["Food"]["spent"]) == 50
    assert Decimal(cats["Food"]["monthly_limit"]) == 300
    assert Decimal(cats["Travel"]["spent"]) == 100
    assert cats["Travel"]["monthly_limit"] is None


def test_breakdown_sums_to_total(client):
    a = make_category(client, "A")
    b = make_category(client, "B")
    add_expense(client, a, "10.10")
    add_expense(client, b, "20.20")
    body = summary(client)
    assert sum(Decimal(c["spent"]) for c in body["categories"]) == Decimal(body["total_spent"])


def test_categories_without_spending_show_zero(client):
    make_category(client, "Unused", 50)
    body = summary(client)
    assert Decimal(by_name(body)["Unused"]["spent"]) == 0


def test_overspent_budget_gives_negative_remaining(client):
    food = make_category(client, "Food")
    add_expense(client, food, "120")
    client.put("/api/v1/budgets/2026-09", json={"amount": 100})
    assert Decimal(summary(client)["remaining"]) == -20


def test_budget_without_spending(client):
    client.put("/api/v1/budgets/2026-09", json={"amount": 100})
    body = summary(client)
    assert Decimal(body["remaining"]) == 100
    assert Decimal(body["total_spent"]) == 0


def test_only_the_requested_month_is_counted(client):
    food = make_category(client, "Food")
    add_expense(client, food, "10", "2026-08-31")
    add_expense(client, food, "20", "2026-09-01")
    add_expense(client, food, "30", "2026-09-30")
    add_expense(client, food, "40", "2026-10-01")
    assert Decimal(summary(client)["total_spent"]) == 50


def test_december_does_not_include_january(client):
    food = make_category(client, "Food")
    add_expense(client, food, "10", "2026-12-31")
    add_expense(client, food, "99", "2027-01-01")
    assert Decimal(summary(client, "2026-12")["total_spent"]) == 10


def test_budget_of_another_month_is_not_used(client):
    client.put("/api/v1/budgets/2026-10", json={"amount": 100})
    assert summary(client, "2026-09")["budget"] is None


def test_summary_reflects_edits_and_deletes(client):
    food = make_category(client, "Food")
    travel = make_category(client, "Travel")
    expense_id = client.post(
        "/api/v1/expenses",
        json={"amount": 60, "expense_date": "2026-09-05", "category_id": food},
    ).json()["id"]
    assert Decimal(by_name(summary(client))["Food"]["spent"]) == 60

    # Moving the expense to another category moves its spending too.
    client.put(
        f"/api/v1/expenses/{expense_id}",
        json={"amount": 60, "expense_date": "2026-09-05", "category_id": travel},
    )
    cats = by_name(summary(client))
    assert Decimal(cats["Food"]["spent"]) == 0
    assert Decimal(cats["Travel"]["spent"]) == 60

    client.delete(f"/api/v1/expenses/{expense_id}")
    assert Decimal(summary(client)["total_spent"]) == 0


def test_month_is_required_and_validated(client):
    assert client.get("/api/v1/summary").status_code == 422
    assert client.get("/api/v1/summary?month=2026-13").status_code == 422
