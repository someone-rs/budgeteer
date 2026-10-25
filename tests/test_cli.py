import json

import pytest

from budgeteer.cli import main


def run(db, *args, capsys=None):
    rc = main(["--db", str(db)] + list(args))
    if capsys is not None:
        captured = capsys.readouterr()
        return rc, captured.out, captured.err
    return rc


def test_cli_add_list_delete(tmp_path, capsys):
    db = tmp_path / "cli.db"
    assert run(db, "add", "--kind", "expense", "--amount", "12.50",
               "--category", "food", "--date", "2026-10-05",
               "--note", "lunch") == 0
    out = capsys.readouterr().out
    assert "added #1" in out and "12.50" in out

    assert run(db, "list") == 0
    out = capsys.readouterr().out
    assert "food" in out and "12.50" in out

    assert run(db, "delete", "1") == 0
    assert run(db, "delete", "1") == 2  # already gone


def test_cli_validation_errors(tmp_path, capsys):
    db = tmp_path / "cli.db"
    assert run(db, "add", "--kind", "expense", "--amount", "-5",
               "--category", "food") == 2
    assert run(db, "add", "--kind", "expense", "--amount", "5",
               "--category", "food", "--date", "2026-02-30") == 2
    assert run(db, "report", "--month", "2026-13") == 2


def test_cli_unknown_category_warns(tmp_path, capsys):
    db = tmp_path / "cli.db"
    assert run(db, "add", "--kind", "expense", "--amount", "5",
               "--category", "spaceships") == 0
    err = capsys.readouterr().err
    assert "warning" in err and "spaceships" in err


def test_cli_report_and_budget(tmp_path, capsys):
    db = tmp_path / "cli.db"
    run(db, "add", "--kind", "income", "--amount", "5000",
        "--category", "salary", "--date", "2026-10-01")
    run(db, "add", "--kind", "expense", "--amount", "100",
        "--category", "food", "--date", "2026-10-05")
    assert run(db, "budget", "set", "food", "80", "--month", "2026-10") == 0
    assert run(db, "budget", "status", "--month", "2026-10") == 0
    out = capsys.readouterr().out
    assert "OVER!" in out  # 100 spent vs 80 limit
    assert run(db, "report", "--month", "2026-10") == 0
    out = capsys.readouterr().out
    assert "5,000.00" in out and "100.00" in out and "food" in out


def test_cli_json_output(tmp_path, capsys):
    db = tmp_path / "cli.db"
    run(db, "add", "--kind", "expense", "--amount", "12.50",
        "--category", "food", "--date", "2026-10-05", capsys=capsys)
    rc, out, _ = run(db, "list", "--json", capsys=capsys)
    assert rc == 0
    docs = json.loads(out)
    assert docs[0]["amount_cents"] == 1250
    assert docs[0]["category"] == "food"
    rc, out, _ = run(db, "summary", "--json", capsys=capsys)
    assert rc == 0
    docs = json.loads(out)
    assert docs["expense_total_cents"] == 1250


def test_cli_categories(tmp_path, capsys):
    db = tmp_path / "cli.db"
    rc, out, _ = run(db, "categories", capsys=capsys)
    assert rc == 0 and "food" in out
    rc, out, _ = run(db, "categories", "add", "gym", "--kind", "expense", capsys=capsys)
    assert rc == 0
    rc, out, _ = run(db, "categories", capsys=capsys)
    assert "gym" in out
    rc, out, _ = run(db, "categories", "remove", "gym", capsys=capsys)
    assert rc == 0
    rc, out, _ = run(db, "categories", capsys=capsys)
    assert "gym" not in out


def test_cli_import_export(tmp_path, capsys):
    db = tmp_path / "cli.db"
    csv_file = tmp_path / "in.csv"
    csv_file.write_text("kind,amount,category,date,note,account\n"
                        "expense,9.99,shopping,2026-10-11,book,card\n")
    rc, _, _ = run(db, "import", str(csv_file), capsys=capsys)
    assert rc == 0
    out_file = tmp_path / "out.csv"
    rc, _, _ = run(db, "export", "--out", str(out_file), capsys=capsys)
    assert rc == 0
    assert "shopping" in out_file.read_text()
    rc, out, _ = run(db, "export", "--format", "json", capsys=capsys)
    assert rc == 0
    docs = json.loads(out)
    assert docs[0]["amount"] == "9.99"
