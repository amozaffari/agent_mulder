#!/usr/bin/env python3
"""
Agent Mulder — Registry & Communication CLI

Usage:
    python mulder.py add <path> <name> --goal "..."   Register a project
    python mulder.py remove <name>                     Unregister a project
    python mulder.py list                              List all projects
    python mulder.py scan                              Read status from all projects
    python mulder.py status <name>                     Read status of one project
    python mulder.py task <name> "<task>"              Leave a task for a project agent
    python mulder.py introduce <name>                  Create .mulder/ structure in a project
    python mulder.py log <name>                        Show activity log for a project
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

# Registry lives in the agent_mulder repo itself
MULDER_DIR = Path(__file__).parent
REGISTRY_FILE = MULDER_DIR / "registry.json"

MULDER_SUBDIR = ".mulder"
STATUS_FILE = "status.md"
TASKS_FILE = "tasks.md"
LOG_FILE = "log.md"


# ── Registry helpers ──────────────────────────────────────────────────────────

def load_registry() -> dict:
    if not REGISTRY_FILE.exists():
        return {"projects": {}}
    with open(REGISTRY_FILE) as f:
        return json.load(f)


def save_registry(reg: dict):
    with open(REGISTRY_FILE, "w") as f:
        json.dump(reg, f, indent=2)


def get_project(name: str) -> dict | None:
    return load_registry()["projects"].get(name)


def ts() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


# ── File helpers ──────────────────────────────────────────────────────────────

def mulder_path(project: dict, filename: str) -> Path:
    return Path(project["path"]) / MULDER_SUBDIR / filename


def read_md(path: Path) -> str | None:
    if path.exists():
        return path.read_text().strip()
    return None


def append_log(project: dict, actor: str, message: str):
    log_path = mulder_path(project, LOG_FILE)
    entry = f"\n## {ts()} — {actor}\n{message}\n"
    with open(log_path, "a") as f:
        f.write(entry)


# ── CLI ───────────────────────────────────────────────────────────────────────

@click.group()
def cli():
    """Agent Mulder — repository monitoring and coordination."""
    pass


@cli.command()
@click.argument("path")
@click.argument("name")
@click.option("--goal", "-g", default="", help="Overall goal of this project")
def add(path, name, goal):
    """Register a new project in Mulder's registry."""
    resolved = Path(path).expanduser().resolve()

    if not resolved.exists():
        console.print(f"[red]Path does not exist:[/red] {resolved}")
        sys.exit(1)

    reg = load_registry()
    if name in reg["projects"]:
        console.print(f"[yellow]Project '{name}' already registered.[/yellow]")
        sys.exit(1)

    reg["projects"][name] = {
        "name": name,
        "path": str(resolved),
        "goal": goal,
        "registered_at": ts(),
    }
    save_registry(reg)

    console.print(Panel(
        f"[green]Registered:[/green] [bold]{name}[/bold]\n"
        f"[dim]Path:[/dim]  {resolved}\n"
        f"[dim]Goal:[/dim]  {goal or '(none set)'}",
        title="[bold green]✓ Project Added[/bold green]",
    ))
    console.print("\n[dim]Run [bold]python mulder.py introduce {name}[/bold] to create the .mulder/ structure in this project.[/dim]".format(name=name))


@cli.command()
@click.argument("name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def remove(name, yes):
    """Unregister a project and clean up its Mulder files."""
    reg = load_registry()
    if name not in reg["projects"]:
        console.print(f"[red]Project '{name}' not found.[/red]")
        sys.exit(1)

    p = reg["projects"][name]
    path = Path(p["path"])

    if not yes:
        console.print(f"[yellow]This will remove '{name}' from the registry and clean up:[/yellow]")
        console.print(f"  • {path / MULDER_SUBDIR}  (deleted)")
        console.print(f"  • .gitignore entry for .mulder/")
        console.print(f"  • Mulder snippet from CLAUDE.md")
        click.confirm("Continue?", abort=True)

    # Remove .mulder/ directory
    mulder_dir = path / MULDER_SUBDIR
    if mulder_dir.exists():
        import shutil
        shutil.rmtree(mulder_dir)
        console.print(f"  [green]Deleted[/green] {mulder_dir}")
    else:
        console.print(f"  [dim]No .mulder/ directory found[/dim]")

    # Remove .mulder/ from .gitignore
    gitignore_path = path / ".gitignore"
    if gitignore_path.exists():
        lines = gitignore_path.read_text().splitlines()
        filtered = [
            l for l in lines
            if l.strip() not in (f"{MULDER_SUBDIR}/", "# Mulder coordination files (local only)")
        ]
        # Strip trailing blank lines left behind
        while filtered and not filtered[-1].strip():
            filtered.pop()
        gitignore_path.write_text("\n".join(filtered) + "\n")
        console.print(f"  [green]Cleaned[/green] {gitignore_path}")

    # Remove Mulder snippet from CLAUDE.md
    claude_md_path = path / "CLAUDE.md"
    if claude_md_path.exists():
        content = claude_md_path.read_text()
        snippet = _claude_md_snippet(name)
        cleaned = content.replace(f"\n{snippet}", "").replace(snippet, "").strip()
        if cleaned:
            claude_md_path.write_text(cleaned + "\n")
            console.print(f"  [green]Cleaned[/green] {claude_md_path}")
        else:
            claude_md_path.unlink()
            console.print(f"  [green]Deleted[/green] {claude_md_path} (was only Mulder content)")

    # Remove from registry
    del reg["projects"][name]
    save_registry(reg)

    console.print(Panel(
        f"[green]Mulder has stopped watching[/green] [bold]{name}[/bold]\n\n"
        f"[dim]Registry entry removed, .mulder/ deleted, project files cleaned.[/dim]",
        title="[bold red]✓ Project Removed[/bold red]",
        border_style="red",
    ))


@cli.command("list")
def list_projects():
    """List all registered projects."""
    reg = load_registry()
    projects = reg["projects"]

    if not projects:
        console.print("[dim]No projects registered. Use [bold]python mulder.py add[/bold] to start.[/dim]")
        return

    table = Table(title="Mulder's Registry", show_lines=True)
    table.add_column("Name", style="bold cyan")
    table.add_column("Path", style="dim")
    table.add_column("Goal")
    table.add_column("Status", style="dim")
    table.add_column("Introduced", style="dim")

    for p in projects.values():
        path = Path(p["path"])
        introduced = "✓" if (path / MULDER_SUBDIR).exists() else "✗ (run introduce)"
        # Peek at last_updated from status file
        status_path = path / MULDER_SUBDIR / STATUS_FILE
        last_updated = ""
        if status_path.exists():
            for line in status_path.read_text().splitlines():
                if line.startswith("last_updated:"):
                    last_updated = line.replace("last_updated:", "").strip()
                    break

        table.add_row(
            p["name"],
            str(path),
            p.get("goal", "") or "[dim](none)[/dim]",
            last_updated or "[dim]—[/dim]",
            introduced,
        )

    console.print(table)


@cli.command()
def scan():
    """Read and display status from all registered projects."""
    reg = load_registry()
    projects = reg["projects"]

    if not projects:
        console.print("[dim]No projects registered.[/dim]")
        return

    for p in projects.values():
        _print_project_status(p)


@cli.command()
@click.argument("name")
def status(name):
    """Read and display status of a single project."""
    p = get_project(name)
    if not p:
        console.print(f"[red]Project '{name}' not found.[/red]")
        sys.exit(1)
    _print_project_status(p)


def _print_project_status(project: dict):
    name = project["name"]
    path = Path(project["path"])
    goal = project.get("goal", "")

    # Read available files
    claude_md = read_md(path / "CLAUDE.md")
    status_md = read_md(path / MULDER_SUBDIR / STATUS_FILE)
    tasks_md = read_md(path / MULDER_SUBDIR / TASKS_FILE)

    sections = []

    if goal:
        sections.append(f"**Goal:** {goal}")

    if status_md:
        sections.append(status_md)
    else:
        sections.append("_No status file found. Run `python mulder.py introduce {name}` to set up._".format(name=name))

    if tasks_md:
        sections.append("---\n" + tasks_md)

    content = "\n\n".join(sections)

    console.print(Panel(
        Markdown(content),
        title=f"[bold cyan]{name}[/bold cyan]  [dim]{path}[/dim]",
        border_style="cyan",
    ))


@cli.command()
@click.argument("name")
@click.argument("task")
def task(name, task):
    """Leave a task for a project agent (writes to .mulder/tasks.md)."""
    p = get_project(name)
    if not p:
        console.print(f"[red]Project '{name}' not found.[/red]")
        sys.exit(1)

    tasks_path = mulder_path(p, TASKS_FILE)
    if not tasks_path.parent.exists():
        console.print(f"[red]Project '{name}' has no .mulder/ directory. Run [bold]introduce[/bold] first.[/red]")
        sys.exit(1)

    # Read existing tasks
    existing = read_md(tasks_path) or ""

    # Parse out sections or just append
    new_task_line = f"- [ ] {task}"

    if "## Pending" in existing:
        # Insert after the ## Pending header
        lines = existing.splitlines()
        new_lines = []
        inserted = False
        for line in lines:
            new_lines.append(line)
            if line.strip() == "## Pending" and not inserted:
                new_lines.append(new_task_line)
                inserted = True
        content = "\n".join(new_lines)
    elif existing:
        content = existing + "\n" + new_task_line
    else:
        content = _tasks_template()
        content = content.replace("<!-- tasks will appear here -->", new_task_line)

    content = _update_last_updated(content)
    tasks_path.write_text(content)

    # Append to log
    append_log(p, "Mulder", f"Left task: {task}")

    console.print(Panel(
        f"[green]Task written to[/green] [bold]{name}[/bold]\n\n"
        f"[dim]{tasks_path}[/dim]\n\n"
        f"[yellow]→[/yellow] {task}",
        title="[bold green]✓ Task Queued[/bold green]",
    ))


@cli.command()
@click.argument("name")
def introduce(name):
    """Create the .mulder/ structure inside a registered project."""
    p = get_project(name)
    if not p:
        console.print(f"[red]Project '{name}' not found.[/red]")
        sys.exit(1)

    path = Path(p["path"])
    mulder_dir = path / MULDER_SUBDIR
    mulder_dir.mkdir(exist_ok=True)

    # Create status.md if missing
    status_path = mulder_dir / STATUS_FILE
    if not status_path.exists():
        status_path.write_text(_status_template(name))
        console.print(f"  [green]Created[/green] {status_path}")

    # Create tasks.md if missing
    tasks_path = mulder_dir / TASKS_FILE
    if not tasks_path.exists():
        tasks_path.write_text(_tasks_template())
        console.print(f"  [green]Created[/green] {tasks_path}")

    # Create log.md if missing
    log_path = mulder_dir / LOG_FILE
    if not log_path.exists():
        log_path.write_text(f"# Mulder Activity Log — {name}\n\n")
        console.print(f"  [green]Created[/green] {log_path}")

    # Create .mulder/README.md explaining the protocol
    readme_path = mulder_dir / "README.md"
    if not readme_path.exists():
        readme_path.write_text(_mulder_readme(name))
        console.print(f"  [green]Created[/green] {readme_path}")

    # Add .mulder/ to the project's .gitignore
    gitignore_path = path / ".gitignore"
    gitignore_entry = f"{MULDER_SUBDIR}/"
    if gitignore_path.exists():
        existing = gitignore_path.read_text()
        if gitignore_entry not in existing:
            with open(gitignore_path, "a") as f:
                f.write(f"\n# Mulder coordination files (local only)\n{gitignore_entry}\n")
            console.print(f"  [green]Updated[/green] {gitignore_path} (added {gitignore_entry})")
        else:
            console.print(f"  [dim]Already in .gitignore:[/dim] {gitignore_entry}")
    else:
        gitignore_path.write_text(f"# Mulder coordination files (local only)\n{gitignore_entry}\n")
        console.print(f"  [green]Created[/green] {gitignore_path}")

    # Write the CLAUDE.md snippet into the project
    snippet = _claude_md_snippet(name)
    claude_md_path = path / "CLAUDE.md"
    if claude_md_path.exists():
        existing = claude_md_path.read_text()
        if "Mulder Integration" not in existing:
            with open(claude_md_path, "a") as f:
                f.write(f"\n{snippet}")
            console.print(f"  [green]Appended[/green] Mulder snippet to {claude_md_path}")
        else:
            console.print(f"  [dim]Mulder snippet already in[/dim] {claude_md_path}")
    else:
        claude_md_path.write_text(snippet)
        console.print(f"  [green]Created[/green] {claude_md_path}")

    # Log the introduction
    append_log(p, "Mulder", f"Introduced Mulder to project '{name}'.")

    console.print(Panel(
        f"[green]Mulder is now watching[/green] [bold]{name}[/bold]\n\n"
        f"[dim].mulder/ created, .gitignore updated, CLAUDE.md written.[/dim]",
        title="[bold green]✓ Introduction Complete[/bold green]",
        border_style="green",
    ))


@cli.command()
@click.argument("name")
def log(name):
    """Show the activity log for a project."""
    p = get_project(name)
    if not p:
        console.print(f"[red]Project '{name}' not found.[/red]")
        sys.exit(1)

    log_path = mulder_path(p, LOG_FILE)
    content = read_md(log_path)

    if not content:
        console.print(f"[dim]No log entries yet for '{name}'.[/dim]")
        return

    console.print(Panel(
        Markdown(content),
        title=f"[bold cyan]Activity Log — {name}[/bold cyan]",
        border_style="dim",
    ))


# ── Templates ─────────────────────────────────────────────────────────────────

def _update_last_updated(content: str) -> str:
    now = ts()
    lines = content.splitlines()
    new_lines = []
    found = False
    for line in lines:
        if line.startswith("last_updated:"):
            new_lines.append(f"last_updated: {now}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.insert(0, f"last_updated: {now}")
    return "\n".join(new_lines)


def _status_template(project_name: str) -> str:
    return f"""# Status — {project_name}
last_updated: {ts()}

## Current Work
_What are you working on right now?_

## Recently Completed
_What did you finish recently?_

## Blockers
_Anything blocking progress?_

## Notes
_Anything Mulder should know about this project?_
"""


def _tasks_template() -> str:
    return f"""# Tasks from Mulder
last_updated: {ts()}

## Pending
<!-- tasks will appear here -->

## Completed
"""


def _mulder_readme(project_name: str) -> str:
    return f"""# .mulder/ — Agent Mulder Integration

This directory connects **{project_name}** to Agent Mulder, the master monitoring agent.

## Files

| File | Written by | Purpose |
|------|-----------|---------|
| `status.md` | **This agent** | Current work, progress, blockers |
| `tasks.md` | **Mulder** | Tasks queued for this agent |
| `log.md` | Both | Activity log |

## Your responsibility

Keep `status.md` updated as you work. Mulder reads it to understand what's happening across all projects.

Update it:
- When you start or finish a significant task
- When you hit a blocker
- When the project direction changes

## Checking for tasks

Read `tasks.md` at the start of each session and after completing current work.
Mark tasks complete by changing `- [ ]` to `- [x]`.
"""


def _claude_md_snippet(project_name: str) -> str:
    return f"""## Mulder Integration

This project is monitored by **Agent Mulder** (master coordination agent).

**At the start of each session:** Read `.mulder/tasks.md` for any pending tasks from Mulder.

**During and after work:** Keep `.mulder/status.md` updated with:
- What you are currently working on
- What you have recently completed
- Any blockers or important context

Update the `last_updated:` timestamp whenever you write to `status.md`.

**Completing tasks:** When you finish a task from `.mulder/tasks.md`, mark it `- [x]` and move it to the Completed section.

The `.mulder/` directory is the communication channel between this agent and Mulder.
"""


if __name__ == "__main__":
    cli()
