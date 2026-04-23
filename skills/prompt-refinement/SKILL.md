---
name: prompt-refinement
description: "[guide] Extract behavior principles from external
  projects and refine personal agent prompts. Use when
  evaluating GitHub repos, frameworks, or methodologies
  for agent behavior ideas, or when improving agent-prompt.md
  or work prompts. Trigger on 'prompt 改进', '行为原则',
  'agent behavior', 'agent-prompt.md', or 'work prompt'.
  Do NOT use for writing Fungus module SKILL.md
  or general prompt engineering
  tutorials."
---

# Prompt Refinement

> Distill actionable behavior principles from external
> sources into personal agent prompts.

## Boundary

- **Does**:
  - Analyze external projects for agent behavior patterns.
  - Evaluate which patterns apply to the user's agent context.
  - Distill principles into concise, rhetoric-free rules.
  - Write principles into target prompt files.
- **Does not**:
  - Write Fungus module SKILL.md.
  - Teach general prompt engineering theory.
  - Modify Kiro system prompt or built-in behavior.

## Interface

- **Triggers**: user shares an external project to evaluate,
  asks to improve agent prompt behavior, mentions agent-prompt.md
  or work prompt refinement.
- **Related**: `fruit` for skill emergence from nutrients.

## Behavior

### Evaluate External Source

1. **Situation** — user shares a repo, framework,
   or methodology and asks what is useful.
2. **Guidance** —
   - Read the source material thoroughly.
   - Identify behavior-shaping patterns: role definitions,
     decision heuristics, quality gates, failure responses.
   - Classify each pattern:
     - **Applicable** — addresses a gap in current prompts.
     - **Already covered** — current prompts handle this.
     - **Not relevant** — wrong domain or abstraction level.
   - Present the classification with reasoning.
     Let the user decide what to adopt.
3. **Handoff** — if the source contains Fungus module ideas,
   hand off to `fruit`.

### Refine Prompt

1. **Situation** — user confirms which principles to adopt,
   or asks to improve a specific prompt file.
2. **Guidance** —
   - Read the target prompt file first.
   - Strip rhetoric, jargon, and pressure language
     from the source principles. Keep only the actionable
     core — the agent is smart enough to follow reasoning
     without being threatened.
   - Write principles as short imperative phrases.
     Each principle should be one line, self-contained.
   - Group under a clear heading (e.g. `行为原则`).
   - Verify: would a fresh agent session understand
     and follow each principle without extra context?
3. **Handoff** — if the user wants to test prompt changes
   across sessions, suggest manual verification
   in a new chat.

### Quality Check

1. **Situation** — after writing principles, self-review.
2. **Guidance** —
   - Each principle must be actionable (starts with a verb).
   - No overlap — two principles should not say the same
     thing in different words.
   - No vague aspirations — "be proactive" is too vague;
     "发现隐患主动提出，不等用户追问" is actionable.
   - Total principles per prompt should stay under 7.
     Beyond that, the agent stops internalizing them.
3. **Handoff** — none. This is the final step.
