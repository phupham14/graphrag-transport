"""
agent_core.state — Định nghĩa Agent State

State dùng chung (shared) giữa Supervisor và tất cả Worker Agent.
Sử dụng TypedDict + reducer ``add_messages`` theo chuẩn LangGraph 1.2.
"""

from __future__ import annotations

from typing import Annotated, Any, Dict, List, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State trung tâm của toàn bộ Multi-Agent Workflow.

    Mỗi trường tương ứng với một phần dữ liệu được truyền qua các Agent.
    Trường ``messages`` sử dụng reducer ``add_messages`` để tự động append
    thay vì ghi đè — đảm bảo lịch sử hội thoại không bao giờ bị mất.
    """

    # ── Lịch sử hội thoại (append-only qua reducer) ──────────────────────────
    messages: Annotated[list[BaseMessage], add_messages]

    # ── Câu hỏi gốc từ user ──────────────────────────────────────────────────
    original_question: str

    # ── Câu hỏi đã được refine (bằng Short-term Memory / ngữ cảnh chat) ─────
    refined_question: str

    # ── Các thực thể được trích xuất từ câu hỏi ──────────────────────────────
    extracted_entities: list[str]

    # ── Schema context từ GraphRAG (danh sách bảng, cột, join path) ───────────
    schema_context: str

    # ── Câu truy vấn được sinh ra (Cypher hoặc SQL) ──────────────────────────
    generated_query: str

    # ── Kết quả thực thi thành công ───────────────────────────────────────────
    query_result: list[dict[str, Any]]

    # ── Thông báo lỗi nếu thực thi thất bại ──────────────────────────────────
    error_log: str

    # ── Bộ đếm số lần tự sửa lỗi trong lượt hiện tại ────────────────────────
    retry_count: int

    # ── Phân tích insight cuối cùng trả cho user ─────────────────────────────
    insight_response: str

    # ── Agent tiếp theo do Supervisor quyết định ──────────────────────────────
    next_agent: str
