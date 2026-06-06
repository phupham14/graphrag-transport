"""
Agent 5: Error Correction Agent

Phân tích lỗi từ Query Executor, tăng retry_count,
và chuẩn bị ngữ cảnh để Query Generator sinh lại query đúng.

Agent này KHÔNG tự sinh query — nó chỉ phân tích lỗi và
cập nhật state để Supervisor chuyển lại cho Query Generator.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import SystemMessage, HumanMessage

from agent_core.config import get_llm
from agent_core.state import AgentState


ANALYSIS_PROMPT = """Bạn là chuyên gia phân tích lỗi Cypher/SQL. Phân tích lỗi sau và đưa ra hướng dẫn sửa ngắn gọn.

Câu query bị lỗi:
{query}

Thông báo lỗi:
{error}

Schema hiện tại:
{schema}

Hãy phân tích nguyên nhân lỗi và đưa ra hướng dẫn cụ thể để sửa query.
Trả lời ngắn gọn, tập trung vào:
1. Nguyên nhân lỗi (sai tên property? sai relationship? sai cú pháp?)
2. Cách sửa cụ thể (thay X bằng Y, thêm/bớt phần Z)

Chỉ trả lời phân tích, KHÔNG sinh query mới."""


async def error_correction_node(state: AgentState) -> dict[str, Any]:
    """Node phân tích lỗi và chuẩn bị ngữ cảnh sửa lỗi.

    Tăng retry_count lên 1 và bổ sung phân tích lỗi chi tiết
    vào error_log để Query Generator sử dụng khi sinh lại query.

    Args:
        state: AgentState hiện tại.

    Returns:
        Dict cập nhật ``error_log`` (bổ sung phân tích) và ``retry_count``.
    """
    llm = get_llm()

    query = state.get("generated_query", "")
    error = state.get("error_log", "")
    schema = state.get("schema_context", "")
    current_retry = state.get("retry_count", 0)

    # Gọi LLM phân tích lỗi
    response = await llm.ainvoke([
        SystemMessage(content="Bạn là chuyên gia debug Cypher/SQL."),
        HumanMessage(content=ANALYSIS_PROMPT.format(
            query=query,
            error=error,
            schema=schema,
        )),
    ])

    # Bổ sung phân tích vào error_log để Generator sử dụng
    enriched_error = (
        f"{error}\n\n"
        f"--- Phân tích lỗi (lần thử {current_retry + 1}) ---\n"
        f"{response.content.strip()}"
    )

    return {
        "error_log": enriched_error,
        "retry_count": current_retry + 1,
    }
