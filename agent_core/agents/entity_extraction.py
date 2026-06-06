"""
Agent 1: Entity Extraction Agent

Trích xuất các thực thể (entity) và từ khóa cốt lõi từ câu hỏi
của user. Output được sử dụng bởi Graph Retrieval Agent để tìm
các bảng liên quan trong schema.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import SystemMessage, HumanMessage

from agent_core.config import get_llm
from agent_core.state import AgentState


SYSTEM_PROMPT = """Bạn là chuyên gia trích xuất thực thể (Entity Extraction) từ câu hỏi tiếng Việt liên quan đến dữ liệu vận chuyển/giao hàng.

Nhiệm vụ: Phân tích câu hỏi và trích xuất các thực thể quan trọng.

Các loại thực thể cần tìm:
- Tên khu vực (ví dụ: Cầu Giấy, Ba Đình, Hải Châu)
- Tên người (khách hàng, thành viên giao hàng)
- Dịch vụ (giao hàng nhanh, tiết kiệm, hỏa tốc)
- Loại mặt hàng (đồ ăn, tài liệu, điện tử)
- Trạng thái (đang giao, đã giao, chưa giao, đã duyệt, chờ duyệt)
- Phương thức thanh toán (tiền mặt, chuyển khoản)
- Giới tính (nam, nữ)
- Khung giờ (07:00 - 09:00, v.v.)
- Số liệu, ngày tháng, năm

Trả về JSON array chứa các entity đã trích xuất.
Ví dụ: ["Cầu Giấy", "đang giao", "nam"]

Chỉ trả về JSON array, KHÔNG giải thích."""


async def entity_extraction_node(state: AgentState) -> dict[str, Any]:
    """Node trích xuất thực thể từ câu hỏi đã refine.

    Args:
        state: AgentState hiện tại.

    Returns:
        Dict cập nhật ``extracted_entities`` trong state.
    """
    llm = get_llm()
    question = state.get("refined_question") or state.get("original_question", "")

    response = await llm.ainvoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Câu hỏi: {question}"),
    ])

    # Parse JSON array từ response
    try:
        content = response.content.strip()
        # Loại bỏ markdown code block nếu có
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        entities = json.loads(content)
        if not isinstance(entities, list):
            entities = [str(entities)]
    except (json.JSONDecodeError, IndexError):
        # Fallback: tách theo dấu phẩy
        entities = [e.strip().strip('"') for e in response.content.split(",") if e.strip()]

    return {"extracted_entities": entities}
