# Fungus

Skills are folders of instructions, scripts, and resources that AI coding agents load dynamically to improve performance on specialized tasks. Skills teach agents how to complete specific tasks in a repeatable way, whether that's extracting knowledge from past sessions, injecting context-aware reminders, or integrating with external services.

For information about the Agent Skills standard, see [agentskills.io](http://agentskills.io).

# About This Repository

This repository contains skills that augment AI coding agents with self-improvement and productivity capabilities. These skills range from agent-internal enhancements (persistent memory, dynamic prompts) to external integrations (Atlassian, task tracking).

Each skill is self-contained in its own folder with a `SKILL.md` file containing the instructions and metadata that the agent uses. Browse through these skills to get inspiration for your own skills or to understand different patterns and approaches.

# Skills

- [`skills/fragment-extractor`](./skills/fragment-extractor): Automatically extracts reusable knowledge fragments from session transcripts. Runs in the background after each session ends.
- [`skills/dynamic-prompts`](./skills/dynamic-prompts): Intent-aware dynamic prompt injection. Detects user intent and injects relevant context on demand instead of loading all rules statically.
- [`skills/atlassian`](./skills/atlassian): PAT management, Confluence page caching with full-text search, and live Jira issue fetching. Hand it any Atlassian URL and it dispatches automatically.
- [`skills/task-tracking`](./skills/task-tracking): Tracks lifecycle metadata for any ongoing task: deliverable paths, milestones, blockers, changelogs, review comments, and decision notes.

# Install

## Hook registration

Hook scripts stay in their skill directories. Register them in your agent's config (e.g. `~/.kiro/agents/your-agent.json`):

```json
{
  "hooks": {
    "userPromptSubmit": ["~/.kiro/skills/dynamic-prompts/hooks/router.py"],
    "agentSpawn": ["~/.kiro/skills/fragment-extractor/hooks/spawn-extract.py"]
  }
}
```

## Skills placement

Copy skills to your agent's skill directory:

```bash
cp -r skills/fragment-extractor ~/.kiro/skills/
cp -r skills/dynamic-prompts ~/.kiro/skills/
```

## Extractor agents

The fragment-extractor skill uses 3 worker agents that run in the background. Register them:

```bash
for f in skills/fragment-extractor/agents/*.json; do
    sed "s|FUNGUS_ROOT|$HOME/.kiro/skills|g" "$f" > ~/.kiro/agents/$(basename "$f")
done
```

# How It Works

```
┌─────────────────────────────────────────────────────┐
│  User prompt                                        │
│       │                                             │
│       ▼                                             │
│  dynamic-prompts: detect intent → inject context    │
│                                                     │
│  Session ends                                       │
│       │                                             │
│       ▼                                             │
│  fragment-extractor: extract → score → persist      │
│       │                                             │
│       ▼                                             │
│  SQLite DB → rules.md + fragments.md (KB)           │
└─────────────────────────────────────────────────────┘
```

# Structure

```
fungus/
├── README.md
├── spec/
│   └── agent-skills-spec.md
└── skills/
    ├── fragment-extractor/
    │   ├── SKILL.md
    │   ├── hooks/
    │   ├── scripts/
    │   ├── prompts/
    │   └── agents/
    └── dynamic-prompts/
        ├── SKILL.md
        └── hooks/
```

- [./skills](./skills): The skill collection
- [./spec](./spec): The Agent Skills specification

# Requirements

- Python 3.10+
- An agent platform with hook support (currently tested with Kiro CLI)

# License

MIT
