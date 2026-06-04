"""Application settings loaded from environment variables."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DATABASE_")

    url: str = "postgresql+asyncpg://trust_safety:dev_password_change_me@localhost:5432/trust_safety_dev"
    echo: bool = False
    pool_size: int = 20
    max_overflow: int = 10


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REDIS_")

    url: str = "redis://localhost:6379/0"
    max_connections: int = 20
    socket_timeout: int = 5


class QdrantSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QDRANT_")

    url: str = "http://localhost:6333"
    api_key: str | None = None


class S3Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="S3_")

    endpoint: str = "http://localhost:9000"
    access_key: str = "minioadmin"
    secret_key: str = "minioadmin"
    bucket: str = "trust-safety-media"
    region: str = "us-east-1"


class OllamaSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OLLAMA_")

    base_url: str = "http://localhost:11434"
    model: str = "llama3.2"


class JWTSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JWT_")

    algorithm: str = "ES256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    private_key_path: Path | None = None
    public_key_path: Path | None = None


class OTelSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OTEL_")

    service_name: str = "adult-platform-trust-safety-os"
    exporter_otlp_endpoint: str = "http://localhost:4317"
    exporter_otlp_insecure: bool = True
    traces_sampler: str = "parentbased_traceidratio"
    traces_sampler_arg: float = 1.0


class SecuritySettings(BaseSettings):
    encryption_key: SecretStr = SecretStr("")
    vault_addr: str = ""
    vault_token: SecretStr = SecretStr("")


class AISettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AI_")

    classification_threshold: float = 0.85
    nsfw_threshold: float = 0.90
    toxicity_threshold: float = 0.80


class RateLimitSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RATE_LIMIT_")

    per_minute: int = 60
    per_hour: int = 1000


class AuditSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AUDIT_")

    log_retention_days: int = 365
    batch_size: int = 100
    flush_interval: int = 5


class QuantumSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="")

    qiskit_backend: str = "aer_simulator"
    cudaq_enabled: bool = False
    pqc_enabled: bool = True


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "adult-platform-trust-safety-os"
    app_version: str = "1.0.0-alpha.1"
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = True
    app_secret_key: str = "change-me-in-production"
    app_log_level: str = "INFO"

    server_host: str = "0.0.0.0"
    server_port: int = 8000
    server_workers: int = 4

    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    qdrant: QdrantSettings = QdrantSettings()
    s3: S3Settings = S3Settings()
    ollama: OllamaSettings = OllamaSettings()
    jwt: JWTSettings = JWTSettings()
    otel: OTelSettings = OTelSettings()
    security: SecuritySettings = SecuritySettings()
    ai: AISettings = AISettings()
    rate_limit: RateLimitSettings = RateLimitSettings()
    audit: AuditSettings = AuditSettings()
    quantum: QuantumSettings = QuantumSettings()

    webhook_secret: str = ""
    webhook_timeout: int = 30

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_from: str = "noreply@trust-safety.example.com"

    gdpr_data_retention_days: int = 30
    ccpa_opt_out_enabled: bool = True
    coppa_age_threshold: int = 13
    dsa_transparency_reporting: bool = True

    plugin_dir: str = "./plugins"
    plugin_sandbox_enabled: bool = True
    plugin_max_memory_mb: int = 256
    plugin_timeout_seconds: int = 30

    federated_round_timeout: int = 300
    federated_min_clients: int = 3
    federated_strategy: str = "fedavg"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


settings = Settings()
