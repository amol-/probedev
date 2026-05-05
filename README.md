# Code-First Probe-Driven Development

Agents speak code. Developers speak code. Specs were invented to communicate between humans; probes are for communication between humans and agents.

Code-First Probe-Driven Development is a project management and software development workflow that never leaves code. A software idea starts as a short README description, becomes an executable architectural probe, and then evolves through ordered evolutions anchored by `TODO(PROBE-...)` markers at the exact code locations where the work belongs.

The codebase is the source of truth. The README explains intent. The probe shows architecture. The ordered evolutions are the plan.

An evolution is not just one line of text. It is closer to an issue in an issue tracker, but code-local: the `TODO(PROBE-...)` line gives the ID, order, and short title; the surrounding code, names, comments, types, tests, and optional linked BDD feature file provide the context needed to apply it.

For the process foundations, rules, and glossary, see [pdd/README.md](pdd/README.md).

## The Probe Development Toolkit

This repository defines the command toolkit needed to practice Probe-Driven Development.

The toolkit should help a developer and agent move through the full lifecycle:

- discuss the software intent without prematurely choosing technical design
- refine that intent into executable architecture
- challenge the code-local plan against the README
- list the ordered implementation plan from code
- apply one evolution at a time

The toolkit exists to keep agents inside the Probe-Driven Development workflow. It should prevent common failure modes: writing architecture documents instead of code, creating detached prototypes, overbuilding production features too early, losing the implementation order, and letting TODO markers become stale.

## Product behavior

Canonical product behavior is described in [`features/`](features/).

The `.feature` files are the source of truth for what the software does. They are product specifications first and executable BDD scenarios second.

Implementation progress is tracked by probe evolutions by referencing stable feature and scenario IDs

## Commands

### `probe discuss`

Challenge and improve the README description.

This command works on the product idea, not the architecture. It asks about users, workflows, value, scope, constraints, and completion. It should avoid technical questions unless they block understanding the software.

Expected outcome:

- a clearer README-level software description
- no code changes unless the user explicitly asks to continue into a probe

### `probe refine`

Create or evolve an architectural probe.

This command reads the README and the current codebase, then updates the executable probe and its ordered probe plan.

It must handle all project states:

- no codebase yet: create the first executable architectural probe
- existing codebase with no evolutions: introduce a probe for the requested idea inside the existing system
- existing probe: evolve it in place
- completed probe-based software: add a new capability through a new or extended probe

Expected outcome:

- executable code
- realistic entrypoint and integration points
- ordered evolutions for the remaining plan, each anchored by a `TODO(PROBE-...)` marker
- no detached architecture document

### `probe challenge`

Challenge the current probe plan against the README.

This command compares product intent, executable code, and ordered evolutions. It should find drift, missing core flows, vague evolutions, oversized evolutions, stale evolutions, ordering problems, and places where the code no longer communicates the intended software.

Expected outcome:

- suggested `probe refine` steps
- no code changes by default

### `probe list`

List the ordered probe plan.

This command scans the codebase for `TODO(PROBE-...)` markers and prints the ordered evolutions with file locations.

Expected outcome:

- ordered evolution list
- current first unapplied evolution highlighted
- warnings for malformed IDs, duplicate IDs, or confusing sequence structure

### `probe evolve`

Apply one ordered evolution.

This command assigns an agent to apply exactly one evolution. If no ID is provided, it should apply the first unapplied evolution in order.

Expected outcome:

- the selected evolution is implemented, removed, or replaced with more precise follow-up evolutions
- targeted verification is run
- unrelated evolutions are left untouched
- the probe plan remains ordered and reviewable

## TODO Syntax

Evolutions are ordered and code-local. Each evolution is anchored by a searchable marker:

```text
TODO(PROBE-010): Add persistent storage behind MovieRepository.
TODO(PROBE-020): Replace in-memory movie list with repository-backed state.
TODO(PROBE-030): Add edit and remove flows to the existing movie UI.
```

Rules:

- use `TODO(PROBE-010)` as the default syntax
- use zero-padded numbers so lexical sorting matches execution order
- number by tens to leave space for insertions
- write the marker as a short issue title, not the whole issue body
- rely on nearby code context to carry the details needed to apply the evolution
- place each marker where the work belongs
- update evolutions as the software changes

For multiple active architectural scopes, use a named sequence only when needed:

```text
TODO(PROBE-AUTH-010): Add login session boundary.
TODO(PROBE-SHARING-010): Add share link model.
```

The default should be one ordered sequence. Multiple sequences are useful only when the project has multiple independent architectural fronts.

## Core Requirements

The toolkit must preserve these requirements:

- code is the primary artifact
- README describes intent, not implementation details
- probes are executable
- probes live inside the real codebase
- evolutions are ordered
- `probe refine` changes the plan
- `probe evolve` applies the plan one evolution at a time
- every command keeps the workflow reviewable in minutes
- completion means no `TODO(PROBE-...)` markers remain for the current agreed scope
