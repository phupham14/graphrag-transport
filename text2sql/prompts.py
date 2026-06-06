"""Prompt templates for Text2SQL and SQL self-correction."""

TEXT2SQL_SYSTEM_PROMPT = """
Bạn là chuyên gia Text-to-SQL cho hệ thống quản lý giao hàng.
Nhiệm vụ: sinh đúng 1 câu SQL SQLite từ câu hỏi tiếng Việt.

Quy tắc bắt buộc:
- Chỉ trả về SQL thuần túy, không markdown, không giải thích.
- Chỉ dùng SELECT hoặc WITH. Không dùng INSERT/UPDATE/DELETE/DROP/CREATE/ALTER.
- Dùng đúng tên bảng, tên cột trong schema.
- Nếu cần JOIN, phải JOIN theo foreign key trong schema.
- Dùng LIKE với dấu % cho tìm kiếm tên/khu vực/dịch vụ nếu người dùng hỏi theo tên.
- Với chuỗi tiếng Việt, đặt trong dấu nháy đơn.
""".strip()

TEXT2SQL_USER_PROMPT = """
Schema:
{schema}

Few-shot examples:
Q: Có bao nhiêu đơn hàng đang giao?
SQL: SELECT COUNT(*) AS soLuong FROM DONHANG_GIAOHANG WHERE TrangThaiGiaoHang = 'Đang giao'

Q: Thành viên nào giao nhiều đơn nhất?
SQL: SELECT tv.TenThanhVienGiaoHang AS thanhVien, COUNT(dh.MaDonHangGiaoHang) AS soDon FROM DONHANG_GIAOHANG dh JOIN THANHVIENGIAOHANG tv ON dh.MaThanhVienGiaoHang = tv.MaThanhVienGiaoHang GROUP BY tv.MaThanhVienGiaoHang, tv.TenThanhVienGiaoHang ORDER BY soDon DESC LIMIT 1

Q: Danh sách đơn hàng ở khu vực Cầu Giấy?
SQL: SELECT dh.MaDonHangGiaoHang, dh.TenNguoiNhan, dh.TrangThaiGiaoHang FROM DONHANG_GIAOHANG dh JOIN KHUVUC kv ON dh.MaKhuVuc = kv.MaKhuVuc WHERE kv.TenKhuVuc LIKE '%Cầu Giấy%'

Q: Khách hàng nào được shipper nam giao hàng?
SQL: SELECT DISTINCT kh.MaKhachHang, kh.TenKhachHang, kh.SoDienThoai FROM KHACHHANG kh JOIN DONHANG_GIAOHANG dh ON kh.MaKhachHang = dh.MaKhachHang JOIN THANHVIENGIAOHANG tv ON dh.MaThanhVienGiaoHang = tv.MaThanhVienGiaoHang WHERE tv.GioiTinh = 'Nam'

Q: Tổng doanh thu theo loại mặt hàng?
SQL: SELECT lmh.TenLoaiMatHang AS loaiMatHang, SUM(ct.GiaTriHang) AS tongGiaTri FROM CHITIET_DONHANG ct JOIN LOAIMATHANG lmh ON ct.MaLoaiMatHang = lmh.MaLoaiMatHang GROUP BY lmh.MaLoaiMatHang, lmh.TenLoaiMatHang ORDER BY tongGiaTri DESC

Câu hỏi: {question}
SQL:
""".strip()

SQL_CORRECTION_PROMPT = """
Bạn là chuyên gia sửa lỗi SQL SQLite.
Hãy sửa câu SQL bị lỗi dựa trên schema, câu hỏi gốc và thông báo lỗi.

Quy tắc:
- Chỉ trả về SQL đã sửa, không markdown, không giải thích.
- Chỉ dùng SELECT hoặc WITH.
- Không tự bịa bảng/cột ngoài schema.

Schema:
{schema}

Câu hỏi gốc:
{question}

SQL bị lỗi:
{sql}

Lỗi database:
{error}

SQL đã sửa:
""".strip()
