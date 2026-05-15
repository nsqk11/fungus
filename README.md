# Fungus

General-purpose AI coding agent with persistent memory, built on
[Kiro CLI](https://github.com/kirolabs/kiro).

## Features

- **Persistent memory** — a background pipeline extracts reusable
  knowledge from every interaction and stores it in a searchable
  knowledge base.
- **Drop-in skills** — extend behavior by adding skill directories
  from the community or your own.
- **Single-entry hook router** — one script dispatches all hook events
  to annotated handlers by priority.

## Requirements

- [Kiro CLI](https://github.com/kirolabs/kiro)
- Python ≥ 3.10
- Git

## Install

```bash
git clone https://github.com/youruser/fungus.git
cd fungus
bash install.sh
kiro-cli chat --agent fungus
```

## Structure

```
hooks/
├── router.py             # Hook dispatcher
├── _event.py             # Events DB library
├── _memory.py            # Memory DB library
├── spawn_extractor.py    # Memory extraction trigger
└── extract_cli.py        # Extraction CLI tool
prompts/
├── system-prompt.md      # Agent system prompt
└── extract-criteria.md   # Memory extraction rules
install.sh                # Installer
```

## License

MIT
