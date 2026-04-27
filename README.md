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
pip install -r requirements.txt
```

---

## Usage

### Register a project

```bash
python mulder.py add /path/to/project myproject --goal "What this project is trying to achieve"
```

### Introduce Mulder to a project

Creates the `.mulder/` structure and prints a snippet to paste into the project's `CLAUDE.md`:

```bash
python mulder.py introduce myproject
```

Add the printed snippet to the project's `CLAUDE.md`. From that point on, any Claude Code session inside that project will know to read tasks from Mulder and write status back.

### Scan all projects

```bash
python mulder.py scan
```

Reads and displays the current status and open tasks for every registered project.

### Check a single project

```bash
python mulder.py status myproject
```

### Leave a task for a project agent

```bash
python mulder.py task myproject "Refactor the auth module to use the new JWT library — see issue #42"
```

The task is written to `.mulder/tasks.md`. The project agent picks it up at the start of its next session.

### View activity log

```bash
python mulder.py log myproject
```

### List all registered projects

```bash
python mulder.py list
```

### Remove a project

```bash
python mulder.py remove myproject
```

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

---

## What Gets Committed

```
.gitignore       ← keeps personal data out of git
CLAUDE.md        ← Mulder's instructions
mulder.py        ← the CLI
requirements.txt ← dependencies
README.md        ← this file
```

`registry.json` is gitignored — it contains your local paths and project goals and stays on your machine.

---

## Dependencies

- [click](https://click.palletsprojects.com/) — CLI framework
- [rich](https://github.com/Textualize/rich) — terminal output

No Anthropic SDK. No API calls. Intelligence is provided by Claude Code running in each directory.
