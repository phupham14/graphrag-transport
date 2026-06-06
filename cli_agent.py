"""
cli_agent.py — CLI entry point để chạy thử Multi-Agent Workflow

Cách dùng:
    python cli_agent.py

Yêu cầu:
    - Neo4j đang chạy (docker-compose up -d)
    - Dữ liệu đã nạp (python load_graph.py)
    - File .env đã cấu hình (NEO4J_*, GOOGLE_API_KEY)

Gõ câu hỏi tiếng Việt để truy vấn dữ liệu.
Gõ 'debug' để bật/tắt hiển thị chi tiết state transitions.
Gõ 'quit' hoặc 'exit' để thoát.
"""

import asyncio
import uuid
import sys

from langchain_core.messages import HumanMessage

from agent_core.mock_engine import MockQueryEngine
from agent_core.workflow import create_app


async def main() -> None:
    print("=" * 60)
    print("🤖 Multi-Agent System — Truy vấn dữ liệu vận chuyển")
    print("   Sử dụng LangGraph + GraphRAG + Memory")
    print("=" * 60)
    print()
    print("Gõ câu hỏi tiếng Việt để bắt đầu.")
    print("Gõ 'debug' để bật/tắt chế độ chi tiết.")
    print("Gõ 'new' để bắt đầu phiên chat mới.")
    print("Gõ 'quit' để thoát.")
    print()

    # Khởi tạo hệ thống
    try:
        engine = MockQueryEngine()
        app = create_app(engine)
        print("✅ Kết nối Neo4j thành công.\n")
    except Exception as e:
        print(f"❌ Lỗi khởi tạo: {e}")
        print("   Kiểm tra Neo4j đang chạy và file .env đã cấu hình.")
        return

    # Mỗi phiên chat có thread_id riêng (Short-term Memory)
    thread_id = str(uuid.uuid4())
    debug_mode = False

    while True:
        try:
            question = input("📝 Câu hỏi: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Tạm biệt!")
            break

        if not question:
            continue

        if question.lower() in ("quit", "exit", "thoát"):
            print("👋 Tạm biệt!")
            break

        if question.lower() == "debug":
            debug_mode = not debug_mode
            print(f"🔧 Debug mode: {'ON' if debug_mode else 'OFF'}\n")
            continue

        if question.lower() == "new":
            thread_id = str(uuid.uuid4())
            print(f"🆕 Phiên chat mới (thread: {thread_id[:8]}...)\n")
            continue

        # Chuẩn bị input cho graph
        config = {"configurable": {"thread_id": thread_id}}
        input_state = {
            "messages": [HumanMessage(content=question)],
            "original_question": question,
        }

        # Chạy graph
        try:
            if debug_mode:
                print(f"\n🔍 Thread: {thread_id[:8]}...")
                print("── State Transitions ──")

                # Stream từng bước để debug
                async for event in app.astream(input_state, config=config):
                    for node_name, node_output in event.items():
                        if node_name == "__end__":
                            continue
                        print(f"  📍 {node_name}:")
                        # In các key đã thay đổi (bỏ messages vì quá dài)
                        for key, value in node_output.items():
                            if key == "messages":
                                print(f"     messages: [{len(value)} message(s)]")
                            elif isinstance(value, str) and len(value) > 100:
                                print(f"     {key}: {value[:100]}...")
                            else:
                                print(f"     {key}: {value}")
                print("── End ──\n")

                # Lấy state cuối
                final_state = await app.aget_state(config)
                messages = final_state.values.get("messages", [])
                if messages:
                    print(f"💬 Trả lời:\n{messages[-1].content}\n")

            else:
                # Chạy bình thường (không debug)
                result = await app.ainvoke(input_state, config=config)
                messages = result.get("messages", [])
                if messages:
                    # Lấy message cuối cùng (AI response)
                    last_msg = messages[-1]
                    content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
                    print(f"\n💬 Trả lời:\n{content}\n")
                else:
                    print("\n⚠️ Không có phản hồi.\n")

        except Exception as e:
            print(f"\n❌ Lỗi: {e}\n")
            if debug_mode:
                import traceback
                traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
