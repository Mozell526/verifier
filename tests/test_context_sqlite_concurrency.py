from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from impl.core.context.registry import SQLiteContextDatabase


def test_sqlite_context_survives_concurrent_connect_stampede(tmp_path):
    database = SQLiteContextDatabase(tmp_path / "context.sqlite3")
    errors: list[BaseException] = []

    def worker() -> None:
        for _ in range(24):
            with database.transaction() as connection:
                connection.execute("SELECT count(*) FROM context_units").fetchone()
            with database.reader() as connection:
                connection.execute("SELECT 1").fetchone()

    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = [executor.submit(worker) for _ in range(16)]
        for future in as_completed(futures, timeout=20):
            try:
                future.result()
            except BaseException as exc:
                errors.append(exc)

    assert errors == []


def test_sqlite_context_survives_multi_instance_connect_stampede(tmp_path):
    db_path = tmp_path / "context.sqlite3"
    errors: list[BaseException] = []

    def worker() -> None:
        database = SQLiteContextDatabase(db_path)
        for _ in range(12):
            with database.transaction() as connection:
                connection.execute("SELECT count(*) FROM context_units").fetchone()
            with database.reader() as connection:
                connection.execute("SELECT 1").fetchone()

    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = [executor.submit(worker) for _ in range(16)]
        for future in as_completed(futures, timeout=20):
            try:
                future.result()
            except BaseException as exc:
                errors.append(exc)

    assert errors == []


def test_sqlite_context_sets_wal_once_and_keeps_busy_timeout(tmp_path):
    database = SQLiteContextDatabase(tmp_path / "context.sqlite3")
    with database.reader() as connection:
        journal = connection.execute("PRAGMA journal_mode").fetchone()[0]
        timeout = connection.execute("PRAGMA busy_timeout").fetchone()[0]
    assert str(journal).lower() == "wal"
    assert int(timeout) >= 30000
