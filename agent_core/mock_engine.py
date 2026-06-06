"""
agent_core.mock_engine — Mock adapter cho GraphRAG hiện tại

Wrap logic từ ``graphrag.py`` gốc qua ``QueryEngineInterface``.
Dùng trong giai đoạn phát triển song song: khi Thành viên 1 hoàn thiện
module GraphRAG thực sự, chỉ cần thay thế class này.
"""

from __future__ import annotations

import os
import re
from typing import Any

from langchain_neo4j import Neo4jGraph

from agent_core.config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
from agent_core.interface import QueryEngineInterface


# Schema tĩnh — copy từ graphrag.py gốc để giữ tương thích
_STATIC_SCHEMA = """
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
""".strip()


class MockQueryEngine(QueryEngineInterface):
    """Adapter tạm thời sử dụng Neo4j + schema tĩnh.

    Khi Thành viên 1 hoàn thiện GraphRAG thực sự (duyệt đồ thị tìm
    join path, ánh xạ entity tự động), chỉ cần viết class mới kế thừa
    ``QueryEngineInterface`` và truyền vào workflow thay cho class này.
    """

    def __init__(self) -> None:
        self._graph = Neo4jGraph(
            url=NEO4J_URI,
            username=NEO4J_USERNAME,
            password=NEO4J_PASSWORD,
            refresh_schema=False,
        )

    # ── Interface methods ─────────────────────────────────────────────────────

    def retrieve_schema(self, question: str, entities: list[str]) -> str:
        """Trả về schema tĩnh (chưa có GraphRAG thực sự).

        Khi Thành viên 1 hoàn thiện, hàm này sẽ được thay thế bằng
        logic duyệt đồ thị schema → tìm bảng liên quan → trả join path.
        """
        # TODO: Thành viên 1 sẽ implement logic GraphRAG tại đây
        return _STATIC_SCHEMA

    def execute_query(self, query: str) -> list[dict[str, Any]]:
        """Thực thi câu lệnh Cypher trên Neo4j.

        Args:
            query: Câu lệnh Cypher thuần túy.

        Returns:
            Danh sách dict chứa kết quả truy vấn.

        Raises:
            Exception: Nếu Cypher bị lỗi cú pháp hoặc thực thi thất bại.
        """
        # Bỏ markdown code block nếu LLM thêm vào
        clean = re.sub(r"```(?:cypher|sql)?\s*", "", query)
        clean = clean.replace("```", "").strip()
        return self._graph.query(clean)

    def get_full_schema(self) -> str:
        """Trả về toàn bộ schema text tĩnh."""
        return _STATIC_SCHEMA
