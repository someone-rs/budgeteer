import pytest

from budgeteer.csvio import export_csv, export_json, import_csv
from budgeteer.store import ValidationError, list_transactions


def test_export_csv_roundtrip(conn):
    from budgeteer.store import add_transaction

    add_transaction(conn, "expense", 1250, "food", "2026-10-05", "lunch", "cash")
    csv_text = export_csv(list_transactions(conn))
    assert csv_text.startswith("id,kind,amount,category,date,note,account")
    assert "expense,12.50,food,2026-10-05,lunch,cash" in csv_text


def test_export_json(conn):
    from budgeteer.store import add_transaction

    add_transaction(conn, "income", 500000, "salary", "2026-10-01", "", "bank")
    data = export_json(list_transactions(conn))
    assert '"kind": "income"' in data
    assert '"amount": "5000.00"' in data


def test_import_csv_ok(conn):
    text = ("kind,amount,category,date,note,account\n"
            "expense,12.50,food,2026-10-05,lunch,cash\n"
            "income,5000.00,salary,2026-10-01,,bank\n")
    imported, errors = import_csv(conn, text)
    assert imported == 2
    assert errors == []
    rows = list_transactions(conn)
    assert len(rows) == 2


def test_import_csv_skips_bad_rows(conn):
    text = ("kind,amount,category,date,note,account\n"
            "expense,12.50,food,2026-10-05,ok,cash\n"
            "expense,-5,food,2026-10-06,negative,cash\n"
            "expense,10,food,2026-02-30,bad date,cash\n"
            "expense,3.50,food,2026-10-07,ok2,cash\n")
    imported, errors = import_csv(conn, text)
    assert imported == 2
    assert len(errors) == 2
    assert "line 3" in errors[0]
    assert "line 4" in errors[1]


def test_import_csv_missing_header(conn):
    with pytest.raises(ValidationError):
        import_csv(conn, "foo,bar\n1,2\n")


def test_import_csv_defaults_account(conn):
    text = "kind,amount,category,date\nincome,100,salary,2026-10-01\n"
    imported, _ = import_csv(conn, text, default_account="wallet")
    assert imported == 1
    assert list_transactions(conn)[0]["account"] == "wallet"


def test_import_then_export_roundtrip(conn):
    text = ("kind,amount,category,date,note,account\n"
            "expense,9.99,shopping,2026-10-11,book,card\n")
    import_csv(conn, text)
    out = export_csv(list_transactions(conn))
    assert "shopping" in out and "9.99" in out
