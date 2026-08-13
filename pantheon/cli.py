"""CLI entry point. Uses Typer + Rich for a nice terminal experience."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

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
service_app = typer.Typer(
    name="service",
    help="Install and manage Pantheon Web as a per-user background service.",
    no_args_is_help=True,
)
app.add_typer(service_app, name="service")


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


def _service_failure(error: Exception) -> None:
    console.print(f"[red]Service error:[/red] {error}")
    raise typer.Exit(code=1)


@service_app.command("install")
def service_install(
    workspace: Path = typer.Option(
        Path.cwd(),
        "--workspace",
        "-w",
        help="Workspace Pantheon should use. Defaults to the current directory.",
    ),
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port", "-p"),
    config: Path | None = typer.Option(None, "--config", "-c"),
    allow_network: bool = typer.Option(
        False,
        "--allow-network",
        help="Allow a non-loopback host after securing the Web UI.",
    ),
    no_start: bool = typer.Option(False, "--no-start", help="Install without starting."),
) -> None:
    """Install Pantheon Web so it starts automatically after login."""
    from pantheon.service import ServiceError, install_service

    try:
        paths = install_service(
            workspace,
            host=host,
            port=port,
            config=config,
            allow_network=allow_network,
            start=not no_start,
        )
    except ServiceError as error:
        _service_failure(error)
    console.print("[green]Pantheon service installed.[/green]")
    console.print(f"Definition: [dim]{paths.definition}[/dim]")
    console.print(f"Logs: [dim]{paths.stdout_log.parent}[/dim]")
    if not no_start:
        console.print(f"Open [cyan]http://{host}:{port}/[/cyan]")


@service_app.command("status")
def service_show_status(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port", "-p"),
) -> None:
    """Show installation, process, and HTTP health status."""
    from pantheon.service import ServiceError, service_status

    try:
        status = service_status(host=host, port=port)
    except ServiceError as error:
        _service_failure(error)
    state = "healthy" if status.healthy else "running" if status.running else "stopped"
    color = "green" if status.healthy else "yellow" if status.running else "red"
    console.print(f"[{color}]{state}[/{color}]  {status.url}")
    console.print(
        f"Backend: {status.platform} · Installed: {'yes' if status.installed else 'no'} · "
        f"Running: {'yes' if status.running else 'no'}"
    )
    console.print(f"Definition: [dim]{status.definition}[/dim]")
    if status.detail:
        console.print(f"Detail: [dim]{status.detail}[/dim]")


@service_app.command("start")
def service_start() -> None:
    """Start an installed Pantheon service."""
    from pantheon.service import ServiceError, start_service

    try:
        start_service()
    except ServiceError as error:
        _service_failure(error)
    console.print("[green]Pantheon service started.[/green]")


@service_app.command("stop")
def service_stop() -> None:
    """Stop the installed Pantheon service."""
    from pantheon.service import ServiceError, stop_service

    try:
        stop_service()
    except ServiceError as error:
        _service_failure(error)
    console.print("[yellow]Pantheon service stopped.[/yellow]")


@service_app.command("restart")
def service_restart() -> None:
    """Restart the installed Pantheon service."""
    from pantheon.service import ServiceError, restart_service

    try:
        restart_service()
    except ServiceError as error:
        _service_failure(error)
    console.print("[green]Pantheon service restarted.[/green]")


@service_app.command("logs")
def service_logs(
    lines: int = typer.Option(80, "--lines", "-n", min=1),
    follow: bool = typer.Option(False, "--follow", "-f"),
) -> None:
    """Print recent service logs, optionally following new output."""
    from pantheon.service import ServiceError, read_service_logs

    try:
        code = read_service_logs(lines=lines, follow=follow)
    except ServiceError as error:
        _service_failure(error)
    if code:
        raise typer.Exit(code=code)


@service_app.command("uninstall")
def service_uninstall() -> None:
    """Stop and remove the per-user Pantheon service."""
    from pantheon.service import ServiceError, uninstall_service

    try:
        removed = uninstall_service()
    except ServiceError as error:
        _service_failure(error)
    if removed:
        console.print("[green]Pantheon service uninstalled.[/green]")
    else:
        console.print("[dim]Pantheon service was not installed.[/dim]")


@app.command("provider-test")
def provider_test(
    role: str = typer.Option(
        "hermes",
        "--role",
        "-r",
        help="Saved role configuration to test.",
    ),
    config: str | None = typer.Option(None, "--config", "-c"),
    live: bool = typer.Option(
        False,
        "--live",
        help="Acknowledge that this makes a real provider request and may incur a small charge.",
    ),
) -> None:
    """Run an opt-in, minimal live request against one saved provider."""
    if not live and os.environ.get("PANTHEON_LIVE_TEST") != "1":
        console.print(
            "[yellow]Live request not sent.[/yellow] Add [bold]--live[/bold] or set "
            "PANTHEON_LIVE_TEST=1. The test may incur a small provider charge."
        )
        raise typer.Exit(code=2)

    from pantheon.diagnostics import ProviderProbeError, probe_role_provider

    try:
        result = probe_role_provider(role, config_path=config)
    except (FileNotFoundError, ProviderProbeError) as error:
        console.print(f"[red]Provider test failed:[/red] {error}")
        raise typer.Exit(code=1)
    console.print(
        f"[green]Provider connection works.[/green] "
        f"{result['role']} · {result['provider']} · {result['model']} · "
        f"{result['duration_ms']} ms"
    )


def cli_entry() -> None:
    """Entry point for the console script."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/dim]")
        sys.exit(130)


if __name__ == "__main__":
    cli_entry()
