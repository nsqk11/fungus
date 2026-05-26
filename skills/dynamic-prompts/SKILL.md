---
name: dynamic-prompts
description: "Intent-aware dynamic prompt injection. Intercepts user prompts, detects intent via pattern matching or LLM analysis, and injects relevant context on demand — instead of loading all rules statically. Trigger on: userPromptSubmit hook event."
---

# Dynamic Prompts

Replaces static, always-loaded prompt rules with on-demand context
injection based on detected user intent.

## How it works

```
User prompt → router.py (hook) → intent detection → inject context
```

The router intercepts every `userPromptSubmit` event, analyzes the
user's message, and injects targeted reminders only when relevant.

## Examples

| Detected intent | Injected context |
|-----------------|-----------------|
| Push to remote | Check remote URL; if GitHub, exclude sensitive files |
| Delete files | Confirm irreversibility, suggest -f flag |
| Edit production config | Remind to prototype in /tmp first |
| Fragments accumulated | Suggest distill session |

## Architecture

`hooks/router.py` serves dual purpose:
1. **Event dispatcher** — routes hook events to matching handler scripts
   across all installed skills (scans `$KIRO_HOME/skills/*/hooks/*.py`)
2. **Intent analyzer** — for `userPromptSubmit`, applies dynamic prompt
   rules before dispatching

## Adding rules

Rules are defined as pattern → context pairs. When a pattern matches
the user's prompt, the corresponding context is injected into the
agent's input.
