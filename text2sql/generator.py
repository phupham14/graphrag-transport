"""Text2SQL generator with LLM prompt, validation, and self-correction."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional

from dotenv import load_dotenv

from .prompts import SQL_CORRECTION_PROMPT, TEXT2SQL_SYSTEM_PROMPT, TEXT2SQL_USER_PROMPT
from .rules import generate_sql_by_rules
from .schema import schema_text
from .validator import QueryResult, clean_sql, execute_sql

load_dotenv()


@dataclass
class Text2SQLResponse:
    question: str
    sql: str
    rows: list[dict[str, Any]]
    ok: bool
    error: str | None = None
    corrected: bool = False
    source: str = "rule"


class Text2SQLAgent:
    def __init__(self, db_path: str, use_llm: bool = True, max_retries: int = 2):
        self.db_path = db_path
        self.use_llm = use_llm
        self.max_retries = max_retries
        self._llm = None

    def _get_llm(self):
        if not self.use_llm:
            return None
        if not os.getenv("GOOGLE_API_KEY"):
            return None
        if self._llm is None:
            from langchain_google_genai import ChatGoogleGenerativeAI

            self._llm = ChatGoogleGenerativeAI(
                model=os.getenv("TEXT2SQL_LLM_MODEL", "gemini-2.5-flash"),
                google_api_key=os.getenv("GOOGLE_API_KEY"),
                temperature=0,
            )
        return self._llm

    def generate_sql(self, question: str) -> tuple[str, str]:
        """Return (sql, source)."""
        llm = self._get_llm()
        if llm is not None:
            prompt = TEXT2SQL_SYSTEM_PROMPT + "\n\n" + TEXT2SQL_USER_PROMPT.format(
                schema=schema_text(), question=question
            )
            try:
                sql = clean_sql(llm.invoke(prompt).content)
                if sql:
                    return sql, "llm"
            except Exception:
                pass

        sql = generate_sql_by_rules(question)
        if sql:
            return sql, "rule"

        # Safe fallback: show a limited sample so the UI never crashes.
        return (
            "SELECT MaDonHangGiaoHang, TenNguoiNhan, NgayGiaoHang, TrangThaiGiaoHang "
            "FROM DONHANG_GIAOHANG LIMIT 20",
            "fallback",
        )

    def correct_sql(self, question: str, sql: str, error: str) -> Optional[str]:
        llm = self._get_llm()
        if llm is None:
            return None
        prompt = SQL_CORRECTION_PROMPT.format(
            schema=schema_text(), question=question, sql=sql, error=error
        )
        try:
            return clean_sql(llm.invoke(prompt).content)
        except Exception:
            return None

    def ask(self, question: str) -> Text2SQLResponse:
        sql, source = self.generate_sql(question)
        result: QueryResult = execute_sql(self.db_path, sql)
        corrected = False

        retry = 0
        while not result.ok and retry < self.max_retries:
            retry += 1
            fixed_sql = self.correct_sql(question, result.sql, result.error or "")
            if not fixed_sql or fixed_sql == result.sql:
                break
            corrected = True
            result = execute_sql(self.db_path, fixed_sql)

        return Text2SQLResponse(
            question=question,
            sql=result.sql,
            rows=result.rows,
            ok=result.ok,
            error=result.error,
            corrected=corrected,
            source=source,
        )
