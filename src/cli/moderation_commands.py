"""Moderation CLI commands: scan, classify, queue, approve, reject."""

from __future__ import annotations

import asyncio
import json

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Content moderation operations")
console = Console()


@app.command("scan-content")
def scan_content(
    text: str = typer.Option(..., "--text", "-t", help="Text content to scan"),
    submitter: str = typer.Option("cli-user", "--submitter", "-s", help="Submitter ID"),
) -> None:
    """Scan content for policy violations."""
    from src.api.mcp.tools.content_tools import scan_content as _scan

    result = asyncio.run(_scan(content_text=text, submitter_id=submitter))

    table = Table(title="Scan Results")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Content ID", result["content_id"])
    table.add_row("Status", result["status"])
    table.add_row("Needs Review", str(result["needs_review"]))
    table.add_row("Auto Action", str(result["auto_action"]))

    cls = result["classification"]
    table.add_row("Labels", ", ".join(cls["labels"]) if cls["labels"] else "None")
    table.add_row("Confidence", f"{cls['confidence']:.2f}")
    table.add_row("NSFW Score", f"{cls['nsfw_score']:.2f}")
    table.add_row("Toxicity Score", f"{cls['toxicity_score']:.2f}")
    table.add_row("Violence Score", f"{cls['violence_score']:.2f}")
    console.print(table)


@app.command()
def classify(
    text: str = typer.Option(..., "--text", "-t", help="Text to classify"),
) -> None:
    """Classify content without storing."""
    from src.moderation.classifier import ContentClassifier

    classifier = ContentClassifier()
    result = classifier.classify_text(text)

    table = Table(title="Classification")
    table.add_column("Label", style="cyan")
    table.add_column("Score", style="green")

    if result.labels:
        for label in result.labels:
            table.add_row(label, f"{result.scores.get(label, 0.0):.2f}")
    else:
        table.add_row("CLEAN", "0.00")

    table.add_row("Confidence", f"{result.confidence:.2f}")
    console.print(table)


@app.command("queue-list")
def queue_list(
    status: str | None = typer.Option(None, "--status", help="Filter by status"),
    limit: int = typer.Option(20, help="Max items to show"),
) -> None:
    """List items in the moderation queue."""
    from src.api.mcp.tools.moderation_tools import get_queue

    result = asyncio.run(get_queue(status=status, limit=limit))

    if not result["items"]:
        console.print("[yellow]Queue is empty.[/yellow]")
        return

    table = Table(title=f"Moderation Queue ({result['total']} total)")
    table.add_column("Content ID", style="cyan")
    table.add_column("Status")
    table.add_column("Type")
    table.add_column("Submitter")
    table.add_column("Needs Review")
    table.add_column("Scanned At")

    for item in result["items"]:
        table.add_row(
            item["content_id"][:12] + "...",
            item["status"],
            item.get("content_type", "TEXT"),
            item.get("submitter_id", "—"),
            str(item.get("needs_review", "—")),
            item.get("scanned_at", "—")[:19],
        )
    console.print(table)


@app.command()
def approve(
    content_id: str = typer.Option(..., help="Content ID to approve"),
    reviewer: str = typer.Option("cli-moderator", "--reviewer", "-r", help="Reviewer ID"),
    reason: str = typer.Option("Approved via CLI", "--reason", help="Reason"),
) -> None:
    """Approve content."""
    from src.api.mcp.tools.moderation_tools import approve_content

    result = asyncio.run(approve_content(content_id, reviewer, reason))

    if result.get("error"):
        console.print(f"[red]Error: {result['error']}[/red]")
        raise typer.Exit(1)

    console.print(f"[green]Content {content_id[:12]}... approved (action: {result['action_id'][:8]}...)[/green]")


@app.command()
def reject(
    content_id: str = typer.Option(..., help="Content ID to reject"),
    reviewer: str = typer.Option("cli-moderator", "--reviewer", "-r", help="Reviewer ID"),
    reason: str = typer.Option("Rejected via CLI", "--reason", help="Reason"),
    violations: str = typer.Option(None, "--violations", help="Comma-separated policy violations"),
) -> None:
    """Reject content."""
    from src.api.mcp.tools.moderation_tools import reject_content

    violation_list = [v.strip() for v in violations.split(",")] if violations else None
    result = asyncio.run(reject_content(content_id, reviewer, reason, violation_list))

    if result.get("error"):
        console.print(f"[red]Error: {result['error']}[/red]")
        raise typer.Exit(1)

    console.print(f"[red]Content {content_id[:12]}... rejected (action: {result['action_id'][:8]}...)[/red]")
