# locale/ — source of truth for the RiveScript brain

The `ovos_solver_rivescript_plugin/locale/` tree is the canonical, human-editable
source of conversational content.  A CI workflow compiles it into RiveScript
brain files after every merge to `dev`; contributors never write `.rive` directly.

## File format

Each conversational pair is two files with a shared base name:

| File | Purpose |
|------|---------|
| `<name>.intent` | One trigger utterance per line (what the user says) |
| `<name>.dialog` | One response per line (what the bot replies, chosen at random) |

### The `{query}` slot

Use `{query}` wherever the RiveScript wildcard (`*`) would appear.  The compiler
maps it back to `*` in the trigger and to `<star>` in the response:

```
# hello_what_is.intent
hello what is {query}

# hello_what_is.dialog
I think {query} is pretty interesting.
You're asking about {query}? Let me think…
```

Compiles to:

```
+ hello what is *
- I think <star> is pretty interesting.
- You're asking about <star>? Let me think…
```

Multiple response lines become a random set (the bot picks one per reply).  
Multiple trigger lines in the same `.intent` compile to a canonical trigger plus
`@` redirects for the extras.

## Adding an intent

1. Pick a descriptive base name, e.g. `do_you_dream`.
2. Create `locale/en-us/do_you_dream.intent` — one utterance per line.
3. Create `locale/en-us/do_you_dream.dialog` — one response per line.
4. Open a PR to `dev`.  The `regenerate-brain` CI job runs on merge and updates
   `brain/en-us/generated.rive` automatically.

You do **not** need to touch any `.rive` file.

## Translating to a new language

1. Copy the entire `locale/en-us/` tree to `locale/<lang>/`
   (e.g. `locale/pt-pt/`, `locale/de-de/`).
2. Translate the text in each file.  Keep `{query}` verbatim — do not translate
   the slot marker.
3. Open a PR to `dev`.  CI regenerates `brain/<lang>/generated.rive`.

## The regenerate-on-merge CI flow

`.github/workflows/regenerate-brain.yml` runs on every push to `dev` (and on
`workflow_dispatch`).  It loops over every `locale/<lang>/` directory, calls

```
python scripts/locale_to_brain.py rivescript locale/<lang> brain/<lang>/generated.rive
```

and commits the result back to `dev` only when files actually changed (idempotent:
a second run without locale edits produces no commit).  Pushing to `dev` does not
trigger the release workflow (which fires only on PR close → `dev`), so no loop.

## Supported constructs

| Construct | Supported | Notes |
|-----------|-----------|-------|
| Plain trigger | ✓ | Normalised to lower-case |
| Single wildcard `*` / `_` → `{query}` | ✓ | Mapped bidirectionally |
| `<star>` / `<star1>` in response | ✓ | Compiled back from `{query}` |
| Multiple responses (random) | ✓ | All lines in `.dialog` |
| Multiple triggers per intent | ✓ | Extra triggers become `@` redirects |
| `%` previous-input | ✗ | Skipped at conversion; stays in legacy `.rive` |
| `@` redirect (as source) | ✗ | Skipped |
| `{topic}` / topic blocks | ✗ | Skipped |
| `<call>` / object macros | ✗ | Skipped |
| Arrays `(@array)` | ✗ | Skipped |
| Multi-capture `<star2>`, `<star3>` … | ✗ | Skipped |

Triggers that use unsupported constructs remain in the legacy `.rive` files under
`brain/en-us/` and are loaded alongside `generated.rive`.
