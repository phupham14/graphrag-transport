"""
Agent 2: Graph Retrieval Agent

Gọi QueryEngineInterface.retrieve_schema() để lấy schema context
(các bảng liên quan, join path, column info) dựa trên câu hỏi
và các thực thể đã trích xuất.

Hiện tại sử dụng MockQueryEngine (schema tĩnh).
Khi Thành viên 1 hoàn thiện GraphRAG, module này sẽ tự động
nhận được schema context chính xác hơn mà không cần sửa code.
"""

from __future__ import annotations

from typing import Any

from agent_core.interface import QueryEngineInterface
from agent_core.state import AgentState


# Engine instance sẽ được inject từ workflow.py
_engine: QueryEngineInterface | None = None


def set_engine(engine: QueryEngineInterface) -> None:
    """Inject QueryEngineInterface instance (gọi 1 lần khi khởi tạo)."""
    global _engine
    _engine = engine


def get_engine() -> QueryEngineInterface:
    """Lấy engine đã được inject."""
    if _engine is None:
        raise RuntimeError(
            "QueryEngineInterface chưa được inject. "
            "Gọi set_engine() trước khi chạy workflow."
        )
    return _engine


async def graph_retrieval_node(state: AgentState) -> dict[str, Any]:
    """Node truy vấn GraphRAG để lấy schema context.

    Args:
        state: AgentState hiện tại.

    Returns:
        Dict cập nhật ``schema_context`` trong state.
    """
    engine = get_engine()
    question = state.get("refined_question") or state.get("original_question", "")
    entities = state.get("extracted_entities", [])

    schema_context = engine.retrieve_schema(question, entities)

    return {"schema_context": schema_context}
