"""
Relational schema metadata for Vietnamese Text2SQL.
This module is intentionally independent from Neo4j so member 3 can work on
SQL generation/validation/self-correction with SQLite or another SQL database.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class TableSchema:
    name: str
    columns: List[str]
    description: str


TABLES: Dict[str, TableSchema] = {
    "KHUVUC": TableSchema(
        "KHUVUC",
        ["MaKhuVuc", "TenKhuVuc"],
        "Danh mục khu vực giao hàng",
    ),
    "DICHVU": TableSchema(
        "DICHVU",
        ["MaDichVu", "TenDichVu"],
        "Danh mục dịch vụ giao hàng",
    ),
    "LOAIMATHANG": TableSchema(
        "LOAIMATHANG",
        ["MaLoaiMatHang", "TenLoaiMatHang"],
        "Danh mục loại mặt hàng",
    ),
    "KHOANGTHOIGIAN": TableSchema(
        "KHOANGTHOIGIAN",
        ["MaKhoangThoiGian", "KhungGio"],
        "Danh mục khung giờ giao hàng",
    ),
    "KHACHHANG": TableSchema(
        "KHACHHANG",
        [
            "MaKhachHang",
            "MaKhuVuc",
            "TenKhachHang",
            "TenShop",
            "SoDienThoai",
            "Email",
            "DiaChi",
        ],
        "Khách hàng đặt đơn giao hàng",
    ),
    "THANHVIENGIAOHANG": TableSchema(
        "THANHVIENGIAOHANG",
        [
            "MaThanhVienGiaoHang",
            "TenThanhVienGiaoHang",
            "NgaySinh",
            "GioiTinh",
            "SoDienThoai",
            "DiaChi",
        ],
        "Thành viên/shipper giao hàng",
    ),
    "DONHANG_GIAOHANG": TableSchema(
        "DONHANG_GIAOHANG",
        [
            "MaDonHangGiaoHang",
            "MaKhachHang",
            "MaThanhVienGiaoHang",
            "MaDichVu",
            "MaKhuVuc",
            "TenNguoiNhan",
            "DiaChiGiaoHang",
            "SoDienThoaiNguoiNhan",
            "MaKhoangThoiGian",
            "NgayGiaoHang",
            "PhuongThucThanhToan",
            "TrangThaiDuyet",
            "TrangThaiGiaoHang",
        ],
        "Đơn hàng giao hàng",
    ),
    "CHITIET_DONHANG": TableSchema(
        "CHITIET_DONHANG",
        [
            "MaDonHangGiaoHang",
            "TenHang",
            "SoLuong",
            "KhoiLuong",
            "MaLoaiMatHang",
            "GiaTriHang",
        ],
        "Chi tiết hàng hóa trong đơn hàng",
    ),
    "DANGKYGIAOHANG": TableSchema(
        "DANGKYGIAOHANG",
        ["MaThanhVienGiaoHang", "MaKhoangThoiGian"],
        "Thành viên đăng ký khung giờ giao hàng",
    ),
}

# Foreign-key graph used by prompt and join-path reasoning.
FOREIGN_KEYS: List[Tuple[str, str, str, str]] = [
    ("KHACHHANG", "MaKhuVuc", "KHUVUC", "MaKhuVuc"),
    ("DONHANG_GIAOHANG", "MaKhachHang", "KHACHHANG", "MaKhachHang"),
    (
        "DONHANG_GIAOHANG",
        "MaThanhVienGiaoHang",
        "THANHVIENGIAOHANG",
        "MaThanhVienGiaoHang",
    ),
    ("DONHANG_GIAOHANG", "MaDichVu", "DICHVU", "MaDichVu"),
    ("DONHANG_GIAOHANG", "MaKhuVuc", "KHUVUC", "MaKhuVuc"),
    (
        "DONHANG_GIAOHANG",
        "MaKhoangThoiGian",
        "KHOANGTHOIGIAN",
        "MaKhoangThoiGian",
    ),
    (
        "CHITIET_DONHANG",
        "MaDonHangGiaoHang",
        "DONHANG_GIAOHANG",
        "MaDonHangGiaoHang",
    ),
    ("CHITIET_DONHANG", "MaLoaiMatHang", "LOAIMATHANG", "MaLoaiMatHang"),
    (
        "DANGKYGIAOHANG",
        "MaThanhVienGiaoHang",
        "THANHVIENGIAOHANG",
        "MaThanhVienGiaoHang",
    ),
    (
        "DANGKYGIAOHANG",
        "MaKhoangThoiGian",
        "KHOANGTHOIGIAN",
        "MaKhoangThoiGian",
    ),
]

BUSINESS_TERMS: Dict[str, List[str]] = {
    "KHACHHANG": ["khách hàng", "customer", "người đặt", "shop"],
    "DONHANG_GIAOHANG": ["đơn hàng", "order", "giao hàng", "đơn"],
    "THANHVIENGIAOHANG": ["shipper", "thành viên", "nhân viên giao", "người giao"],
    "KHUVUC": ["khu vực", "quận", "địa bàn"],
    "DICHVU": ["dịch vụ", "giao nhanh", "giao tiết kiệm", "hỏa tốc"],
    "LOAIMATHANG": ["loại mặt hàng", "mặt hàng", "hàng hóa", "doanh thu"],
    "KHOANGTHOIGIAN": ["khung giờ", "thời gian", "giờ giao"],
}

ENUM_VALUES = {
    "TrangThaiGiaoHang": ["Đã giao", "Đang giao", "Chưa giao"],
    "TrangThaiDuyet": ["Đã duyệt", "Chờ duyệt"],
    "PhuongThucThanhToan": ["Tiền mặt", "Chuyển khoản"],
    "GioiTinh": ["Nam", "Nữ"],
}


def schema_text() -> str:
    """Return a compact schema block for LLM prompt."""
    lines: List[str] = []
    for table in TABLES.values():
        lines.append(f"{table.name}({', '.join(table.columns)}) -- {table.description}")
    lines.append("\nForeign keys:")
    for left_table, left_col, right_table, right_col in FOREIGN_KEYS:
        lines.append(f"- {left_table}.{left_col} -> {right_table}.{right_col}")
    lines.append("\nBusiness terms:")
    for table, terms in BUSINESS_TERMS.items():
        lines.append(f"- {', '.join(terms)} -> {table}")
    lines.append("\nEnum values:")
    for col, values in ENUM_VALUES.items():
        lines.append(f"- {col}: {', '.join(values)}")
    return "\n".join(lines)
