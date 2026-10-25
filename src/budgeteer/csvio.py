"""CSV import / export and JSON export for budgeteer."""

import csv
import io
import json

from .store import ValidationError, add_transaction, format_amount_plain, parse_amount, parse_date


def export_csv(rows) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "kind", "amount", "category", "date", "note", "account"])
    for r in rows:
        w.writerow([r["id"], r["kind"], format_amount_plain(r["amount"]),
                    r["category"], r["date"], r["note"], r["account"]])
    return buf.getvalue()


def export_json(rows) -> str:
    docs = [{
        "id": r["id"], "kind": r["kind"], "amount": format_amount_plain(r["amount"]),
        "category": r["category"], "date": r["date"],
        "note": r["note"], "account": r["account"],
    } for r in rows]
    return json.dumps(docs, indent=2)


def import_csv(conn, text: str, default_account=None):
    """Import rows. Returns (imported_count, errors).

    Expected header: kind,amount,category,date[,note][,account].
    Rows that fail validation are skipped and reported, never half-imported.
    """
    reader = csv.DictReader(io.StringIO(text))
    required = {"kind", "amount", "category", "date"}
    if reader.fieldnames is None or not required.issubset(
            {h.strip() for h in reader.fieldnames}):
        raise ValidationError(
            "CSV must have header: kind,amount,category,date[,note][,account]")
    imported = 0
    errors = []
    for lineno, row in enumerate(reader, start=2):
        try:
            kind = (row.get("kind") or "").strip().lower()
            amount = parse_amount(row.get("amount") or "")
            category = (row.get("category") or "").strip()
            d = parse_date((row.get("date") or "").strip())
            note = (row.get("note") or "").strip()
            account = (row.get("account") or "").strip() or (default_account or "default")
            add_transaction(conn, kind, amount, category, d, note, account)
            imported += 1
        except (ValidationError, ValueError) as exc:
            errors.append(f"line {lineno}: {exc}")
    return imported, errors
