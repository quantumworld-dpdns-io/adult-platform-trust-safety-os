"""Semantic search: vector-based search, hybrid search, similarity, and recommendations."""

from __future__ import annotations

import hashlib
import math
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def _hash_embedding(text: str, dimensions: int = 128) -> list[float]:
    """Generate a deterministic pseudo-embedding from text using hashing."""
    import hashlib
    values: list[float] = []
    for i in range(dimensions):
        seed = f"{text}:{i}"
        h = hashlib.sha256(seed.encode()).digest()
        val = int.from_bytes(h[:4], "big") / (2**32) * 2 - 1
        values.append(val)
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
    norm_b = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (norm_a * norm_b)


class SemanticSearch:
    def __init__(self, embedding_dim: int = 128) -> None:
        self._documents: dict[str, dict[str, Any]] = {}
        self._embeddings: dict[str, list[float]] = {}
        self._embedding_dim = embedding_dim
        self._tag_index: dict[str, set[str]] = {}

    def index(
        self,
        doc_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        embedding = _hash_embedding(content, self._embedding_dim)

        self._documents[doc_id] = {
            "content": content,
            "metadata": metadata or {},
            "tags": tags or [],
        }
        self._embeddings[doc_id] = embedding

        for tag in tags or []:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(doc_id)

        return {
            "doc_id": doc_id,
            "indexed": True,
            "embedding_dim": self._embedding_dim,
            "tags": tags or [],
        }

    def search(
        self,
        query: str,
        limit: int = 20,
        tags: list[str] | None = None,
        min_score: float = 0.0,
    ) -> dict[str, Any]:
        query_embedding = _hash_embedding(query, self._embedding_dim)

        candidate_ids: set[str] | None = None
        if tags:
            for tag in tags:
                tag_docs = self._tag_index.get(tag, set())
                if candidate_ids is None:
                    candidate_ids = set(tag_docs)
                else:
                    candidate_ids |= tag_docs
            if not candidate_ids:
                return {"results": [], "total": 0, "query": query}
        else:
            candidate_ids = set(self._documents.keys())

        scored: list[tuple[str, float]] = []
        for doc_id in candidate_ids:
            doc_embedding = self._embeddings.get(doc_id)
            if doc_embedding is None:
                continue
            similarity = _cosine_similarity(query_embedding, doc_embedding)
            if similarity >= min_score:
                scored.append((doc_id, similarity))

        scored.sort(key=lambda x: -x[1])
        results = scored[:limit]

        output = []
        for doc_id, score in results:
            doc = self._documents[doc_id]
            output.append({
                "doc_id": doc_id,
                "score": round(score, 4),
                "content": doc["content"][:500],
                "metadata": doc["metadata"],
                "tags": doc["tags"],
            })

        return {
            "results": output,
            "total": len(scored),
            "query": query,
            "returned": len(output),
        }

    def hybrid_search(
        self,
        query: str,
        keyword_results: list[str] | None = None,
        semantic_weight: float = 0.6,
        keyword_weight: float = 0.4,
        limit: int = 20,
    ) -> dict[str, Any]:
        semantic_results = self.search(query, limit=limit * 2)

        semantic_scores: dict[str, float] = {}
        for r in semantic_results["results"]:
            semantic_scores[r["doc_id"]] = r["score"]

        keyword_scores: dict[str, float] = {}
        if keyword_results:
            for i, doc_id in enumerate(keyword_results):
                keyword_scores[doc_id] = 1.0 - (i / max(len(keyword_results), 1))

        all_ids = set(semantic_scores.keys()) | set(keyword_scores.keys())
        combined: list[tuple[str, float]] = []
        for doc_id in all_ids:
            s_score = semantic_scores.get(doc_id, 0.0)
            k_score = keyword_scores.get(doc_id, 0.0)
            combined_score = (semantic_weight * s_score) + (keyword_weight * k_score)
            combined.append((doc_id, combined_score))

        combined.sort(key=lambda x: -x[1])
        results = combined[:limit]

        output = []
        for doc_id, score in results:
            doc = self._documents.get(doc_id, {})
            output.append({
                "doc_id": doc_id,
                "score": round(score, 4),
                "content": doc.get("content", "")[:500],
                "metadata": doc.get("metadata", {}),
            })

        return {
            "results": output,
            "total": len(combined),
            "query": query,
            "semantic_weight": semantic_weight,
            "keyword_weight": keyword_weight,
        }

    def find_similar(
        self,
        doc_id: str,
        limit: int = 10,
        min_score: float = 0.5,
    ) -> dict[str, Any]:
        if doc_id not in self._documents:
            return {"error": "Document not found", "doc_id": doc_id}

        source_embedding = self._embeddings[doc_id]
        scored: list[tuple[str, float]] = []

        for other_id, other_embedding in self._embeddings.items():
            if other_id == doc_id:
                continue
            similarity = _cosine_similarity(source_embedding, other_embedding)
            if similarity >= min_score:
                scored.append((other_id, similarity))

        scored.sort(key=lambda x: -x[1])
        results = scored[:limit]

        output = []
        for other_id, score in results:
            doc = self._documents[other_id]
            output.append({
                "doc_id": other_id,
                "score": round(score, 4),
                "content": doc["content"][:300],
                "metadata": doc["metadata"],
            })

        return {
            "source_doc_id": doc_id,
            "similar_documents": output,
            "total_found": len(scored),
        }

    def get_recommendations(
        self,
        user_id: str,
        user_history: list[str] | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        if not user_history:
            return {"recommendations": [], "total": 0}

        combined_embedding = [0.0] * self._embedding_dim
        count = 0
        for doc_id in user_history:
            if doc_id in self._embeddings:
                emb = self._embeddings[doc_id]
                for i in range(self._embedding_dim):
                    combined_embedding[i] += emb[i]
                count += 1

        if count == 0:
            return {"recommendations": [], "total": 0}

        for i in range(self._embedding_dim):
            combined_embedding[i] /= count

        scored: list[tuple[str, float]] = []
        history_set = set(user_history)
        for doc_id, embedding in self._embeddings.items():
            if doc_id in history_set:
                continue
            similarity = _cosine_similarity(combined_embedding, embedding)
            scored.append((doc_id, similarity))

        scored.sort(key=lambda x: -x[1])
        results = scored[:limit]

        output = []
        for doc_id, score in results:
            doc = self._documents[doc_id]
            output.append({
                "doc_id": doc_id,
                "score": round(score, 4),
                "content": doc["content"][:300],
                "metadata": doc["metadata"],
            })

        return {
            "user_id": user_id,
            "recommendations": output,
            "total": len(scored),
            "based_on_history_size": count,
        }

    def get_index_stats(self) -> dict[str, Any]:
        return {
            "total_documents": len(self._documents),
            "embedding_dimensions": self._embedding_dim,
            "total_tags": len(self._tag_index),
            "memory_estimate_bytes": len(self._embeddings) * self._embedding_dim * 8,
        }
