from __future__ import annotations

import logging
import math
from typing import Sequence

logger = logging.getLogger(__name__)

DEFAULT_TEXT_MODEL = "all-MiniLM-L6-v2"
DEFAULT_IMAGE_MODEL = "clip-ViT-B-32"


class EmbeddingService:
    def __init__(
        self,
        text_model_name: str = DEFAULT_TEXT_MODEL,
        image_model_name: str = DEFAULT_IMAGE_MODEL,
        device: str | None = None,
    ) -> None:
        self._text_model_name = text_model_name
        self._image_model_name = image_model_name
        self._device = device
        self._text_model = None
        self._image_model = None
        self._use_ollama_fallback = False
        self._ollama_client = None

    def _load_text_model(self):
        if self._text_model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer

            self._text_model = SentenceTransformer(self._text_model_name, device=self._device)
            logger.info("Loaded text embedding model: %s", self._text_model_name)
        except ImportError:
            logger.warning("sentence-transformers not installed, using Ollama fallback")
            self._use_ollama_fallback = True
            self._init_ollama_fallback()

    def _load_image_model(self):
        if self._image_model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer

            self._image_model = SentenceTransformer(self._image_model_name, device=self._device)
            logger.info("Loaded image embedding model: %s", self._image_model_name)
        except ImportError:
            logger.warning("sentence-transformers not installed for image model")
            self._use_ollama_fallback = True
            self._init_ollama_fallback()

    def _init_ollama_fallback(self):
        if self._ollama_client is not None:
            return
        try:
            from src.ai.ollama_client import OllamaClient

            self._ollama_client = OllamaClient()
        except Exception as exc:
            logger.error("Failed to init Ollama fallback: %s", exc)

    async def generate_text_embedding(self, text: str, model: str | None = None) -> list[float]:
        self._load_text_model()

        if self._text_model is not None:
            import numpy as np

            embedding = self._text_model.encode(text, normalize_embeddings=True)
            return embedding.tolist() if isinstance(embedding, np.ndarray) else list(embedding)

        if self._ollama_client is not None:
            result = await self._ollama_client.embeddings(
                model=model or "nomic-embed-text",
                input=text,
            )
            if result:
                return result[0]
            raise RuntimeError("Ollama returned empty embedding")

        raise RuntimeError("No embedding backend available")

    async def generate_image_embedding(self, image_path: str, model: str | None = None) -> list[float]:
        self._load_image_model()

        if self._image_model is not None:
            from PIL import Image

            import numpy as np

            img = Image.open(image_path).convert("RGB")
            embedding = self._image_model.encode(img, normalize_embeddings=True)
            return embedding.tolist() if isinstance(embedding, np.ndarray) else list(embedding)

        raise RuntimeError("No image embedding backend available (install sentence-transformers)")

    async def batch_embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        self._load_text_model()

        if self._text_model is not None:
            import numpy as np

            embeddings = self._text_model.encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False)
            return [e.tolist() if isinstance(e, np.ndarray) else list(e) for e in embeddings]

        if self._ollama_client is not None:
            results = []
            for text in texts:
                emb = await self.generate_text_embedding(text, model=model)
                results.append(emb)
            return results

        raise RuntimeError("No embedding backend available")

    @staticmethod
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b, strict=False))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    async def rank_by_similarity(
        self,
        query: str,
        candidates: list[str],
        model: str | None = None,
    ) -> list[tuple[int, float]]:
        query_emb = await self.generate_text_embedding(query, model=model)
        candidate_embs = await self.batch_embed(candidates, model=model)
        scored = [
            (i, self.cosine_similarity(query_emb, cemb))
            for i, cemb in enumerate(candidate_embs)
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
