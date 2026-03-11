# GitHub Copilot Integration

The Agency works natively with GitHub Copilot. No conversion needed — agents work
natively with the existing `.md` + YAML frontmatter format.

## Install

```bash
# Copy all agents to your GitHub Copilot agents directory
./scripts/install.sh --tool copilot

# Or manually copy a category
cp engineering/*.md ~/.github/agents/
```

## Activate an Agent

In any GitHub Copilot session, reference an agent by name:

```
Activate Frontend Developer and help me build a React component.
```

```
Use the Reality Checker agent to verify this feature is production-ready.
```

## Agent Directory

Agents are organized into divisions. See the [main README](../../README.md) for
the full current roster.
