from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from src.ai.embeddings import EmbeddingService
from src.ai.ollama_client import OllamaClient
from src.data.vector_store import VectorStore

logger = logging.getLogger(__name__)


@dataclass
class RAGDocument:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] = field(default_factory=list)


@dataclass
class RAGResponse:
    answer: str
    sources: list[dict[str, Any]]
    context: str


class RAGEngine:
    def __init__(
        self,
        vector_store: VectorStore,
        ollama_client: OllamaClient,
        embedding_service: EmbeddingService,
        collection_name: str = "documents",
        embedding_model: str = "nomic-embed-text",
        llm_model: str = "llama3.1",
        chunk_size: int = 512,
        chunk_overlap: int = 64,
    ) -> None:
        self._vector_store = vector_store
        self._ollama = ollama_client
        self._embeddings = embedding_service
        self._collection = collection_name
        self._embedding_model = embedding_model
        self._llm_model = llm_model
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def _chunk_text(self, text: str) -> list[str]:
        chunks = []
        start = 0
        while start < len(text):
            end = start + self._chunk_size
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk)
            start = end - self._chunk_overlap
            if start >= len(text):
                break
        return chunks

    async def index_document(
        self,
        document_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        metadata = metadata or {}
        chunks = self._chunk_text(content)

        texts = []
        metadatas = []
        ids = []
        for i, chunk in enumerate(chunks):
            chunk_id = f"{document_id}_chunk_{i}"
            ids.append(chunk_id)
            texts.append(chunk)
            metadatas.append({**metadata, "document_id": document_id, "chunk_index": i, "total_chunks": len(chunks)})

        embeddings = await self._embeddings.batch_embed(texts, model=self._embedding_model)

        points = [
            {
                "id": chunk_id,
                "vector": emb,
                "payload": {**meta, "text": text},
            }
            for chunk_id, emb, meta, text in zip(ids, embeddings, metadatas, texts, strict=False)
        ]

        await self._vector_store.insert_vectors(self._collection, points)
        logger.info("Indexed %d chunks for document %s", len(chunks), document_id)
        return len(chunks)

    async def query(
        self,
        query_text: str,
        top_k: int = 5,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        query_embedding = await self._embeddings.generate_text_embedding(query_text, model=self._embedding_model)

        results = await self._vector_store.search(
            collection_name=self._collection,
            query_vector=query_embedding,
            top_k=top_k,
            query_filter=filter_metadata,
        )
        return results

    async def hybrid_search(
        self,
        query_text: str,
        top_k: int = 10,
        keyword_boost: float = 0.3,
        semantic_boost: float = 0.7,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        semantic_results = await self.query(query_text, top_k=top_k * 2, filter_metadata=filter_metadata)

        keyword_results = await self._keyword_search(query_text, top_k=top_k * 2, filter_metadata=filter_metadata)

        combined: dict[str, dict[str, Any]] = {}
        for rank, result in enumerate(semantic_results):
            rid = result.get("id", "")
            combined[rid] = {**result, "semantic_score": result.get("score", 0) * semantic_boost, "keyword_score": 0.0, "rank_semantic": rank}

        for rank, result in enumerate(keyword_results):
            rid = result.get("id", "")
            if rid in combined:
                combined[rid]["keyword_score"] = result.get("score", 0) * keyword_boost
            else:
                combined[rid] = {**result, "semantic_score": 0.0, "keyword_score": result.get("score", 0) * keyword_boost, "rank_keyword": rank}

        for item in combined.values():
            item["combined_score"] = item.get("semantic_score", 0) + item.get("keyword_score", 0)

        sorted_results = sorted(combined.values(), key=lambda x: x["combined_score"], reverse=True)
        return sorted_results[:top_k]

    async def _keyword_search(
        self,
        query_text: str,
        top_k: int = 10,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        try:
            return await self._vector_store.search(
                collection_name=self._collection,
                query_vector=await self._embeddings.generate_text_embedding(query_text, model=self._embedding_model),
                top_k=top_k,
                query_filter=filter_metadata,
            )
        except Exception:
            return []

    async def get_context(self, query_text: str, top_k: int = 3) -> str:
        results = await self.query(query_text, top_k=top_k)
        context_parts = []
        for r in results:
            text = r.get("payload", {}).get("text", "")
            if text:
                context_parts.append(text)
        return "\n\n---\n\n".join(context_parts) if context_parts else ""

    async def generate_answer(
        self,
        query_text: str,
        system_prompt: str | None = None,
        top_k: int = 3,
        temperature: float = 0.3,
    ) -> RAGResponse:
        context = await self.get_context(query_text, top_k=top_k)
        sources = await self.query(query_text, top_k=top_k)

        if not system_prompt:
            system_prompt = (
                "You are a helpful assistant. Answer the question based on the provided context. "
                "If the context does not contain enough information, say so clearly. "
                "Cite specific parts of the context when possible."
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query_text}"},
        ]

        result = await self._ollama.chat(
            model=self._llm_model,
            messages=messages,
            temperature=temperature,
        )

        answer = result.get("message", {}).get("content", "") if isinstance(result, dict) else ""

        return RAGResponse(
            answer=answer,
            sources=[{"id": s.get("id"), "score": s.get("score"), "text": s.get("payload", {}).get("text", "")} for s in sources],
            context=context,
        )
