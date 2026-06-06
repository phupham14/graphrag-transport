"""
agent_core.config — Cấu hình hệ thống

Tập trung mọi hằng số, thông số cấu hình và khởi tạo LLM tại một nơi duy nhất.
"""

import os
from dotenv import load_dotenv
# --- Gemini ---
from langchain_google_genai import ChatGoogleGenerativeAI
# --- OpenAI ---
# from langchain_openai import ChatOpenAI

load_dotenv()

# ── Neo4j ─────────────────────────────────────────────────────────────────────
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# ── Google Gemini ─────────────────────────────────────────────────────────────
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# ── OpenAI ────────────────────────────────────────────────────────────────────
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ── Agent Settings ────────────────────────────────────────────────────────────
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
SUPERVISOR_MODEL = os.getenv("SUPERVISOR_MODEL", "gemini-2.5-flash")
WORKER_MODEL = os.getenv("WORKER_MODEL", "gemini-2.5-flash")
# SUPERVISOR_MODEL = os.getenv("SUPERVISOR_MODEL", "gpt-4o-mini")
# WORKER_MODEL = os.getenv("WORKER_MODEL", "gpt-4o-mini")

# ── LangSmith (Optional — bật để trace/debug) ────────────────────────────────
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "")
if LANGSMITH_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = LANGSMITH_API_KEY


def get_llm(model: str | None = None, temperature: float = 0):
    """Tạo instance LLM dùng chung cho các Agent.

    Args:
        model: Tên model. Mặc định dùng WORKER_MODEL.
        temperature: Độ sáng tạo. 0 = deterministic (tốt cho SQL/Cypher).
    """
    # --- Gemini ---
    return ChatGoogleGenerativeAI(
        model=model or WORKER_MODEL,
        google_api_key=GOOGLE_API_KEY,
        temperature=temperature,
    )
    
    # --- OpenAI ---
    # return ChatOpenAI(
    #     model=model or WORKER_MODEL,
    #     api_key=OPENAI_API_KEY,
    #     temperature=temperature,
    # )
