"""Translation service: translation lookup, loading, and missing key detection."""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_translations: dict[str, dict[str, str]] = {
    "en": {
        "app.name": "Trust & Safety Platform",
        "app.description": "Adult platform trust and safety operating system",
        "auth.login": "Login",
        "auth.logout": "Logout",
        "auth.register": "Register",
        "moderation.approve": "Approve",
        "moderation.reject": "Reject",
        "moderation.escalate": "Escalate",
        "moderation.pending": "Pending Review",
        "moderation.approved": "Approved",
        "moderation.rejected": "Rejected",
        "audit.export": "Export Audit Log",
        "audit.verify": "Verify Chain Integrity",
        "compliance.gdpr.export": "Export My Data",
        "compliance.gdpr.delete": "Delete My Data",
        "compliance.coppa.parental_consent": "Parental Consent Required",
        "error.not_found": "Resource not found",
        "error.unauthorized": "Authentication required",
        "error.forbidden": "Access denied",
        "error.validation": "Invalid input",
        "error.server": "Internal server error",
        "content.scan": "Scan Content",
        "content.classify": "Classify Content",
        "content.status": "Content Status",
        "notification.content_reviewed": "Your content has been reviewed",
        "notification.account_suspended": "Your account has been suspended",
    },
    "es": {
        "app.name": "Plataforma de Confianza y Seguridad",
        "app.description": "Sistema operativo de confianza y seguridad para plataformas para adultos",
        "auth.login": "Iniciar sesion",
        "auth.logout": "Cerrar sesion",
        "auth.register": "Registrar",
        "moderation.approve": "Aprobar",
        "moderation.reject": "Rechazar",
        "moderation.escalate": "Escalar",
        "error.not_found": "Recurso no encontrado",
        "error.unauthorized": "Autenticacion requerida",
        "error.forbidden": "Acceso denegado",
    },
    "fr": {
        "app.name": "Plateforme Confiance et Securite",
        "app.description": "Systeme d'exploitation confiance et securite pour plateformes adultes",
        "auth.login": "Connexion",
        "auth.logout": "Deconnexion",
        "auth.register": "S'inscrire",
        "moderation.approve": "Approuver",
        "moderation.reject": "Rejeter",
        "moderation.escalate": "Escalader",
        "error.not_found": "Ressource non trouvee",
        "error.unauthorized": "Authentification requise",
        "error.forbidden": "Acces refuse",
    },
    "de": {
        "app.name": "Vertrauens- und Sicherheitsplattform",
        "app.description": "Vertrauens- und Sicherheits-Betriebssystem fur Erwachsenenplattformen",
        "auth.login": "Anmelden",
        "auth.logout": "Abmelden",
        "auth.register": "Registrieren",
        "moderation.approve": "Genehmigen",
        "moderation.reject": "Ablehnen",
        "moderation.escalate": "Eskalieren",
    },
    "ja": {
        "app.name": "信頼と安全のプラットフォーム",
        "auth.login": "ログイン",
        "auth.logout": "ログアウト",
        "auth.register": "登録",
        "moderation.approve": "承認",
        "moderation.reject": "却下",
        "moderation.escalate": "エスカレーション",
    },
    "zh": {
        "app.name": "信任与安全平台",
        "auth.login": "登录",
        "auth.logout": "退出",
        "auth.register": "注册",
        "moderation.approve": "批准",
        "moderation.reject": "拒绝",
        "moderation.escalate": "升级",
    },
}


class TranslationService:
    def __init__(self, default_locale: str = "en") -> None:
        self._translations = _translations
        self._default_locale = default_locale
        self._loaded_locales: set[str] = set(self._translations.keys())

    def translate(
        self,
        key: str,
        locale: str | None = None,
        fallback: bool = True,
    ) -> str:
        loc = locale or self._default_locale

        if loc in self._translations and key in self._translations[loc]:
            return self._translations[loc][key]

        if fallback and loc != self._default_locale:
            if self._default_locale in self._translations:
                default_val = self._translations[self._default_locale].get(key)
                if default_val is not None:
                    return default_val

        return key

    def get_translation(
        self,
        key: str,
        locale: str | None = None,
    ) -> dict[str, Any]:
        loc = locale or self._default_locale
        value = self.translate(key, locale=loc, fallback=False)
        has_translation = value != key

        return {
            "key": key,
            "locale": loc,
            "value": value if has_translation else None,
            "has_translation": has_translation,
            "fallback_used": not has_translation and loc != self._default_locale,
        }

    def load_translations(
        self,
        locale: str,
        translations: dict[str, str],
    ) -> dict[str, Any]:
        if locale not in self._translations:
            self._translations[locale] = {}

        loaded = 0
        updated = 0
        for key, value in translations.items():
            if key in self._translations[locale]:
                updated += 1
            else:
                loaded += 1
            self._translations[locale][key] = value

        self._loaded_locales.add(locale)

        return {
            "locale": locale,
            "loaded": loaded,
            "updated": updated,
            "total": loaded + updated,
        }

    def get_missing_keys(
        self,
        locale: str,
        base_locale: str | None = None,
    ) -> dict[str, Any]:
        base = base_locale or self._default_locale
        base_keys = set(self._translations.get(base, {}).keys())
        locale_keys = set(self._translations.get(locale, {}).keys())

        missing = base_keys - locale_keys
        extra = locale_keys - base_keys

        return {
            "locale": locale,
            "base_locale": base,
            "missing_keys": sorted(missing),
            "extra_keys": sorted(extra),
            "missing_count": len(missing),
            "extra_count": len(extra),
            "coverage": round(len(locale_keys & base_keys) / max(len(base_keys), 1) * 100, 1),
        }

    def get_available_locales(self) -> list[str]:
        return sorted(self._translations.keys())

    def get_all_keys(self, locale: str) -> dict[str, str]:
        return dict(self._translations.get(locale, {}))
