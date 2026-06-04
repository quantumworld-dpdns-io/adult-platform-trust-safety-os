"""Audit CLI commands: query, verify chain, export, stats."""

from __future__ import annotations

import asyncio
import json

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Audit log operations")
console = Console()


@app.command("query-events")
def query_events(
    event_type: str | None = typer.Option(None, "--type", "-t", help="Event type filter"),
    actor_id: str | None = typer.Option(None, "--actor", "-a", help="Actor filter"),
    severity: str | None = typer.Option(None, "--severity", help="Severity filter"),
    limit: int = typer.Option(20, help="Max events"),
    offset: int = typer.Option(0, help="Offset for pagination"),
) -> None:
    """Query audit log events."""
    from src.api.mcp.tools.audit_tools import query_audit_log

    result = asyncio.run(query_audit_log(
        event_type=event_type,
        actor_id=actor_id,
        severity=severity,
        limit=limit,
        offset=offset,
    ))

    if not result["events"]:
        console.print("[yellow]No events found.[/yellow]")
        return

    table = Table(title=f"Audit Events ({result['total']} total)")
    table.add_column("Event ID", style="cyan")
    table.add_column("Type")
    table.add_column("Actor")
    table.add_column("Severity")
    table.add_column("Timestamp")

    for event in result["events"]:
        table.add_row(
            event["event_id"][:12] + "...",
            event["event_type"],
            event["actor_id"],
            event.get("severity", "info"),
            event["timestamp"][:19],
        )
    console.print(table)

    if result["has_more"]:
        console.print(f"[dim]Showing {offset + limit} of {result['total']} (use --offset to paginate)[/dim]")


@app.command("verify-chain")
def verify_chain() -> None:
    """Verify the integrity of the audit chain."""
    from src.api.mcp.tools.audit_tools import verify_audit_integrity

    result = asyncio.run(verify_audit_integrity())

    if result["valid"]:
        console.print(f"[green]Audit chain valid ({result['total_entries']} entries)[/green]")
    else:
        console.print(f"[red]Audit chain BROKEN ({len(result['errors'])} errors)[/red]")
        table = Table(title="Errors")
        table.add_column("Index")
        table.add_column("Event ID")
        table.add_column("Error")
        for err in result["errors"][:10]:
            table.add_row(
                str(err["index"]),
                err.get("event_id", "—")[:12] + "...",
                err["error"],
            )
        console.print(table)


@app.command("export-events")
def export_events(
    format: str = typer.Option("json", "--format", "-f", help="Export format (json/csv)"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path"),
    start_time: str | None = typer.Option(None, "--start", help="Start time ISO"),
    end_time: str | None = typer.Option(None, "--end", help="End time ISO"),
) -> None:
    """Export audit events."""
    from src.api.mcp.tools.audit_tools import export_audit_log

    result = asyncio.run(export_audit_log(
        format=format,
        start_time=start_time,
        end_time=end_time,
    ))

    if result.get("error"):
        console.print(f"[red]Error: {result['error']}[/red]")
        raise typer.Exit(1)

    if output:
        with open(output, "w") as f:
            f.write(result["data"])
        console.print(f"[green]Exported {result['record_count']} events to {output}[/green]")
        console.print(f"Export hash: {result['export_hash']}")
    else:
        console.print(result["data"][:5000])
        if len(result["data"]) > 5000:
            console.print(f"[dim]... truncated ({result['record_count']} records total)[/dim]")


@app.command()
def stats() -> None:
    """Show audit log statistics."""
    from src.api.mcp.tools.audit_tools import _audit_log, _chain_hashes

    total = len(_audit_log)
    if total == 0:
        console.print("[yellow]Audit log is empty.[/yellow]")
        return

    type_counts: dict[str, int] = {}
    severity_counts: dict[str, int] = {}
    for entry in _audit_log:
        etype = entry.get("event_type", "unknown")
        type_counts[etype] = type_counts.get(etype, 0) + 1
        sev = entry.get("severity", "info")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    table = Table(title="Audit Log Stats")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Total Events", str(total))
    table.add_row("Chain Length", str(len(_chain_hashes)))
    for etype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        table.add_row(f"  {etype}", str(count))
    for sev, count in sorted(severity_counts.items(), key=lambda x: -x[1]):
        table.add_row(f"  severity:{sev}", str(count))
    console.print(table)
