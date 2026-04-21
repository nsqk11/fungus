# Hooks

Infrastructure for the Fungus agent.

## Hook Payloads

Each hook receives a JSON payload via stdin from Kiro CLI.

### agentSpawn

```json
{
  "hook_event_name": "agentSpawn",
  "cwd": "/current/working/directory"
}
```

### userPromptSubmit

```json
{
  "hook_event_name": "userPromptSubmit",
  "cwd": "/current/working/directory",
  "prompt": "user's input text"
}
```

### preToolUse

```json
{
  "hook_event_name": "preToolUse",
  "cwd": "/current/working/directory",
  "tool_name": "fs_read",
  "tool_input": {}
}
```

### postToolUse

```json
{
  "hook_event_name": "postToolUse",
  "cwd": "/current/working/directory",
  "tool_name": "fs_read",
  "tool_input": {},
  "tool_response": {}
}
```

### stop

```json
{
  "hook_event_name": "stop",
  "cwd": "/current/working/directory",
  "assistant_response": "the assistant's complete response text"
}
```

## Scripts

| Script | Role |
|--------|------|
| `substrate.sh` | Thin shell — routes hooks to module scripts |
| `substrate.py` | Core — scan annotations, match hook, sort by priority |
| `memory.py` | CRUD operations for `memory.db` |
