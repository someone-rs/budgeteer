import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from budgeteer.db import connect  # noqa: E402


@pytest.fixture
def conn(tmp_path):
    c = connect(tmp_path / "test.db")
    yield c
    c.close()


@pytest.fixture
def seeded(conn):
    from budgeteer.store import add_transaction

    add_transaction(conn, "expense", 1250, "food", "2026-10-05", "lunch", "cash")
    add_transaction(conn, "expense", 3000, "transport", "2026-10-06", "bus", "cash")
    add_transaction(conn, "income", 500000, "salary", "2026-10-01", "pay", "bank")
    add_transaction(conn, "expense", 2000, "food", "2026-09-20", "dinner", "cash")
    return conn
