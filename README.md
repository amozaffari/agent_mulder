# Agent Mulder

> *"The truth is out there."*

A master coordination agent for Claude Code. Mulder monitors a constellation of local development projects, reads their state, synthesizes what matters, and keeps each project agent aligned with the broader mission.

---

## Concept

Agent Mulder is a **file-based coordination layer** — no API calls, no servers. Communication between Mulder and project agents happens entirely through markdown files.

Each registered project gets a `.mulder/` directory with three files:

| File | Written by | Purpose |
|------|-----------|---------|
| `.mulder/status.md` | Project agent | Current work, completions, blockers |
| `.mulder/tasks.md` | Mulder | Tasks queued for the project agent |
| `.mulder/log.md` | Both | Timestamped activity trail |

**Mulder reads** what project agents have been doing. **Mulder writes** what they should do next. Project agents do the inverse.

---

## How It Works

There are two kinds of Claude Code sessions:

**Mulder session** — open Claude Code in this directory. Claude reads `CLAUDE.md` and becomes the coordination agent: it scans all registered projects, synthesizes their state, and briefs you.

**Project session** — open Claude Code in any registered project. That agent reads its own `CLAUDE.md` (which contains a Mulder snippet), checks `.mulder/tasks.md` for queued work, does the work, and writes progress back to `.mulder/status.md`.

```
agent_mulder/           ← run `claude` here → this is Mulder
  mulder.py
  registry.json         ← gitignored, stays local
  CLAUDE.md

your-project/           ← run `claude` here → this is a project agent
  CLAUDE.md             ← contains the Mulder snippet
  .mulder/
    status.md           ← project agent writes here
    tasks.md            ← Mulder writes here
    log.md
```

---

## Installation

```bash
git clone <this repo>
cd agent_mulder
uv venv && uv pip install -r requirements.txt
```

> Requires [uv](https://github.com/astral-sh/uv). Install it with `curl -LsSf https://astral.sh/uv/install.sh | sh`.

All commands are run with `uv run python mulder.py <command>`.

---

## Usage

### Register a project

```bash
uv run python mulder.py add /path/to/project myproject --goal "What this project is trying to achieve"
```

### Introduce Mulder to a project

Creates the `.mulder/` structure, adds `.mulder/` to the project's `.gitignore`, and writes the Mulder snippet into the project's `CLAUDE.md` (creating it if it doesn't exist):

```bash
uv run python mulder.py introduce myproject
```

From that point on, any Claude Code session inside that project will know to read tasks from Mulder and write status back.

### Scan all projects

```bash
uv run python mulder.py scan
```

Reads and displays the current status and open tasks for every registered project.

### Check a single project

```bash
uv run python mulder.py status myproject
```

### Leave a task for a project agent

```bash
uv run python mulder.py task myproject "Refactor the auth module to use the new JWT library — see issue #42"
```

The task is written to `.mulder/tasks.md`. The project agent picks it up at the start of its next session.

### Update the Mulder snippet in a project

When the Mulder protocol changes (new shorthands, updated instructions), push the latest snippet to one or all projects:

```bash
uv run python mulder.py update myproject   # single project
uv run python mulder.py update --all       # all registered projects
```

### View activity log

```bash
uv run python mulder.py log myproject
```

### List all registered projects

```bash
uv run python mulder.py list
```

### Remove a project

Reverses `introduce` — deletes `.mulder/`, cleans `.gitignore`, removes the Mulder snippet from `CLAUDE.md`, and unregisters the project:

```bash
uv run python mulder.py remove myproject
```

Use `-y` to skip the confirmation prompt.

---

## The Communication Loop

```
Mulder  →  project/.mulder/tasks.md    (what to do next)
Mulder  ←  project/.mulder/status.md   (what was done)

Project →  .mulder/status.md           (current state)
Project ←  .mulder/tasks.md            (queued work)
```

### Staleness detection

Every `status.md` has a `last_updated:` timestamp. If a project hasn't updated in more than 24 hours during active development, Mulder flags it as potentially blocked or abandoned.

### Shorthand command

Inside any project session, say **mulder-sync** to trigger a full sync:
1. Read `.mulder/tasks.md` for pending tasks
2. Update `.mulder/status.md` with current work, completions, and blockers
3. Update the `last_updated:` timestamp

---

## What Gets Committed

- `.gitignore` — keeps personal data out of git
- `CLAUDE.md` — Mulder's instructions
- `mulder.py` — the CLI
- `requirements.txt` — dependencies
- `pyproject.toml` — uv project config
- `uv.lock` — locked dependencies
- `README.md` — this file

`registry.json` is gitignored — it contains your local paths and project goals and stays on your machine.

---

## Dependencies

- [click](https://click.palletsprojects.com/) — CLI framework
- [rich](https://github.com/Textualize/rich) — terminal output

No Anthropic SDK. No API calls. Intelligence is provided by Claude Code running in each directory.
