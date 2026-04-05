# Agency Agents — Project Guide

## Overview

This is a fork of [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents) — a collection of specialized AI agent personalities organized into divisions. We maintain our own agents (security, testing, documentation, etc.) alongside community-contributed upstream agents.

## Repo Structure

```
agency-agents/
├── academic/           # Scholarly rigor agents (anthropologist, historian, etc.)
├── design/             # UI/UX, brand, visual storytelling
├── engineering/        # Frontend, backend, DevOps, security eng, etc.
├── game-development/   # Unity, Unreal, Godot, Roblox, Blender
├── marketing/          # Growth, social, content, China market
├── paid-media/         # PPC, programmatic, paid social
├── product/            # Sprint planning, trends, feedback, feature ideation
├── project-management/ # Orchestration, PM, Jira, production readiness
├── sales/              # Outbound, discovery, pipeline, coaching
├── security/           # Audit, pentest, auth, compliance (fork-only)
├── spatial-computing/  # XR, visionOS, Metal
├── specialized/        # Niche experts (MCP builder, civil eng, etc.)
├── support/            # Ops, finance, legal, docs, incident response
├── testing/            # QA, accessibility, playwright, performance
├── examples/           # Workflow examples (not agents)
├── integrations/       # Tool-specific install guides
├── strategy/           # Playbooks and runbooks
└── scripts/            # Tooling (add-metadata.py, convert.sh, etc.)
```

## Agent Front Matter Schema

Every agent `.md` file must have YAML front matter with these fields:

```yaml
---
name: Agent Display Name
description: >
  One-paragraph description of what this agent does.
version: 1.0.0
author: github-handle
contributors:
  - "contributor-handle-1"
  - "contributor-handle-2"
source: msitarzewski/agency-agents   # or bernierllc/agency-agents
division: engineering                 # matches directory name
color: blue
emoji: 🔧                            # optional
tools: Read, Write, Edit, Bash       # optional
---
```

### Required fields

| Field | Description |
|-------|-------------|
| `name` | Human-readable agent name |
| `description` | What this agent does (use `>` for multi-line) |
| `version` | Semantic version (see version bumping below) |
| `author` | GitHub handle of the original creator |
| `source` | Which repo this agent originated from |
| `division` | Directory/division name |
| `color` | Agent color for UI rendering |

### Optional fields

| Field | Description |
|-------|-------------|
| `contributors` | List of GitHub handles who modified the agent |
| `emoji` | Display emoji |
| `tools` | Comma-separated list of tools the agent uses |
| `vibe` | One-line personality summary |

## Version Bumping

When modifying an agent, bump its `version` field using semver:

| Change type | Bump | Example |
|-------------|------|---------|
| Fix typos, formatting, minor wording | **patch** | `1.0.0` → `1.0.1` |
| Add new capabilities, sections, or workflows | **minor** | `1.0.0` → `1.1.0` |
| Rewrite personality, change core mission, or rename | **major** | `1.0.0` → `2.0.0` |

**Rule**: If you modify an agent's `.md` file, bump the version. The pre-push hook will handle updating contributor metadata automatically.

## Metadata Script

The `scripts/add-metadata.py` script manages front matter metadata:

```bash
# Incremental scan (default) — only processes files changed since last run
python3 scripts/add-metadata.py

# Full rescan — reprocesses all agent files from scratch
python3 scripts/add-metadata.py --full
```

The script stores its cursor in `.metadata-scan-cursor` (gitignored). On first run or with `--full`, it scans the entire git history. On subsequent runs, it only looks at files changed since the last scan.

This runs automatically as a **pre-push hook** — you don't need to run it manually.

## Adding a New Agent

1. Create `<division>/<division>-<agent-name>.md` in the appropriate directory
2. Add YAML front matter (see schema above) with `version: 1.0.0`
3. Set `author` to your GitHub handle
4. Set `source: bernierllc/agency-agents` for fork-originated agents
5. Write the agent personality, mission, workflows, and deliverables
6. Add the agent to the README roster table in the correct division section
7. Commit and push — the pre-push hook will finalize metadata

## Upstream Sync

This fork tracks `msitarzewski/agency-agents` as the `upstream` remote:

```bash
git remote add upstream https://github.com/msitarzewski/agency-agents.git
git fetch upstream main
git merge upstream/main
```

After merging, run `python3 scripts/add-metadata.py --full` to ensure all new upstream agents get metadata.

## Conventions

- Agent files live in division directories, never at the repo root
- File names follow `<division>-<agent-name>.md` pattern
- The README roster must list every agent with a link, specialty, and use case
- Don't modify upstream agents without good reason — prefer adding new fork-only agents
- Security, testing, and documentation agents are our primary fork contributions
