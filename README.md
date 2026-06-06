# GraphRAG Transport

Hệ thống chatbot hỏi đáp bằng tiếng Việt trên dữ liệu vận chuyển/giao hàng, sử dụng Neo4j Knowledge Graph kết hợp LangChain và Google Gemini API.

## Yêu cầu hệ thống

- Python 3.10+
- Docker & Docker Compose
- Google API Key (Gemini)

## Cài đặt

### 1. Clone repo

```bash
git clone https://github.com/phupham14/graphrag-transport.git
cd graphrag-transport
```

### 2. Tạo môi trường ảo và cài dependencies

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Cấu hình biến môi trường

Tạo file `.env` ở thư mục gốc:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
GOOGLE_API_KEY=your_google_api_key
```

> Lấy Google API Key tại: https://aistudio.google.com/app/apikey

### 4. Khởi động Neo4j bằng Docker

```bash
docker-compose up -d
```

Neo4j sẽ chạy tại:
- **Browser UI:** http://localhost:7474
- **Bolt:** bolt://localhost:7687

Đợi khoảng 30 giây để Neo4j khởi động hoàn toàn trước bước tiếp theo.

### 5. Nạp dữ liệu vào Neo4j

```bash
python load_graph.py
```

Script sẽ tự động xóa dữ liệu cũ (nếu có) rồi tạo toàn bộ nodes và relationships từ các file CSV trong thư mục `data/`.

## Chạy chatbot

```bash
python graphrag.py
```

Nhập câu hỏi bằng tiếng Việt, gõ `quit` để thoát.

**Ví dụ câu hỏi:**

```
Có bao nhiêu đơn hàng đang giao?
Thành viên nào giao nhiều đơn nhất?
Danh sách đơn hàng ở khu vực Cầu Giấy?
Tổng doanh thu theo loại mặt hàng?
```

> Gõ `debug` trong lúc chat để bật/tắt chế độ hiển thị câu Cypher được sinh ra.

## Cấu trúc project

```
transport/
├── data/                    # Dữ liệu CSV nguồn
│   ├── khachhang.csv
│   ├── donhang_giaohang.csv
│   ├── chitiet_donhang.csv
│   └── ...
├── neo4j/                   # Volume dữ liệu Neo4j (tự sinh)
├── graphrag.py              # Chatbot chính
├── load_graph.py            # Script nạp dữ liệu
├── requirements.txt
├── docker-compose.yml
└── .env                     # Credentials (không commit)
```

## Schema Knowledge Graph

| Node | Mô tả |
|------|-------|
| `KhachHang` | Khách hàng |
| `ThanhVien` | Thành viên giao hàng |
| `DonHang` | Đơn hàng |
| `DichVu` | Dịch vụ giao hàng |
| `KhuVuc` | Khu vực |
| `LoaiMatHang` | Loại mặt hàng |
| `KhoangThoiGian` | Khung giờ giao |

## Troubleshooting

**Neo4j chưa sẵn sàng:** Nếu `load_graph.py` báo lỗi kết nối, đợi thêm 30–60 giây rồi thử lại.

**Lỗi xác thực Neo4j:** Kiểm tra `NEO4J_PASSWORD` trong `.env` khớp với mật khẩu trong `docker-compose.yml`.

**Reset dữ liệu:** Chạy lại `python load_graph.py` — script tự xóa và nạp lại từ đầu.

**Dừng Neo4j:**

```bash
docker-compose down
```


## Module Thành viên 3: Text2SQL + SQL Self-Correction

Phần này bổ sung workflow chuyển câu hỏi tiếng Việt sang SQL trên SQLite, độc lập với chatbot Neo4j hiện có.

### Tạo SQLite DB từ CSV

```bash
python -m text2sql.db_loader
```

Hoặc chạy CLI và tự tạo DB:

```bash
python text2sql_cli.py --init-db --debug --no-llm
```

Nếu có `GOOGLE_API_KEY`, bỏ `--no-llm` để dùng Gemini sinh SQL. Nếu không có API key, hệ thống tự dùng rule-based fallback để demo.

### Ví dụ câu hỏi

```text
Có bao nhiêu đơn hàng đang giao?
Thành viên nào giao nhiều đơn nhất?
Danh sách đơn hàng ở khu vực Cầu Giấy?
Tổng doanh thu theo loại mặt hàng?
Khách hàng nào được shipper nam giao hàng?
Khung giờ nào có nhiều đơn hàng nhất?
```

### Chạy evaluation

```bash
python evaluation/evaluate_text2sql.py --no-llm
```

### File chính

```text
text2sql/schema.py       # schema metadata, foreign keys, business terms
text2sql/db_loader.py    # tạo SQLite DB từ CSV
text2sql/prompts.py      # prompt generation + prompt correction
text2sql/rules.py        # rule-based fallback không cần API key
text2sql/validator.py    # validate SELECT-only và execute SQL
text2sql/generator.py    # Text2SQLAgent + self-correction loop
text2sql_cli.py          # CLI demo
```
