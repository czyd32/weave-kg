"""
Query entry point for Weave.
Dual recall (vector + tag) + RRF fusion.

Configuration via environment variables:
  EMBED_API_KEY: API key for embedding
  KG_SHARED_DIR: Path to knowledge-graph/_shared/ directory
"""

import os
import sys
import json
import argparse
from typing import List, Dict

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from embed_call import embed_single


def rrf_fusion(results_a: List[dict], results_b: List[dict], k: int = 60) -> List[dict]:
    """
    Reciprocal Rank Fusion.
    Merges two ranked lists into one.
    """
    scores = {}
    docs = {}

    for rank, item in enumerate(results_a):
        doc_id = item["id"]
        scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank + 1)
        docs[doc_id] = item

    for rank, item in enumerate(results_b):
        doc_id = item["id"]
        scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank + 1)
        docs[doc_id] = item

    merged = []
    for doc_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        item = docs[doc_id].copy()
        item["rrf_score"] = score
        merged.append(item)

    return merged


def query_kg(query: str, kg_dir: str, top_k: int = 10) -> List[dict]:
    """
    Query a knowledge graph.

    Args:
        query: Natural language query
        kg_dir: Path to knowledge-graph/ directory
        top_k: Number of results

    Returns:
        List of matching propositions with scores
    """
    # TODO: Implement full dual recall + RRF fusion
    # This is a placeholder that shows the API structure
    query_vector = embed_single(query)

    # Load propositions from kg_dir
    propositions_dir = os.path.join(kg_dir, "kg-proposition", "propositions")
    results = []

    if os.path.exists(propositions_dir):
        for fname in os.listdir(propositions_dir):
            if fname.endswith(".json") and not fname.startswith("_"):
                with open(os.path.join(propositions_dir, fname), "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        results.extend(data)
                    elif isinstance(data, dict):
                        results.append(data)

    return results[:top_k]


def main():
    parser = argparse.ArgumentParser(description="Weave Query")
    parser.add_argument("query", help="Natural language query")
    parser.add_argument("--kg-dir", default=os.environ.get("KG_SHARED_DIR", "./knowledge-graph"),
                        help="Path to knowledge-graph directory")
    parser.add_argument("--top-k", type=int, default=10, help="Number of results")
    args = parser.parse_args()

    print(f"Query: {args.query}")
    print(f"KG directory: {args.kg_dir}")
    print("-" * 50)

    results = query_kg(args.query, args.kg_dir, args.top_k)

    for i, r in enumerate(results):
        print(f"\n[{i+1}] {r.get('subject', '?')} → {r.get('relation', '?')} → {r.get('object', '?')}")
        print(f"    Source: {r.get('source_id', '?')}")
        if r.get('original_text'):
            print(f"    Text: {r['original_text'][:100]}...")


if __name__ == "__main__":
    main()