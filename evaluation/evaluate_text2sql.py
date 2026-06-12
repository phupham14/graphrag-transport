"""Simple evaluation pipeline for Text2SQL module."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from text2sql.db_loader import DEFAULT_DB_PATH, create_database
from text2sql.generator import Text2SQLAgent

DEFAULT_DATASET = ROOT / "evaluation" / "questions.jsonl"


def load_dataset(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--no-llm", action="store_true")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        create_database(db_path)

    agent = Text2SQLAgent(str(db_path), use_llm=not args.no_llm)
    cases = load_dataset(Path(args.dataset))

    passed = 0
    results = []
    for case in cases:
        response = agent.ask(case["question"])
        sql_upper = response.sql.upper()
        contains_ok = all(token.upper() in sql_upper for token in case.get("expected_sql_contains", []))
        ok = response.ok and contains_ok
        passed += int(ok)
        results.append(
            {
                "id": case["id"],
                "question": case["question"],
                "ok": ok,
                "source": response.source,
                "corrected": response.corrected,
                "sql": response.sql,
                "row_count": len(response.rows),
                "error": response.error,
            }
        )

    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\nExecution Accuracy: {passed}/{len(cases)} = {passed / len(cases):.2%}")


if __name__ == "__main__":
    main()
