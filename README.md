# budgeteer 💰

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-33%20passed-brightgreen.svg)](tests/)

**Personal finance tracker for the terminal.** Record income and expenses,
see monthly reports with ASCII bar charts, set per-category budgets, and
import/export CSV — all in a single SQLite file. Zero dependencies.

## Install

```bash
pip install budgeteer
# or from source:
git clone https://github.com/someone-rs/budgeteer && cd budgeteer
pip install .
```

Requires Python 3.9+. Data lives in `~/.local/share/budgeteer/budgeteer.db`
by default; override with `--db` or the `BUDGETEER_DB` environment variable.

## Quickstart

```bash
# Record transactions
budgeteer add --kind income --amount 5000 --category salary --date 2026-10-01
budgeteer add --kind expense --amount 12.50 --category food --date 2026-10-05 --note lunch
budgeteer add --kind expense --amount 45 --category transport --date 2026-10-06

# Monthly report with bar charts
budgeteer report --month 2026-10
```

```
Report for 2026-10
  income : 5,000.00
  expense: 57.50
  balance: 4,942.50

Expenses by category:
  transport | ######################################## 45.00
  food      | ########### 12.50

Income by category:
  salary | ######################################## 5,000.00
```

```bash
# Budgets: set a limit, then check how you're doing
budgeteer budget set food 100 --month 2026-10
budgeteer budget status --month 2026-10
```

```
CATEGORY  LIMIT   SPENT  REMAINING  STATUS
--------  ------  -----  ---------  ------
food      100.00  12.50  87.50      ok
```

```bash
# List with filters, export, and overall summary
budgeteer list --category food --from 2026-10-01 --to 2026-10-31
budgeteer export --format csv --out transactions.csv
budgeteer import bank-statement.csv
budgeteer summary
```

## Commands

| Command | What it does |
|---|---|
| `add` | Record an expense/income (`--kind`, `--amount`, `--category`, `--date`, `--note`, `--account`) |
| `list` | List transactions, filter by kind/category/account/date range, sort by date or amount |
| `report` | Monthly summary: income vs expense by category, totals, ASCII bar charts |
| `budget set` / `budget status` | Monthly per-category limits and spent-vs-limit tracking |
| `import` | Import a CSV file (or `-` for stdin); bad rows are skipped with a warning |
| `export` | Export to CSV or JSON, optionally filtered by date range |
| `categories` | List, add, or remove categories |
| `summary` | Overall balance and top categories |
| `delete` | Delete a transaction by id |

## Details

- **Amounts are stored as integer cents** — no floating-point rounding surprises.
- **Validation that helps, not annoys:** negative or zero amounts are rejected,
  impossible dates (`2026-02-30`) are rejected, and unknown categories produce
  a warning instead of silently creating junk data.
- **Script-friendly:** `--json` on `list`, `report`, `summary`, and
  `budget status` (amounts in minor units); exit code `2` on validation errors.
- **CSV format:** `kind,amount,category,date[,note][,account]`.

## Development

```bash
pip install pytest
python -m pytest tests/ -q   # 33 tests
```

## License

MIT — see [LICENSE](LICENSE).
