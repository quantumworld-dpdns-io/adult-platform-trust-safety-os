"""Locale management: detection, configuration, and supported locale handling."""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger(__name__)

SUPPORTED_LOCALES: dict[str, dict[str, Any]] = {
    "en": {"name": "English", "region": "US", "rtl": False, "fallback": None},
    "es": {"name": "Spanish", "region": "ES", "rtl": False, "fallback": "en"},
    "fr": {"name": "French", "region": "FR", "rtl": False, "fallback": "en"},
    "de": {"name": "German", "region": "DE", "rtl": False, "fallback": "en"},
    "pt": {"name": "Portuguese", "region": "BR", "rtl": False, "fallback": "en"},
    "ja": {"name": "Japanese", "region": "JP", "rtl": False, "fallback": "en"},
    "ko": {"name": "Korean", "region": "KR", "rtl": False, "fallback": "en"},
    "zh": {"name": "Chinese", "region": "CN", "rtl": False, "fallback": "en"},
    "ar": {"name": "Arabic", "region": "SA", "rtl": True, "fallback": "en"},
    "he": {"name": "Hebrew", "region": "IL", "rtl": True, "fallback": "en"},
    "ru": {"name": "Russian", "region": "RU", "rtl": False, "fallback": "en"},
    "hi": {"name": "Hindi", "region": "IN", "rtl": False, "fallback": "en"},
    "it": {"name": "Italian", "region": "IT", "rtl": False, "fallback": "en"},
    "nl": {"name": "Dutch", "region": "NL", "rtl": False, "fallback": "en"},
    "pl": {"name": "Polish", "region": "PL", "rtl": False, "fallback": "en"},
    "tr": {"name": "Turkish", "region": "TR", "rtl": False, "fallback": "en"},
    "th": {"name": "Thai", "region": "TH", "rtl": False, "fallback": "en"},
    "vi": {"name": "Vietnamese", "region": "VN", "rtl": False, "fallback": "en"},
}

_current_locale: str = "en"


class LocaleManager:
    def __init__(self) -> None:
        self._supported = SUPPORTED_LOCALES.copy()
        self._current = _current_locale
        self._overrides: dict[str, str] = {}

    def detect_locale(self, accept_language: str | None = None) -> str:
        if accept_language:
            languages = [lang.strip().split(";")[0].split("-")[0].lower() for lang in accept_language.split(",")]
            for lang in languages:
                base = lang.split("-")[0].lower()
                if base in self._supported:
                    return base

        return self._current

    def get_supported_locales(self) -> list[dict[str, Any]]:
        locales = []
        for code, config in self._supported.items():
            locales.append({
                "code": code,
                "name": config["name"],
                "region": config["region"],
                "rtl": config["rtl"],
                "has_fallback": config["fallback"] is not None,
            })
        return locales

    def set_locale(self, locale_code: str) -> bool:
        if locale_code not in self._supported:
            logger.warning("unsupported_locale", locale=locale_code)
            return False
        self._current = locale_code
        _current_locale = locale_code
        logger.info("locale_changed", locale=locale_code)
        return True

    def get_locale_config(self, locale_code: str | None = None) -> dict[str, Any]:
        code = locale_code or self._current
        config = self._supported.get(code)
        if config is None:
            fallback = self._supported.get(self._current)
            return {
                "code": code,
                "resolved": False,
                "fallback": self._current,
                "fallback_config": fallback,
            }

        return {
            "code": code,
            "resolved": True,
            "name": config["name"],
            "region": config["region"],
            "rtl": config["rtl"],
            "fallback": config["fallback"],
        }

    def get_rtl(self, locale_code: str | None = None) -> bool:
        config = self.get_locale_config(locale_code)
        return config.get("rtl", False)

    def get_fallback_chain(self, locale_code: str) -> list[str]:
        chain: list[str] = [locale_code]
        current = locale_code
        seen = {current}
        while True:
            config = self._supported.get(current)
            if config is None or config["fallback"] is None:
                break
            fallback = config["fallback"]
            if fallback in seen:
                break
            chain.append(fallback)
            seen.add(fallback)
            current = fallback
        return chain
