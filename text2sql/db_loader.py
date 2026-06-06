"""Create and seed SQLite database from the existing CSV files."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Iterable, List

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
DEFAULT_DB_PATH = ROOT_DIR / "transport.sqlite"


def read_csv(filename: str, fieldnames: List[str]) -> List[dict]:
    with open(DATA_DIR / filename, encoding="utf-8") as f:
        return list(csv.DictReader(f, fieldnames=fieldnames))


def executemany(conn: sqlite3.Connection, sql: str, rows: Iterable[dict]) -> None:
    conn.executemany(sql, rows)


def create_database(db_path: str | Path = DEFAULT_DB_PATH, reset: bool = True) -> Path:
    db_path = Path(db_path)
    if reset and db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS KHUVUC (
            MaKhuVuc TEXT PRIMARY KEY,
            TenKhuVuc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS DICHVU (
            MaDichVu TEXT PRIMARY KEY,
            TenDichVu TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS LOAIMATHANG (
            MaLoaiMatHang TEXT PRIMARY KEY,
            TenLoaiMatHang TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS KHOANGTHOIGIAN (
            MaKhoangThoiGian TEXT PRIMARY KEY,
            KhungGio TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS KHACHHANG (
            MaKhachHang TEXT PRIMARY KEY,
            MaKhuVuc TEXT NOT NULL,
            TenKhachHang TEXT NOT NULL,
            TenShop TEXT,
            SoDienThoai TEXT,
            Email TEXT,
            DiaChi TEXT,
            FOREIGN KEY (MaKhuVuc) REFERENCES KHUVUC(MaKhuVuc)
        );

        CREATE TABLE IF NOT EXISTS THANHVIENGIAOHANG (
            MaThanhVienGiaoHang TEXT PRIMARY KEY,
            TenThanhVienGiaoHang TEXT NOT NULL,
            NgaySinh TEXT,
            GioiTinh TEXT,
            SoDienThoai TEXT,
            DiaChi TEXT
        );

        CREATE TABLE IF NOT EXISTS DONHANG_GIAOHANG (
            MaDonHangGiaoHang TEXT PRIMARY KEY,
            MaKhachHang TEXT NOT NULL,
            MaThanhVienGiaoHang TEXT NOT NULL,
            MaDichVu TEXT NOT NULL,
            MaKhuVuc TEXT NOT NULL,
            TenNguoiNhan TEXT,
            DiaChiGiaoHang TEXT,
            SoDienThoaiNguoiNhan TEXT,
            MaKhoangThoiGian TEXT NOT NULL,
            NgayGiaoHang TEXT,
            PhuongThucThanhToan TEXT,
            TrangThaiDuyet TEXT,
            TrangThaiGiaoHang TEXT,
            FOREIGN KEY (MaKhachHang) REFERENCES KHACHHANG(MaKhachHang),
            FOREIGN KEY (MaThanhVienGiaoHang) REFERENCES THANHVIENGIAOHANG(MaThanhVienGiaoHang),
            FOREIGN KEY (MaDichVu) REFERENCES DICHVU(MaDichVu),
            FOREIGN KEY (MaKhuVuc) REFERENCES KHUVUC(MaKhuVuc),
            FOREIGN KEY (MaKhoangThoiGian) REFERENCES KHOANGTHOIGIAN(MaKhoangThoiGian)
        );

        CREATE TABLE IF NOT EXISTS CHITIET_DONHANG (
            MaDonHangGiaoHang TEXT NOT NULL,
            TenHang TEXT NOT NULL,
            SoLuong INTEGER,
            KhoiLuong REAL,
            MaLoaiMatHang TEXT NOT NULL,
            GiaTriHang REAL,
            FOREIGN KEY (MaDonHangGiaoHang) REFERENCES DONHANG_GIAOHANG(MaDonHangGiaoHang),
            FOREIGN KEY (MaLoaiMatHang) REFERENCES LOAIMATHANG(MaLoaiMatHang)
        );

        CREATE TABLE IF NOT EXISTS DANGKYGIAOHANG (
            MaThanhVienGiaoHang TEXT NOT NULL,
            MaKhoangThoiGian TEXT NOT NULL,
            PRIMARY KEY (MaThanhVienGiaoHang, MaKhoangThoiGian),
            FOREIGN KEY (MaThanhVienGiaoHang) REFERENCES THANHVIENGIAOHANG(MaThanhVienGiaoHang),
            FOREIGN KEY (MaKhoangThoiGian) REFERENCES KHOANGTHOIGIAN(MaKhoangThoiGian)
        );
        """
    )

    executemany(
        conn,
        "INSERT INTO KHUVUC VALUES (:MaKhuVuc, :TenKhuVuc)",
        [
            {"MaKhuVuc": r["id"], "TenKhuVuc": r["ten"]}
            for r in read_csv("khuvuc.csv", ["id", "ten"])
        ],
    )
    executemany(
        conn,
        "INSERT INTO DICHVU VALUES (:MaDichVu, :TenDichVu)",
        [
            {"MaDichVu": r["id"], "TenDichVu": r["ten"]}
            for r in read_csv("dichvu.csv", ["id", "ten"])
        ],
    )
    executemany(
        conn,
        "INSERT INTO LOAIMATHANG VALUES (:MaLoaiMatHang, :TenLoaiMatHang)",
        [
            {"MaLoaiMatHang": r["id"], "TenLoaiMatHang": r["ten"]}
            for r in read_csv("loaimathang.csv", ["id", "ten"])
        ],
    )
    executemany(
        conn,
        "INSERT INTO KHOANGTHOIGIAN VALUES (:MaKhoangThoiGian, :KhungGio)",
        [
            {"MaKhoangThoiGian": r["id"], "KhungGio": r["khungGio"]}
            for r in read_csv("khoangthoigian.csv", ["id", "khungGio"])
        ],
    )
    executemany(
        conn,
        """
        INSERT INTO KHACHHANG
        VALUES (:MaKhachHang, :MaKhuVuc, :TenKhachHang, :TenShop, :SoDienThoai, :Email, :DiaChi)
        """,
        [
            {
                "MaKhachHang": r["id"],
                "MaKhuVuc": r["kvId"],
                "TenKhachHang": r["ten"],
                "TenShop": r["tenShop"],
                "SoDienThoai": r["sdt"],
                "Email": r["email"],
                "DiaChi": r["diaChi"],
            }
            for r in read_csv(
                "khachhang.csv", ["id", "kvId", "ten", "tenShop", "sdt", "email", "diaChi"]
            )
        ],
    )
    executemany(
        conn,
        """
        INSERT INTO THANHVIENGIAOHANG
        VALUES (:MaThanhVienGiaoHang, :TenThanhVienGiaoHang, :NgaySinh, :GioiTinh, :SoDienThoai, :DiaChi)
        """,
        [
            {
                "MaThanhVienGiaoHang": r["id"],
                "TenThanhVienGiaoHang": r["ten"],
                "NgaySinh": r["ngaySinh"],
                "GioiTinh": r["gioiTinh"],
                "SoDienThoai": r["sdt"],
                "DiaChi": r["diaChi"],
            }
            for r in read_csv(
                "thanhviengiaohang.csv", ["id", "ten", "ngaySinh", "gioiTinh", "sdt", "diaChi"]
            )
        ],
    )
    executemany(
        conn,
        """
        INSERT INTO DONHANG_GIAOHANG
        VALUES (
            :MaDonHangGiaoHang, :MaKhachHang, :MaThanhVienGiaoHang, :MaDichVu,
            :MaKhuVuc, :TenNguoiNhan, :DiaChiGiaoHang, :SoDienThoaiNguoiNhan,
            :MaKhoangThoiGian, :NgayGiaoHang, :PhuongThucThanhToan,
            :TrangThaiDuyet, :TrangThaiGiaoHang
        )
        """,
        [
            {
                "MaDonHangGiaoHang": r["id"],
                "MaKhachHang": r["khId"],
                "MaThanhVienGiaoHang": r["tvId"],
                "MaDichVu": r["dvId"],
                "MaKhuVuc": r["kvId"],
                "TenNguoiNhan": r["tenNguoiNhan"],
                "DiaChiGiaoHang": r["diaChiGiao"],
                "SoDienThoaiNguoiNhan": r["sdt"],
                "MaKhoangThoiGian": r["tgId"],
                "NgayGiaoHang": r["ngay"],
                "PhuongThucThanhToan": r["thanhToan"],
                "TrangThaiDuyet": r["trangThaiDuyet"],
                "TrangThaiGiaoHang": r["trangThaiGiao"],
            }
            for r in read_csv(
                "donhang_giaohang.csv",
                [
                    "id",
                    "khId",
                    "tvId",
                    "dvId",
                    "kvId",
                    "tenNguoiNhan",
                    "diaChiGiao",
                    "sdt",
                    "tgId",
                    "ngay",
                    "thanhToan",
                    "trangThaiDuyet",
                    "trangThaiGiao",
                ],
            )
        ],
    )
    executemany(
        conn,
        """
        INSERT INTO CHITIET_DONHANG
        VALUES (:MaDonHangGiaoHang, :TenHang, :SoLuong, :KhoiLuong, :MaLoaiMatHang, :GiaTriHang)
        """,
        [
            {
                "MaDonHangGiaoHang": r["dhId"],
                "TenHang": r["tenHang"],
                "SoLuong": int(r["soLuong"]),
                "KhoiLuong": float(r["khoiLuong"]),
                "MaLoaiMatHang": r["lhId"],
                "GiaTriHang": float(r["giaTri"]),
            }
            for r in read_csv(
                "chitiet_donhang.csv", ["dhId", "tenHang", "soLuong", "khoiLuong", "lhId", "giaTri"]
            )
        ],
    )
    executemany(
        conn,
        "INSERT INTO DANGKYGIAOHANG VALUES (:MaThanhVienGiaoHang, :MaKhoangThoiGian)",
        [
            {"MaThanhVienGiaoHang": r["tvId"], "MaKhoangThoiGian": r["tgId"]}
            for r in read_csv("dangkygiaohang.csv", ["tvId", "tgId"])
        ],
    )

    conn.commit()
    conn.close()
    return db_path


if __name__ == "__main__":
    path = create_database()
    print(f"SQLite database created: {path}")
