# Rule Extraction

## Background

### What are prompt rules

Prompt rules are behavioral constraints injected into the agent's system
prompt — they are **always active**, shaping every response regardless
of task. They are short, imperative, and unconditional.

Examples: "Reply in Chinese", "Don't ask for confirmation", "Use
kebab-case for file names".

### What you are doing

You will receive a conversation between a user and an AI agent. Your job
is to extract **behavioral rules** — corrections, preferences, and
constraints that the user expects the agent to follow in all future
interactions.

### Your perspective

You analyze from the **behavioral rule** perspective. You care about
information that should change the agent's default behavior regardless
of what task it is doing. Information that only applies within a
specific task, or that is a factual statement, is less relevant to you —
but you still score it on all three dimensions.

## Input

See [extract-common.md](extract-common.md) for input format and scoring
dimensions.

## Extraction rules

For each candidate, ask:

1. **Is it a behavioral constraint?** — Does it tell the agent to do or
   not do something?
2. **Is it unconditional (or nearly)?** — Does it apply broadly, not
   just to one specific task?
3. **Is it persistent?** — Is this a standing rule, not a one-time
   instruction for this session only?

All three must be true to extract.

## Drop rules

Do NOT extract if ANY apply:
1. One-time instruction for the current session only ("this time, skip the tests")
2. Task-specific step disguised as a rule (belongs in skill extraction)
3. Already present in the current system prompt
4. Too vague to act on ("be better")
5. Contradicts a rule the user previously established (flag as conflict instead)

## Output format

```json
[
  {
    "rule": "Imperative statement (do X / don't do Y)",
    "context": "What triggered this — correction, explicit preference, or observed pattern",
    "scope": "universal | conditional",
    "condition": "When/where this applies (only if scope is conditional)",
    "scores": {
      "x_knowledge": 0.0,
      "y_rule": 0.0,
      "z_task": 0.0
    }
  }
]
```

### Scope

- **universal**: Applies always, no conditions ("reply in Chinese")
- **conditional**: Applies in a class of situations ("when writing documents, don't compare with previous versions")

### Scoring guidance

As the rule extraction prompt, your outputs should typically have high
y_rule scores. If you find yourself scoring y_rule below 0.3, reconsider
whether this entry belongs here.

## Examples

Good extractions:
```json
[
  {
    "rule": "Don't ask for confirmation before executing file changes",
    "context": "User corrected agent for asking 'should I proceed?' multiple times",
    "scope": "universal",
    "scores": {"x_knowledge": 0.0, "y_rule": 0.9, "z_task": 0.0}
  },
  {
    "rule": "When writing CSIM documents, don't compare the new design with R608",
    "context": "User explicitly said NDS should describe CT50 on its own terms",
    "scope": "conditional",
    "condition": "Writing CSIM NDS or similar design documents",
    "scores": {"x_knowledge": 0.1, "y_rule": 0.7, "z_task": 0.4}
  }
]
```

Bad extraction (task-bound step, not a rule):
```json
[{"rule": "Fill title with format 'RA <SubProg>: SP Kickoff...'", "scores": {"x_knowledge": 0.3, "y_rule": 0.2, "z_task": 0.9}}]
```
This has z_task=0.9 — it's a skill fragment, not a behavioral rule.

Output `[]` if nothing qualifies.
