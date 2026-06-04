from __future__ import annotations

import logging
import uuid
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    Filter,
    FieldCondition,
    MatchValue,
    PointIdsList,
    VectorParams,
    UpdateStatus,
)

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        api_key: str | None = None,
        https: bool = False,
        timeout: float = 30.0,
    ) -> None:
        self._host = host
        self._port = port
        self._client: QdrantClient | None = None
        self._api_key = api_key
        self._https = https
        self._timeout = timeout

    def _get_client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(
                host=self._host,
                port=self._port,
                api_key=self._api_key,
                https=self._https,
                timeout=self._timeout,
            )
        return self._client

    async def create_collection(
        self,
        collection_name: str,
        vector_size: int = 384,
        distance: str = "Cosine",
        **kwargs: Any,
    ) -> bool:
        client = self._get_client()

        distance_map = {
            "Cosine": Distance.COSINE,
            "Euclid": Distance.EUCLID,
            "Dot": Distance.DOT,
        }

        try:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance_map.get(distance, Distance.COSINE),
                ),
                **kwargs,
            )
            logger.info("Created collection %s with vector_size=%d", collection_name, vector_size)
            return True
        except Exception as exc:
            if "already exists" in str(exc).lower():
                logger.info("Collection %s already exists", collection_name)
                return True
            raise

    async def insert_vectors(
        self,
        collection_name: str,
        points: list[dict[str, Any]],
    ) -> UpdateStatus | None:
        client = self._get_client()

        processed_points = []
        for point in points:
            point_id = point.get("id", str(uuid.uuid4()))
            vector = point.get("vector", [])
            payload = point.get("payload", {})

            processed_points.append({
                "id": point_id,
                "vector": vector,
                "payload": payload,
            })

        result = client.upsert(
            collection_name=collection_name,
            points=processed_points,
        )
        logger.info("Inserted %d vectors into %s", len(processed_points), collection_name)
        return result

    async def search(
        self,
        collection_name: str,
        query_vector: list[float],
        top_k: int = 10,
        query_filter: dict[str, Any] | None = None,
        score_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        client = self._get_client()

        qdrant_filter = None
        if query_filter:
            conditions = []
            for key, value in query_filter.items():
                conditions.append(
                    FieldCondition(key=key, match=MatchValue(value=value))
                )
            qdrant_filter = Filter(must=conditions)

        results = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k,
            query_filter=qdrant_filter,
            score_threshold=score_threshold,
        )

        return [
            {
                "id": hit.id,
                "score": hit.score,
                "payload": hit.payload,
            }
            for hit in results
        ]

    async def delete_vectors(
        self,
        collection_name: str,
        ids: list[str | int],
    ) -> UpdateStatus | None:
        client = self._get_client()

        result = client.delete(
            collection_name=collection_name,
            points_selector=PointIdsList(points=ids),
        )
        logger.info("Deleted %d vectors from %s", len(ids), collection_name)
        return result

    async def update_vectors(
        self,
        collection_name: str,
        points: list[dict[str, Any]],
    ) -> UpdateStatus | None:
        return await self.insert_vectors(collection_name, points)

    async def get_collection_info(self, collection_name: str) -> dict[str, Any]:
        client = self._get_client()
        info = client.get_collection(collection_name)

        return {
            "name": collection_name,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "config": {
                "vector_size": info.config.params.vectors.size if info.config.params.vectors else None,
                "distance": str(info.config.params.vectors.distance) if info.config.params.vectors else None,
            },
        }

    async def list_collections(self) -> list[str]:
        client = self._get_client()
        collections = client.get_collections()
        return [c.name for c in collections.collections]

    async def health_check(self) -> dict[str, Any]:
        try:
            client = self._get_client()
            collections = client.get_collections()
            return {
                "status": "healthy",
                "collections": len(collections.collections),
                "host": self._host,
                "port": self._port,
            }
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}

    async def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
