"""
agent_core.memory — Quản lý Short-term & Long-term Memory

Short-term Memory:
    Sử dụng MemorySaver (checkpointer) từ langgraph-checkpoint.
    Lưu trữ toàn bộ AgentState theo thread_id (phiên chat).
    Swap sang PostgresSaver / RedisSaver cho production.

Long-term Memory:
    Sử dụng InMemoryStore từ LangGraph Store API.
    Lưu trữ cross-thread: schema mappings, successful queries, common joins.
    Swap sang PostgresStore cho production.
"""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore


# ── Namespaces cho Long-term Memory ──────────────────────────────────────────

NS_SCHEMA_MAPPINGS = ("schema_mappings",)
NS_SUCCESSFUL_QUERIES = ("successful_queries",)
NS_COMMON_JOINS = ("common_joins",)


def create_checkpointer() -> MemorySaver:
    """Tạo Short-term Memory checkpointer.

    Trong quá trình phát triển, sử dụng MemorySaver (in-memory).
    Khi triển khai production, thay bằng:
        from langgraph.checkpoint.postgres import PostgresSaver
        return PostgresSaver(conn_string="postgresql://...")
    """
    return MemorySaver()


def create_store() -> InMemoryStore:
    """Tạo Long-term Memory store.

    Trong quá trình phát triển, sử dụng InMemoryStore (in-memory).
    Khi triển khai production, thay bằng:
        from langgraph.store.postgres import PostgresStore
        return PostgresStore(conn_string="postgresql://...")
    """
    return InMemoryStore()


# ── Helper Functions cho Long-term Memory Operations ─────────────────────────

def _make_key(text: str) -> str:
    """Tạo key ngắn gọn từ text bằng hash MD5."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]


async def save_successful_query(
    store: InMemoryStore,
    question: str,
    query: str,
    result_summary: str,
) -> None:
    """Lưu một cặp (question, query) đã chạy thành công vào Long-term Memory.

    Khi sinh query mới, Query Generator Agent sẽ đọc các mẫu này
    làm few-shot examples để tăng độ chính xác.

    Args:
        store: Instance của InMemoryStore.
        question: Câu hỏi gốc của user.
        query: Câu lệnh Cypher/SQL đã chạy thành công.
        result_summary: Tóm tắt ngắn gọn kết quả.
    """
    key = _make_key(question)
    await store.aput(
        NS_SUCCESSFUL_QUERIES,
        key,
        {
            "question": question,
            "query": query,
            "result_summary": result_summary,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        },
    )


async def save_schema_mapping(
    store: InMemoryStore,
    term: str,
    mapped_to: str,
) -> None:
    """Lưu ánh xạ thuật ngữ tiếng Việt → tên bảng/cột.

    Ví dụ: "shipper" → "ThanhVien", "khu vực" → "KhuVuc"

    Args:
        store: Instance của InMemoryStore.
        term: Thuật ngữ tiếng Việt.
        mapped_to: Tên bảng/cột tương ứng trong CSDL.
    """
    key = _make_key(term)
    await store.aput(
        NS_SCHEMA_MAPPINGS,
        key,
        {
            "term": term,
            "mapped_to": mapped_to,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        },
    )


async def get_similar_queries(
    store: InMemoryStore,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Lấy các query thành công gần nhất từ Long-term Memory.

    Dùng làm few-shot examples cho Query Generator Agent.

    Args:
        store: Instance của InMemoryStore.
        limit: Số lượng mẫu tối đa.

    Returns:
        Danh sách dict chứa các cặp (question, query) thành công.
    """
    items = await store.asearch(NS_SUCCESSFUL_QUERIES, limit=limit)
    return [item.value for item in items]


async def get_schema_mappings(
    store: InMemoryStore,
) -> list[dict[str, Any]]:
    """Lấy toàn bộ ánh xạ thuật ngữ từ Long-term Memory.

    Args:
        store: Instance của InMemoryStore.

    Returns:
        Danh sách dict chứa các cặp (term, mapped_to).
    """
    items = await store.asearch(NS_SCHEMA_MAPPINGS, limit=100)
    return [item.value for item in items]
