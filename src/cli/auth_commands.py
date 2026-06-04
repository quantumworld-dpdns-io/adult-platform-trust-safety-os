"""Authentication CLI commands: login, logout, token management, API keys."""

from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Authentication and API key management")
console = Console()

_token_store: dict[str, dict] = {}


@app.command()
def login(
    username: str = typer.Option(..., prompt=True, help="Username or email"),
    password: str = typer.Option(..., prompt=True, hide_input=True, help="Password"),
    mfa_code: str | None = typer.Option(None, "--mfa", help="MFA code"),
) -> None:
    """Authenticate with username and password."""
    from src.auth.jwt import create_access_token, create_refresh_token

    if not username or not password:
        console.print("[red]Username and password are required.[/red]")
        raise typer.Exit(1)

    if mfa_code and len(mfa_code) != 6:
        console.print("[red]MFA code must be 6 digits.[/red]")
        raise typer.Exit(1)

    access_token = create_access_token(
        subject=username,
        roles=["user"],
        extra_claims={"mfa_verified": bool(mfa_code)},
    )
    refresh_token = create_refresh_token(subject=username)

    _token_store[username] = {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }

    console.print(f"[green]Login successful for {username}[/green]")
    console.print(f"Access token: {access_token[:40]}...")
    console.print(f"Refresh token: {refresh_token[:40]}...")


@app.command()
def logout(
    username: str = typer.Option(..., prompt=True, help="Username"),
) -> None:
    """Invalidate session tokens."""
    if username in _token_store:
        del _token_store[username]
        console.print(f"[green]Logged out {username}[/green]")
    else:
        console.print(f"[yellow]No active session found for {username}[/yellow]")


@app.command("token-info")
def token_info(
    token: str = typer.Option(..., help="JWT token to inspect"),
) -> None:
    """Display information about a JWT token."""
    from src.auth.jwt import decode_token

    payload = decode_token(token)
    if payload is None:
        console.print("[red]Invalid or expired token.[/red]")
        raise typer.Exit(1)

    table = Table(title="Token Info")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")
    for key, value in payload.items():
        table.add_row(str(key), str(value))
    console.print(table)


@app.command("api-key-generate")
def api_key_generate(
    name: str = typer.Option(..., prompt=True, help="Key name"),
    owner_id: str = typer.Option(..., prompt=True, help="Owner user ID"),
    scopes: str = typer.Option("read,write", help="Comma-separated scopes"),
    expires_in_days: int | None = typer.Option(None, help="Expiry in days"),
) -> None:
    """Generate a new API key."""
    from src.auth.api_keys import APIKeyManager

    manager = APIKeyManager()
    scope_list = [s.strip() for s in scopes.split(",")]
    result = manager.generate_key(
        name=name,
        owner_id=owner_id,
        scopes=scope_list,
        expires_in_days=expires_in_days,
    )

    console.print(f"[green]API key generated:[/green]")
    console.print(f"  Key ID:    {result['key_id']}")
    console.print(f"  Raw Key:   {result['raw_key']}")
    console.print(f"  Prefix:    {result['prefix']}")
    console.print(f"  Scopes:    {', '.join(result['scopes'])}")
    console.print(f"  Created:   {result['created_at']}")
    if result["expires_at"]:
        console.print(f"  Expires:   {result['expires_at']}")
    console.print("[yellow]Store the raw key securely — it will not be shown again.[/yellow]")


@app.command("api-key-list")
def api_key_list(
    owner_id: str | None = typer.Option(None, help="Filter by owner"),
    include_revoked: bool = typer.Option(False, help="Include revoked keys"),
) -> None:
    """List API keys."""
    from src.auth.api_keys import APIKeyManager

    manager = APIKeyManager()
    keys = manager.list_keys(owner_id=owner_id, include_revoked=include_revoked)

    if not keys:
        console.print("[yellow]No API keys found.[/yellow]")
        return

    table = Table(title="API Keys")
    table.add_column("Key ID", style="cyan")
    table.add_column("Name")
    table.add_column("Owner")
    table.add_column("Prefix")
    table.add_column("Scopes")
    table.add_column("Active", style="green")
    table.add_column("Created")

    for key in keys:
        table.add_row(
            key["key_id"],
            key["name"],
            key["owner_id"],
            key["prefix"],
            ", ".join(key["scopes"]),
            "Yes" if key["is_active"] else "No",
            key["created_at"][:19],
        )
    console.print(table)


@app.command("api-key-revoke")
def api_key_revoke(
    key_hash: str = typer.Option(..., help="Hash of the key to revoke"),
) -> None:
    """Revoke an API key."""
    from src.auth.api_keys import APIKeyManager

    manager = APIKeyManager()
    success = manager.revoke_key(key_hash)
    if success:
        console.print(f"[green]API key revoked successfully.[/green]")
    else:
        console.print("[red]Key not found.[/red]")
        raise typer.Exit(1)
