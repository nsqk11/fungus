# Writing Standards

Project-specific writing conventions for the Fungus repository.

## Scope

Applies to all documentation, prompts, and `SKILL.md` bodies in this
repository. Does not govern code comments (see `coding-standards.md`).

## Authority

Defer to the Google Developer Documentation Style Guide (indexed as a
knowledge base) for general writing rules: language, grammar, tone,
formatting, and terminology. Search the KB when in doubt.

This file defines only the conventions that are specific to Fungus and
not covered by the upstream guide.

## Voice by Document Type

Different files serve different purposes and require different voices.

| Type | Example | Voice |
|------|---------|-------|
| Identity / context | `<identity>` section | Descriptive |
| Rules / constraints | `<rules>`, standards files | Imperative |
| SKILL.md body | `skills/*/SKILL.md` | Imperative |
| Reference / guide | `references/*.md`, README | Descriptive |
| Code comments | Inline, docstrings | What: descriptive. How: imperative. |

## Project-Specific Conventions

- One sentence per line in Markdown source. Easier diffs and reviews.
- Keep lines within reasonable width for human review.
  Long sentences in LLM-facing content (e.g., `system-prompt.md`)
  may exceed typical line length when breaking would harm clarity.
- SKILL.md `description` frontmatter must state what the skill does
  and when to trigger, include relevant trigger keywords, and list
  `Do NOT` exclusions for adjacent concerns.
- Do not invent arbitrary numeric limits ("max 5 items"). Constrain
  quality with principles. Exceptions apply only when an external
  standard sets a specific number, such as the 72-character summary
  limit from Conventional Commits.

## Description Quality Checklist

Apply when writing or reviewing any skill `description` frontmatter.

- States what the skill does in one sentence.
- States when to trigger (reminder tags, user intents, file types).
- Includes trigger keywords — the words a user would naturally say
  when they need this skill.
- Includes `Do NOT` exclusions — adjacent concerns that belong to
  other skills.
- Pushy enough: would the agent pick this skill even if the user
  does not name it explicitly?
- Stays under 1024 characters (per the `agent-skills-spec` KB).
