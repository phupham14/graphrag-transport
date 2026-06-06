"""CLI demo for member 3: Vietnamese Text2SQL + SQL self-correction."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from text2sql.db_loader import DEFAULT_DB_PATH, create_database
from text2sql.generator import Text2SQLAgent


def main() -> None:
    parser = argparse.ArgumentParser(description="Vietnamese Text2SQL demo")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite database path")
    parser.add_argument("--init-db", action="store_true", help="Create/recreate SQLite DB from CSV files")
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM and use rule-based fallback only")
    parser.add_argument("--debug", action="store_true", help="Print generated SQL")
    args = parser.parse_args()

    db_path = Path(args.db)
    if args.init_db or not db_path.exists():
        create_database(db_path)
        print(f"Đã tạo SQLite DB: {db_path}")

    agent = Text2SQLAgent(str(db_path), use_llm=not args.no_llm)
    print("Text2SQL Transport - gõ 'quit' để thoát\n")

    while True:
        question = input("Câu hỏi: ").strip()
        if not question:
            continue
        if question.lower() in {"quit", "exit", "thoát"}:
            break

        response = agent.ask(question)
        if args.debug:
            print(f"\n[Source] {response.source}")
            print(f"[SQL] {response.sql}")
            print(f"[Corrected] {response.corrected}")

        if not response.ok:
            print(f"Lỗi SQL: {response.error}\n")
            continue

        if not response.rows:
            print("Không tìm thấy dữ liệu phù hợp.\n")
        else:
            print(json.dumps(response.rows, ensure_ascii=False, indent=2))
            print()


if __name__ == "__main__":
    main()
