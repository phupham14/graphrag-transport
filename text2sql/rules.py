"""Small deterministic Vietnamese Text2SQL baseline.

This fallback helps the project run without external LLM credentials. When an LLM
key exists, generator.py can call the LLM first and use these rules as backup.
"""

from __future__ import annotations

import re
import unicodedata


def normalize(text: str) -> str:
    text = text.lower().strip().replace("đ", "d")
    text = "".join(
        ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn"
    )
    return re.sub(r"\s+", " ", text)


def extract_known_area(question: str) -> str | None:
    areas = ["Cầu Giấy", "Ba Đình", "Đống Đa", "Hoàng Mai", "Thanh Xuân", "Hai Bà Trưng", "Tây Hồ"]
    q_norm = normalize(question)
    for area in areas:
        if normalize(area) in q_norm:
            return area
    return None


def extract_status(question: str) -> str | None:
    q = normalize(question)
    if "dang giao" in q:
        return "Đang giao"
    if "da giao" in q:
        return "Đã giao"
    if "chua giao" in q:
        return "Chưa giao"
    return None


def generate_sql_by_rules(question: str) -> str | None:
    q = normalize(question)
    area = extract_known_area(question)
    status = extract_status(question)

    if ("bao nhieu" in q or "so luong" in q or "dem" in q) and "don" in q:
        if status:
            return (
                "SELECT COUNT(*) AS soLuong "
                "FROM DONHANG_GIAOHANG "
                f"WHERE TrangThaiGiaoHang = '{status}'"
            )
        return "SELECT COUNT(*) AS soLuong FROM DONHANG_GIAOHANG"

    if "thanh vien" in q and "giao nhieu" in q or "shipper" in q and "nhieu don" in q:
        return (
            "SELECT tv.TenThanhVienGiaoHang AS thanhVien, "
            "COUNT(dh.MaDonHangGiaoHang) AS soDon "
            "FROM DONHANG_GIAOHANG dh "
            "JOIN THANHVIENGIAOHANG tv "
            "ON dh.MaThanhVienGiaoHang = tv.MaThanhVienGiaoHang "
            "GROUP BY tv.MaThanhVienGiaoHang, tv.TenThanhVienGiaoHang "
            "ORDER BY soDon DESC LIMIT 1"
        )

    if ("doanh thu" in q or "tong gia tri" in q) and ("loai" in q or "mat hang" in q):
        return (
            "SELECT lmh.TenLoaiMatHang AS loaiMatHang, SUM(ct.GiaTriHang) AS tongGiaTri "
            "FROM CHITIET_DONHANG ct "
            "JOIN LOAIMATHANG lmh ON ct.MaLoaiMatHang = lmh.MaLoaiMatHang "
            "GROUP BY lmh.MaLoaiMatHang, lmh.TenLoaiMatHang "
            "ORDER BY tongGiaTri DESC"
        )

    if "khach hang" in q and ("shipper nam" in q or "nguoi giao nam" in q or "thanh vien nam" in q):
        return (
            "SELECT DISTINCT kh.MaKhachHang, kh.TenKhachHang, kh.SoDienThoai "
            "FROM KHACHHANG kh "
            "JOIN DONHANG_GIAOHANG dh ON kh.MaKhachHang = dh.MaKhachHang "
            "JOIN THANHVIENGIAOHANG tv ON dh.MaThanhVienGiaoHang = tv.MaThanhVienGiaoHang "
            "WHERE tv.GioiTinh = 'Nam'"
        )

    if "khach hang" in q and area:
        return (
            "SELECT kh.MaKhachHang, kh.TenKhachHang, kh.TenShop, kh.SoDienThoai "
            "FROM KHACHHANG kh "
            "JOIN KHUVUC kv ON kh.MaKhuVuc = kv.MaKhuVuc "
            f"WHERE kv.TenKhuVuc LIKE '%{area}%'"
        )

    if "don" in q and area:
        return (
            "SELECT dh.MaDonHangGiaoHang, dh.TenNguoiNhan, dh.TrangThaiGiaoHang "
            "FROM DONHANG_GIAOHANG dh "
            "JOIN KHUVUC kv ON dh.MaKhuVuc = kv.MaKhuVuc "
            f"WHERE kv.TenKhuVuc LIKE '%{area}%'"
        )

    if "khung gio" in q and ("nhieu" in q or "nhat" in q):
        return (
            "SELECT tg.KhungGio AS khungGio, COUNT(dh.MaDonHangGiaoHang) AS soDon "
            "FROM DONHANG_GIAOHANG dh "
            "JOIN KHOANGTHOIGIAN tg ON dh.MaKhoangThoiGian = tg.MaKhoangThoiGian "
            "GROUP BY tg.MaKhoangThoiGian, tg.KhungGio "
            "ORDER BY soDon DESC LIMIT 1"
        )

    if "danh sach" in q and "don" in q:
        where = f" WHERE TrangThaiGiaoHang = '{status}'" if status else ""
        return (
            "SELECT MaDonHangGiaoHang, TenNguoiNhan, NgayGiaoHang, TrangThaiGiaoHang "
            f"FROM DONHANG_GIAOHANG{where} LIMIT 50"
        )

    if "danh sach" in q and "khach hang" in q:
        return "SELECT MaKhachHang, TenKhachHang, TenShop, SoDienThoai FROM KHACHHANG LIMIT 50"

    return None
