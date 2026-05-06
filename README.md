# Code-First Probe-Driven Development

Agents speak code. Developers speak code. Specs were invented to communicate between humans; probes are for communication between humans and agents.

Code-First Probe-Driven Development is a project management and software development workflow that never leaves code. A software idea starts as a short README description, becomes an executable architectural probe, and then evolves through ordered evolutions anchored by `TODO(EVO-...)` markers at the exact code locations where the work belongs.

The codebase is the source of truth. The README explains intent. The probe shows architecture. The ordered evolutions are the plan.

An evolution is not just one line of text. It is closer to an issue in an issue tracker, but code-local: the `TODO(EVO-...)` line gives the ID, order, and short title; the surrounding code, names, comments, types, tests, and optional linked BDD feature file provide the context needed to apply it.

For the process foundations, rules, and glossary, see [pdd/README.md](pdd/README.md).

## The Probe Development Toolkit

This repository defines the command toolkit needed to practice Probe-Driven Development.

The toolkit gives developers and agents a deterministic view of the code-local project plan:

- list the ordered implementation plan from code
- add a new ordered evolution with a unique ID
- identify pending evolutions that do not have valid unique IDs

The toolkit exists to keep the project-management state inside the codebase. Agent-shaped activities such as discussion, challenge, refinement, and applying evolutions belong in coding agents that can read and edit the project with judgment.

## Product behavior

Canonical product behavior is described in [`features/`](features/).

The `.feature` files are the source of truth for what the software does. They are product specifications first and executable BDD scenarios second.

Implementation progress is tracked by probe evolutions by referencing stable feature and scenario IDs

## Commands

### `probedev list`

List the ordered probe plan.

This command scans the codebase for `TODO(EVO-...)` markers and prints pending evolutions grouped by source file.

Expected outcome:

- pending evolutions grouped by file
- current first unapplied evolution highlighted
- warnings for malformed IDs or duplicate IDs

### `probedev add`

Add one ordered evolution to the code-local probe plan.

This command records a `TODO(EVO-...)` marker without applying the work. It requires a source file and an evolution description, assigns the next unique ID in the default sequence, and appends the marker to the end of the requested file.

Expected outcome:

- a new ordered evolution marker
- a unique ID chosen by the tool
- marker placement at the end of the requested file
- the probe plan remains ordered and reviewable

### `probedev identify`

Assign stable unique IDs to existing evolution markers that are missing IDs, use placeholders, use invalid IDs, or conflict with another marker.

This command updates marker syntax without applying the work. It preserves descriptions and file placement while making the plan addressable through `EVO-XXX` IDs.

Expected outcome:

- every pending evolution has a valid unique `EVO-XXX` ID
- existing valid unique IDs are left unchanged
- identified evolutions remain visible through `probedev list`

## TODO Syntax

Evolutions are ordered and code-local. Each evolution is anchored by a searchable marker:

```text
TODO(EVO-010): Add persistent storage behind MovieRepository.
TODO(EVO-020): Replace in-memory movie list with repository-backed state.
TODO(EVO-030): Add edit and remove flows to the existing movie UI.
```

Rules:

- use `TODO(EVO-010)` as the default syntax
- use zero-padded numbers so lexical sorting matches execution order
- number by tens to leave space for insertions
- write the marker as a short issue title, not the whole issue body
- rely on nearby code context to carry the details needed to apply the evolution
- place each marker where the work belongs
- update evolutions as the software changes

Use one ordered `EVO-XXX` sequence for the current agreed scope. If the project has multiple independent architectural fronts, keep them in the same sequence and make the scope clear in the marker title and nearby code.

## Core Requirements

The toolkit must preserve these requirements:

- code is the primary artifact
- README describes intent, not implementation details
- probes are executable
- probes live inside the real codebase
- evolutions are ordered
- `probedev list` reads the plan from code
- `probedev add` records one new planned evolution
- `probedev identify` assigns valid unique IDs to existing planned evolutions
- coding agents perform nondeterministic workflow actions such as discussion, challenge, refinement, and applying evolutions
- completion means no `TODO(EVO-...)` markers remain for the current agreed scope
