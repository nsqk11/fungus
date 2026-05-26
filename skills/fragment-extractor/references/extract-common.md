# Common Definitions

## Input format

The conversation is in JSONL format. Each line is a JSON object with a
`kind` field:

- **"Prompt"**: User message. Found in `data.content`.
- **"AssistantMessage"**: Agent response. Found in `data.content`.
- **"ToolResults"**: Output from tools the agent invoked. Found in `data.content`.

A single conversation may cover zero, one, or many topics and tasks.

## Scoring dimensions

Every extracted item must include three scores, each 0.0 to 1.0:

### x_knowledge — Is this a standalone fact?

- 1.0: Pure fact, true regardless of any task context ("CT50 has 2 Squid chips")
- 0.5: Has factual content but needs context to be meaningful ("kickoff email uses Review Invitation template")
- 0.0: No factual content — pure instruction or preference ("use Chinese")

### y_rule — Is this an unconditional behavioral constraint?

- 1.0: Applies in any scenario, no task or topic dependency ("never ask for confirmation, just do it")
- 0.5: Applies within a class of scenarios ("when writing documents, don't compare with old versions")
- 0.0: Not a behavioral constraint — it's knowledge or a task step

### z_task — Is this bound to a specific nameable task?

- 1.0: Meaningless outside this task ("step 3: fill Required invitee as TC")
- 0.5: Useful across a few related tasks ("all CSIM documents follow WRITING.md")
- 0.0: Completely general, no task binding ("user's timezone is CET")
