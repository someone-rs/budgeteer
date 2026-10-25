"""Command-line interface for budgeteer."""

import argparse
import json
import sys
from datetime import date as _date

from . import __version__
from .csvio import export_csv, export_json, import_csv
from .db import connect
from .render import render_bar_chart, render_table
from .store import (
    ValidationError,
    add_category,
    add_transaction,
    budget_status,
    delete_transaction,
    format_amount,
    known_categories,
    list_transactions,
    monthly_report,
    parse_amount,
    parse_date,
    remove_category,
    set_budget,
    summary,
)


def _fail(msg):
    print(f"budgeteer: error: {msg}", file=sys.stderr)
    return 2


def _tx_rows(rows):
    return [[str(r["id"]), r["date"], r["kind"], r["category"],
             format_amount(r["amount"]), r["account"], r["note"]] for r in rows]


def cmd_add(args, conn):
    try:
        amount = parse_amount(args.amount)
        d = parse_date(args.date) if args.date else _date.today().isoformat()
        tx_id, unknown = add_transaction(
            conn, args.kind, amount, args.category, d, args.note, args.account)
    except ValidationError as exc:
        return _fail(str(exc))
    if unknown:
        print(f"warning: category {args.category!r} is not in your category list"
              " (use `budgeteer categories add` to add it)", file=sys.stderr)
    print(f"added #{tx_id}: {args.kind} {format_amount(amount)} "
          f"[{args.category}] on {d}")
    return 0


def cmd_list(args, conn):
    try:
        rows = list_transactions(
            conn, kind=args.kind, category=args.category, account=args.account,
            date_from=args.from_date, date_to=args.to_date,
            sort=args.sort, limit=args.limit)
    except ValidationError as exc:
        return _fail(str(exc))
    if args.json:
        print(json.dumps([{
            "id": r["id"], "kind": r["kind"], "amount_cents": r["amount"],
            "category": r["category"], "date": r["date"],
            "note": r["note"], "account": r["account"],
        } for r in rows], indent=2))
    elif rows:
        print(render_table(
            ["ID", "DATE", "KIND", "CATEGORY", "AMOUNT", "ACCOUNT", "NOTE"],
            _tx_rows(rows)))
        tot = sum(r["amount"] if r["kind"] == "income" else -r["amount"] for r in rows)
        print(f"\n{len(rows)} transaction(s), net: {format_amount(tot)}")
    else:
        print("no transactions match")
    return 0


def cmd_delete(args, conn):
    if delete_transaction(conn, args.id):
        print(f"deleted #{args.id}")
        return 0
    return _fail(f"no transaction with id {args.id}")


def cmd_report(args, conn):
    month = args.month or _date.today().strftime("%Y-%m")
    try:
        rep = monthly_report(conn, month)
    except ValidationError as exc:
        return _fail(str(exc))
    if args.json:
        print(json.dumps(rep, indent=2))
        return 0
    print(f"Report for {month}")
    print(f"  income : {format_amount(rep['income_total'])}")
    print(f"  expense: {format_amount(rep['expense_total'])}")
    print(f"  balance: {format_amount(rep['balance'])}")
    print("\nExpenses by category:")
    for line in render_bar_chart(
            sorted(rep["expense_by_category"].items(), key=lambda kv: -kv[1])):
        print("  " + line)
    print("\nIncome by category:")
    for line in render_bar_chart(
            sorted(rep["income_by_category"].items(), key=lambda kv: -kv[1])):
        print("  " + line)
    return 0


def cmd_budget(args, conn):
    if args.action == "set":
        try:
            limit = parse_amount(args.amount)
            set_budget(conn, args.category, args.month or _date.today().strftime("%Y-%m"),
                       limit)
        except ValidationError as exc:
            return _fail(str(exc))
        print(f"budget set: {args.category} = {format_amount(limit)}/month")
        return 0
    # status
    month = args.month or _date.today().strftime("%Y-%m")
    try:
        rows = budget_status(conn, month)
    except ValidationError as exc:
        return _fail(str(exc))
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    if not rows:
        print(f"no budgets set for {month} (use `budgeteer budget set`)")
        return 0
    print(render_table(
        ["CATEGORY", "LIMIT", "SPENT", "REMAINING", "STATUS"],
        [[r["category"], format_amount(r["limit"]), format_amount(r["spent"]),
          format_amount(r["remaining"]), "OVER!" if r["over"] else "ok"]
         for r in rows]))
    return 0


def cmd_import(args, conn):
    try:
        text = sys.stdin.read() if args.file == "-" else open(args.file).read()
        imported, errors = import_csv(conn, text, default_account=args.account)
    except (OSError, ValidationError) as exc:
        return _fail(str(exc))
    print(f"imported {imported} transaction(s)")
    for err in errors:
        print(f"warning: {err}", file=sys.stderr)
    return 0


def cmd_export(args, conn):
    try:
        rows = list_transactions(conn, date_from=args.from_date, date_to=args.to_date)
    except ValidationError as exc:
        return _fail(str(exc))
    out = export_json(rows) if args.format == "json" else export_csv(rows)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(out)
        print(f"wrote {len(rows)} transaction(s) to {args.out}")
    else:
        sys.stdout.write(out)
    return 0


def cmd_categories(args, conn):
    if args.action == "add":
        try:
            add_category(conn, args.name, args.kind)
        except ValidationError as exc:
            return _fail(str(exc))
        print(f"category added: {args.name.lower()} ({args.kind})")
    elif args.action == "remove":
        remove_category(conn, args.name)
        print(f"category removed: {args.name.lower()}")
    else:
        cats = known_categories(conn)
        print(render_table(["NAME", "KIND"], [[c["name"], c["kind"]] for c in cats]))
    return 0


def cmd_summary(args, conn):
    s = summary(conn)
    if args.json:
        print(json.dumps({
            "transactions": s["transactions"],
            "income_total_cents": s["income_total"],
            "expense_total_cents": s["expense_total"],
            "balance_cents": s["balance"],
            "top_expense_categories": s["top_expense_categories"],
            "top_income_categories": s["top_income_categories"],
        }, indent=2))
        return 0
    print(f"transactions: {s['transactions']}")
    print(f"total income : {format_amount(s['income_total'])}")
    print(f"total expense: {format_amount(s['expense_total'])}")
    print(f"balance      : {format_amount(s['balance'])}")
    print("\nTop expense categories:")
    for line in render_bar_chart(s["top_expense_categories"]):
        print("  " + line)
    print("\nTop income categories:")
    for line in render_bar_chart(s["top_income_categories"]):
        print("  " + line)
    return 0


def build_parser():
    p = argparse.ArgumentParser(
        prog="budgeteer",
        description="Personal finance tracker for the terminal (SQLite-backed).")
    p.add_argument("--db", default=None, help="path to SQLite database")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("add", help="record an expense or income")
    a.add_argument("--kind", required=True, choices=["expense", "income"])
    a.add_argument("--amount", required=True, help="e.g. 12.50")
    a.add_argument("--category", required=True)
    a.add_argument("--date", default=None, help="YYYY-MM-DD (default: today)")
    a.add_argument("--note", default="")
    a.add_argument("--account", default="default")
    a.set_defaults(func=cmd_add)

    li = sub.add_parser("list", help="list transactions with filters")
    li.add_argument("--kind", choices=["expense", "income"])
    li.add_argument("--category")
    li.add_argument("--account")
    li.add_argument("--from", dest="from_date")
    li.add_argument("--to", dest="to_date")
    li.add_argument("--sort", choices=["date", "amount"], default="date")
    li.add_argument("--limit", type=int)
    li.add_argument("--json", action="store_true")
    li.set_defaults(func=cmd_list)

    d = sub.add_parser("delete", help="delete a transaction by id")
    d.add_argument("id", type=int)
    d.set_defaults(func=cmd_delete)

    r = sub.add_parser("report", help="monthly income vs expense report")
    r.add_argument("--month", help="YYYY-MM (default: current month)")
    r.add_argument("--json", action="store_true")
    r.set_defaults(func=cmd_report)

    b = sub.add_parser("budget", help="monthly category budgets")
    bsub = b.add_subparsers(dest="action", required=True)
    bs = bsub.add_parser("set", help="set a monthly limit for a category")
    bs.add_argument("category")
    bs.add_argument("amount", help="e.g. 300")
    bs.add_argument("--month", help="YYYY-MM (default: current month)")
    bstat = bsub.add_parser("status", help="show spent vs limit")
    bstat.add_argument("--month", help="YYYY-MM (default: current month)")
    bstat.add_argument("--json", action="store_true")
    b.set_defaults(func=cmd_budget)

    im = sub.add_parser("import", help="import transactions from CSV (or - for stdin)")
    im.add_argument("file")
    im.add_argument("--account")
    im.set_defaults(func=cmd_import)

    ex = sub.add_parser("export", help="export transactions to CSV or JSON")
    ex.add_argument("--format", choices=["csv", "json"], default="csv")
    ex.add_argument("--from", dest="from_date")
    ex.add_argument("--to", dest="to_date")
    ex.add_argument("--out", help="output file (default: stdout)")
    ex.set_defaults(func=cmd_export)

    c = sub.add_parser("categories", help="list/manage categories")
    csub = c.add_subparsers(dest="action")
    cadd = csub.add_parser("add", help="add a category")
    cadd.add_argument("name")
    cadd.add_argument("--kind", choices=["expense", "income", "both"], default="both")
    crem = csub.add_parser("remove", help="remove a category")
    crem.add_argument("name")
    c.set_defaults(func=cmd_categories)

    s = sub.add_parser("summary", help="overall balance and top categories")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_summary)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    conn = connect(args.db)
    try:
        return args.func(args, conn)
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
