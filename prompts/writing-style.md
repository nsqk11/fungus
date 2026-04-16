# Writing Style

Writing standards for all documentation and prompts in this repository.

## Language

- English only. No mixed languages.
- Use American English spelling (behavior, not behaviour).

## Voice by Document Type

| Type | Examples | Voice |
|------|----------|-------|
| Identity / context | agent-context.md (role section) | Descriptive: "You are...", "This project uses..." |
| Rules / constraints | coding-style.md, agent-context.md (rules) | Imperative: "Follow...", "Never...", "Always..." |
| Templates / guides | skill-spec.md, `<description>` tags | Descriptive: "This section covers...", "Given the role above..." |
| SKILL.md body | Module and skill definitions | Imperative: "Sense signals", not "This module senses signals" |
| Code comments | Inline and docstrings | Descriptive for *what*, imperative for *instructions* |

## Formatting

- One sentence per line in Markdown source (easier diffs).
- Max 80 characters per line in Markdown source.
- Use ATX headers (`#`), not Setext (underlines).
- Use `-` for unordered lists, `1.` for ordered lists.
- Use backticks for code references: `mycelium`, `mem.json`.
- Use `**bold**` for key terms on first mention only.

## Structure

- Lead with the most important information.
- Keep paragraphs short.
- Prefer tables over long prose for comparisons.
- Prefer lists over paragraphs for enumerations.
