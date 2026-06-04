from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    label: str
    confidence: float
    details: dict[str, Any] = field(default_factory=dict)
    method: str = "rule_based"


NSFW_KEYWORDS = [
    "porn", "xxx", "nsfw", "nude", "naked", "sex", "erotic", "adult",
    "hentai", "fetish", "orgasm", "masturbat", "prostitut", "escort",
]

TOXICITY_KEYWORDS = [
    "idiot", "stupid", "moron", "dumb", "trash", "loser", "shut up",
    "damn", "hell", "suck", "ugly", "fat", "disgusting", "pathetic",
    "kill yourself", "kys", "no one likes you", "go away", "worthless",
]

HATE_SPEECH_KEYWORDS = [
    "nigger", "faggot", "retard", "spic", "chink", "kike", "dyke",
    "tranny", "cripple", "towelhead", "raghead", "beaner", "wetback",
]

SPAM_INDICATORS = [
    "buy now", "click here", "free money", "act now", "limited time",
    "congratulations", "you won", "claim your", "risk free", "no cost",
    "earn money", "work from home", "make $$$", "100% free", "unsubscribe",
]

DEFAULT_TOXICITY_THRESHOLD = 0.6
DEFAULT_NSFW_THRESHOLD = 0.7
DEFAULT_HATE_THRESHOLD = 0.8
DEFAULT_SPAM_THRESHOLD = 0.5


class TextClassifier:
    def __init__(
        self,
        nsfw_threshold: float = DEFAULT_NSFW_THRESHOLD,
        toxicity_threshold: float = DEFAULT_TOXICITY_THRESHOLD,
        hate_threshold: float = DEFAULT_HATE_THRESHOLD,
        spam_threshold: float = DEFAULT_SPAM_THRESHOLD,
        api_fallback_url: str | None = None,
    ) -> None:
        self._nsfw_threshold = nsfw_threshold
        self._toxicity_threshold = toxicity_threshold
        self._hate_threshold = hate_threshold
        self._spam_threshold = spam_threshold
        self._api_fallback_url = api_fallback_url
        self._api_client = None

    def _normalize_text(self, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text

    def _keyword_score(self, text: str, keywords: list[str]) -> float:
        normalized = self._normalize_text(text)
        if not normalized:
            return 0.0
        words = set(normalized.split())
        matched = sum(1 for kw in keywords if kw in normalized or any(w.startswith(kw) for w in words))
        if not keywords:
            return 0.0
        return min(matched / max(len(keywords) * 0.3, 1), 1.0)

    def _caps_ratio(self, text: str) -> float:
        alpha_chars = [c for c in text if c.isalpha()]
        if not alpha_chars:
            return 0.0
        return sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)

    def _exclamation_ratio(self, text: str) -> float:
        if not text:
            return 0.0
        return text.count("!") / max(len(text), 1) * 10

    def _url_count(self, text: str) -> int:
        return len(re.findall(r"https?://\S+|www\.\S+", text))

    async def classify(self, text: str) -> list[ClassificationResult]:
        results = []

        nsfw_result = await self.detect_nsfw(text)
        results.append(nsfw_result)

        toxicity_result = await self.detect_toxicity(text)
        results.append(toxicity_result)

        hate_result = await self.detect_hate_speech(text)
        results.append(hate_result)

        spam_result = await self.detect_spam(text)
        results.append(spam_result)

        return results

    async def detect_nsfw(self, text: str) -> ClassificationResult:
        score = self._keyword_score(text, NSFW_KEYWORDS)

        if score >= self._nsfw_threshold:
            method = "rule_based"
            if score < 1.0 and self._api_fallback_url:
                api_score = await self._api_classify(text, "nsfw")
                if api_score is not None:
                    score = (score + api_score) / 2
                    method = "ensemble"

            return ClassificationResult(
                label="NSFW",
                confidence=score,
                details={"matched_keywords": self._get_matched_keywords(text, NSFW_KEYWORDS)},
                method=method,
            )

        return ClassificationResult(label="SFW", confidence=1.0 - score, method="rule_based")

    async def detect_toxicity(self, text: str) -> ClassificationResult:
        score = self._keyword_score(text, TOXICITY_KEYWORDS)
        caps_bonus = self._caps_ratio(text) * 0.2
        excl_bonus = min(self._exclamation_ratio(text), 0.3)
        score = min(score + caps_bonus + excl_bonus, 1.0)

        if score >= self._toxicity_threshold:
            method = "rule_based"
            if score < 1.0 and self._api_fallback_url:
                api_score = await self._api_classify(text, "toxicity")
                if api_score is not None:
                    score = (score + api_score) / 2
                    method = "ensemble"

            return ClassificationResult(
                label="TOXIC",
                confidence=score,
                details={
                    "caps_ratio": round(self._caps_ratio(text), 3),
                    "exclamation_ratio": round(self._exclamation_ratio(text), 3),
                    "matched_keywords": self._get_matched_keywords(text, TOXICITY_KEYWORDS),
                },
                method=method,
            )

        return ClassificationResult(label="NOT_TOXIC", confidence=1.0 - score, method="rule_based")

    async def detect_hate_speech(self, text: str) -> ClassificationResult:
        score = self._keyword_score(text, HATE_SPEECH_KEYWORDS)

        if score >= self._hate_threshold:
            method = "rule_based"
            if score < 1.0 and self._api_fallback_url:
                api_score = await self._api_classify(text, "hate_speech")
                if api_score is not None:
                    score = (score + api_score) / 2
                    method = "ensemble"

            return ClassificationResult(
                label="HATE_SPEECH",
                confidence=score,
                details={"matched_keywords": self._get_matched_keywords(text, HATE_SPEECH_KEYWORDS)},
                method=method,
            )

        return ClassificationResult(label="NOT_HATE", confidence=1.0 - score, method="rule_based")

    async def detect_spam(self, text: str) -> ClassificationResult:
        keyword_score = self._keyword_score(text, SPAM_INDICATORS)
        url_bonus = min(self._url_count(text) * 0.15, 0.4)
        caps_bonus = self._caps_ratio(text) * 0.2
        score = min(keyword_score + url_bonus + caps_bonus, 1.0)

        if score >= self._spam_threshold:
            return ClassificationResult(
                label="SPAM",
                confidence=score,
                details={
                    "url_count": self._url_count(text),
                    "caps_ratio": round(self._caps_ratio(text), 3),
                    "matched_keywords": self._get_matched_keywords(text, SPAM_INDICATORS),
                },
                method="rule_based",
            )

        return ClassificationResult(label="NOT_SPAM", confidence=1.0 - score, method="rule_based")

    async def _api_classify(self, text: str, category: str) -> float | None:
        if not self._api_fallback_url:
            return None
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self._api_fallback_url}/classify",
                    json={"text": text, "category": category},
                )
                if response.status_code == 200:
                    data = response.json()
                    return float(data.get("score", 0))
        except Exception as exc:
            logger.warning("API classification failed for %s: %s", category, exc)
        return None

    def _get_matched_keywords(self, text: str, keywords: list[str]) -> list[str]:
        normalized = self._normalize_text(text)
        return [kw for kw in keywords if kw in normalized]
