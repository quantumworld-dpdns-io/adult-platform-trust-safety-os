"""Full-text search: indexing, querying, suggestions, and highlighting."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class FullTextSearch:
    def __init__(self) -> None:
        self._index: dict[str, dict[str, Any]] = {}
        self._inverted_index: dict[str, set[str]] = {}
        self._doc_count = 0

    def _tokenize(self, text: str) -> list[str]:
        text_lower = text.lower()
        tokens = re.findall(r"\b\w+\b", text_lower)
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "shall", "can", "to", "of", "in", "for",
            "on", "with", "at", "by", "from", "as", "into", "through", "during",
            "before", "after", "above", "below", "between", "and", "but", "or",
            "not", "no", "nor", "if", "then", "else", "this", "that", "these",
            "those", "it", "its", "i", "me", "my", "we", "our", "you", "your",
            "he", "him", "his", "she", "her", "they", "them", "their", "what",
            "which", "who", "whom", "when", "where", "why", "how", "all", "each",
            "every", "both", "few", "more", "most", "other", "some", "such", "than",
        }
        return [t for t in tokens if t not in stopwords and len(t) > 1]

    def _compute_tf(self, tokens: list[str]) -> dict[str, float]:
        counts = Counter(tokens)
        total = len(tokens) or 1
        return {token: count / total for token, count in counts.items()}

    def index_document(
        self,
        doc_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        tokens = self._tokenize(content)
        tf = self._compute_tf(tokens)

        self._index[doc_id] = {
            "content": content,
            "tokens": tokens,
            "tf": tf,
            "metadata": metadata or {},
            "token_count": len(tokens),
        }

        for token in set(tokens):
            if token not in self._inverted_index:
                self._inverted_index[token] = set()
            self._inverted_index[token].add(doc_id)

        self._doc_count += 1

        return {
            "doc_id": doc_id,
            "indexed": True,
            "token_count": len(tokens),
            "unique_tokens": len(set(tokens)),
        }

    def remove_from_index(self, doc_id: str) -> dict[str, Any]:
        if doc_id not in self._index:
            return {"doc_id": doc_id, "removed": False, "error": "Document not found"}

        doc = self._index.pop(doc_id)
        for token in set(doc["tokens"]):
            if token in self._inverted_index:
                self._inverted_index[token].discard(doc_id)
                if not self._inverted_index[token]:
                    del self._inverted_index[token]

        self._doc_count -= 1
        return {"doc_id": doc_id, "removed": True}

    def search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return {"results": [], "total": 0, "query": query}

        candidate_ids: set[str] | None = None
        for token in query_tokens:
            token_docs = self._inverted_index.get(token, set())
            if candidate_ids is None:
                candidate_ids = set(token_docs)
            else:
                candidate_ids &= token_docs

        if not candidate_ids:
            return {"results": [], "total": 0, "query": query}

        scored: list[tuple[str, float]] = []
        for doc_id in candidate_ids:
            doc = self._index[doc_id]
            score = sum(doc["tf"].get(t, 0.0) for t in query_tokens)

            if filters:
                metadata = doc.get("metadata", {})
                skip = False
                for key, value in filters.items():
                    if metadata.get(key) != value:
                        skip = True
                        break
                if skip:
                    continue

            scored.append((doc_id, score))

        scored.sort(key=lambda x: -x[1])
        total = len(scored)
        paginated = scored[offset:offset + limit]

        results = []
        for doc_id, score in paginated:
            doc = self._index[doc_id]
            results.append({
                "doc_id": doc_id,
                "score": round(score, 4),
                "content": doc["content"][:500],
                "metadata": doc["metadata"],
            })

        return {
            "results": results,
            "total": total,
            "query": query,
            "offset": offset,
            "limit": limit,
        }

    def get_suggestions(self, prefix: str, limit: int = 10) -> list[str]:
        prefix_lower = prefix.lower()
        suggestions: list[str] = []
        for token in sorted(self._inverted_index.keys()):
            if token.startswith(prefix_lower):
                suggestions.append(token)
                if len(suggestions) >= limit:
                    break
        return suggestions

    def highlight(
        self,
        text: str,
        query: str,
        highlight_tag: str = "mark",
    ) -> str:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return text

        result = text
        for token in query_tokens:
            pattern = re.compile(re.escape(token), re.IGNORECASE)
            result = pattern.sub(
                f"<{highlight_tag}>{token}</{highlight_tag}>",
                result,
            )
        return result

    def get_index_stats(self) -> dict[str, Any]:
        return {
            "total_documents": self._doc_count,
            "total_tokens": len(self._inverted_index),
            "index_size_estimate": sum(
                len(doc["content"]) for doc in self._index.values()
            ),
        }
