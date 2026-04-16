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
| **Hypha** | Sense signals from user, agent, and environment | Every interaction |
| **Mycelium** | Digest spores into structured nutrients | Session end |
| **Fruit** | Detect mature patterns, produce new skills | Session end |

No manual intervention. The network grows silently in the background.

### Sensing Dimensions

Hyphae don't sense blindly — each hook is a different kind of soil:

| Soil | Hook | What Hyphae Detect |
|------|------|--------------------|
| **User** | `user-prompt-submit` | Habits, preferences, corrections, communication patterns |
| **Agent** | `pre-tool-use` | Decision logic, tool selection, reasoning paths |
| **Environment** | `post-tool-use` | Tool failures, gotchas, environment limitations |

Three dimensions — user, agent, environment — give the network a complete picture
of every interaction.

### Data Flow

Nutrients flow in one direction — from raw spores to mature network memory:

```
spores → nutrients → fruiting → network
  ↑          ↑           ↑          ↑
Hypha      Mycelium     Fruit    agent-spawn
writes     writes       writes   reads
```

Each module writes to its own partition in the agent's `memory.json`.
Memory is per-agent — each agent configured in `~/.kiro/agents/` gets its own
`data/agents/<name>/memory.json`, so multiple agents can run concurrently
without conflict. Boundaries are declared in each script's annotations —
no central config:

```python
# @hook post-tool-use
# @priority 10
# @module hypha
# @writes spores
# @description Sense tool errors from environment
```

The substrate scans these annotations at runtime to enforce permissions.

## 🍄 Grown Skills

Skills are the mushrooms — visible outputs of the underground network.

| Skill | Description |
|-------|-------------|
| [docx-toolkit](skills/docx-toolkit/) | JSON-based surgical editing for `.docx` files |

## 📁 Structure

```
fungus/
├── assets/                      Images
├── data/
│   └── agents/<name>/           Per-agent memory (gitignored)
│       └── memory.json
├── hooks/
│   ├── substrate.sh             Signal conductor — routes hooks to modules
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
│   └── docx-toolkit/
├── prompts/                     Shared prompt frameworks
├── install.sh
└── LICENSE
```

## 📄 License

[MIT](LICENSE)
