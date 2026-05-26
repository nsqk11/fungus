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
    → hooks/router.py
        → filter rules by event name
            → match keywords (regex or LLM) against event content
                → if match: inject context
                → if no match: silent pass-through
```

Two-stage matching:
1. **Event filter** — only rules whose `event` matches the current hook fire
2. **Keyword match** — regex pattern or LLM judgment against event content

## Setup

Register the hook for all events you want to intercept:

```json
{
  "hooks": {
    "userPromptSubmit": ["$KIRO_HOME/skills/dynamic-prompts/hooks/router.py"],
    "preToolUse": ["$KIRO_HOME/skills/dynamic-prompts/hooks/router.py"],
    "postToolUse": ["$KIRO_HOME/skills/dynamic-prompts/hooks/router.py"]
  }
}
```

Register for as many or as few events as needed.

## Rules

Rules are YAML files in `rules/`:

```yaml
# rules/git-push.yaml
event: userPromptSubmit
pattern: "push|force.push|git push"
context: |
  Before pushing:
  - Check the remote URL (git remote -v)
  - If pushing to GitHub, ensure no sensitive files
  - Never force push to main/master without permission
```

```yaml
# rules/dangerous-rm.yaml
event: preToolUse
pattern: "rm -rf|rm -f|rmdir"
context: |
  This is a destructive operation. Before proceeding:
  - Confirm the exact path with the user
  - Prefer moving to /tmp over permanent deletion
```

```yaml
# rules/post-deploy-check.yaml
event: postToolUse
pattern: "deploy|kubectl apply"
context: |
  Deployment executed. Remind user to:
  - Verify the service is healthy
  - Check logs for errors
```

### Rule format

| Field | Required | Description |
|-------|----------|-------------|
| `event` | Yes | Hook event name to respond to |
| `pattern` | No* | Regex matched against event content (case-insensitive) |
| `llm_prompt` | No* | Prompt sent to LLM to judge intent (yes/no) |
| `context` | Yes | Text injected when matched |
| `priority` | No | Integer, lower runs first (default: 50) |

*At least one of `pattern` or `llm_prompt` is required.

### Event content

What gets matched depends on the event type:

| Event | Content matched against |
|-------|------------------------|
| `userPromptSubmit` | User's prompt text |
| `preToolUse` | Tool name + arguments |
| `postToolUse` | Tool name + output |
| `agentSpawn` | Session metadata |

### Rule discovery

Router scans `rules/*.yaml` on each invocation. Add a file → active
immediately on next event.

## Examples

**Event:** `userPromptSubmit`, user says "ok push it to github"
**Matched:** `git-push.yaml` (event matches + pattern matches "push")
**Output:**
```json
{"type": "context", "context": "Before pushing:\n- Check the remote URL..."}
```

---

**Event:** `preToolUse`, agent about to run `rm -rf /tmp/old-build`
**Matched:** `dangerous-rm.yaml` (event matches + pattern matches "rm -rf")
**Output:**
```json
{"type": "context", "context": "This is a destructive operation..."}
```

---

**Event:** `userPromptSubmit`, user says "fix the typo in utils.ts"
**Matched:** nothing (no rule's pattern matches)
**Output:** (none, silent pass-through)

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
| No rules/ directory | Hook exits silently |
| Malformed YAML rule | Skipped with warning to stderr |
| Rule missing `event` field | Skipped |
| Regex compilation error | Rule skipped with warning to stderr |
| LLM call fails | Falls back to pattern-only; if no pattern, skip rule |
| Multiple rules match | All contexts injected, ordered by priority |

## Design principles

- **Event-first filtering** — cheap string compare before any regex/LLM work
- **Zero false positives over coverage** — better to miss than inject noise
- **Fast path** — regex for clear-cut cases; LLM only for ambiguous intent
- **Additive** — only injects context, never blocks or modifies user input
- **Transparent** — injected context is visible to the agent
