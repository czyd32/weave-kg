"""
Embedding API unified wrapper.
Supports: BGE-M3, Qwen3-Embedding-0.6B/4B/8B
API: OpenAI-compatible (SiliconFlow, OpenAI, etc.)

Configuration via environment variables:
  EMBED_API_KEY: API key (required)
  EMBED_API_BASE: API base URL (default: https://api.siliconflow.cn/v1)
  EMBED_MODEL: Model name (default: BAAI/bge-m3)
"""

import os
import json
import time
import requests
from typing import List, Optional

# === Config (environment variables) ===
API_KEY = os.environ.get("EMBED_API_KEY", "")
API_BASE = os.environ.get("EMBED_API_BASE", "https://api.siliconflow.cn/v1")
DEFAULT_MODEL = os.environ.get("EMBED_MODEL", "BAAI/bge-m3")

EMBEDDING_MODELS = {
    "BGE-M3": "BAAI/bge-m3",
    "Qwen3-Embedding-0.6B": "Qwen/Qwen3-Embedding-0.6B",
    "Qwen3-Embedding-4B": "Qwen/Qwen3-Embedding-4B",
    "Qwen3-Embedding-8B": "Qwen/Qwen3-Embedding-8B",
}


def embed(texts: List[str], model: str = None, max_retries: int = 3) -> List[List[float]]:
    """
    Generate embeddings for a list of texts.

    Args:
        texts: List of input texts
        model: Model name (default: from EMBED_MODEL env var or BAAI/bge-m3)
        max_retries: Max retries on failure

    Returns:
        List of embedding vectors (list of floats)
    """
    if not texts:
        return []

    model = model or DEFAULT_MODEL
    if model in EMBEDDING_MODELS:
        model = EMBEDDING_MODELS[model]

    if not API_KEY:
        raise ValueError("EMBED_API_KEY environment variable not set. "
                         "Set it with: export EMBED_API_KEY=your-key")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "input": texts,
        "encoding_format": "float",
    }

    for attempt in range(max_retries):
        try:
            resp = requests.post(
                f"{API_BASE}/embeddings",
                headers=headers,
                json=payload,
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            return [item["embedding"] for item in data["data"]]
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                time.sleep(wait)
            else:
                raise RuntimeError(f"Embedding failed after {max_retries} retries: {e}")


def embed_single(text: str, model: str = None) -> List[float]:
    """Generate embedding for a single text."""
    return embed([text], model=model)[0]


if __name__ == "__main__":
    # Test
    test_texts = ["Hello world", "知识图谱"]
    print(f"Testing embedding with model: {DEFAULT_MODEL}")
    try:
        embeddings = embed(test_texts)
        print(f"  Success: {len(embeddings)} vectors, dim={len(embeddings[0])}")
    except Exception as e:
        print(f"  Error: {e}")