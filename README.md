# Code-First Probe-Driven Development

Agents speak code. Developers speak code. Specs were invented to communicate between humans; probes are for communication between humans and agents.

Code-First Probe-Driven Development is a project management and software development workflow that never leaves code. A software idea starts as a short README description, becomes an executable architectural probe, and then evolves through ordered evolutions anchored by `TODO(EVO-...)` markers at the exact code locations where the work belongs.

* The codebase is the single source of truth.
* The README or the BDD specs explain intent.
* The architectural probe shows architecture.
* The ordered evolutions are the implementation plan.

An evolution is not just one line of text. It is closer to an issue in an issue tracker, but code-local: the `TODO(EVO-...)` line gives the ID, order, and short title; the surrounding code, names, comments, types, tests, and optional linked BDD feature file provide the context needed to apply it.

For the process foundations, rules, and glossary, see [pdd/README.md](pdd/README.md).

## The Probe Development Toolkit

This repository defines the command toolkit needed to practice Probe-Driven Development.

The toolkit gives developers and agents a deterministic view of the code-local project plan:

- list the ordered implementation plan from code
- add a new ordered evolution with a unique ID
- identify pending evolutions that do not have valid unique IDs
- open the source location for a specific evolution ID

The toolkit exists to keep the project-management state inside the codebase. Agent-shaped activities such as discussion, challenge, refinement, and applying evolutions belong in coding agents that can read and edit the project with judgment.

## Product behavior

Canonical product behavior is described in [`features/`](features/).

The `.feature` files are the source of truth for what the software does. They are product specifications first and executable BDD scenarios second.

Implementation progress is tracked by probe evolutions by referencing stable feature and scenario IDs

## Commands

### `probedev list`

List the ordered probe plan.

This command scans the codebase for `TODO(EVO-...)` markers and prints pending evolutions grouped by source file.

```bash
% probedev list
Pending evolutions
src/probedev/evolutions.py
  next EVO-010 line 52 Extract id allocation into a component that rejects duplicate default-sequence markers before choosing the next id.
       EVO-020 line 69 Confirm whether add should create missing files or require the target file to already exist.
       EVO-030 line 79 Preserve original file newline style and write atomically once the append boundary graduates from probe to production.
       EVO-040 line 87 Replace suffix guessing with a small language comment-style table that covers every scannable source type.
src/probedev/identification.py
       EVO-080 line 79 Split candidate scanning into a shared parser so list and identify agree on every marker candidate shape.
       EVO-090 line 80 Preserve file newline style and permissions when identify rewrites source files.
       EVO-100 line 81 Report unchanged valid markers and rewritten conflicts separately for clearer command output.
src/probedev/listing.py
       EVO-060 line 31 Group duplicate and malformed marker warnings by file once the main grouped list shape is accepted.
       EVO-070 line 37 Add explicit coverage for ignored directories and Markdown exclusions in grouped list output.
src/probedev/plan.py
       EVO-050 line 93 Skip permission-denied or inaccessible files instead of crashing during plan scans.
src/probedev/show.py
       EVO-110 line 60 Surface editor launch failures as a failed show command with the attempted command line.
       EVO-120 line 82 Add platform-specific default editor discovery and a user-facing setup hint when none is available.
       EVO-130 line 106 Support line-number argument templates for configured editors outside the initial code/vim family.
```

### `probedev add`

Add one ordered evolution to the code-local probe plan.

This command records a `TODO(EVO-...)` marker without applying the work. It requires a source file or existing directory and an evolution description, assigns the next unique ID in the default sequence, and appends the marker to the end of the requested file. Directory targets write to `<dir>/Evolutions.txt`.

```bash
% probedev add src/probedev/show.py when opening an evolution with editor it should print what editor is going to use
Added evolution
- marker: EVO-150
- description: when opening an evolution with editor it should print what editor is going to use
- location: src/probedev/show.py:109
Run probedev list to review the ordered plan.
```

### `probedev identify`

Assign stable unique IDs to existing evolution markers that are missing IDs, use placeholders, use invalid IDs, or conflict with another marker.

This command updates marker syntax without applying the work. It preserves descriptions and file placement while making the plan addressable through `EVO-XXX` IDs.

Expected outcome:

- every pending evolution has a valid unique `EVO-XXX` ID
- existing valid unique IDs are left unchanged
- identified evolutions remain visible through `probedev list`

### `probedev show`

Open one pending evolution in an editor.

This command receives an `EVO-XXX` ID, finds the matching `TODO(EVO-...)` marker, and opens the configured editor at that source file and line.

```bash
% probedev show EVO-050
Opening evolution
- marker: EVO-050
- editor: /usr/local/bin/code --goto /Users/amol/src/probedev/src/probedev/plan.py:93
- location: src/probedev/plan.py:93
```

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

When source files need to quote marker-shaped text as examples or test fixtures, use ignore pragmas so the quoted text does not become part of the active plan:

```text
# probedev: ignore-next-line
"# TODO(EVO-010): fixture text, not a real evolution"

# probedev: ignore-start
"# TODO(EVO-020): another fixture"
"# TODO(EVO-030): more fixture text"
# probedev: ignore-end
```

Supported pragmas are `probedev: ignore-line`, `probedev: ignore-next-line`, `probedev: ignore-start`, `probedev: ignore-end`, and `probedev: ignore-file`; place them on source comment lines.

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
- `probedev show` opens the file and line for one planned evolution
- coding agents perform nondeterministic workflow actions such as discussion, challenge, refinement, and applying evolutions
- completion means no `TODO(EVO-...)` markers remain for the current agreed scope
