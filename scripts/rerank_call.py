"""
Rerank API wrapper.
Supports: BGE-Reranker-v2
API: OpenAI-compatible (SiliconFlow, etc.)

Configuration via environment variables:
  RERANK_API_KEY: API key (default: same as EMBED_API_KEY)
  RERANK_API_BASE: API base URL (default: same as EMBED_API_BASE)
  RERANK_MODEL: Model name (default: BAAI/bge-reranker-v2-m3)
"""

import os
import json
import time
import requests
from typing import List, Optional


API_KEY = os.environ.get("RERANK_API_KEY") or os.environ.get("EMBED_API_KEY", "")
API_BASE = os.environ.get("RERANK_API_BASE") or os.environ.get("EMBED_API_BASE", "https://api.siliconflow.cn/v1")
DEFAULT_MODEL = os.environ.get("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")


def rerank(query: str, documents: List[str], top_n: int = 10, model: str = None) -> List[dict]:
    """
    Rerank documents for a query.

    Args:
        query: Query string
        documents: List of document strings
        top_n: Number of top results to return
        model: Model name

    Returns:
        List of {"index": int, "score": float, "document": str}
    """
    if not query or not documents:
        return []

    model = model or DEFAULT_MODEL

    if not API_KEY:
        raise ValueError("RERANK_API_KEY or EMBED_API_KEY environment variable not set")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "query": query,
        "documents": documents,
        "top_n": min(top_n, len(documents)),
    }

    resp = requests.post(
        f"{API_BASE}/rerank",
        headers=headers,
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])