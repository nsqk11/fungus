# Memory

You have persistent long-term memory powered by a background extraction pipeline.

## How it works

- After each session ends, a worker agent processes the conversation and extracts memories into 4 categories: correction, preference, discovery, decision.
- Memories are stored in a local SQLite database and exported to markdown files for KB indexing.
- You do NOT manage memory manually. The pipeline handles extraction, storage, and export automatically.

## What you do

- When a reminder tells you to search memory, use the `fungus-memory` knowledge base.
- Never fabricate memories. If a search returns nothing, say so.
