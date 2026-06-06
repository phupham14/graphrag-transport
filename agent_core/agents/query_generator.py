"""
Agent 3: Query Generator Agent

Sinh câu lệnh Cypher/SQL từ schema context, câu hỏi đã refine,
và few-shot examples từ Long-term Memory.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import SystemMessage, HumanMessage

from agent_core.config import get_llm
from agent_core.state import AgentState


SYSTEM_PROMPT = """Bạn là chuyên gia Neo4j Cypher. Nhiệm vụ: sinh Cypher query từ câu hỏi tiếng Việt.

Schema:
{schema}

{few_shot_section}

Quy tắc bắt buộc:
- Chỉ trả về Cypher query thuần túy, KHÔNG có markdown, KHÔNG có backtick, KHÔNG có giải thích.
- Chỉ dùng MATCH/WHERE/RETURN/ORDER BY/LIMIT/count/sum/avg/collect — KHÔNG dùng CREATE/DELETE/SET.
- Sử dụng đúng tên property và relationship như trong schema.
- Nếu câu hỏi yêu cầu thống kê, dùng aggregate functions phù hợp.
- Nếu câu hỏi liên quan đến nhiều bảng, sử dụng relationship patterns để JOIN.

{error_context}"""


CYPHER_FEW_SHOTS = """Ví dụ mẫu:
Q: Có bao nhiêu đơn hàng đang giao?
A: MATCH (d:DonHang) WHERE d.trangThaiGiao = "Đang giao" RETURN count(d) AS soLuong

Q: Thành viên nào giao nhiều đơn nhất?
A: MATCH (d:DonHang)-[:DUOC_GIAO_BOI]->(tv:ThanhVien) RETURN tv.ten AS thanhVien, count(d) AS soDon ORDER BY soDon DESC LIMIT 1

Q: Danh sách đơn hàng ở khu vực Cầu Giấy?
A: MATCH (d:DonHang)-[:GIAO_TAI]->(kv:KhuVuc) WHERE kv.ten = "Cầu Giấy" RETURN d.id, d.tenNguoiNhan, d.trangThaiGiao

Q: Tổng doanh thu theo loại mặt hàng?
A: MATCH (d:DonHang)-[c:CHUA]->(lh:LoaiMatHang) RETURN lh.ten AS loai, sum(c.giaTri) AS tongGiaTri ORDER BY tongGiaTri DESC

Q: Khung giờ nào có nhiều đơn hàng nhất?
A: MATCH (d:DonHang)-[:TRONG_KHUNG_GIO]->(tg:KhoangThoiGian) RETURN tg.khungGio AS khungGio, count(d) AS soDon ORDER BY soDon DESC LIMIT 1"""


def _build_few_shot_section(memory_examples: list[dict[str, Any]] | None) -> str:
    """Xây dựng phần few-shot từ ví dụ tĩnh + Long-term Memory."""
    sections = [CYPHER_FEW_SHOTS]

    if memory_examples:
        memory_lines = ["\nVí dụ từ các truy vấn thành công trước đó:"]
        for ex in memory_examples[:3]:  # Tối đa 3 ví dụ từ memory
            q = ex.get("question", "")
            a = ex.get("query", "")
            if q and a:
                memory_lines.append(f"Q: {q}\nA: {a}")
        if len(memory_lines) > 1:
            sections.append("\n".join(memory_lines))

    return "\n\n".join(sections)


def _build_error_context(error_log: str, previous_query: str) -> str:
    """Xây dựng ngữ cảnh lỗi cho prompt self-correction."""
    if not error_log:
        return ""
    return (
        f"\n⚠️ QUAN TRỌNG — Câu truy vấn trước đó bị lỗi:\n"
        f"Query cũ: {previous_query}\n"
        f"Lỗi: {error_log}\n"
        f"Hãy phân tích lỗi trên và sinh lại Cypher query ĐÚNG. "
        f"Đảm bảo tên property và relationship khớp chính xác với schema."
    )


async def query_generator_node(
    state: AgentState,
    memory_examples: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Node sinh câu lệnh Cypher/SQL.

    Sử dụng schema context, entities, và few-shot examples từ
    cả bộ ví dụ tĩnh lẫn Long-term Memory để tăng độ chính xác.

    Nếu có error_log (từ lần thử trước), prompt sẽ bao gồm
    thông tin lỗi để LLM tự sửa.

    Args:
        state: AgentState hiện tại.
        memory_examples: Few-shot examples từ Long-term Memory (optional).

    Returns:
        Dict cập nhật ``generated_query`` trong state.
    """
    llm = get_llm()

    question = state.get("refined_question") or state.get("original_question", "")
    schema = state.get("schema_context", "")
    error_log = state.get("error_log", "")
    previous_query = state.get("generated_query", "")

    few_shot_section = _build_few_shot_section(memory_examples)
    error_context = _build_error_context(error_log, previous_query)

    system_content = SYSTEM_PROMPT.format(
        schema=schema,
        few_shot_section=few_shot_section,
        error_context=error_context,
    )

    response = await llm.ainvoke([
        SystemMessage(content=system_content),
        HumanMessage(content=f"Câu hỏi: {question}"),
    ])

    # Làm sạch output — bỏ markdown nếu LLM thêm
    query = response.content.strip()
    if query.startswith("```"):
        query = query.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    return {"generated_query": query}
