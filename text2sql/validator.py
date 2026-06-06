"""SQL validation and safe execution helpers."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from typing import Any, List

FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|TRUNCATE|MERGE|ATTACH|DETACH|PRAGMA)\b",
    re.IGNORECASE,
)


@dataclass
class QueryResult:
    ok: bool
    sql: str
    rows: List[dict[str, Any]]
    error: str | None = None


def clean_sql(raw: str) -> str:
    raw = re.sub(r"```(?:sql)?\s*", "", raw, flags=re.IGNORECASE)
    raw = raw.replace("```", "").strip()
    raw = raw.rstrip(";").strip()
    return raw


def validate_select_only(sql: str) -> None:
    normalized = sql.strip().rstrip(";")
    if not re.match(r"^\s*(SELECT|WITH)\b", normalized, flags=re.IGNORECASE):
        raise ValueError("Only SELECT/WITH queries are allowed.")
    if ";" in normalized:
        raise ValueError("Multiple SQL statements are not allowed.")
    if FORBIDDEN_SQL.search(normalized):
        raise ValueError("Unsafe SQL keyword detected. Only read-only query is allowed.")


def execute_sql(db_path: str, sql: str, limit: int = 100) -> QueryResult:
    sql = clean_sql(sql)
    try:
        validate_select_only(sql)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.execute(sql)
        rows = [dict(row) for row in cur.fetchmany(limit)]
        conn.close()
        return QueryResult(ok=True, sql=sql, rows=rows)
    except Exception as exc:  # noqa: BLE001 - return DB error for correction module
        return QueryResult(ok=False, sql=sql, rows=[], error=str(exc))
