"""
agent_core.supervisor — Supervisor Agent (Điều phối trung tâm)

Supervisor là "bộ não" của hệ thống Multi-Agent:
1. Nhận câu hỏi từ user
2. Đọc Short-term Memory để refine câu hỏi (xử lý multi-turn)
3. Điều phối 6 Worker Agent theo thứ tự logic
4. Xử lý Self-Correction loop khi query thất bại
5. Tổng hợp kết quả cuối cùng

Sử dụng deterministic routing (không dùng LLM để route)
để đảm bảo luồng xử lý ổn định và dễ debug.
"""

from __future__ import annotations

from typing import Any, Literal

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)

from agent_core.config import get_llm, MAX_RETRIES, SUPERVISOR_MODEL
from agent_core.state import AgentState


# ── Node: Nhận input và refine câu hỏi ──────────────────────────────────────

REFINE_PROMPT = """Bạn là trợ lý giúp viết lại câu hỏi cho rõ ràng và đầy đủ.

Lịch sử hội thoại:
{history}

Câu hỏi mới nhất: {question}

Nếu câu hỏi mới nhất tham chiếu đến ngữ cảnh từ hội thoại trước đó
(ví dụ: "Còn Sơn Trà thì sao?", "Chỉ lấy năm 2017 thôi", "Sắp xếp giảm dần"),
hãy viết lại thành câu hỏi ĐẦY ĐỦ, KHÔNG phụ thuộc vào ngữ cảnh.

Nếu câu hỏi đã đủ rõ ràng, giữ nguyên.

Chỉ trả về câu hỏi đã viết lại, KHÔNG giải thích."""


async def receive_and_refine_node(state: AgentState) -> dict[str, Any]:
    """Node đầu tiên: nhận input và refine câu hỏi bằng Short-term Memory.

    Đọc lịch sử hội thoại (messages) để hiểu ngữ cảnh,
    sau đó viết lại câu hỏi thành dạng đầy đủ.

    Ví dụ:
        Lượt 1: "Liệt kê đơn hàng ở Hải Châu"
        Lượt 2: "Còn Sơn Trà thì sao?"
        → Refine: "Liệt kê đơn hàng ở Sơn Trà"
    """
    llm = get_llm(model=SUPERVISOR_MODEL)
    question = state.get("original_question", "")
    messages = state.get("messages", [])

    # Nếu không có lịch sử, câu hỏi đã đủ rõ
    if len(messages) <= 1:
        return {
            "refined_question": question,
            "error_log": "",
            "retry_count": 0,
        }

    # Xây dựng lịch sử từ messages (bỏ message cuối = câu hỏi hiện tại)
    history_lines = []
    for msg in messages[:-1]:
        role = "User" if isinstance(msg, HumanMessage) else "Assistant"
        content = msg.content if hasattr(msg, "content") else str(msg)
        # Rút gọn nếu quá dài
        if len(content) > 200:
            content = content[:200] + "..."
        history_lines.append(f"{role}: {content}")

    history_text = "\n".join(history_lines[-10:])  # Giữ tối đa 10 lượt gần nhất

    response = await llm.ainvoke([
        SystemMessage(content="Bạn viết lại câu hỏi cho rõ ràng dựa trên ngữ cảnh."),
        HumanMessage(content=REFINE_PROMPT.format(
            history=history_text,
            question=question,
        )),
    ])

    refined = response.content.strip()
    # Nếu LLM trả về chuỗi rỗng hoặc quá ngắn, giữ nguyên câu gốc
    if len(refined) < 5:
        refined = question

    return {
        "refined_question": refined,
        "error_log": "",      # Reset error cho lượt mới
        "retry_count": 0,     # Reset retry counter
    }


# ── Node: Tổng hợp kết quả cuối cùng ────────────────────────────────────────

async def finalize_node(state: AgentState) -> dict[str, Any]:
    """Node cuối: tổng hợp kết quả và đóng gói response.

    Thêm AIMessage chứa insight vào messages để MemorySaver
    lưu lại cho các lượt tiếp theo.
    """
    insight = state.get("insight_response", "")
    query = state.get("generated_query", "")

    # Tạo response message hoàn chỉnh
    if insight:
        response_text = insight
        if query:
            response_text = f"🔍 Query: {query}\n\n{insight}"
    else:
        response_text = "Xin lỗi, tôi không thể xử lý yêu cầu này."

    return {
        "messages": [AIMessage(content=response_text)],
    }


# ── Node: Xử lý lỗi cuối cùng (Fallback) ───────────────────────────────────

async def fallback_error_node(state: AgentState) -> dict[str, Any]:
    """Node xử lý khi vượt quá MAX_RETRIES.

    Thay vì crash, trả thông báo lỗi thân thiện cho user.
    """
    error = state.get("error_log", "Lỗi không xác định")
    retry_count = state.get("retry_count", 0)
    query = state.get("generated_query", "")

    error_msg = (
        f"⚠️ Xin lỗi, tôi không thể tạo truy vấn chính xác sau {retry_count} lần thử.\n\n"
        f"🔍 Query cuối: {query}\n"
        f"❌ Lỗi: {error.split(chr(10))[0]}\n\n"  # Chỉ lấy dòng lỗi đầu tiên
        f"💡 Gợi ý: Thử diễn đạt câu hỏi rõ ràng hơn hoặc "
        f"chia thành các câu hỏi nhỏ hơn."
    )

    return {
        "insight_response": error_msg,
    }


# ── Routing functions ────────────────────────────────────────────────────────

def route_after_execution(state: AgentState) -> str:
    """Quyết định bước tiếp theo sau khi Query Executor chạy xong.

    Returns:
        "error_correction" nếu có lỗi VÀ còn retry
        "fallback_error" nếu có lỗi VÀ hết retry
        "insight" nếu thành công
    """
    error_log = state.get("error_log", "")
    retry_count = state.get("retry_count", 0)

    if error_log:
        if retry_count < MAX_RETRIES:
            return "error_correction"
        else:
            return "fallback_error"
    return "insight"


def route_after_correction(state: AgentState) -> str:
    """Sau Error Correction, luôn quay lại Query Generator."""
    return "query_generator"
