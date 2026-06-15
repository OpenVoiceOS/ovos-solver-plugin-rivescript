# Converter scripts

Two stdlib-only scripts (no third-party dependencies) handle round-trip
conversion between OVOS `locale/` notation and RiveScript / AIML brain files.

## `scripts/brain_to_locale.py` — brain → locale

Converts an existing `.rive` or `.aiml` brain directory into OVOS `locale/`
intent/dialog pairs.  Run once to bootstrap a `locale/` tree from a legacy brain.

```
python scripts/brain_to_locale.py rivescript <rive_dir>   <out_locale_dir>
python scripts/brain_to_locale.py aiml       <aiml_dir>   <out_locale_dir>
```

**Example — bootstrap English locale from the bundled brain:**

```bash
python scripts/brain_to_locale.py \
    rivescript \
    ovos_solver_rivescript_plugin/brain/en-us \
    ovos_solver_rivescript_plugin/locale/en-us
# rivescript: converted 134/255 entries (52%), skipped 121 (unmappable constructs) -> …/locale/en-us
```

The ~52 % conversion rate reflects the fact that roughly half the triggers in the
original brain use constructs (`%`, `@`, `{topic}`, `<call>`, arrays, multi-star)
that have no direct OVOS equivalent.  Those 121 entries are **not deleted** — they
remain in the legacy `.rive` files and continue to be loaded by the engine.

## `scripts/locale_to_brain.py` — locale → brain

The reverse direction.  This is what the CI workflow calls after every merge to
`dev`.

```
python scripts/locale_to_brain.py rivescript <locale_dir> <out.rive>
python scripts/locale_to_brain.py aiml       <locale_dir> <out.aiml>
```

**Example — regenerate brain from locale (all pairs → one file):**

```bash
python scripts/locale_to_brain.py \
    rivescript \
    ovos_solver_rivescript_plugin/locale/en-us \
    ovos_solver_rivescript_plugin/brain/en-us/generated.rive
# rivescript: compiled 134 intents from …/locale/en-us -> …/brain/en-us/generated.rive
```

## Round-trip behaviour

```
locale/en-us/  →(locale_to_brain)→  brain/en-us/generated.rive
                ←(brain_to_locale)← brain/en-us/generated.rive
```

The round-trip is lossless for the supported subset:

- `{query}` slot ↔ `*` trigger wildcard ↔ `<star>` response tag.
- Multiple `.dialog` lines ↔ multiple `- response` lines (random set).
- Multiple `.intent` lines ↔ canonical trigger + `@` redirect lines.

A second call to `locale_to_brain.py` with no locale edits produces an identical
`.rive` file (idempotent).

## The ~52 % conversion caveat

`brain_to_locale.py` skips any trigger/response pair that involves:

- `%` previous-input constraints
- `@` redirect targets (as the *source* of a redirect)
- `{topic=…}` topic switches
- `<call>` object macros
- `(@array)` array references
- `<star2>` / `<star3>` multi-capture (more than one wildcard)

These entries stay in the original `.rive` files.  The engine loads **both** the
legacy files and `generated.rive`, so nothing is lost.

New content added via `locale/` will have 100 % round-trip fidelity as long as
authors stick to the supported constructs documented in [`locale.md`](locale.md).
