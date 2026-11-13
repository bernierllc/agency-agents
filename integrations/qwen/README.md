# Qwen Code Integration

Qwen Code uses project-scoped `.md` SubAgent files in `.qwen/agents/`.

The generated files come from `scripts/convert.sh --tool qwen`, which writes one
SubAgent Markdown file per agency agent into `integrations/qwen/agents/`.

## Requirements

Qwen Code **0.25.1 or later**. Earlier releases treat every `${name}` in a
SubAgent's prompt as a value to fill and refuse to launch the agent when they
have none ("Missing context values for the following keys: …"). Several agents
show `${name}` in their code examples, so on those releases they can't be
launched. From 0.25.1, Qwen leaves any `${name}` it doesn't fill as written
([#1081](https://github.com/msitarzewski/agency-agents/issues/1081)).

Qwen does fill three names: `${task_prompt}`, `${hook_context}` and
`${external_inputs_override}`. `scripts/lint-agents.sh` rejects them in agent
bodies, so no agent text is replaced at launch.

## Generate

From the repository root:

```bash
./scripts/convert.sh --tool qwen
```

## Install

Run the installer from your target project root:

```bash
cd /your/project && /path/to/agency-agents/scripts/install.sh --tool qwen
```

This copies the generated SubAgent files into:

```text
.qwen/agents/
```

## Refresh in Qwen Code

After installation:

- run `/agents manage` in Qwen Code to refresh the agent list, or
- restart the current Qwen Code session

## Notes

- Qwen Code is project-scoped, not home-scoped
- The generated Qwen files use minimal frontmatter: `name`, `description`, and
  optional `tools`
- If you update agents in this repo, regenerate the Qwen output before
  reinstalling
