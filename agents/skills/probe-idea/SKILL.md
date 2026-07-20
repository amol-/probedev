---
name: probe-idea
description: Create or refine a small executable architectural probe with a complete, tool-verified evolution path to graduation.
---

# Probe and evolve

Use this skill when the user wants to test an architectural direction before building the full feature.

A **probe** is small, real, runnable code in the target codebase. It is an architectural hypothesis: it makes the proposed entrypoint, modules, types, functions, responsibilities, and collaboration visible so a reviewer can decide whether the structure belongs in this codebase.

A probe is not a design document, detached demo, mock-only prototype, or a partial full implementation. It may use fake business behavior, but its boundaries and wiring must be real enough to reveal how the system would work.

An **evolution** is one small future change. Its active anchor is `TODO(EVO-###)`, created by `probedev`. Together, the active evolutions are the complete high-level plan from the probe to the agreed feature's production-ready implementation. **Graduation** means that agreed scope is real software and has no active `TODO(EVO-###)` markers.

## Build the architectural probe

Before editing, state in one sentence:

- **Feature goal:** the requested user-visible result.
- **Architectural question:** what the probe must reveal about fit, boundaries, ownership, or integration.

Build the smallest runnable slice that answers that question:

- use the real codebase and its natural entrypoint;
- reuse existing routing, storage, UI, CLI, and test infrastructure when it exists;
- create the real names, modules, types, and function signatures being evaluated;
- wire the collaborators through their real integration points; and
- implement only the shortest happy path needed to make that collaboration observable.

Use a small stub when a function's internal logic is not what the probe is testing. A stub may return a fixed value, use in-memory state, or implement only a happy path so the probe runs.

Do not fake the connections between components. The real entrypoint must call the real classes, functions, modules, and integration points that the probe is evaluating. For example, a CLI may call a real `NoteService`, which calls a real `NoteStore`; the store may keep notes in memory instead of a database. Do not make the CLI print a result directly and skip `NoteService` or `NoteStore`.

Focus on structure, not algorithm details. The probe should let a reviewer quickly see which components exist, who owns each responsibility, and how control and data move between them. Put unfinished business rules, persistence, validation, error handling, retries, configuration, migrations, performance work, and broad test coverage into evolutions unless one is the architectural question itself.

Do not build the full feature. Do not add speculative abstractions, broad configuration, compatibility layers, or unrelated refactoring. Verify the probe with one focused command, smoke test, or happy-path test.

## Add evolutions where their code will change

Make a short checklist of every capability, integration point, and production concern named by the user or requirement. Before finishing, every item must map to either:

- executable probe behavior, or
- exactly one active evolution at the code location that will change.

For every evolution with a known code owner, use `probedev add` with the file and the first line of the smallest code block that owns the future change:

```bash
probedev add path/to/codefile.ext:LINE "Short, specific title"
```

Choose the block by scope:

- use a function, method, class, type, route, or command declaration when the whole component must evolve;
- use an `if`, loop, or other nested block when only that block must evolve; and
- for a new component placeholder, omit `:LINE` so the first evolution is appended at the end of its new file.

`add` inserts the evolution immediately before the chosen block. Do not choose an arbitrary inner statement or call site unless that exact statement is the work to evolve.

First locate the target from the project root, for example:

```bash
nl -ba path/to/codefile.ext
```

Use that displayed relative path and line. Do not guess a path or retry alternate paths. Run exactly one `add` command for that evolution.

`probedev add` creates the correctly formatted, positioned anchor and allocates its ID. After it succeeds, use the returned ID. Do not add another anchor, invent an ID, or move the generated anchor. Extend that generated evolution with a self-contained body:

```text
TODO(EVO-010): Short, specific title
Why:
- Why this gap exists at this location and how it relates to the probe.
Done:
- Concrete observable completion signal.
Non-Goals:
- Explicit work this evolution must not add.
```

Each evolution is one independently actionable, high-level step. Its `Why`, `Done`, and `Non-Goals` state the purpose, finish line, and boundary; they do not prescribe algorithms or a file-by-file implementation. Split “implement the rest” into ordered steps. Do not implement an active evolution in the same change that creates it.

Never pass a directory when a known file, type, function, method, class, route, or code block owns the work. Do not use a bare source-file target for existing code-owned work: choose the line beside the block that will change. A newly created component placeholder is the exception because it has no block yet.

Use a directory target only when no code unit can own the work, such as a project-wide external operational decision. Then and only then use:

```bash
probedev add path/to/directory "Short, specific project-level title"
```

This creates `path/to/directory/Evolutions.txt`. It is an exception, not a shortcut for an unknown or inconvenient code location. For a new source file, create the smallest honest placeholder and run `probedev add newfile.ext "title"` without `:LINE`.

## Verify the active plan

Run commands from the target project root, or pass its path with `--root`.

- `probedev add file.ext:LINE "title"` is the default for code-owned work.
- `probedev add DIR "title"` is only for work with no code owner.
- `probedev identify` repairs missing, invalid, placeholder, or duplicate IDs.
- `probedev show EVO-010` opens a pending evolution at its anchor.
- `probedev list` audits the active plan.
- `probedev done EVO-010` closes an implemented evolution.

Before reporting a new or refined probe, run:

```bash
probedev list --short
```

Check all of these, not just the exit status:

1. Every expected active ID appears exactly once.
2. No unexpected active ID appears.
3. The output has no malformed-marker or duplicate-ID warning.
4. Listed files are the intended code owners. `Evolutions.txt` appears only for genuinely ownerless project work.
5. Comparing the list with the requirement checklist shows every known step needed to turn the probe into the agreed production-ready feature.

If any check fails, fix the plan and run `probedev list --short` again. Inspect normal `probedev list` to confirm every evolution has its title, `Why`, `Done`, and `Non-Goals` body.

## Apply one evolution

If the user says “do EVO-010” (or equivalent):

1. Use `probedev show EVO-010` or `probedev list` to find its anchor.
2. Implement only that evolution's `Done` criteria. Respect its `Non-Goals`.
3. Run focused verification.
4. Run `probedev done EVO-010`. It must print `Marked evolution as done`.
5. Do not delete or rename the marker yourself. If `done` fails, fix the problem and run it again.
6. Run `probedev list --short` and confirm `EVO-010` is absent while every still-unimplemented expected evolution remains.

Do not implement neighboring evolutions merely because their code is nearby.

## Final review

Before completion, confirm:

- The probe runs through a realistic entrypoint.
- A reviewer can understand the proposed components, responsibilities, boundaries, and main flow in minutes.
- Every agreed-scope item, including known production-readiness work, is executable probe behavior or one complete code-local evolution.
- The active evolutions form the complete high-level plan from this probe to the agreed production-ready feature.
- `probedev list --short` exactly matches that plan with no warnings.

Report only the runnable slice, entrypoint and verification command, and major omissions already represented by active evolutions.
