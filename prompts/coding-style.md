# Coding Style

Code standards for the Fungus repository.

## Style Guide

Apply [Google Style Guide](https://google.github.io/styleguide/)
for the corresponding language:

- [Python](https://google.github.io/styleguide/pyguide.html)
- [Shell](https://google.github.io/styleguide/shellguide.html)

When Google Style does not cover a case, choose the more readable option.

## Design Principles

Apply these principles to all code.

### KISS — Keep It Simple

Write the simplest solution that works.
If code needs a comment to explain *what* it does (not *why*),
refactor until it speaks for itself.

### YAGNI — You Aren't Gonna Need It

Do not build for hypothetical future requirements.
Implement what is needed today.
Simple code is easy to change when the future arrives.

### DRY — Don't Repeat Yourself

Give every piece of knowledge a single, authoritative representation.
If the same logic appears twice, extract it.
If the same constant appears twice, name it.

### SoC — Separation of Concerns

Give each file, function, and module one reason to change.
Keep parsing, logic, and I/O in separate functions.
Split a module that does two things.

### SOLID

- **Single Responsibility**: one function, one job.
- **Open/Closed**: extend through composition, not modification.
- **Liskov Substitution**: honor the same contract.
- **Interface Segregation**: depend on narrow interfaces.
- **Dependency Inversion**: depend on abstractions.

### LoD — Law of Demeter

Only talk to direct dependencies.
Pass data, not deep object graphs.
If you see `a.b.c.d`, refactor.

### COI — Composition Over Inheritance

Build behavior by combining small, focused functions.
Prefer has-a over is-a.
Do not use class inheritance for code reuse.

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <short summary>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`.
Write in imperative mood, lowercase, no period, max 72 characters.
