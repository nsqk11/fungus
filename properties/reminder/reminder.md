# Reminder

Context-aware reminders are injected into your prompt automatically before you respond.

## How it works

- On each user message, a classifier analyzes the content and selects relevant reminders.
- Matched reminders appear as XML tags (e.g. `<memory-reminder>`, `<todo-reminder>`).
- A separate rule-based hook detects consecutive tool failures and injects `<failure-warning>`.

## What you do

- When you see a reminder tag, follow its instruction before proceeding.
- Do not mention or explain the reminder system to the user.
