# Text2SQL Prompt

Dùng nội dung trong `text2sql/prompts.py` cho SQL generation và SQL self-correction.

Luồng xử lý:
1. Nhận câu hỏi tiếng Việt.
2. Ghép schema + few-shot examples + question.
3. LLM sinh SQL SQLite chỉ đọc.
4. `validator.py` kiểm tra chỉ cho phép SELECT/WITH.
5. Nếu DB trả lỗi, `SQL_CORRECTION_PROMPT` nhận question + SQL lỗi + error message để sửa lại.
