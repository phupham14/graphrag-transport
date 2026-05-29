"""
Agent 4: Query Executor Agent

Thực thi câu lệnh Cypher/SQL trên Database thông qua
QueryEngineInterface.execute_query().

Sử dụng RetryPolicy cho lỗi tạm thời (network timeout, connection drop).
Lỗi logic (sai cú pháp, sai tên cột) sẽ được bắt và ghi vào error_log
để Error Correction Agent xử lý.
"""

from __future__ import annotations

from typing import Any

from agent_core.state import AgentState
from agent_core.agents.graph_retrieval import get_engine


async def query_executor_node(state: AgentState) -> dict[str, Any]:
    """Node thực thi câu lệnh Cypher/SQL trên Database.

    Nếu thực thi thành công:
        - Ghi kết quả vào ``query_result``
        - Xóa ``error_log``

    Nếu thực thi thất bại:
        - Ghi thông báo lỗi vào ``error_log``
        - Giữ ``query_result`` rỗng

    Args:
        state: AgentState hiện tại.

    Returns:
        Dict cập nhật ``query_result`` và ``error_log`` trong state.
    """
    engine = get_engine()
    query = state.get("generated_query", "")

    if not query:
        return {
            "query_result": [],
            "error_log": "Không có câu truy vấn nào được sinh ra.",
        }

    try:
        results = engine.execute_query(query)
        return {
            "query_result": results if results else [],
            "error_log": "",  # Xóa lỗi cũ nếu có
        }
    except Exception as e:
        return {
            "query_result": [],
            "error_log": f"{type(e).__name__}: {e}",
        }
