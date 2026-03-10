# Github Copilot Integration

The Agency was built for Github Copilot. No conversion needed — agents work
natively with the existing `.md` + YAML frontmatter format.

## Install

```bash
# Copy all agents to your Github Copilot agents directory
./scripts/install.sh --tool copilot

# Or manually copy a category
cp engineering/*.md ~/.github/agents/
```

## Activate an Agent

In any Github Copilot session, reference an agent by name:

```
Activate Frontend Developer and help me build a React component.
```

```
Use the Reality Checker agent to verify this feature is production-ready.
```

## Agent Directory

Agents are organized into divisions. See the [main README](../../README.md) for
the full roster of 61 specialists.
