# Coding Standards

Project-specific coding conventions for the Fungus repository.

## Scope

Applies to all code written in this repository, regardless of language.
Supplements but does not replace the Google Style Guide.

## Authority

Defer to the Google Style Guide (indexed as a knowledge base) for
language-specific rules: naming, layout, formatting, and idioms.
Search the KB when in doubt for the target language.

This file defines only the design principles and commit conventions
that are specific to Fungus and not covered by the upstream guide.

## Design Principles

Apply these to all code. Each principle has one-line definition and
one-line smell test.

### KISS — Keep It Simple

Write the simplest solution that works.
Smell: code needs a comment to explain *what* it does, not *why*.

### YAGNI — You Aren't Gonna Need It

Implement what today's requirement needs. No hypothetical hooks.
Smell: a parameter or abstraction with no current caller.

### DRY — Don't Repeat Yourself

Give every piece of knowledge a single authoritative representation.
Smell: the same constant or logic appears twice.

### SoC — Separation of Concerns

Give each file, function, and module one reason to change.
Smell: parsing, business logic, and I/O live in the same function.

### SOLID

- **S**ingle Responsibility: one function, one job.
- **O**pen/Closed: extend through composition, not modification.
- **L**iskov Substitution: honor the same contract.
- **I**nterface Segregation: depend on narrow interfaces.
- **D**ependency Inversion: depend on abstractions.

### LoD — Law of Demeter

Only talk to direct dependencies. Pass data, not deep object graphs.
Smell: `a.b.c.d` — refactor.

### CoI — Composition over Inheritance

Build behavior by combining small, focused functions.
Smell: class inheritance used for code reuse rather than subtyping.

## Commit Messages

Use Conventional Commits.

```
<type>: <short summary>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`.
Imperative mood, lowercase, no period, max 72 characters.
