# Fungus

Memory pipeline for Kiro CLI agents. Automatically extracts reusable
knowledge from session transcripts and makes it available to the main
agent.

## How it works

```
Session ends → cron triggers → 3 extractor agents run in parallel
                                    │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
             skill-extractor   kb-extractor    rule-extractor
                    │                │                │
                    └────────────────┼────────────────┘
                                    ▼
                              SQLite DB
                                    │
                         ┌──────────┴──────────┐
                         ▼                     ▼
                    rules.md              fragments.md
                 (always loaded)         (KB searchable)
```

Each extractor scores every fragment on three dimensions:
- **x_knowledge** — standalone factual content
- **y_rule** — unconditional behavioral constraint
- **z_task** — bound to a specific recurring task

Fragments with `y_rule > 0` go to `rules.md` (injected into every
session). The rest go to `fragments.md` (searchable via knowledge base).

## Distill

Over time, fragments accumulate. The distill skill (SKILL.md) guides a
human-in-the-loop process to consolidate fragments into stable outputs:
- Complete SKILL.md files
- Permanent prompt rules
- Curated KB documents

A hook reminds the user when fragments reach a threshold.

## Structure

```
fungus/
├── SKILL.md              # Distill skill (human-in-the-loop)
├── hooks/
│   └── distill-reminder.py
├── prompts/
│   ├── extract-common.md # Shared definitions (input format, scoring)
│   ├── extract-skill.md  # Skill extractor prompt
│   ├── extract-kb.md     # Knowledge extractor prompt
│   └── extract-rule.md   # Rule extractor prompt
├── agents/
│   ├── skill-extractor.json
│   ├── kb-extractor.json
│   └── rule-extractor.json
├── _memory.py            # DB operations CLI
├── run-extraction.py     # Cron scheduler
├── data/                 # Exported .md files (gitignored)
└── install.sh
```

## Install

```bash
bash install.sh
```

This copies files to `~/.kiro/skills/github/fungus/`, installs agent
configs to `~/.kiro/agents/`, and adds a cron job (every 5 min).

## License

MIT
