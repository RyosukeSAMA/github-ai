"""CLI entry point. Uses Typer + Rich for a nice terminal experience."""

from __future__ import annotations

import json
import sys

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
    version: bool | None = typer.Option(
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
    role: str | None = typer.Option(
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
    skill: str | None = typer.Option(
        None,
        "--skill",
        "-s",
        help="Invoke an installed skill by id.",
    ),
    config: str | None = typer.Option(
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
        if skill:
            console.print(f"[dim]Skill:[/dim] [magenta]${skill.lstrip('$')}[/magenta]")
        console.print(f"[dim]Task:[/dim] {task}\n")

    try:
        result = p.ask(task, mode=mode, skill=skill)
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
            # step is a TaskResult dataclass; access via attributes
            role_name = getattr(step, "role", "?")
            success = getattr(step, "success", True)
            content = getattr(step, "content", "") or ""
            status = "✓" if success else "✗"
            color = "green" if success else "red"
            preview = content[:120] + ("..." if len(content) > 120 else "")
            console.print(f"  [{color}]{status}[/{color}] [cyan]{role_name}[/cyan]: {preview}")
        console.print()

    console.print(Panel(
        Markdown(result.get("content", "(no content)")),
        title="[bold green]Answer[/bold green]",
        border_style="green",
    ))


@app.command("roles")
def list_roles(
    config: str | None = typer.Option(None, "--config", "-c"),
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


@app.command("skills")
def list_skills(
    config: str | None = typer.Option(None, "--config", "-c"),
) -> None:
    """List installed built-in and local skills."""
    try:
        p = Pantheon(config_path=config)
    except FileNotFoundError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(code=1)

    console.print("\n[bold]Installed skills:[/bold]\n")
    for skill in p.skill_store.list():
        state = "active" if skill.get("enabled", True) else "off"
        roles = ", ".join(skill.get("roles") or ["global"])
        console.print(
            f"  [magenta]${skill['id']}[/magenta]  "
            f"[dim]{skill.get('source', 'local')} · {state} · {roles}[/dim]"
        )
        console.print(f"      {skill.get('description', '')}")
    console.print()


@app.command("web")
def web(
    host: str = typer.Option("127.0.0.1", "--host", "-h"),
    port: int = typer.Option(8000, "--port", "-p"),
    reload: bool = typer.Option(False, "--reload"),
    config: str | None = typer.Option(None, "--config", "-c"),
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
    console.print("\n[bold green]🏛️ Pantheon Web UI[/bold green]")
    console.print(f"   [cyan]http://{host}:{port}[/cyan]\n")
    if host not in {"127.0.0.1", "localhost", "::1"}:
        console.print(
            "[bold yellow]Warning:[/bold yellow] this exposes file and terminal APIs to "
            "the network. Enable Settings -> Security and restrict network access.\n"
        )

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
