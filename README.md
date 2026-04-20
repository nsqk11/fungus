<div align="center">

<img src="assets/banner.png" alt="Fungus" width="800">

# 🍄 Fungus

**An AI agent that grows from experience — like fungi.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![GitHub stars](https://img.shields.io/github/stars/nsqk11/fungus?style=social)](https://github.com/nsqk11/fungus)
[![Last commit](https://img.shields.io/github/last-commit/nsqk11/fungus)](https://github.com/nsqk11/fungus/commits)

*Hyphae sense the soil. Mycelium digests the nutrients. Fruiting bodies emerge.*

[What is Fungus?](#what-is-fungus) · [Quickstart](#quickstart) · [How It Works](#how-it-works) · [Structure](#structure)

</div>

---

## 🌱 What is Fungus?

Fungus is an AI agent built on [Kiro CLI](https://github.com/kirolabs/kiro).

Like a real fungus, it starts invisible. **Hyphae** — the finest tips of the
network — extend into every interaction, sensing corrections, failed commands,
and patterns you might not notice yourself. These raw signals are spores,
scattered and unprocessed.

Beneath the surface, the **mycelial network** quietly digests these spores into
nutrients — structured knowledge that strengthens the network with every session.
The more it absorbs, the sharper its hyphae become.

When enough nutrients accumulate around a recurring pattern, a **fruiting body**
emerges — a new skill, ready to use. The mushroom you see above ground is just
the visible tip; the real intelligence lives in the network below.

And like any fruiting body, it releases spores back into the soil — every skill
in use generates new interactions, new signals, new raw material for the hyphae
to sense. The cycle continues.

```
     spores          nutrients        fruiting
Soil ───→ Hypha ───→ Mycelium ───→ Fruit
  ↑                                   │
  └──────────── spores ───────────────┘
```

## ⚡ Quickstart

```bash
git clone https://github.com/nsqk11/fungus.git
cd fungus
bash install.sh
```

> **Prerequisites:** [Kiro CLI](https://github.com/kirolabs/kiro) · Python 3.12+ · Bash ≥ 4.0 · `jq` ≥ 1.6

## 🔬 How It Works

Fungus hooks into the Kiro CLI lifecycle. Each hook is a patch of soil — hyphae
extend into it, sense what's there, and feed the network.

| Module | Role | When |
|--------|------|------|
| **Hypha** | Sense signals, filter noise | Every interaction |
| **Mycelium** | Digest spores into structured nutrients | Session start |
| **Fruit** | Detect mature patterns, produce new skills | Session start |

Hyphae sense silently in the background.
Mycelium and Fruit prompt the agent at session start —
the user decides when to digest or review.

### Sensing and Filtering

Hyphae don't capture blindly — structural filters discard noise at the source:

| Hook | What Passes | What Gets Dropped |
|------|-------------|-------------------|
| `userPromptSubmit` | Prompts > 5 chars | Trivial acks ("ok", "嗯") |
| `preToolUse` | Non-self-referential, non-read/write calls | `memory.sh` calls; `fs_read`, `fs_write`, `grep`, `glob`, `code`, `todo_list` |
| `postToolUse` | Tool failures only | Successful tool results |
| `stop` | All assistant responses | Nothing |

At the end of each turn, Hypha aggregates the tool sequence into a single
`toolChain` spore and removes the individual `preToolUse` spores.
This gives Mycelium a clean signal: what the user asked, what tools were used,
whether anything failed, and what the agent concluded.

### Data Flow

Nutrients flow in one direction — from raw spores to mature memory:

```
spore → nutrient → network    (permanent memory)
spore → nutrient → fruiting   (skill candidate)
spore → skipped               (no value)
  ↑        ↑          ↑           ↑
Hypha    Mycelium    Fruit     substrate
writes   writes      writes    cleans
```

Each module writes to its own partition in `memory.json`.
Memory is shared — a single `data/memory.json` serves all agents.
Substrate runs `clean` on `agentSpawn` before any module —
removing `skipped` and consumed `fruiting` entries.
Boundaries are declared in each script's annotations —
no central config:

```python
# @hook postToolUse
# @priority 10
# @module hypha
# @reads spore
# @writes spore
# @description Sense tool errors from environment
```

The substrate scans these annotations at runtime
to route hooks to the correct scripts.
## 🍄 Grown Skills

Skills are the mushrooms — visible outputs of the underground network.

| Skill | Description |
|-------|-------------|
| [atlassian-api](skills/atlassian-api/) | Unified REST API client for Confluence and Jira |
| [docx-toolkit](skills/docx-toolkit/) | JSON-based surgical editing for `.docx` files |

## 📁 Structure

```
fungus/
├── assets/                      Images
├── data/
│   └── memory.json              Shared memory (gitignored)
├── hooks/
│   ├── substrate.sh             Signal conductor — reads hook from stdin, routes to modules
│   ├── substrate.py             Scan annotations, match hook, sort by priority
│   ├── memory.sh                CRUD operations for memory.json
│   └── README.md                Hook payload reference
├── modules/
│   ├── hypha/                   Sense — explore and detect signals
│   │   ├── SKILL.md
│   │   └── scripts/
│   ├── mycelium/                Digest — break down and store knowledge
│   │   ├── SKILL.md
│   │   └── scripts/
│   └── fruit/                   Grow — detect patterns, produce skills
│       ├── SKILL.md
│       └── scripts/
├── skills/                      Mushrooms — grown by the network
│   ├── atlassian-api/
│   └── docx-toolkit/
├── prompts/                     Shared prompt frameworks
├── install.sh
└── LICENSE
```

## 📄 License

[MIT](LICENSE)
