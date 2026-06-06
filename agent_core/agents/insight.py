"""
Agent 6: Insight Agent

Phân tích kết quả truy vấn và sinh mô tả bằng tiếng Việt.
Đồng thời đề xuất loại biểu đồ phù hợp để trực quan hóa.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import SystemMessage, HumanMessage

from agent_core.config import get_llm
from agent_core.state import AgentState


SYSTEM_PROMPT = """Bạn là trợ lý phân tích dữ liệu vận chuyển. Trả lời bằng tiếng Việt, ngắn gọn, rõ ràng.

Nhiệm vụ:
1. Tổng hợp kết quả truy vấn thành câu trả lời tự nhiên cho người dùng.
2. Nếu kết quả rỗng → trả lời "Không tìm thấy dữ liệu phù hợp."
3. Nếu kết quả có dữ liệu số → đề xuất loại biểu đồ phù hợp (bar chart, pie chart, line chart, v.v.)
4. Highlight các insight quan trọng (giá trị lớn nhất, nhỏ nhất, xu hướng, v.v.)

Format trả lời:
📊 [Câu trả lời tổng hợp]

💡 Insight: [Phân tích nổi bật nếu có]

📈 Đề xuất biểu đồ: [Loại chart phù hợp nếu dữ liệu có thể trực quan hóa]"""


async def insight_node(state: AgentState) -> dict[str, Any]:
    """Node phân tích kết quả và sinh insight.

    Args:
        state: AgentState hiện tại.

    Returns:
        Dict cập nhật ``insight_response`` trong state.
    """
    llm = get_llm()

    question = state.get("refined_question") or state.get("original_question", "")
    query = state.get("generated_query", "")
    results = state.get("query_result", [])

    response = await llm.ainvoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=(
            f"Câu hỏi: {question}\n"
            f"Cypher đã chạy: {query}\n"
            f"Kết quả: {results}"
        )),
    ])

    return {"insight_response": response.content.strip()}
