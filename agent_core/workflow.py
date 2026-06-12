"""
agent_core.workflow — Xây dựng và biên dịch StateGraph

File này là nơi kết nối mọi thứ lại:
- Tạo StateGraph từ AgentState
- Thêm 6 Worker Agent nodes + Supervisor nodes
- Định nghĩa edges (bao gồm conditional edges cho self-correction loop)
- Compile graph với MemorySaver (Short-term Memory) + InMemoryStore (Long-term Memory)
- Cung cấp hàm ``create_app()`` để khởi tạo toàn bộ hệ thống
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import StateGraph, START, END
from langgraph.types import RetryPolicy

from agent_core.state import AgentState
from agent_core.interface import QueryEngineInterface
from agent_core.memory import create_checkpointer, create_store, get_similar_queries, save_successful_query
from agent_core.agents.graph_retrieval import set_engine

# Import các agent nodes
from agent_core.agents.entity_extraction import entity_extraction_node
from agent_core.agents.graph_retrieval import graph_retrieval_node
from agent_core.agents.query_generator import query_generator_node
from agent_core.agents.query_executor import query_executor_node
from agent_core.agents.error_correction import error_correction_node
from agent_core.agents.insight import insight_node

# Import supervisor nodes & routing
from agent_core.supervisor import (
    receive_and_refine_node,
    finalize_node,
    fallback_error_node,
    route_after_execution,
    route_after_correction,
)


# ── Wrapper nodes (thêm Long-term Memory interaction) ────────────────────────

_store = None  # Sẽ được set trong create_app()


async def _query_generator_with_memory(state: AgentState) -> dict[str, Any]:
    """Wrapper: Đọc few-shot examples từ Long-term Memory trước khi sinh query."""
    memory_examples = []
    if _store is not None:
        try:
            memory_examples = await get_similar_queries(_store, limit=3)
        except Exception:
            pass  # Nếu store lỗi, tiếp tục với few-shot tĩnh
    return await query_generator_node(state, memory_examples=memory_examples)


async def _insight_with_memory_save(state: AgentState) -> dict[str, Any]:
    """Wrapper: Sau khi sinh insight, lưu query thành công vào Long-term Memory."""
    result = await insight_node(state)

    # Lưu query thành công vào Long-term Memory
    if _store is not None and state.get("query_result"):
        try:
            question = state.get("refined_question") or state.get("original_question", "")
            query = state.get("generated_query", "")
            result_summary = str(state.get("query_result", []))[:200]
            await save_successful_query(_store, question, query, result_summary)
        except Exception:
            pass  # Không để lỗi memory ảnh hưởng luồng chính

    return result


# ── Build Graph ──────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """Xây dựng StateGraph với đầy đủ nodes và edges.

    Returns:
        StateGraph chưa compile (cần gọi .compile() với checkpointer).
    """
    builder = StateGraph(AgentState)

    # ── Thêm Nodes ────────────────────────────────────────────────────────

    # Supervisor nodes
    builder.add_node("receive_and_refine", receive_and_refine_node)
    builder.add_node("finalize", finalize_node)
    builder.add_node("fallback_error", fallback_error_node)

    # Worker Agent nodes
    builder.add_node("entity_extraction", entity_extraction_node)
    builder.add_node("graph_retrieval", graph_retrieval_node)
    builder.add_node(
        "query_generator",
        _query_generator_with_memory,
    )
    builder.add_node(
        "query_executor",
        query_executor_node,
        # RetryPolicy cho lỗi tạm thời (Tầng 1)
        retry=RetryPolicy(
            max_attempts=3,
            initial_interval=1.0,
            backoff_factor=2.0,
            max_interval=10.0,
            jitter=True,
        ),
    )
    builder.add_node("error_correction", error_correction_node)
    builder.add_node(
        "insight",
        _insight_with_memory_save,
    )

    # ── Định nghĩa Edges ─────────────────────────────────────────────────

    # Luồng chính (Happy Path):
    # START → refine → extract → retrieve → generate → execute
    builder.add_edge(START, "receive_and_refine")
    builder.add_edge("receive_and_refine", "entity_extraction")
    builder.add_edge("entity_extraction", "graph_retrieval")
    builder.add_edge("graph_retrieval", "query_generator")
    builder.add_edge("query_generator", "query_executor")

    # Sau execution: routing có điều kiện (Self-Correction Loop / Tầng 2)
    builder.add_conditional_edges(
        "query_executor",
        route_after_execution,
        {
            "error_correction": "error_correction",
            "fallback_error": "fallback_error",
            "insight": "insight",
        },
    )

    # Error Correction → quay lại Query Generator
    builder.add_conditional_edges(
        "error_correction",
        route_after_correction,
        {
            "query_generator": "query_generator",
        },
    )

    # Insight → Finalize → END
    builder.add_edge("insight", "finalize")
    builder.add_edge("finalize", END)

    # Fallback Error → Finalize → END
    builder.add_edge("fallback_error", "finalize")

    return builder


# ── App Factory ──────────────────────────────────────────────────────────────

def create_app(engine: QueryEngineInterface):
    """Khởi tạo toàn bộ hệ thống Multi-Agent.

    Args:
        engine: Instance của QueryEngineInterface
                (MockQueryEngine hoặc GraphRAG thực sự).

    Returns:
        Compiled LangGraph app sẵn sàng chạy.
    """
    global _store

    # Inject engine cho Graph Retrieval + Query Executor
    set_engine(engine)

    # Tạo memory components
    checkpointer = create_checkpointer()
    _store = create_store()

    # Build & compile graph
    builder = build_graph()
    app = builder.compile(
        checkpointer=checkpointer,
        store=_store,
    )

    return app
