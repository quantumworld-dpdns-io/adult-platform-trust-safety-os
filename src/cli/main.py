"""CLI application with Typer for trust and safety operations."""

from __future__ import annotations

import typer

from src.cli import auth_commands, moderation_commands, audit_commands, quantum_commands, doctor

app = typer.Typer(
    name="trust-safety",
    help="Adult Platform Trust & Safety CLI",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

app.add_typer(auth_commands.app, name="auth", help="Authentication and API key management")
app.add_typer(moderation_commands.app, name="content", help="Content moderation operations")
app.add_typer(audit_commands.app, name="audit", help="Audit log queries and verification")
app.add_typer(quantum_commands.app, name="quantum", help="Quantum security operations")
app.add_typer(doctor.app, name="doctor", help="System health checks")


@app.command()
def version() -> None:
    """Show version information."""
    from src.config.settings import settings
    typer.echo(f"{settings.app_name} v{settings.app_version}")


@app.command()
def config(
    show: bool = typer.Option(False, "--show", "-s", help="Show current config"),
    set_key: str | None = typer.Option(None, "--set", help="Config key to set"),
    set_value: str | None = typer.Option(None, "--value", help="Value to set"),
) -> None:
    """View and manage configuration."""
    from src.config.settings import settings
    if show:
        typer.echo(f"App Name: {settings.app_name}")
        typer.echo(f"Environment: {settings.app_env}")
        typer.echo(f"Debug: {settings.is_development}")
        typer.echo(f"Database URL: {settings.database.url[:30]}...")
        typer.echo(f"Redis URL: {settings.redis.url}")
    elif set_key and set_value:
        typer.echo(f"Setting {set_key} = {set_value} (not persisted, use env vars)")
    else:
        typer.echo("Use --show to display config or --set and --value to update.")


if __name__ == "__main__":
    app()
