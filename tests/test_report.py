from budgeteer.store import (
    budget_status,
    by_category,
    monthly_report,
    set_budget,
    summary,
    totals,
)


def test_totals(seeded):
    t = totals(seeded)
    assert t["income"] == 500000
    assert t["expense"] == 6250


def test_totals_date_range(seeded):
    t = totals(seeded, date_from="2026-10-01", date_to="2026-10-31")
    assert t["expense"] == 4250
    assert t["income"] == 500000


def test_by_category(seeded):
    assert by_category(seeded, "expense") == [("transport", 3000), ("food", 3250)] \
        or by_category(seeded, "expense") == [("food", 3250), ("transport", 3000)]
    assert by_category(seeded, "income") == [("salary", 500000)]


def test_monthly_report(seeded):
    rep = monthly_report(seeded, "2026-10")
    assert rep["income_total"] == 500000
    assert rep["expense_total"] == 4250
    assert rep["balance"] == 495750
    assert rep["expense_by_category"] == {"food": 1250, "transport": 3000}
    assert rep["income_by_category"] == {"salary": 500000}
    # September is excluded
    assert "2026-09" not in str(rep)


def test_monthly_report_empty_month(seeded):
    rep = monthly_report(seeded, "2026-01")
    assert rep["income_total"] == 0
    assert rep["expense_total"] == 0
    assert rep["balance"] == 0


def test_monthly_report_year_boundary(conn):
    from budgeteer.store import add_transaction

    add_transaction(conn, "expense", 100, "food", "2026-12-31")
    add_transaction(conn, "expense", 200, "food", "2027-01-01")
    assert monthly_report(conn, "2026-12")["expense_total"] == 100
    assert monthly_report(conn, "2027-01")["expense_total"] == 200


def test_summary(seeded):
    s = summary(seeded)
    assert s["transactions"] == 4
    assert s["balance"] == 500000 - 6250
    assert s["top_expense_categories"][0] == ("food", 3250)


def test_budget_status(seeded):
    set_budget(seeded, "food", "2026-10", 2000)
    set_budget(seeded, "transport", "2026-10", 10000)
    rows = budget_status(seeded, "2026-10")
    by_cat = {r["category"]: r for r in rows}
    assert by_cat["food"]["spent"] == 1250
    assert by_cat["food"]["remaining"] == 750
    assert not by_cat["food"]["over"]
    assert by_cat["transport"]["spent"] == 3000
    # Over-budget case
    set_budget(seeded, "food", "2026-10", 1000)
    rows = budget_status(seeded, "2026-10")
    by_cat = {r["category"]: r for r in rows}
    assert by_cat["food"]["over"]
    assert by_cat["food"]["remaining"] == -250
    # Budgets from another month do not leak in
    assert budget_status(seeded, "2026-09") == []
