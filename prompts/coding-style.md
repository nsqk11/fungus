# Coding Style

Code standards for the Fungus repository.

## Style Guide

Follow [Google Style Guide](https://google.github.io/styleguide/) for the
corresponding language:

- [Python](https://google.github.io/styleguide/pyguide.html)
- [Shell](https://google.github.io/styleguide/shellguide.html)

When Google Style does not cover a case, prefer readability over cleverness.

## Design Principles

Seven principles govern all code in this repository. Listed in order of
priority — when two principles conflict, the higher one wins.

### 1. KISS — Keep It Simple

Write the simplest solution that works. If a piece of code needs a comment to
explain *what* it does (not *why*), it is too complex. Refactor until the code
speaks for itself.

### 2. YAGNI — You Aren't Gonna Need It

Do not build for hypothetical future requirements. Implement what is needed
today. When the future arrives, refactor — simple code is easy to change.

### 3. DRY — Don't Repeat Yourself

Every piece of knowledge should have a single, authoritative representation.
If the same logic appears twice, extract it. If the same constant appears
twice, name it.

### 4. SoC — Separation of Concerns

Each file, function, and module should have one reason to change. Parsing,
logic, and I/O belong in separate functions. A module that does two things
should be two modules.

### 5. SOLID

- **Single Responsibility**: one function, one job.
- **Open/Closed**: extend behavior through composition, not modification.
- **Liskov Substitution**: substitutable components must honor the same contract.
- **Interface Segregation**: depend on narrow interfaces, not broad ones.
- **Dependency Inversion**: depend on abstractions, not concrete implementations.

### 6. LoD — Law of Demeter

A function should only talk to its direct dependencies. Pass data, not deep
object graphs. If you see `a.b.c.d`, something is wrong.

### 7. COI — Composition Over Inheritance

Build behavior by combining small, focused functions — not by inheriting from
base classes. Prefer has-a over is-a.

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <short summary>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`.
Summary: imperative mood, lowercase, no period, max 72 characters.
