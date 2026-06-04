from __future__ import annotations

import hashlib
import logging
import os
import struct
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ImageClassificationResult:
    label: str
    confidence: float
    details: dict[str, Any] = field(default_factory=dict)
    method: str = "heuristic"


@dataclass
class FaceDetectionResult:
    face_count: int
    regions: list[dict[str, Any]]
    has未成年人: bool = False


@dataclass
class OCRResult:
    text: str
    confidence: float
    regions: list[dict[str, Any]]


NSFW_SIGNATURES = {
    b"\xff\xd8\xff": "JPEG",
    b"\x89PNG": "PNG",
    b"GIF8": "GIF",
    b"RIFF": "WEBP",
}


class ImageClassifier:
    def __init__(
        self,
        nsfw_threshold: float = 0.7,
        api_fallback_url: str | None = None,
    ) -> None:
        self._nsfw_threshold = nsfw_threshold
        self._api_fallback_url = api_fallback_url
        self._nsfw_model = None
        self._face_cascade = None
        self._ocr_reader = None

    def _load_nsfw_model(self):
        if self._nsfw_model is not None:
            return
        try:
            from transformers import pipeline

            self._nsfw_model = pipeline(
                "image-classification",
                model="Falconsai/nsfw_image_detection",
                device=-1,
            )
            logger.info("Loaded NSFW image classification model")
        except Exception as exc:
            logger.warning("Could not load NSFW model: %s", exc)

    def _load_face_cascade(self):
        if self._face_cascade is not None:
            return
        try:
            import cv2

            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self._face_cascade = cv2.CascadeClassifier(cascade_path)
            logger.info("Loaded face detection cascade")
        except Exception as exc:
            logger.warning("Could not load face cascade: %s", exc)

    def _load_ocr(self):
        if self._ocr_reader is not None:
            return
        try:
            import easyocr

            self._ocr_reader = easyocr.Reader(["en"], gpu=False)
            logger.info("Loaded EasyOCR reader")
        except Exception as exc:
            logger.warning("Could not load EasyOCR: %s", exc)

    async def classify(self, image_path: str) -> ImageClassificationResult:
        nsfw_result = await self.detect_nsfw(image_path)
        return nsfw_result

    async def detect_nsfw(self, image_path: str) -> ImageClassificationResult:
        self._load_nsfw_model()

        if self._nsfw_model is not None:
            try:
                from PIL import Image

                img = Image.open(image_path).convert("RGB")
                predictions = self._nsfw_model(img)

                nsfw_score = 0.0
                sfw_score = 0.0
                for pred in predictions:
                    label = pred.get("label", "").lower()
                    score = pred.get("score", 0)
                    if "nsfw" in label or "porn" in label or "sexy" in label:
                        nsfw_score += score
                    else:
                        sfw_score += score

                method = "transformer"
                if nsfw_score >= self._nsfw_threshold:
                    return ImageClassificationResult(
                        label="NSFW",
                        confidence=nsfw_score,
                        details={"raw_predictions": predictions, "file": image_path},
                        method=method,
                    )
                return ImageClassificationResult(
                    label="SFW",
                    confidence=sfw_score,
                    details={"raw_predictions": predictions, "file": image_path},
                    method=method,
                )
            except Exception as exc:
                logger.warning("NSFW model inference failed: %s", exc)

        if self._api_fallback_url:
            try:
                import httpx

                async with httpx.AsyncClient(timeout=30.0) as client:
                    with open(image_path, "rb") as f:
                        response = await client.post(
                            f"{self._api_fallback_url}/classify/image",
                            files={"file": (os.path.basename(image_path), f)},
                        )
                    if response.status_code == 200:
                        data = response.json()
                        score = float(data.get("nsfw_score", 0))
                        label = "NSFW" if score >= self._nsfw_threshold else "SFW"
                        return ImageClassificationResult(
                            label=label,
                            confidence=score,
                            details=data,
                            method="api",
                        )
            except Exception as exc:
                logger.warning("API image classification failed: %s", exc)

        file_size = os.path.getsize(image_path)
        ext = os.path.splitext(image_path)[1].lower()
        heuristic_score = 0.0
        if ext in (".gif",):
            heuristic_score += 0.1
        if file_size > 5 * 1024 * 1024:
            heuristic_score += 0.05

        return ImageClassificationResult(
            label="SFW",
            confidence=max(0.5, 1.0 - heuristic_score),
            details={"file_size": file_size, "extension": ext},
            method="heuristic",
        )

    async def detect_faces(self, image_path: str) -> FaceDetectionResult:
        self._load_face_cascade()

        if self._face_cascade is not None:
            try:
                import cv2

                img = cv2.imread(image_path)
                if img is None:
                    return FaceDetectionResult(face_count=0, regions=[])

                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                faces = self._face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

                regions = []
                for x, y, w, h in faces:
                    regions.append({"x": int(x), "y": int(y), "width": int(w), "height": int(h)})

                return FaceDetectionResult(face_count=len(regions), regions=regions)
            except Exception as exc:
                logger.warning("Face detection failed: %s", exc)

        return FaceDetectionResult(face_count=0, regions=[])

    async def detect_text_in_image(self, image_path: str) -> OCRResult:
        self._load_ocr()

        if self._ocr_reader is not None:
            try:
                results = self._ocr_reader.readtext(image_path)

                texts = []
                regions = []
                total_conf = 0.0
                for bbox, text, conf in results:
                    texts.append(text)
                    total_conf += conf
                    regions.append({"text": text, "confidence": float(conf), "bbox": bbox})

                avg_conf = total_conf / len(results) if results else 0.0
                return OCRResult(
                    text=" ".join(texts),
                    confidence=avg_conf,
                    regions=regions,
                )
            except Exception as exc:
                logger.warning("OCR failed: %s", exc)

        return OCRResult(text="", confidence=0.0, regions=[])
