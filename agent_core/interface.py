"""
agent_core.interface — Abstract interface ghép nối Phần 1 (GraphRAG)

Lớp trừu tượng này đóng vai trò "hợp đồng" giữa Phần 2 (LangGraph Workflow)
và Phần 1 (GraphRAG + Schema Reasoning).

Phần LangGraph chỉ tương tác qua interface này. Khi Thành viên 1 hoàn thiện
module GraphRAG, chỉ cần viết class kế thừa QueryEngineInterface mà
không phải sửa bất kỳ dòng code nào trong LangGraph.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class QueryEngineInterface(ABC):
    """Giao diện trừu tượng cho engine truy vấn CSDL.

    Thành viên 1 (GraphRAG) sẽ implement interface này.
    Phần 2 (LangGraph) sử dụng nó mà không cần biết chi tiết bên trong.
    """

    @abstractmethod
    def retrieve_schema(self, question: str, entities: list[str]) -> str:
        """Trả về schema context (bảng liên quan, join path, column info).

        Trong tương lai, Thành viên 1 sẽ implement bằng GraphRAG thực sự:
        duyệt đồ thị schema → tìm bảng phù hợp → trả về join path.

        Args:
            question: Câu hỏi đã refine của user.
            entities: Danh sách thực thể đã trích xuất.

        Returns:
            Chuỗi mô tả schema context để đưa vào prompt sinh query.
        """

    @abstractmethod
    def execute_query(self, query: str) -> list[dict[str, Any]]:
        """Thực thi câu lệnh Cypher/SQL trên Database.

        Args:
            query: Câu lệnh Cypher hoặc SQL cần thực thi.

        Returns:
            Danh sách dict chứa kết quả truy vấn.

        Raises:
            Exception: Nếu câu lệnh bị lỗi cú pháp hoặc thực thi thất bại.
        """

    @abstractmethod
    def get_full_schema(self) -> str:
        """Trả về toàn bộ schema text (dùng làm fallback khi GraphRAG chưa sẵn sàng).

        Returns:
            Chuỗi mô tả đầy đủ schema của CSDL.
        """
