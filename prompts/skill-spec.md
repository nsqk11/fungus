# Skill Spec

Writing standard for all SKILL.md files in Fungus — modules and grown skills.

## Rules

- Voice: imperative.
  "Sense signals", not "This module senses signals".
- Language: English only.
- Keep sections focused.
  If a Boundary list grows unwieldy, the module has too many
  responsibilities — split it.
- References: backtick + name (`mycelium`), not file paths.
- After writing: remove all `<description>` and `<variant>` tags.

## Template

Copy the skeleton below.
Choose one variant per section where marked.
Fill each section following its `<description>` guidance,
then remove the tags.

---

````markdown
---
name: <kebab-case, must match directory name>
description: "[type] <Concise one-sentence summary. Include trigger keywords and Do NOT exclusions.>"
---
````

Type prefix in description: `[module]`, `[tool]`, or `[guide]`.

### Writing a Good Description

The description is the primary triggering mechanism.
The agent sees only name + description when deciding
whether to consult a skill.

**Be pushy.**
The agent tends to undertrigger — it skips skills
it should use. Combat this by making the description
assertive about when to activate.

Bad: "Handle DNS ad blocking configuration."
Good: "DNS-level ad blocking server — installation,
  configuration, blocklist management. Use when setting up
  AdGuard Home, managing DNS blocklists, or debugging
  DNS filtering. Trigger on mentions of 'AdGuard', 'AGH',
  'blocklist', or 'Unbound'. Do NOT use for client-side
  ad blocking or non-DNS filtering."

**Include trigger keywords.**
List the words a user would naturally say.
Include abbreviations, aliases, and non-English terms
if the user speaks multiple languages.

**Include Do NOT exclusions.**
Name adjacent concerns that belong to other skills.
This prevents false triggers and helps the agent
route to the correct skill.

**Keep it under 100 words.**
The description is always in context.
Long descriptions waste tokens on every turn.

````markdown
# {Name}

> {One-line role definition. Everything below flows from this.}

## Boundary

<description>
Given the role above, what is this responsible for — and what is
explicitly outside its scope?
Every Does item becomes a contract that Behavior must fulfill.

- **Does**: core responsibilities. Start each with a verb.
- **Does not**: key exclusions.
  Grown skills may name who handles it instead.
  Core modules do not reference each other by name.
</description>

## Interface

<variant type="module">
<description>
To fulfill the Boundary above, what hooks and data partitions
are needed?
Declare only what is necessary.
Must match script annotations (@hook, @writes).
Prefer `bash memory.sh` over direct file references.

- **Hooks**: registered hook names.
- **Reads**: memory.json partitions read. (none) if none.
- **Writes**: memory.json partitions written. (none) if none.
</description>
</variant>

<variant type="tool">
<description>
What commands does this tool expose, and what are their
input/output contracts?

- **Commands**: CLI commands or script entry points.
- **Input**: expected input formats (file types, stdin structure).
- **Output**: what each command produces.
</description>
</variant>

<variant type="guide">
<description>
When does this guide activate, and what does it relate to?

- **Triggers**: keywords or situations that activate this skill.
- **Related**: other skills that handle adjacent concerns.
</description>
</variant>

## Behavior

<variant type="module">
<description>
One subsection per hook declared in Interface.
Describe what the module does at each hook.
Include concrete `bash memory.sh` commands where applicable.
If the module does not inspect stdin structure, omit Input.

Every behavior must trace back to a Does item in Boundary.
</description>
</variant>

<variant type="tool">
<description>
One subsection per command declared in Interface. Each covers:

1. **Usage** — command syntax and parameters.
2. **Process** — what the command does step by step.
3. **Output** — what it produces and where.

Every command must trace back to a Does item in Boundary.
</description>
</variant>

<variant type="guide">
<description>
One subsection per trigger scenario declared in Interface.
Each covers:

1. **Situation** — what the user is trying to do.
2. **Guidance** — what to do and in what order.
3. **Handoff** — when to delegate to a related skill.

Every scenario must trace back to a Does item in Boundary.
</description>
</variant>
````
