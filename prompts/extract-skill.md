# Skill Extraction

## Background

### What is a skill

A skill is a packaged unit of specialized knowledge and workflow that an
AI agent loads on demand to perform a specific type of task. A complete
skill contains:

- A trigger description (when to activate)
- Domain knowledge (what you need to know to do this task)
- Workflow (steps, order, decision points)
- Resources (templates, tools, reference materials needed)

### What you are doing

You will receive a conversation between a user and an AI agent. A single
conversation may cover zero, one, or many tasks. Your job is to read the
conversation and extract **skill fragments** — pieces of information
that, when accumulated over multiple conversations, can be assembled
into complete skills.

A fragment might be:
- A sequence of steps for a task
- Domain knowledge needed to do a task correctly
- A resource or template referenced during a task
- A constraint or gotcha specific to a task
- A trigger condition (what signals that this task is starting)

### Your perspective

You analyze from the **task-binding** perspective. You care about
information that is bound to a nameable, recurring task. Information that
is universally true regardless of task, or that is a general behavioral
rule, is less relevant to you — but you still score it on all three
dimensions.

## Input

See [extract-common.md](extract-common.md) for input format and scoring
dimensions.

## Extraction rules

For each candidate fragment, ask:

1. **Is there a nameable task?** — Can you identify a 2-5 word task name
   this fragment belongs to?
2. **Is it non-obvious?** — Would an agent without this fragment do the
   task worse?
3. **Will this task recur?** — Is it likely to happen again in future
   conversations?

All three must be true to extract.

## Drop rules

Do NOT extract if ANY apply:
1. One-time task that won't recur
2. Information is trivially obvious
3. Pure session-local state (temp paths, debugging artifacts)
4. The fragment adds nothing an agent couldn't figure out from source
   code or documentation alone

## Output format

```json
[
  {
    "task": "Short task name (2-5 words)",
    "fragment_type": "step | knowledge | resource | constraint | trigger",
    "content": "The extracted information",
    "context": "Why this matters for the task (1 sentence)",
    "scores": {
      "x_knowledge": 0.0,
      "y_rule": 0.0,
      "z_task": 0.0
    }
  }
]
```

### Fragment types

- **step**: An action in a sequence ("Fill title with format 'RA ...'")
- **knowledge**: Domain fact needed for the task ("Kickoff doesn't need review period")
- **resource**: Template, tool, or reference used ("Use Review Invitation template")
- **constraint**: Gotcha, limitation, or must-not ("Don't include comment classification for kickoff")
- **trigger**: Signal that this task is starting ("User mentions 'kickoff' or 'SP kickoff'")

### Scoring dimensions

See [extract-common.md](extract-common.md) for full definitions. Summary:
- **x_knowledge**: standalone fact? (0.0–1.0)
- **y_rule**: unconditional behavioral constraint? (0.0–1.0)
- **z_task**: bound to a specific task? (0.0–1.0)

As the skill extraction prompt, your outputs should typically have high
z_task scores. If you find yourself scoring z_task below 0.3, reconsider
whether this fragment belongs here.

## Examples

Good extractions:
```json
[
  {
    "task": "send SP kickoff email",
    "fragment_type": "step",
    "content": "Title format: 'RA <SubProgram>: SP Kickoff for <FPT-ID> <Slogan>'",
    "context": "Consistent naming required by CA WoW",
    "scores": {"x_knowledge": 0.3, "y_rule": 0.2, "z_task": 0.9}
  },
  {
    "task": "send SP kickoff email",
    "fragment_type": "resource",
    "content": "Use Review Invitation template, adapted for kickoff",
    "context": "Template is the starting point but needs sections removed",
    "scores": {"x_knowledge": 0.5, "y_rule": 0.1, "z_task": 0.8}
  },
  {
    "task": "send SP kickoff email",
    "fragment_type": "constraint",
    "content": "Remove review period, SharePoint link, and comment classification sections",
    "context": "These sections are for document review, not kickoff",
    "scores": {"x_knowledge": 0.4, "y_rule": 0.3, "z_task": 0.9}
  }
]
```

Bad extraction (no task binding):
```json
[{"task": "general", "content": "Use Chinese for replies", "scores": {"x_knowledge": 0.0, "y_rule": 0.9, "z_task": 0.0}}]
```
This has z_task=0.0 — it doesn't belong in skill extraction.

Output `[]` if nothing qualifies.
