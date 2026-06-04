"""Doctor CLI: system health checks for dependencies, services, and configuration."""

from __future__ import annotations

import shutil
import sys

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="System health checks")
console = Console()


def _check_import(module_name: str) -> tuple[bool, str]:
    try:
        __import__(module_name)
        return True, "installed"
    except ImportError:
        return False, "missing"


@app.command("check-deps")
def check_deps() -> None:
    """Check Python dependency availability."""
    deps = {
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "sqlalchemy": "sqlalchemy",
        "redis": "redis",
        "pydantic": "pydantic",
        "cryptography": "cryptography",
        "typer": "typer",
        "rich": "rich",
        "structlog": "structlog",
        "httpx": "httpx",
        "blake3": "blake3",
        "jose": "jose",
        "websockets": "websockets",
        "msgpack": "msgpack",
        "orjson": "orjson",
        "jinja2": "jinja2",
    }

    table = Table(title="Dependency Check")
    table.add_column("Package", style="cyan")
    table.add_column("Status")

    all_ok = True
    for name, module in deps.items():
        ok, status = _check_import(module)
        style = "green" if ok else "red"
        table.add_row(name, f"[{style}]{status}[/{style}]")
        if not ok:
            all_ok = False

    console.print(table)
    if all_ok:
        console.print("[green]All dependencies are installed.[/green]")
    else:
        console.print("[yellow]Some dependencies are missing.[/yellow]")


@app.command("check-services")
def check_services() -> None:
    """Check connectivity to required services."""
    import asyncio

    table = Table(title="Service Check")
    table.add_column("Service", style="cyan")
    table.add_column("Status")
    table.add_column("Details")

    async def _check_db() -> tuple[bool, str]:
        try:
            from sqlalchemy.ext.asyncio import create_async_engine
            engine = create_async_engine("postgresql+asyncpg://localhost:5432/test", pool_pre_ping=True)
            async with engine.connect() as conn:
                await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            await engine.dispose()
            return True, "connected"
        except Exception as e:
            return False, str(e)[:60]

    async def _check_redis() -> tuple[bool, str]:
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url("redis://localhost:6379", socket_timeout=2)
            await r.ping()
            await r.aclose()
            return True, "connected"
        except Exception as e:
            return False, str(e)[:60]

    checks = [
        ("PostgreSQL", _check_db),
        ("Redis", _check_redis),
    ]

    for name, check_fn in checks:
        ok, detail = asyncio.run(check_fn())
        style = "green" if ok else "red"
        status = "connected" if ok else "unreachable"
        table.add_row(name, f"[{style}]{status}[/{style}]", detail)

    console.print(table)


@app.command("check-config")
def check_config() -> None:
    """Validate configuration settings."""
    from src.config.settings import settings

    table = Table(title="Configuration Check")
    table.add_column("Setting", style="cyan")
    table.add_column("Value")
    table.add_column("Status")

    checks = [
        ("app_name", settings.app_name, bool(settings.app_name)),
        ("app_env", settings.app_env, settings.app_env in ("development", "staging", "production")),
        ("database_url", settings.database.url[:30] + "...", bool(settings.database.url)),
        ("redis_url", settings.redis.url, bool(settings.redis.url)),
        ("jwt_algorithm", settings.jwt.algorithm, settings.jwt.algorithm in ("RS256", "ES256")),
        ("jwt_private_key", str(settings.jwt.private_key_path)[:20] if settings.jwt.private_key_path else "None", True),
        ("jwt_public_key", str(settings.jwt.public_key_path)[:20] if settings.jwt.public_key_path else "None", True),
    ]

    all_ok = True
    for name, value, ok in checks:
        style = "green" if ok else "red"
        table.add_row(name, str(value)[:40], f"[{style}]{'ok' if ok else 'issue'}[/{style}]")
        if not ok:
            all_ok = False

    console.print(table)
    if all_ok:
        console.print("[green]Configuration looks good.[/green]")
    else:
        console.print("[yellow]Some configuration issues found.[/yellow]")


@app.command("full-check")
def full_check() -> None:
    """Run all health checks."""
    console.print("[bold]Running full system check...[/bold]")
    console.print()
    check_deps()
    console.print()
    check_services()
    console.print()
    check_config()
    console.print()
    console.print("[bold green]Full check complete.[/bold green]")
