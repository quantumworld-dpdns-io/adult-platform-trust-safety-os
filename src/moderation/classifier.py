"""Content classification for text, image, video, audio, and multimodal inputs."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ContentClassification:
    labels: list[str] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    nsfw_score: float = 0.0
    toxicity_score: float = 0.0
    violence_score: float = 0.0
    spam_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


# Rule-based keyword banks (placeholder for ML model integration)
NSFW_KEYWORDS = {
    "pornography", "nsfw", "adult", "xxx", "explicit", "nude", "nudity",
    "sexually", "erotic", "fetish",
}
VIOLENCE_KEYWORDS = {
    "kill", "murder", "assault", "weapon", "bomb", "attack", "threat",
    "harm", "violence", "blood",
}
SPAM_KEYWORDS = {
    "buy now", "free money", "click here", "limited offer", "act now",
    "congratulations", "you won", "subscribe", "discount",
}
TOXICITY_KEYWORDS = {
    "hate", "idiot", "stupid", "moron", "loser", "trash", "disgusting",
    "worthless", "pathetic",
}


class ContentClassifier:
    """Classify content using a combination of rule-based and ML-ready hooks.

    Each ``classify_*`` method returns a ``ContentClassification`` with
    labels, scores, and an overall confidence value.  The scores range
    from 0.0 (benign) to 1.0 (definitely problematic).
    """

    def __init__(self, *, toxicity_threshold: float = 0.8, nsfw_threshold: float = 0.9) -> None:
        self._toxicity_threshold = toxicity_threshold
        self._nsfw_threshold = nsfw_threshold

    def classify_text(self, text: str) -> ContentClassification:
        lower = text.lower()
        words = set(re.findall(r"\b\w+\b", lower))

        nsfw_hits = len(words & NSFW_KEYWORDS)
        violence_hits = len(words & VIOLENCE_KEYWORDS)
        spam_hits = len(words & SPAM_KEYWORDS)
        toxicity_hits = len(words & TOXICITY_KEYWORDS)

        total_words = max(len(words), 1)
        nsfw_score = min(nsfw_hits / max(total_words * 0.1, 1), 1.0)
        violence_score = min(violence_hits / max(total_words * 0.1, 1), 1.0)
        spam_score = min(spam_hits / max(total_words * 0.1, 1), 1.0)
        toxicity_score = min(toxicity_hits / max(total_words * 0.1, 1), 1.0)

        labels: list[str] = []
        scores: dict[str, float] = {}
        if nsfw_score > 0:
            labels.append("NSFW")
            scores["nsfw"] = nsfw_score
        if violence_score > 0:
            labels.append("VIOLENCE")
            scores["violence"] = violence_score
        if spam_score > 0:
            labels.append("SPAM")
            scores["spam"] = spam_score
        if toxicity_score > 0:
            labels.append("TOXICITY")
            scores["toxicity"] = toxicity_score

        confidence = max(scores.values()) if scores else 0.0

        return ContentClassification(
            labels=labels,
            scores=scores,
            confidence=confidence,
            nsfw_score=nsfw_score,
            toxicity_score=toxicity_score,
            violence_score=violence_score,
            spam_score=spam_score,
            metadata={"word_count": total_words, "text_length": len(text)},
        )

    def classify_image(self, image_bytes: bytes, *, filename: str = "") -> ContentClassification:
        """Classify an image.  In production this hooks into a vision model."""
        file_size = len(image_bytes)
        is_likely_nsfw = file_size > 5_000_000 and any(
            ext in filename.lower()
            for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp")
        )

        nsfw_score = 0.85 if is_likely_nsfw else 0.1
        labels = ["NSFW"] if nsfw_score > self._nsfw_threshold else []
        scores = {"nsfw": nsfw_score} if nsfw_score > 0 else {}
        confidence = nsfw_score if labels else 0.0

        return ContentClassification(
            labels=labels,
            scores=scores,
            confidence=confidence,
            nsfw_score=nsfw_score,
            metadata={"filename": filename, "file_size": file_size},
        )

    def classify_video(self, video_bytes: bytes, *, filename: str = "") -> ContentClassification:
        """Classify a video.  In production this hooks into a video model."""
        file_size = len(video_bytes)
        nsfw_score = 0.7 if file_size > 50_000_000 else 0.2

        labels = ["NSFW"] if nsfw_score > self._nsfw_threshold else []
        scores = {"nsfw": nsfw_score} if nsfw_score > 0 else {}
        confidence = nsfw_score if labels else 0.0

        return ContentClassification(
            labels=labels,
            scores=scores,
            confidence=confidence,
            nsfw_score=nsfw_score,
            metadata={"filename": filename, "file_size": file_size},
        )

    def classify_audio(self, audio_bytes: bytes, *, filename: str = "") -> ContentClassification:
        """Classify audio content.  In production this hooks into an audio model."""
        file_size = len(audio_bytes)
        spam_score = 0.3 if file_size < 100_000 else 0.05

        labels = ["SPAM"] if spam_score > 0.5 else []
        scores = {"spam": spam_score} if spam_score > 0 else {}
        confidence = spam_score if labels else 0.0

        return ContentClassification(
            labels=labels,
            scores=scores,
            confidence=confidence,
            spam_score=spam_score,
            metadata={"filename": filename, "file_size": file_size},
        )

    def classify_multimodal(
        self,
        *,
        text: str | None = None,
        image_bytes: bytes | None = None,
        video_bytes: bytes | None = None,
        audio_bytes: bytes | None = None,
        filename: str = "",
    ) -> ContentClassification:
        """Classify content that spans multiple modalities."""
        results: list[ContentClassification] = []

        if text:
            results.append(self.classify_text(text))
        if image_bytes is not None:
            results.append(self.classify_image(image_bytes, filename=filename))
        if video_bytes is not None:
            results.append(self.classify_video(video_bytes, filename=filename))
        if audio_bytes is not None:
            results.append(self.classify_audio(audio_bytes, filename=filename))

        if not results:
            return ContentClassification()

        all_labels: list[str] = []
        merged_scores: dict[str, float] = {}
        max_confidence = 0.0

        for r in results:
            all_labels.extend(r.labels)
            merged_scores.update(r.scores)
            max_confidence = max(max_confidence, r.confidence)

        return ContentClassification(
            labels=list(set(all_labels)),
            scores=merged_scores,
            confidence=max_confidence,
            nsfw_score=max((r.nsfw_score for r in results), default=0.0),
            toxicity_score=max((r.toxicity_score for r in results), default=0.0),
            violence_score=max((r.violence_score for r in results), default=0.0),
            spam_score=max((r.spam_score for r in results), default=0.0),
            metadata={"modalities": len(results)},
        )
