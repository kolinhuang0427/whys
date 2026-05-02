# Whys — annotate code with reasons

A local-only code annotation tool that lets you attach a human-readable "why" to any function or line of code. When you hit a confusing piece of code, `whys explain <function>` tells you what the original author was thinking. Stored in `.whys/` locally — no server, no git hooks, no sharing required.

## The problem

Code tells you *what* it does. Git blame tells you *when* and *who*. But neither tells you *why* — the reasoning, constraints, business rules, and context that shaped the implementation. Six months later, you spend hours reconstructing why something is the way it is.

## How it works

```bash
# Annotate a function with a reason
whys add src/auth.py:validate_token "Legacy JWT format from v1 auth — remove after migration"

# Ask why code exists
whys explain src/auth.py:validate_token
# → Legacy JWT format from v1 auth — remove after migration

# List all your annotations
whys list src/

# Show all whys in a file (overlay mode)
whys show src/auth.py

# Search annotations
whys search "migration"
```

## Annotation storage

Annotations live in `.whys/<relative_path>.yaml` — one file per annotated source file. Each entry stores:

- `function` or `line` range
- `reason` (free text)
- `author` (git user if available)
- `created` (ISO timestamp)
- `tags` (optional)

## Installation

```bash
pip install -e .
```

## Editor integration

VS Code: `.vscode/extensions.json` → install "Whys" extension when published.

## Security

`.whys/` is gitignored by default. Reasons can contain sensitive context — keep it local.