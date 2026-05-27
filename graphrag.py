"""
GraphRAG chatbot: hỏi đáp bằng tiếng Việt trên dữ liệu vận chuyển trong Neo4j.
Dùng custom chain thay vì GraphCypherQAChain để kiểm soát chặt hơn.
"""

import os
import re
from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate

load_dotenv()

# ── Neo4j ─────────────────────────────────────────────────────────────────────

graph = Neo4jGraph(
    url=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    username=os.getenv("NEO4J_USERNAME", "neo4j"),
    password=os.getenv("NEO4J_PASSWORD", "password"),
    refresh_schema=False,
)

SCHEMA = """
Node properties (tên property PHẢI viết đúng như sau):
- KhachHang   {id, ten, tenShop, sdt, email, diaChi}
- ThanhVien   {id, ten, ngaySinh, gioiTinh, sdt, diaChi}
- DonHang     {id, tenNguoiNhan, diaChiGiao, sdt, ngay, thanhToan, trangThaiDuyet, trangThaiGiao}
- DichVu      {id, ten}
- KhuVuc      {id, ten}
- LoaiMatHang {id, ten}
- KhoangThoiGian {id, khungGio}

Relationship properties:
- [:CHUA] {tenHang, soLuong, khoiLuong, giaTri}

Relationships:
(:KhachHang)-[:THUOC_KHU_VUC]->(:KhuVuc)
(:DonHang)-[:DAT_BOI]->(:KhachHang)
(:DonHang)-[:DUOC_GIAO_BOI]->(:ThanhVien)
(:DonHang)-[:SU_DUNG]->(:DichVu)
(:DonHang)-[:GIAO_TAI]->(:KhuVuc)
(:DonHang)-[:TRONG_KHUNG_GIO]->(:KhoangThoiGian)
(:DonHang)-[:CHUA]->(:LoaiMatHang)
(:ThanhVien)-[:DANG_KY]->(:KhoangThoiGian)

Giá trị thực tế trong database:
- trangThaiGiao: "Đã giao" | "Đang giao" | "Chưa giao"
- trangThaiDuyet: "Đã duyệt" | "Chờ duyệt"
- thanhToan: "Tiền mặt" | "Chuyển khoản"
- gioiTinh: "Nam" | "Nữ"
- DichVu.ten: "Giao hàng nhanh" | "Giao hàng tiết kiệm" | "Giao hàng hỏa tốc"
- LoaiMatHang.ten: "Đồ ăn" | "Tài liệu" | "Điện tử"
- KhuVuc.ten: "Cầu Giấy" | "Ba Đình" | "Đống Đa" | "Hoàng Mai" | "Thanh Xuân" | "Hai Bà Trưng" | "Tây Hồ"
- KhoangThoiGian.khungGio: "07:00 - 09:00" | "09:00 - 11:00" | "13:00 - 15:00" | "15:00 - 17:00" | "18:00 - 20:00"
"""

# ── LLM ───────────────────────────────────────────────────────────────────────

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0,
)

# ── Prompts ───────────────────────────────────────────────────────────────────

CYPHER_PROMPT = PromptTemplate(
    input_variables=["schema", "question"],
    template="""Bạn là chuyên gia Neo4j Cypher. Nhiệm vụ: sinh Cypher query từ câu hỏi.

Schema:
{schema}

Ví dụ mẫu:
Q: Có bao nhiêu đơn hàng đang giao?
A: MATCH (d:DonHang) WHERE d.trangThaiGiao = "Đang giao" RETURN count(d) AS soLuong

Q: Thành viên nào giao nhiều đơn nhất?
A: MATCH (d:DonHang)-[:DUOC_GIAO_BOI]->(tv:ThanhVien) RETURN tv.ten AS thanhVien, count(d) AS soDon ORDER BY soDon DESC LIMIT 1

Q: Danh sách đơn hàng ở khu vực Cầu Giấy?
A: MATCH (d:DonHang)-[:GIAO_TAI]->(kv:KhuVuc) WHERE kv.ten = "Cầu Giấy" RETURN d.id, d.tenNguoiNhan, d.trangThaiGiao

Q: Tổng doanh thu theo loại mặt hàng?
A: MATCH (d:DonHang)-[c:CHUA]->(lh:LoaiMatHang) RETURN lh.ten AS loai, sum(c.giaTri) AS tongGiaTri ORDER BY tongGiaTri DESC

Q: Khung giờ nào có nhiều đơn hàng nhất?
A: MATCH (d:DonHang)-[:TRONG_KHUNG_GIO]->(tg:KhoangThoiGian) RETURN tg.khungGio AS khungGio, count(d) AS soDon ORDER BY soDon DESC LIMIT 1

Quy tắc bắt buộc:
- Chỉ trả về Cypher query thuần túy, KHÔNG có markdown, KHÔNG có backtick, KHÔNG có giải thích.
- Chỉ dùng MATCH/WHERE/RETURN/ORDER BY/LIMIT/count/sum — KHÔNG dùng CREATE/DELETE/SET.

Câu hỏi: {question}
Cypher:""",
)

QA_PROMPT = PromptTemplate(
    input_variables=["question", "cypher", "context"],
    template="""Bạn là trợ lý phân tích dữ liệu vận chuyển. Trả lời bằng tiếng Việt, ngắn gọn, rõ ràng.
Nếu kết quả rỗng → trả lời "Không tìm thấy dữ liệu phù hợp."

Câu hỏi: {question}
Cypher đã chạy: {cypher}
Kết quả: {context}

Câu trả lời:""",
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def clean_cypher(raw: str) -> str:
    """Bỏ markdown code block mà Gemini hay thêm vào."""
    raw = re.sub(r"```(?:cypher|sql)?\s*", "", raw)
    raw = raw.replace("```", "").strip()
    return raw


def ask(question: str, debug: bool = False) -> str:
    # Bước 1: sinh Cypher
    cypher_raw = llm.invoke(CYPHER_PROMPT.format(schema=SCHEMA, question=question)).content
    cypher = clean_cypher(cypher_raw)

    if debug:
        print(f"\n[Cypher] {cypher}")

    # Bước 2: thực thi trên Neo4j
    try:
        results = graph.query(cypher)
    except Exception as e:
        if debug:
            print(f"[Neo4j Error] {e}")
        return f"Lỗi khi thực thi query: {e}"

    if debug:
        print(f"[Results] {results}")

    # Bước 3: tổng hợp câu trả lời
    answer = llm.invoke(
        QA_PROMPT.format(question=question, cypher=cypher, context=str(results))
    )
    return answer.content


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("GraphRAG - Hệ thống vận chuyển (gõ 'debug' để bật/tắt log Cypher)\n")
    debug_mode = False

    while True:
        try:
            question = input("Câu hỏi: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "thoát"):
            break
        if question.lower() == "debug":
            debug_mode = not debug_mode
            print(f"Debug mode: {'ON' if debug_mode else 'OFF'}\n")
            continue

        try:
            answer = ask(question, debug=debug_mode)
            print(f"Trả lời: {answer}\n")
        except Exception as e:
            print(f"Lỗi: {e}\n")
