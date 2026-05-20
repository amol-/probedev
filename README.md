# probedev

`probedev` is a command line toolkit for projects that use [Probe-Driven Development](pdd/README.md).

It reads and manages ordered `TODO(EVO-###)` evolution markers in a codebase.
For the PDD workflow, philosophy, and evolution-writing guidance, see [pdd/README.md](pdd/README.md).

## Commands

### `probedev list`

List the ordered evolution plan found in the current codebase.

The command scans source files for active `TODO(EVO-###)` markers, groups them by file, and reports malformed or duplicate marker candidates that need attention.

```bash
% probedev list
Pending evolutions
src/probedev/evolutions.py
  next EVO-010 line 52 Extract id allocation into a component that rejects duplicate default-sequence markers before choosing the next id.
       EVO-020 line 69 Confirm whether add should create missing files or require the target file to already exist.
src/probedev/show.py
       EVO-110 line 60 Surface editor launch failures as a failed show command with the attempted command line.
```

### `probedev add`

Add one new ordered evolution marker.

The command assigns the next unique ID in the default sequence and appends the marker to the requested source file.
If the target is an existing directory, it appends to `<dir>/Evolutions.txt`.

Directory targets are for evolutions that do not yet have a more specific source location.
Prefer placing evolutions in the file closest to the code they will change.

```bash
% probedev add src/probedev/show.py print the editor command before opening an evolution
Added evolution
- marker: EVO-150
- description: print the editor command before opening an evolution
- location: src/probedev/show.py:109
Run probedev list to review the ordered plan.
```

### `probedev identify`

Assign stable unique IDs to evolution markers that are missing IDs, use placeholders, use invalid IDs, or conflict with another marker.

The command updates marker syntax without applying the work. It preserves descriptions and file placement while making the plan addressable through `EVO-###` IDs.

Expected outcome:

- every pending evolution has a valid unique `EVO-###` ID
- existing valid unique IDs are left unchanged
- identified evolutions remain visible through `probedev list`

### `probedev show`

Open one pending evolution in an editor.

The command receives an `EVO-###` ID, finds the matching marker, and opens the configured editor at that source file and line.

```bash
% probedev show EVO-050
Opening evolution
- marker: EVO-050
- editor: /usr/local/bin/code --goto /Users/amol/src/probedev/src/probedev/plan.py:93
- location: src/probedev/plan.py:93
```

## Marker Handling

`probedev` recognizes the canonical PDD marker shape:

```text
TODO(EVO-010): Short evolution title
```

When source files need to quote marker-shaped text as examples or test fixtures, use ignore pragmas so the quoted text does not become part of the active plan:

```text
# probedev: ignore-next-line
"# TODO(EVO-010): fixture text, not a real evolution"

# probedev: ignore-start
"# TODO(EVO-020): another fixture"
"# TODO(EVO-030): more fixture text"
# probedev: ignore-end
```

Supported pragmas are:

- `probedev: ignore-line`
- `probedev: ignore-next-line`
- `probedev: ignore-start`
- `probedev: ignore-end`
- `probedev: ignore-file`

Place pragmas on source comment lines.

## Product Behavior

Canonical behavior for this toolkit is described in [features/](features/).

The feature files define expected command behavior and are used as product specifications first and executable BDD scenarios second.
