"""Core operations: validation, CRUD, aggregations, budgets."""

import re
from datetime import date as _date
from decimal import Decimal, InvalidOperation

from .db import connect

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


class ValidationError(ValueError):
    """Raised when user input fails validation."""


def parse_amount(raw: str) -> int:
    """Parse a decimal amount string into integer minor units (cents)."""
    try:
        value = Decimal(str(raw).strip())
    except InvalidOperation:
        raise ValidationError(f"invalid amount: {raw!r}")
    if value <= 0:
        raise ValidationError(f"amount must be positive, got {raw!r}")
    if -value.as_tuple().exponent > 2:
        raise ValidationError(f"amount has more than 2 decimal places: {raw!r}")
    return int(value * 100)


def parse_date(raw: str) -> str:
    """Validate an ISO date string (YYYY-MM-DD)."""
    if not DATE_RE.match(raw or ""):
        raise ValidationError(f"invalid date (expected YYYY-MM-DD): {raw!r}")
    try:
        _date.fromisoformat(raw)
    except ValueError:
        raise ValidationError(f"invalid calendar date: {raw!r}")
    return raw


def parse_month(raw: str) -> str:
    """Validate a YYYY-MM month string."""
    if not MONTH_RE.match(raw or ""):
        raise ValidationError(f"invalid month (expected YYYY-MM): {raw!r}")
    year, month = int(raw[:4]), int(raw[5:7])
    if not 1 <= month <= 12:
        raise ValidationError(f"invalid month: {raw!r}")
    return raw


def format_amount(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}{cents // 100:,}.{cents % 100:02d}"


def format_amount_plain(cents: int) -> str:
    """Machine-friendly amount: no thousands separator (CSV/JSON)."""
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}{cents // 100}.{cents % 100:02d}"


def known_categories(conn, kind=None):
    sql = "SELECT name, kind FROM categories"
    params = []
    if kind in ("expense", "income"):
        sql += " WHERE kind = ? OR kind = 'both'"
        params.append(kind)
    sql += " ORDER BY name"
    return [dict(r) for r in conn.execute(sql, params)]


def category_exists(conn, name) -> bool:
    return conn.execute(
        "SELECT 1 FROM categories WHERE name = ?", (name,)
    ).fetchone() is not None


def add_category(conn, name, kind="both"):
    if kind not in ("expense", "income", "both"):
        raise ValidationError(f"invalid category kind: {kind!r}")
    name = name.strip().lower()
    if not name:
        raise ValidationError("category name must not be empty")
    conn.execute(
        "INSERT OR REPLACE INTO categories (name, kind) VALUES (?, ?)", (name, kind)
    )
    conn.commit()


def remove_category(conn, name):
    conn.execute("DELETE FROM categories WHERE name = ?", (name.strip().lower(),))
    conn.commit()


def add_transaction(conn, kind, amount_cents, category, date, note="", account="default"):
    """Insert a transaction. Returns (row_id, category_was_unknown)."""
    if kind not in ("expense", "income"):
        raise ValidationError(f"kind must be 'expense' or 'income', got {kind!r}")
    if amount_cents <= 0:
        raise ValidationError("amount must be positive")
    parse_date(date)
    category = category.strip().lower()
    if not category:
        raise ValidationError("category must not be empty")
    unknown = not category_exists(conn, category)
    cur = conn.execute(
        "INSERT INTO transactions (kind, amount, category, date, note, account)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (kind, amount_cents, category, date, note, account),
    )
    conn.commit()
    return cur.lastrowid, unknown


def delete_transaction(conn, tx_id: int) -> bool:
    cur = conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
    conn.commit()
    return cur.rowcount > 0


def list_transactions(conn, kind=None, category=None, account=None,
                      date_from=None, date_to=None, sort="date", limit=None):
    sql = "SELECT * FROM transactions WHERE 1=1"
    params = []
    if kind:
        sql += " AND kind = ?"
        params.append(kind)
    if category:
        sql += " AND category = ?"
        params.append(category)
    if account:
        sql += " AND account = ?"
        params.append(account)
    if date_from:
        sql += " AND date >= ?"
        params.append(parse_date(date_from))
    if date_to:
        sql += " AND date <= ?"
        params.append(parse_date(date_to))
    if sort == "amount":
        sql += " ORDER BY amount DESC, date DESC"
    else:
        sql += " ORDER BY date DESC, id DESC"
    if limit:
        sql += " LIMIT ?"
        params.append(int(limit))
    return [dict(r) for r in conn.execute(sql, params)]


def totals(conn, date_from=None, date_to=None):
    """Return {kind: total_cents} for an optional date range."""
    sql = "SELECT kind, COALESCE(SUM(amount), 0) AS total FROM transactions WHERE 1=1"
    params = []
    if date_from:
        sql += " AND date >= ?"
        params.append(date_from)
    if date_to:
        sql += " AND date <= ?"
        params.append(date_to)
    sql += " GROUP BY kind"
    out = {"expense": 0, "income": 0}
    for row in conn.execute(sql, params):
        out[row["kind"]] = row["total"]
    return out


def by_category(conn, kind, date_from=None, date_to=None):
    """Return [(category, total_cents)] sorted by total desc."""
    sql = ("SELECT category, SUM(amount) AS total FROM transactions"
           " WHERE kind = ?")
    params = [kind]
    if date_from:
        sql += " AND date >= ?"
        params.append(date_from)
    if date_to:
        sql += " AND date <= ?"
        params.append(date_to)
    sql += " GROUP BY category ORDER BY total DESC"
    return [(r["category"], r["total"]) for r in conn.execute(sql, params)]


def month_range(month: str):
    """Return (first_day, last_day) ISO strings for a YYYY-MM month."""
    parse_month(month)
    year, mon = int(month[:4]), int(month[5:7])
    if mon == 12:
        next_first = f"{year + 1:04d}-01-01"
    else:
        next_first = f"{year:04d}-{mon + 1:02d}-01"
    return f"{month}-01", next_first  # end-exclusive via < next_first


def monthly_report(conn, month: str):
    """Income vs expense breakdown for one month."""
    start, end = month_range(month)
    rows = conn.execute(
        "SELECT kind, category, SUM(amount) AS total FROM transactions"
        " WHERE date >= ? AND date < ? GROUP BY kind, category"
        " ORDER BY kind, total DESC",
        (start, end),
    ).fetchall()
    income = {}
    expense = {}
    for r in rows:
        (income if r["kind"] == "income" else expense)[r["category"]] = r["total"]
    total_in = sum(income.values())
    total_out = sum(expense.values())
    return {
        "month": month,
        "income_total": total_in,
        "expense_total": total_out,
        "balance": total_in - total_out,
        "income_by_category": income,
        "expense_by_category": expense,
    }


def set_budget(conn, category, month, limit_cents):
    parse_month(month)
    if limit_cents <= 0:
        raise ValidationError("budget limit must be positive")
    conn.execute(
        "INSERT OR REPLACE INTO budgets (category, month, limit_amount)"
        " VALUES (?, ?, ?)",
        (category.strip().lower(), month, limit_cents),
    )
    conn.commit()


def budget_status(conn, month: str):
    """Spent vs limit per budgeted category for a month."""
    parse_month(month)
    start, end = month_range(month)
    spent = dict(conn.execute(
        "SELECT category, SUM(amount) AS total FROM transactions"
        " WHERE kind = 'expense' AND date >= ? AND date < ?"
        " GROUP BY category",
        (start, end),
    ).fetchall())
    rows = []
    for r in conn.execute(
        "SELECT category, limit_amount FROM budgets WHERE month = ? ORDER BY category",
        (month,),
    ):
        s = spent.get(r["category"], 0)
        rows.append({
            "category": r["category"],
            "limit": r["limit_amount"],
            "spent": s,
            "remaining": r["limit_amount"] - s,
            "over": s > r["limit_amount"],
        })
    return rows


def summary(conn):
    totals_all = totals(conn)
    top_expense = by_category(conn, "expense")[:5]
    top_income = by_category(conn, "income")[:5]
    count = conn.execute("SELECT COUNT(*) AS n FROM transactions").fetchone()["n"]
    return {
        "transactions": count,
        "income_total": totals_all["income"],
        "expense_total": totals_all["expense"],
        "balance": totals_all["income"] - totals_all["expense"],
        "top_expense_categories": top_expense,
        "top_income_categories": top_income,
    }
