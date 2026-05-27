"""
Load CSV data from ./data/ into Neo4j as a knowledge graph.
Run once before using graphrag.py.

Schema:
  Nodes: KhachHang, ThanhVien, DonHang, DichVu, KhuVuc, LoaiMatHang, KhoangThoiGian
  Relationships:
    (KhachHang)-[:THUOC_KHU_VUC]->(KhuVuc)
    (DonHang)-[:DAT_BOI]->(KhachHang)
    (DonHang)-[:DUOC_GIAO_BOI]->(ThanhVien)
    (DonHang)-[:SU_DUNG]->(DichVu)
    (DonHang)-[:GIAO_TAI]->(KhuVuc)
    (DonHang)-[:TRONG_KHUNG_GIO]->(KhoangThoiGian)
    (DonHang)-[:CHUA {ten, soLuong, khoiLuong, giaTri}]->(LoaiMatHang)
    (ThanhVien)-[:DANG_KY]->(KhoangThoiGian)
"""

import csv
import os
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

URI      = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USER     = os.getenv("NEO4J_USERNAME", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

DATA_DIR = Path(__file__).parent / "data"


def read_csv(filename, fieldnames):
    rows = []
    with open(DATA_DIR / filename, encoding="utf-8") as f:
        reader = csv.DictReader(f, fieldnames=fieldnames)
        for row in reader:
            rows.append(row)
    return rows


def load_all(driver):
    with driver.session() as s:
        s.run("MATCH (n) DETACH DELETE n")
        print("Cleared existing data.")

        # ── Nodes ──────────────────────────────────────────────

        khuvuc = read_csv("khuvuc.csv", ["id", "ten"])
        s.run(
            "UNWIND $rows AS r MERGE (n:KhuVuc {id: r.id}) SET n.ten = r.ten",
            rows=khuvuc,
        )
        print(f"  KhuVuc: {len(khuvuc)} nodes")

        dichvu = read_csv("dichvu.csv", ["id", "ten"])
        s.run(
            "UNWIND $rows AS r MERGE (n:DichVu {id: r.id}) SET n.ten = r.ten",
            rows=dichvu,
        )
        print(f"  DichVu: {len(dichvu)} nodes")

        loai = read_csv("loaimathang.csv", ["id", "ten"])
        s.run(
            "UNWIND $rows AS r MERGE (n:LoaiMatHang {id: r.id}) SET n.ten = r.ten",
            rows=loai,
        )
        print(f"  LoaiMatHang: {len(loai)} nodes")

        thoigian = read_csv("khoangthoigian.csv", ["id", "khungGio"])
        s.run(
            "UNWIND $rows AS r MERGE (n:KhoangThoiGian {id: r.id}) SET n.khungGio = r.khungGio",
            rows=thoigian,
        )
        print(f"  KhoangThoiGian: {len(thoigian)} nodes")

        khachhang = read_csv(
            "khachhang.csv", ["id", "kvId", "ten", "tenShop", "sdt", "email", "diaChi"]
        )
        s.run(
            """
            UNWIND $rows AS r
            MERGE (n:KhachHang {id: r.id})
            SET n.ten = r.ten, n.tenShop = r.tenShop,
                n.sdt = r.sdt, n.email = r.email, n.diaChi = r.diaChi
            """,
            rows=khachhang,
        )
        print(f"  KhachHang: {len(khachhang)} nodes")

        thanhvien = read_csv(
            "thanhviengiaohang.csv", ["id", "ten", "ngaySinh", "gioiTinh", "sdt", "diaChi"]
        )
        s.run(
            """
            UNWIND $rows AS r
            MERGE (n:ThanhVien {id: r.id})
            SET n.ten = r.ten, n.ngaySinh = r.ngaySinh,
                n.gioiTinh = r.gioiTinh, n.sdt = r.sdt, n.diaChi = r.diaChi
            """,
            rows=thanhvien,
        )
        print(f"  ThanhVien: {len(thanhvien)} nodes")

        donhang = read_csv(
            "donhang_giaohang.csv",
            ["id", "khId", "tvId", "dvId", "kvId",
             "tenNguoiNhan", "diaChiGiao", "sdt",
             "tgId", "ngay", "thanhToan", "trangThaiDuyet", "trangThaiGiao"],
        )
        s.run(
            """
            UNWIND $rows AS r
            MERGE (n:DonHang {id: r.id})
            SET n.tenNguoiNhan = r.tenNguoiNhan, n.diaChiGiao = r.diaChiGiao,
                n.sdt = r.sdt, n.ngay = r.ngay,
                n.thanhToan = r.thanhToan,
                n.trangThaiDuyet = r.trangThaiDuyet,
                n.trangThaiGiao = r.trangThaiGiao
            """,
            rows=donhang,
        )
        print(f"  DonHang: {len(donhang)} nodes")

        # ── Relationships ──────────────────────────────────────

        # KhachHang → KhuVuc
        s.run(
            """
            UNWIND $rows AS r
            MATCH (kh:KhachHang {id: r.id}), (kv:KhuVuc {id: r.kvId})
            MERGE (kh)-[:THUOC_KHU_VUC]->(kv)
            """,
            rows=khachhang,
        )

        # DonHang → KhachHang, ThanhVien, DichVu, KhuVuc, KhoangThoiGian
        s.run(
            """
            UNWIND $rows AS r
            MATCH (dh:DonHang   {id: r.id}),
                  (kh:KhachHang {id: r.khId}),
                  (tv:ThanhVien {id: r.tvId}),
                  (dv:DichVu    {id: r.dvId}),
                  (kv:KhuVuc   {id: r.kvId}),
                  (tg:KhoangThoiGian {id: r.tgId})
            MERGE (dh)-[:DAT_BOI]->(kh)
            MERGE (dh)-[:DUOC_GIAO_BOI]->(tv)
            MERGE (dh)-[:SU_DUNG]->(dv)
            MERGE (dh)-[:GIAO_TAI]->(kv)
            MERGE (dh)-[:TRONG_KHUNG_GIO]->(tg)
            """,
            rows=donhang,
        )
        print("  DonHang relationships created.")

        # DonHang → LoaiMatHang (với thuộc tính chi tiết)
        chitiet = read_csv(
            "chitiet_donhang.csv", ["dhId", "tenHang", "soLuong", "khoiLuong", "lhId", "giaTri"]
        )
        s.run(
            """
            UNWIND $rows AS r
            MATCH (dh:DonHang {id: r.dhId}), (lh:LoaiMatHang {id: r.lhId})
            CREATE (dh)-[:CHUA {
                tenHang:   r.tenHang,
                soLuong:   toInteger(r.soLuong),
                khoiLuong: toFloat(r.khoiLuong),
                giaTri:    toFloat(r.giaTri)
            }]->(lh)
            """,
            rows=chitiet,
        )
        print(f"  ChiTietDonHang: {len(chitiet)} CHUA relationships")

        # ThanhVien → KhoangThoiGian (đăng ký)
        dangky = read_csv("dangkygiaohang.csv", ["tvId", "tgId"])
        s.run(
            """
            UNWIND $rows AS r
            MATCH (tv:ThanhVien {id: r.tvId}), (tg:KhoangThoiGian {id: r.tgId})
            MERGE (tv)-[:DANG_KY]->(tg)
            """,
            rows=dangky,
        )
        print(f"  DangKyGiaoHang: {len(dangky)} DANG_KY relationships")

        print("\nGraph loaded successfully.")


if __name__ == "__main__":
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    try:
        driver.verify_connectivity()
        print(f"Connected to Neo4j at {URI}\n")
        load_all(driver)
    finally:
        driver.close()
