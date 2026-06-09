"""
Streamlit UI cho GraphRAG Transport
Hỗ trợ cả GraphRAG (Neo4j) và Text2SQL (SQLite)
"""

import streamlit as st
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GraphRAG Transport",
    page_icon="🚚",
    layout="wide",
)

st.title("🚚 GraphRAG Transport Chatbot")
st.caption("Hỏi đáp dữ liệu vận chuyển")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Cấu hình")

    mode = st.radio(
        "Chế độ",
        ["GraphRAG (Neo4j)", "Text2SQL (SQLite)"],
        help="GraphRAG dùng Neo4j Knowledge Graph. Text2SQL dùng SQLite thuần."
    )

    show_debug = st.toggle("Hiện câu Cypher / SQL", value=True)

    st.divider()

    st.subheader("Ví dụ câu hỏi")
    example_questions = [
        "Có bao nhiêu đơn hàng đang giao?",
        "Thành viên nào giao nhiều đơn nhất?",
        "Danh sách đơn hàng ở khu vực Cầu Giấy?",
        "Tổng doanh thu theo loại mặt hàng?",
        "Khung giờ nào có nhiều đơn nhất?",
        "Khách hàng nào được shipper nam giao hàng?",
    ]
    for q in example_questions:
        if st.button(q, use_container_width=True, key=q):
            st.session_state["input_question"] = q

    st.divider()
    if st.button("🗑️ Xóa lịch sử chat", use_container_width=True):
        st.session_state["messages"] = []
        st.rerun()

# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# ── Load backends (lazy) ──────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Đang kết nối Neo4j...")
def load_graphrag():
    from langchain_neo4j import Neo4jGraph
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.prompts import PromptTemplate
    import re

    graph = Neo4jGraph(
        url=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        username=os.getenv("NEO4J_USERNAME", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "password"),
        refresh_schema=False,
    )

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0,
    )

    SCHEMA = """
Node properties:
- KhachHang {id, ten, tenShop, sdt, email, diaChi}
- ThanhVien {id, ten, ngaySinh, gioiTinh, sdt, diaChi}
- DonHang {id, tenNguoiNhan, diaChiGiao, sdt, ngay, thanhToan, trangThaiDuyet, trangThaiGiao}
- DichVu {id, ten}
- KhuVuc {id, ten}
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

Giá trị thực tế:
- trangThaiGiao: "Đã giao" | "Đang giao" | "Chưa giao"
- trangThaiDuyet: "Đã duyệt" | "Chờ duyệt"
- thanhToan: "Tiền mặt" | "Chuyển khoản"
- gioiTinh: "Nam" | "Nữ"
- DichVu.ten: "Giao hàng nhanh" | "Giao hàng tiết kiệm" | "Giao hàng hỏa tốc"
- LoaiMatHang.ten: "Đồ ăn" | "Tài liệu" | "Điện tử"
- KhuVuc.ten: "Cầu Giấy" | "Ba Đình" | "Đống Đa" | "Hoàng Mai" | "Thanh Xuân" | "Hai Bà Trưng" | "Tây Hồ"
- KhoangThoiGian.khungGio: "07:00 - 09:00" | "09:00 - 11:00" | "13:00 - 15:00" | "15:00 - 17:00" | "18:00 - 20:00"
"""

    CYPHER_PROMPT = PromptTemplate(
        input_variables=["schema", "question"],
        template="""Bạn là chuyên gia Neo4j Cypher. Sinh Cypher query từ câu hỏi.

Schema:
{schema}

Ví dụ:
Q: Có bao nhiêu đơn hàng đang giao?
A: MATCH (d:DonHang) WHERE d.trangThaiGiao = "Đang giao" RETURN count(d) AS soLuong

Q: Thành viên nào giao nhiều đơn nhất?
A: MATCH (d:DonHang)-[:DUOC_GIAO_BOI]->(tv:ThanhVien) RETURN tv.ten AS thanhVien, count(d) AS soDon ORDER BY soDon DESC LIMIT 1

Q: Danh sách đơn hàng ở khu vực Cầu Giấy?
A: MATCH (d:DonHang)-[:GIAO_TAI]->(kv:KhuVuc) WHERE kv.ten = "Cầu Giấy" RETURN d.id, d.tenNguoiNhan, d.trangThaiGiao

Q: Tổng doanh thu theo loại mặt hàng?
A: MATCH (d:DonHang)-[c:CHUA]->(lh:LoaiMatHang) RETURN lh.ten AS loai, sum(c.giaTri) AS tongGiaTri ORDER BY tongGiaTri DESC

Quy tắc: chỉ trả về Cypher thuần, không markdown, không backtick, không giải thích.

Câu hỏi: {question}
Cypher:""",
    )

    QA_PROMPT = PromptTemplate(
        input_variables=["question", "cypher", "context"],
        template="""Bạn là trợ lý phân tích dữ liệu vận chuyển. Trả lời tiếng Việt, ngắn gọn.
Nếu kết quả rỗng → "Không tìm thấy dữ liệu phù hợp."

Câu hỏi: {question}
Cypher đã chạy: {cypher}
Kết quả: {context}

Câu trả lời:""",
    )

    def clean_cypher(raw):
        raw = re.sub(r"```(?:cypher|sql)?\s*", "", raw)
        return raw.replace("```", "").strip()

    def ask(question):
        cypher_raw = llm.invoke(CYPHER_PROMPT.format(schema=SCHEMA, question=question)).content
        cypher = clean_cypher(cypher_raw)
        try:
            results = graph.query(cypher)
            error = None
        except Exception as e:
            results = []
            error = str(e)
        answer = llm.invoke(
            QA_PROMPT.format(question=question, cypher=cypher, context=str(results))
        ).content
        return answer, cypher, results, error

    return ask


@st.cache_resource(show_spinner="Đang tải Text2SQL agent...")
def load_text2sql():
    from text2sql.db_loader import DEFAULT_DB_PATH, create_database
    from text2sql.generator import Text2SQLAgent

    db_path = Path(DEFAULT_DB_PATH)
    if not db_path.exists():
        create_database(db_path)

    agent = Text2SQLAgent(str(db_path), use_llm=bool(os.getenv("GOOGLE_API_KEY")))

    def ask(question):
        response = agent.ask(question)
        if not response.ok:
            answer = f"❌ Lỗi SQL: {response.error}"
        elif not response.rows:
            answer = "Không tìm thấy dữ liệu phù hợp."
        else:
            import json
            answer = json.dumps(response.rows, ensure_ascii=False, indent=2)
        sql = response.sql
        corrected = response.corrected
        source = response.source
        return answer, sql, corrected, source

    return ask


# ── Chat history display ──────────────────────────────────────────────────────
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and show_debug and msg.get("debug"):
            with st.expander("🔍 Debug info"):
                st.code(msg["debug"], language="cypher")
                if msg.get("extra"):
                    st.caption(msg["extra"])

# ── Input ─────────────────────────────────────────────────────────────────────
# Nhận câu hỏi từ sidebar button
prefill = st.session_state.pop("input_question", "")

question = st.chat_input("Nhập câu hỏi bằng tiếng Việt...", key="chat_input")

# Ưu tiên câu hỏi từ sidebar nếu có
if prefill and not question:
    question = prefill

# ── Handle question ───────────────────────────────────────────────────────────
if question:
    st.session_state["messages"].append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Đang xử lý..."):
            try:
                if mode == "GraphRAG (Neo4j)":
                    ask_fn = load_graphrag()
                    answer, cypher, results, error = ask_fn(question)
                    debug_text = cypher
                    extra = f"Kết quả raw: {results}" if results else (f"Lỗi Neo4j: {error}" if error else "")
                else:
                    ask_fn = load_text2sql()
                    answer, sql, corrected, source = ask_fn(question)
                    debug_text = sql
                    extra = f"Source: {source} | Corrected: {corrected}"

                st.markdown(answer)

                if show_debug and debug_text:
                    with st.expander("🔍 Debug info"):
                        st.code(debug_text, language="sql" if mode == "Text2SQL (SQLite)" else "cypher")
                        if extra:
                            st.caption(extra)

                st.session_state["messages"].append({
                    "role": "assistant",
                    "content": answer,
                    "debug": debug_text if show_debug else None,
                    "extra": extra if show_debug else None,
                })

            except Exception as e:
                err_msg = f"❌ Lỗi: {e}"
                st.error(err_msg)
                st.session_state["messages"].append({"role": "assistant", "content": err_msg})
