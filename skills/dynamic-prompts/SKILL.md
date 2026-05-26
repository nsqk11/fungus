---
name: dynamic-prompts
description: "Intent-aware dynamic context injection for AI agents. Analyzes hook events (user prompts, tool calls, etc.) in real-time and injects relevant reminders, guardrails, or context on demand — instead of loading all rules statically. Runs automatically via hook; no user action needed. The user never interacts with this skill directly."
compatibility: "Python 3.10+, agent platform with hook support (userPromptSubmit, preToolUse, postToolUse, etc.)"
---

# Dynamic Prompts

Injects targeted context into the agent based on detected intent.
Replaces static rules files with on-demand, event-driven injection.

## How it works

```
Hook event (any type)
    → scripts/inject.py
        → filter rules by event name
            → regex match against event content
                → if match: inject context
                → if no match: silent pass-through
```

Two-stage matching:
1. **Event filter** — only rules whose `event` includes the current hook fire
2. **Pattern match** — regex (case-insensitive) against event content

## Setup

Register the hook for all events you want to intercept:

```json
{
  "hooks": {
    "userPromptSubmit": ["$KIRO_HOME/skills/dynamic-prompts/scripts/inject.py"],
    "preToolUse": ["$KIRO_HOME/skills/dynamic-prompts/scripts/inject.py"],
    "postToolUse": ["$KIRO_HOME/skills/dynamic-prompts/scripts/inject.py"]
  }
}
```

## Rules

Single file: `rules.json`. Array of rule objects.

```json
[
  {
    "event": ["userPromptSubmit", "preToolUse"],
    "pattern": "push|force.push|git push",
    "context": "Before pushing:\n- Check remote URL (git remote -v)\n- If GitHub, exclude sensitive files (.env, tokens)\n- Never force push to main without permission"
  },
  {
    "event": ["preToolUse"],
    "pattern": "rm -rf|rm -f|rmdir",
    "context": "Destructive file operation. Before proceeding:\n- Confirm exact path with user\n- Prefer moving to /tmp over permanent deletion"
  },
  {
    "event": ["userPromptSubmit"],
    "pattern": "prod|production.*config|deploy",
    "context": "Production change detected:\n- Prototype in /tmp first\n- Show diff before applying\n- Confirm rollback path exists"
  }
]
```

### Rule format

| Field | Required | Description |
|-------|----------|-------------|
| `event` | Yes | List of hook event names this rule responds to |
| `pattern` | Yes | Regex (case-insensitive) matched against event content |
| `context` | Yes | Text injected when matched |
| `priority` | No | Integer, lower runs first (default: 50) |

### Event content

What gets matched depends on the event type:

| Event | Content matched against |
|-------|------------------------|
| `userPromptSubmit` | User's prompt text |
| `preToolUse` | Tool name + arguments |
| `postToolUse` | Tool name + output |

## Examples

**Event:** `userPromptSubmit`, user says "ok push it to github"
**Rule:** pattern=`push|force.push|git push` → matches
**Output:**
```json
{"type": "context", "context": "Before pushing:\n- Check remote URL..."}
```

---

**Event:** `preToolUse`, agent about to run `rm -rf /tmp/old-build`
**Rule:** pattern=`rm -rf|rm -f` → matches
**Output:**
```json
{"type": "context", "context": "Destructive file operation..."}
```

---

**Event:** `userPromptSubmit`, user says "fix the typo in utils.ts"
**No rule matches** → no output, silent pass-through

## Hook I/O

**Input** (stdin): JSON payload from agent platform:
```json
{
  "hook_event_name": "userPromptSubmit",
  "data": {
    "content": "ok push it to github"
  }
}
```

**Output** (stdout): JSON when context should be injected:
```json
{"type": "context", "context": "<injected text>"}
```

No output = no injection.

## Error handling

| Situation | Behaviour |
|-----------|-----------|
| `rules.json` not found | Hook exits silently |
| Malformed JSON | Hook exits with warning to stderr |
| Rule missing required field | Rule skipped with warning to stderr |
| Regex compilation error | Rule skipped with warning to stderr |
| Multiple rules match | All contexts injected, ordered by priority |

## Design principles

- **Event-first filtering** — cheap string compare before any regex
- **Zero false positives over coverage** — better to miss than inject noise
- **Additive** — only injects context, never blocks or modifies user input
- **Fail-open** — if anything breaks, prompt passes through unmodified
- **Zero dependencies** — pure Python stdlib (json, re, sys)
