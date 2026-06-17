"""CLI entry point. Uses Typer + Rich for a nice terminal experience."""

from __future__ import annotations

import json
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from pantheon.core.pantheon import Pantheon

app = typer.Typer(
    name="pantheon",
    help="🏛️ Pantheon — multi-AI-role collaboration framework.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        from pantheon import __version__

        console.print(f"[bold cyan]pantheon[/bold cyan] {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """🏛️ Pantheon — multi-AI-role collaboration framework."""
    pass


@app.command("ask")
def ask(
    task: str = typer.Argument(..., help="The task to send to the Pantheon."),
    role: Optional[str] = typer.Option(
        None,
        "--role",
        "-r",
        help="Force a specific role (hephaestus, athena, apollo, chronos).",
    ),
    multi: bool = typer.Option(
        False,
        "--multi",
        "-m",
        help="Force multi-role collaboration mode.",
    ),
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to pantheon.yaml."
    ),
    raw: bool = typer.Option(False, "--raw", help="Output raw JSON instead of formatted text."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging."),
) -> None:
    """Ask the Pantheon to do something."""
    try:
        p = Pantheon(config_path=config, verbose=verbose)
    except FileNotFoundError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(code=1)

    mode = "auto"
    if role:
        mode = f"role:{role}"
    elif multi:
        mode = "multi"

    if not raw:
        console.print(f"\n[dim]Mode:[/dim] [cyan]{mode}[/cyan]")
        console.print(f"[dim]Task:[/dim] {task}\n")

    try:
        result = p.ask(task, mode=mode)
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(code=1)

    if raw:
        typer.echo(json.dumps(result, indent=2, default=str))
        return

    # Pretty output
    if result.get("plan"):
        console.print(Panel(str(result["plan"]), title="[dim]Plan[/dim]", border_style="dim"))

    if result.get("steps"):
        console.print(f"[bold]Steps ({len(result['steps'])}):[/bold]")
        for i, step in enumerate(result["steps"], 1):
            role_name = step.get("role", "?")
            status = "✓" if step.get("success", True) else "✗"
            color = "green" if step.get("success", True) else "red"
            console.print(f"  [{color}]{status}[/{color}] [cyan]{role_name}[/cyan]: {step.get('content', '')[:120]}...")
        console.print()

    console.print(Panel(
        Markdown(result.get("content", "(no content)")),
        title="[bold green]Answer[/bold green]",
        border_style="green",
    ))


@app.command("roles")
def list_roles(
    config: Optional[str] = typer.Option(None, "--config", "-c"),
) -> None:
    """List all enabled roles."""
    try:
        p = Pantheon(config_path=config)
    except FileNotFoundError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(code=1)

    console.print("\n[bold]Enabled roles:[/bold]\n")
    for name in p.list_roles():
        role = p.get_role(name)
        desc = getattr(role, "description", "")
        model = getattr(role, "model", "?")
        console.print(f"  [cyan]●[/cyan] [bold]{name}[/bold]  [dim](model: {model})[/dim]")
        console.print(f"      {desc}")
    console.print()


@app.command("web")
def web(
    host: str = typer.Option("127.0.0.1", "--host", "-h"),
    port: int = typer.Option(8000, "--port", "-p"),
    reload: bool = typer.Option(False, "--reload"),
    config: Optional[str] = typer.Option(None, "--config", "-c"),
) -> None:
    """Launch the Web UI."""
    try:
        import uvicorn
    except ImportError:
        console.print("[red]✗ uvicorn not installed. pip install uvicorn[/red]")
        raise typer.Exit(code=1)

    # Lazy import to avoid pulling fastapi/uvicorn when only using CLI
    from pantheon.web import create_app

    app_instance = create_app(config_path=config)
    console.print(f"\n[bold green]🏛️ Pantheon Web UI[/bold green]")
    console.print(f"   [cyan]http://{host}:{port}[/cyan]\n")

    uvicorn.run(app_instance, host=host, port=port, reload=reload, log_level="info")


def cli_entry() -> None:
    """Entry point for the console script."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/dim]")
        sys.exit(130)


if __name__ == "__main__":
    cli_entry()
