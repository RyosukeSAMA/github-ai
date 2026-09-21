"""CLI entry point. Uses Typer + Rich for a nice terminal experience."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import typer
from rich import box
from rich.align import Align
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.status import Status
from rich.table import Table
from rich.text import Text

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

BRAND_COLOR = "#1677c8"
ACCENT_COLOR = "#7047c8"
MUTED_COLOR = "grey42"
ROLE_COLORS = {
    "hephaestus": "#c93c37",
    "athena": "#376ac3",
    "apollo": "#a13bb2",
    "chronos": "#238636",
    "hermes": BRAND_COLOR,
}


def _temple_mark() -> Text:
    """Return a fixed-grid Pantheon temple that stays aligned in terminals."""
    lines = (
        "/\\",
        "/  \\",
        "/____\\",
        "___/______\\___",
        "|==============|",
        "|| |  |  |  | ||",
        "|| |  |  |  | ||",
        "__||_|__|__|__|_||__",
    )
    mark = Text()
    for index, line in enumerate(lines):
        mark.append(
            line.center(20),
            style=f"bold {ACCENT_COLOR if index < 4 else BRAND_COLOR}",
        )
        if index < len(lines) - 1:
            mark.append("\n")
    return mark


def _brand_header(
    section: str,
    subtitle: str,
    metadata: list[str] | None = None,
    *,
    hero: bool = False,
) -> Panel:
    """Build the shared adaptive header used by human-facing CLI commands."""
    from pantheon import __version__

    wide_hero = hero and console.width >= 96
    side_by_side_hero = hero and console.width >= 68
    heading = Text("" if hero else "🏛  ", style=f"bold {BRAND_COLOR}")
    heading.append("PANTHEON", style=f"bold {BRAND_COLOR}")
    heading.append(f"  {section.upper()}", style="bold")

    grid = Table.grid(expand=True)
    grid.add_column(ratio=1)
    if wide_hero or not hero:
        grid.add_column(justify="right", no_wrap=True)
        grid.add_row(heading, Text(f"v{__version__}", style=MUTED_COLOR))
        grid.add_row(Text(subtitle), Text("HERMES · MULTI-AGENT", style=f"bold {ACCENT_COLOR}"))
        if metadata:
            grid.add_row(Text("  •  ".join(metadata), style=MUTED_COLOR), Text(""))
        if wide_hero:
            grid.add_row(Text(""), Text(""))
            grid.add_row(
                Text("ROUTE  →  EXECUTE  →  SYNTHESIZE", style=f"bold {ACCENT_COLOR}"),
                Text(""),
            )
            grid.add_row(
                Text("ATHENA  •  HEPHAESTUS  •  APOLLO  •  CHRONOS", style=MUTED_COLOR),
                Text(""),
            )
    else:
        heading.append(f"  v{__version__}", style=MUTED_COLOR)
        grid.add_row(heading)
        grid.add_row(Text(subtitle))
        if metadata:
            grid.add_row(Text("  •  ".join(metadata), style=MUTED_COLOR))
        grid.add_row(Text("HERMES · MULTI-AGENT", style=f"bold {ACCENT_COLOR}"))
        grid.add_row(Text("ROUTE  →  EXECUTE  →  SYNTHESIZE", style=f"bold {ACCENT_COLOR}"))

    content: object = grid
    if side_by_side_hero:
        hero_grid = Table.grid(expand=True, padding=(0, 2 if wide_hero else 1))
        hero_grid.add_column(width=20)
        hero_grid.add_column(ratio=1)
        hero_grid.add_row(_temple_mark(), grid)
        content = hero_grid
    elif hero:
        hero_stack = Table.grid(expand=True)
        hero_stack.add_column(ratio=1)
        hero_stack.add_row(Align.center(_temple_mark()))
        hero_stack.add_row(grid)
        content = hero_stack

    return Panel(
        content,
        border_style=BRAND_COLOR,
        box=box.ROUNDED,
        padding=(0, 1),
    )


def _workspace_name() -> str:
    workspace = Path(os.environ.get("PANTHEON_WORKSPACE", Path.cwd())).resolve()
    return workspace.name or str(workspace)


def _hermes_model(pantheon: Pantheon) -> str:
    return str(getattr(pantheon.router, "hermes_model", None) or "not configured")


def _duration_label(milliseconds: int | float) -> str:
    if milliseconds < 1000:
        return f"{int(milliseconds)} ms"
    return f"{milliseconds / 1000:.1f} s"


def _compact_summary(value: object, limit: int = 86) -> str:
    text = " ".join(str(value or "").split())
    first_sentence = text.split(". ", 1)[0]
    if first_sentence and first_sentence != text:
        first_sentence += "."
    text = first_sentence or text
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _configure_cli_logging(verbose: bool) -> None:
    """Keep dependency request logs out of the live CLI unless debugging."""
    if verbose:
        return
    for logger_name in ("httpx", "httpcore", "openai", "anthropic"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def _task_panel(task: str, mode: str, skill: str | None) -> Panel:
    details = Table.grid(padding=(0, 1))
    details.add_column(style=MUTED_COLOR, width=8, no_wrap=True)
    details.add_column(ratio=1)
    details.add_row("MODE", Text(mode, style=f"bold {BRAND_COLOR}"))
    if skill:
        details.add_row("SKILL", Text(f"${skill.lstrip('$')}", style=f"bold {ACCENT_COLOR}"))
    details.add_row("TASK", Text(task, overflow="fold"))
    return Panel(details, title="[bold]Session[/bold]", border_style="grey37", box=box.ROUNDED)


def _steps_table(steps: list[object]) -> Table:
    table = Table(
        box=box.ROUNDED,
        border_style="grey37",
        header_style="bold",
        expand=True,
        title="Execution",
        title_style="bold",
    )
    table.add_column("#", justify="right", width=3, style=MUTED_COLOR)
    table.add_column("", width=2, justify="center")
    table.add_column("AGENT", width=13, no_wrap=True)
    table.add_column("RESULT", ratio=1, overflow="fold")
    table.add_column("TIME", justify="right", width=9, no_wrap=True)

    for index, step in enumerate(steps, 1):
        role_name = str(getattr(step, "role", "?"))
        success = bool(getattr(step, "success", True))
        content = str(getattr(step, "content", "") or "").replace("\n", " ").strip()
        preview = content[:180] + ("…" if len(content) > 180 else "")
        duration = int(getattr(step, "duration_ms", 0) or 0)
        color = "green" if success else "red"
        table.add_row(
            str(index),
            Text("✓" if success else "✕", style=f"bold {color}"),
            Text(role_name.title(), style=f"bold {ROLE_COLORS.get(role_name, BRAND_COLOR)}"),
            Text(preview or "No output", style=None if success else "red"),
            Text(_duration_label(duration), style=MUTED_COLOR),
        )
    return table


def _timeline_line(
    marker: str,
    role: str,
    message: str,
    detail: str = "",
    *,
    marker_style: str = BRAND_COLOR,
) -> Text:
    role_key = role.lower()
    line = Text("  ")
    line.append(marker, style=f"bold {marker_style}")
    line.append(f"  {role.upper():<12}", style=f"bold {ROLE_COLORS.get(role_key, BRAND_COLOR)}")
    line.append(message)
    if detail:
        line.append(f"  ·  {detail}", style=MUTED_COLOR)
    return line


def _run_event_handler(status: Status) -> Callable[[str, dict[str, Any]], None]:
    """Translate Hermes runtime events into a compact multi-agent activity feed."""

    def handle(event: str, payload: dict[str, Any]) -> None:
        role = str(payload.get("role") or "hermes")
        if event == "plan_start":
            status.update(f"[{BRAND_COLOR}]Hermes is choosing the council…[/]")
            return

        if event == "plan_ready":
            steps = list(payload.get("steps") or [])
            message = "route selected" if len(steps) == 1 else f"council formed with {len(steps)} steps"
            console.print(_timeline_line("◇", "hermes", message))
            return

        if event == "step_start":
            index = int(payload.get("index", 0)) + 1
            total = int(payload.get("total", 1))
            message = str(payload.get("description") or payload.get("task") or "working")
            status.update(
                f"[{ROLE_COLORS.get(role.lower(), BRAND_COLOR)}]"
                f"{role.title()} is working…[/]"
            )
            console.print(_timeline_line("○", role, message, f"{index}/{total}"))
            return

        if event in {"step_done", "step_error"}:
            duration = _duration_label(int(payload.get("duration_ms", 0) or 0))
            success = event == "step_done" and bool(payload.get("success", True))
            console.print(
                _timeline_line(
                    "✓" if success else "✕",
                    role,
                    "completed" if success else "failed",
                    duration,
                    marker_style="green" if success else "red",
                )
            )
            return

        if event == "agent_message":
            sender = str(payload.get("from_role") or role)
            recipient = str(payload.get("to_role") or "hermes")
            summary = str(payload.get("summary") or "handoff")
            if len(summary) > 100:
                summary = summary[:99] + "…"
            console.print(_timeline_line("↳", sender, summary, f"to {recipient}"))
            return

        if event == "summary_start":
            status.update(f"[{BRAND_COLOR}]Hermes is synthesizing the council…[/]")
            console.print(_timeline_line("◇", "hermes", "synthesizing the final answer"))

    return handle


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
    _configure_cli_logging(verbose)
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
        console.print()
        console.print(
            _brand_header(
                "COUNCIL",
                "Hermes routes the task; specialist agents execute",
                [f"model {_hermes_model(p)}", f"cwd {_workspace_name()}"],
                hero=True,
            )
        )
        console.print(_task_panel(task, mode, skill))

    started_at = time.perf_counter()
    try:
        if raw:
            result = p.ask(task, mode=mode, skill=skill)
        else:
            with console.status(
                f"[{BRAND_COLOR}]Hermes is opening the council…[/]",
                spinner="dots",
            ) as run_status:
                result = p.ask(
                    task,
                    mode=mode,
                    skill=skill,
                    on_event=_run_event_handler(run_status),
                )
    except Exception as e:
        console.print(
            Panel(
                Text(str(e), style="red"),
                title="[bold red]Run failed[/bold red]",
                border_style="red",
                box=box.ROUNDED,
            )
        )
        if verbose:
            console.print_exception()
        raise typer.Exit(code=1)

    if raw:
        typer.echo(json.dumps(result, indent=2, default=str))
        return

    if result.get("plan"):
        console.print(
            Panel(
                Text(str(result["plan"])),
                title=f"[bold {ACCENT_COLOR}]Hermes plan[/]",
                border_style=ACCENT_COLOR,
                box=box.ROUNDED,
            )
        )

    steps = list(result.get("steps") or [])
    if steps:
        console.print(_steps_table(steps))

    console.print(
        Panel(
            Markdown(result.get("content", "(no content)")),
            title="[bold green]Answer[/bold green]",
            border_style="green",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )
    elapsed_ms = (time.perf_counter() - started_at) * 1000
    succeeded = sum(bool(getattr(step, "success", True)) for step in steps)
    completion = Text()
    completion.append("✓ Complete", style="bold green")
    completion.append(f"  •  {succeeded}/{len(steps)} steps", style=MUTED_COLOR)
    completion.append(f"  •  {_duration_label(elapsed_ms)}", style=MUTED_COLOR)
    console.print(Panel(completion, border_style="grey37", box=box.MINIMAL, padding=(0, 1)))


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

    role_names = p.list_roles()
    console.print()
    console.print(
        _brand_header(
            "ROSTER",
            "Specialist agents available to Hermes",
            [f"{len(role_names)} agents", f"model {_hermes_model(p)}", f"cwd {_workspace_name()}"],
        )
    )

    table = Table(
        box=box.SIMPLE_HEAVY,
        border_style="grey37",
        header_style="bold",
        expand=True,
        padding=(0, 1),
    )
    table.add_column("ROLE", width=16, no_wrap=True)
    table.add_column("RUNTIME", ratio=2)
    table.add_column("SPECIALTY", ratio=3)
    table.add_column("STATUS", width=8, justify="right")

    for name in role_names:
        role = p.get_role(name)
        model = str(getattr(role, "model", "?") or "none")
        role_config = getattr(role, "config", {}) or {}
        provider = str(role_config.get("provider") or "none")
        desc = str(role_config.get("description") or getattr(role, "description", ""))
        accent = ROLE_COLORS.get(name, BRAND_COLOR)
        role_label = Text("● ", style=accent)
        role_label.append(name.title(), style=f"bold {accent}")
        runtime = Text(model, style=BRAND_COLOR if model != "none" else MUTED_COLOR)
        if provider != "none":
            runtime.append(f"\n{provider}", style=MUTED_COLOR)
        table.add_row(
            role_label,
            runtime,
            Text(desc),
            Text("enabled", style="green"),
        )
    console.print(table)
    hint = Text("Use ", style=MUTED_COLOR)
    hint.append("pantheon ask --role <name>", style=f"bold {ACCENT_COLOR}")
    hint.append(" to address one specialist directly.", style=MUTED_COLOR)
    console.print(hint)
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

    skills = p.skill_store.list()
    active_count = sum(bool(skill.get("enabled", True)) for skill in skills)
    console.print()
    console.print(
        _brand_header(
            "SKILLS",
            "Prompt extensions available to your agents",
            [f"{len(skills)} skills", f"{active_count} active", f"cwd {_workspace_name()}"],
        )
    )

    table = Table(
        box=box.SIMPLE_HEAVY,
        border_style="grey37",
        header_style="bold",
        expand=True,
        padding=(0, 1),
    )
    table.add_column("SKILL", ratio=2, min_width=16)
    table.add_column("COUNCIL", ratio=2, min_width=12)
    table.add_column("PURPOSE", ratio=4)
    table.add_column("STATUS", width=8, justify="right")

    for skill in skills:
        state = "active" if skill.get("enabled", True) else "off"
        roles = ", ".join(skill.get("roles") or ["global"])
        skill_label = Text(f"${skill['id']}", style=f"bold {ACCENT_COLOR}")
        skill_label.append(f"\n{skill.get('source', 'local')}", style=MUTED_COLOR)
        table.add_row(
            skill_label,
            Text(roles, style=BRAND_COLOR),
            Text(_compact_summary(skill.get("description", ""))),
            Text(state, style="green" if state == "active" else "yellow"),
        )
    console.print(table)
    hint = Text("Invoke with ", style=MUTED_COLOR)
    hint.append('pantheon ask --skill <id> "…"', style=f"bold {ACCENT_COLOR}")
    hint.append(".", style=MUTED_COLOR)
    console.print(hint)
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
    console.print()
    console.print(
        _brand_header(
            "WEB",
            "Browser workspace is ready",
            [f"http://{host}:{port}", f"cwd {_workspace_name()}"],
        )
    )
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
