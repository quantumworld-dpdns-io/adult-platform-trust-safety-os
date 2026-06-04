from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from src.ai.classifiers.image_classifier import ImageClassifier, ImageClassificationResult
from src.ai.classifiers.text_classifier import TextClassifier, ClassificationResult

logger = logging.getLogger(__name__)


@dataclass
class EnsembleResult:
    decision: str
    confidence: float
    reasons: list[str]
    classifier_results: dict[str, Any]
    method: str = "ensemble"


@dataclass
class ClassifierConfig:
    name: str
    weight: float
    enabled: bool = True
    threshold: float = 0.5


DEFAULT_CLASSIFIER_CONFIGS = [
    ClassifierConfig(name="nsfw", weight=0.4, threshold=0.6),
    ClassifierConfig(name="toxicity", weight=0.25, threshold=0.5),
    ClassifierConfig(name="hate_speech", weight=0.25, threshold=0.5),
    ClassifierConfig(name="spam", weight=0.1, threshold=0.5),
]


class EnsembleClassifier:
    def __init__(
        self,
        text_classifier: TextClassifier | None = None,
        image_classifier: ImageClassifier | None = None,
        configs: list[ClassifierConfig] | None = None,
    ) -> None:
        self._text_classifier = text_classifier or TextClassifier()
        self._image_classifier = image_classifier or ImageClassifier()
        self._configs = configs or DEFAULT_CLASSIFIER_CONFIGS
        self._config_map = {c.name: c for c in self._configs}

    async def classify(
        self,
        text: str | None = None,
        image_path: str | None = None,
        audio_path: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> EnsembleResult:
        all_results: dict[str, ClassificationResult] = {}
        image_results: dict[str, ImageClassificationResult] = {}
        reasons: list[str] = []

        if text:
            text_results = await self._text_classifier.classify(text)
            for result in text_results:
                all_results[result.label] = result

        if image_path:
            nsfw_result = await self._image_classifier.detect_nsfw(image_path)
            image_results["nsfw"] = nsfw_result
            if nsfw_result.label == "NSFW":
                all_results["NSFW"] = ClassificationResult(
                    label="NSFW",
                    confidence=nsfw_result.confidence,
                    details={"source": "image", **nsfw_result.details},
                    method=nsfw_result.method,
                )

        if audio_path:
            audio_results = await self._classify_audio(audio_path)
            all_results.update(audio_results)

        weighted_scores: dict[str, float] = {}
        total_weight = 0.0

        for config in self._configs:
            if not config.enabled:
                continue

            matching = [r for label, r in all_results.items() if config.name.upper() in label or config.name in label.lower()]

            if matching:
                max_conf = max(r.confidence for r in matching)
                weighted_scores[config.name] = max_conf * config.weight
                total_weight += config.weight

                if max_conf >= config.threshold:
                    reasons.append(f"{config.name}: {max_conf:.2f} >= {config.threshold} threshold")

        if total_weight > 0:
            normalized_score = sum(weighted_scores.values()) / total_weight
        else:
            normalized_score = 0.0

        decision = "ALLOW"
        if normalized_score >= 0.7:
            decision = "BLOCK"
        elif normalized_score >= 0.4:
            decision = "REVIEW"
        elif normalized_score >= 0.2:
            decision = "FLAG"

        if not reasons:
            reasons.append("No classifiers triggered above threshold")

        return EnsembleResult(
            decision=decision,
            confidence=normalized_score,
            reasons=reasons,
            classifier_results={
                "text": {r.label: {"confidence": r.confidence, "method": r.method} for r in all_results.values() if r.method != "api"},
                "image": {label: {"confidence": r.confidence, "label": r.label} for label, r in image_results.items()},
            },
            method="ensemble",
        )

    async def _classify_audio(self, audio_path: str) -> dict[str, ClassificationResult]:
        results: dict[str, ClassificationResult] = {}
        try:
            import os

            file_size = os.path.getsize(audio_path)
            results["audio_info"] = ClassificationResult(
                label="AUDIO",
                confidence=0.0,
                details={"file_size": file_size, "path": audio_path},
                method="metadata",
            )
        except Exception as exc:
            logger.warning("Audio classification failed: %s", exc)
        return results

    async def vote(self, text: str | None = None, image_path: str | None = None) -> EnsembleResult:
        return await self.classify(text=text, image_path=image_path)

    def update_config(self, name: str, *, weight: float | None = None, threshold: float | None = None, enabled: bool | None = None) -> None:
        if name not in self._config_map:
            raise ValueError(f"Unknown classifier config: {name}")
        config = self._config_map[name]
        if weight is not None:
            config.weight = weight
        if threshold is not None:
            config.threshold = threshold
        if enabled is not None:
            config.enabled = enabled
