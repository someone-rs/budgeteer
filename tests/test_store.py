import pytest

from budgeteer.store import (
    ValidationError,
    add_transaction,
    delete_transaction,
    format_amount,
    list_transactions,
    parse_amount,
    parse_date,
    parse_month,
)


def test_parse_amount_ok():
    assert parse_amount("12.50") == 1250
    assert parse_amount("0.01") == 1
    assert parse_amount("100") == 10000
    assert parse_amount("  7.5 ") == 750


def test_parse_amount_rejects():
    for bad in ("0", "-5", "-0.01", "abc", "", "1.234", "12,50"):
        with pytest.raises(ValidationError):
            parse_amount(bad)


def test_parse_date_ok():
    assert parse_date("2026-10-25") == "2026-10-25"
    assert parse_date("2024-02-29") == "2024-02-29"  # leap day


def test_parse_date_rejects():
    for bad in ("2026-13-01", "2026-02-30", "25-10-2026", "2026/10/25", "", "2026-2-5"):
        with pytest.raises(ValidationError):
            parse_date(bad)


def test_parse_month():
    assert parse_month("2026-10") == "2026-10"
    for bad in ("2026-13", "2026-00", "2026-1", "Oct 2026"):
        with pytest.raises(ValidationError):
            parse_month(bad)


def test_format_amount():
    assert format_amount(1250) == "12.50"
    assert format_amount(-500) == "-5.00"
    assert format_amount(100000) == "1,000.00"


def test_add_and_list(conn):
    tx_id, unknown = add_transaction(
        conn, "expense", 999, "food", "2026-10-10", "snack", "cash")
    assert tx_id == 1
    assert not unknown
    rows = list_transactions(conn)
    assert len(rows) == 1
    assert rows[0]["amount"] == 999
    assert rows[0]["note"] == "snack"


def test_unknown_category_flagged_but_saved(conn):
    tx_id, unknown = add_transaction(
        conn, "expense", 100, "spaceships", "2026-10-10")
    assert unknown
    assert list_transactions(conn)[0]["category"] == "spaceships"


def test_add_validation(conn):
    with pytest.raises(ValidationError):
        add_transaction(conn, "expense", 0, "food", "2026-10-10")
    with pytest.raises(ValidationError):
        add_transaction(conn, "gift", 100, "food", "2026-10-10")
    with pytest.raises(ValidationError):
        add_transaction(conn, "expense", 100, "food", "2026-02-30")
    with pytest.raises(ValidationError):
        add_transaction(conn, "expense", 100, "", "2026-10-10")


def test_list_filters(seeded):
    assert len(list_transactions(seeded, category="food")) == 2
    assert len(list_transactions(seeded, kind="income")) == 1
    assert len(list_transactions(seeded, account="bank")) == 1
    assert len(list_transactions(seeded, date_from="2026-10-01",
                                 date_to="2026-10-31")) == 3
    assert len(list_transactions(seeded, sort="amount")) == 4
    assert list_transactions(seeded, sort="amount")[0]["amount"] == 500000
    assert len(list_transactions(seeded, limit=2)) == 2


def test_delete(seeded):
    assert delete_transaction(seeded, 1)
    assert not delete_transaction(seeded, 999)
    assert len(list_transactions(seeded)) == 3
