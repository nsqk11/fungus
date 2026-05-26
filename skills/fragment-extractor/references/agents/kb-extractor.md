{
  "name": "kb-extractor",
  "description": "Extracts knowledge base entries from session transcripts.",
  "prompt": "",
  "tools": ["read", "shell"],
  "allowedTools": ["read", "shell"],
  "resources": [
    "file://FUNGUS_ROOT/skills/fragment-extractor/references/extract-kb.md",
    "file://FUNGUS_ROOT/skills/fragment-extractor/references/extract-common.md"
  ],
  "hooks": {},
  "toolsSettings": {},
  "model": "claude-sonnet-4.6"
}
