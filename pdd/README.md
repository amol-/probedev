# Probe-Driven Development

Probe-Driven Development is a code-first workflow for turning a software requirement or idea into working architecture and an ordered implementation plan.

The central claim is simple:

> Agents speak code. Developers speak code. Specs were invented to communicate between humans; probes are for communication between humans and agents.

PDD does not prescribe how requirements are created. A requirement may start as BDD scenarios, a README, an issue, a design note, or a conversation. The only requirement is that the idea is clear enough to build a probe from it.

## The Point

PDD produces three things:

1. An executable architectural probe.
2. A complete path from probe to graduation.
3. A code-local plan, where each step lives next to the code it will evolve.

The probe explores uncertainty. The plan explains how to make the probe real.

## Requirements First

PDD starts from a requirement or idea, not from a tool.

The requirement should describe the behavior or outcome well enough that a developer or agent can ask: "What architecture would satisfy this?"

BDD works especially well here. Feature files and scenarios give discipline to the requirement before the probe exists. The probe can then implement a stubbed architecture that satisfies those scenarios, and later evolutions can replace the stubs with real behavior.

BDD is useful, but not mandatory. Any clear requirement format can start a probe.

## Build The Probe

An architectural probe is a deliberately incomplete but executable implementation inside the real codebase.

It is not a detached prototype or an architecture document.
It should run through the most realistic entrypoint available and reveal how the software wants to be shaped, and
how the components should interact.

In a probe, business behavior may be fake, but **architectural contracts should be real enough** to test the direction:

- real entities
- real interfaces
- real module boundaries
- real entrypoints
- fake methods where implementation and logic is not the question yet

The probe is a **working hypothesis**, not a commitment.
It can be rejected, thrown away, or heavily modified when it shows that the direction is wrong. PDD is iterative, not waterfall.

The important rule is that the evolutions stay current as the probe changes.

## Evolutions Are The Plan

An evolution is one ordered step from the current probe toward graduated software.

Together, evolutions form the implementation plan:

```text
Pending evolutions
src/movies/repository.py
  next EVO-010 Replace in-memory movie storage with durable persistence.
               ./src/movies/repository.py:28
       EVO-020 Share the repository between CLI and web entrypoints.
               ./src/movies/repository.py:46
src/movies/ui.py
       EVO-030 Add edit and remove flows to the movie library UI.
               ./src/movies/ui.py:81
tests/movie_library.feature
       EVO-040 Cover restart persistence in the acceptance scenario.
               ./tests/movie_library.feature:12
```

Every evolution is anchored by this syntax:

```text
TODO(EVO-010): Short title of the planned change
```

`TODO(EVO-###)` is the canonical PDD marker because it is easy for tools to parse, easy for humans to search, and recognized by many editors and IDEs as a task.

The marker alone is not enough. A good evolution includes:

- `TODO(EVO-###): Title`
- `Why`
- `Done`
- `Non-Goals`

The evolution should be self-contained enough that a developer or agent can apply it by reading the marker, its structured body, and the surrounding code. The goal is to avoid jumping across planning files to discover what code is involved or what the step means.

Keep each evolution close to the code it will evolve. This helps humans stay oriented and helps LLMs keep the relevant context small.

## Example: Python

```python
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Movie:
    title: str
    year: int


class MovieRepository(Protocol):
    def add(self, movie: Movie) -> None: ...
    def list(self) -> list[Movie]: ...


class InMemoryMovieRepository:
    def __init__(self) -> None:
        self._movies: list[Movie] = []

    def add(self, movie: Movie) -> None:
        self._movies.append(movie)

    def list(self) -> list[Movie]:
        # TODO(EVO-010): Replace in-memory movie storage with durable persistence
        # Why:
        # - The probe validates the repository boundary, but movies disappear after restart.
        # - Graduation requires the CLI and web entrypoints to share the same saved library.
        # Done:
        # - MovieRepository is backed by durable storage selected by configuration.
        # - Existing add/list behavior passes through the same repository contract.
        # - A restart preserves movies added before shutdown.
        # Non-Goals:
        # - Do not add editing, deletion, search, or user accounts in this evolution.
        # - Do not change the public MovieRepository interface unless persistence proves it wrong.
        return list(self._movies)
```

The storage behavior is fake enough for a probe, but the entity, interface, and repository boundary are real enough to test the architecture.

## Example: Go

```go
package movies

import "context"

type Movie struct {
	Title string
	Year  int
}

type Repository interface {
	Add(ctx context.Context, movie Movie) error
	List(ctx context.Context) ([]Movie, error)
}

type MemoryRepository struct {
	movies []Movie
}

func (r *MemoryRepository) Add(ctx context.Context, movie Movie) error {
	r.movies = append(r.movies, movie)
	return nil
}

func (r *MemoryRepository) List(ctx context.Context) ([]Movie, error) {
	// TODO(EVO-020): Replace memory repository with shared persistent storage
	// Why:
	// - The probe proves the Repository contract, but state is process-local.
	// - Graduation requires multiple commands and server handlers to see the same movie library.
	// Done:
	// - Repository has a persistent implementation behind the existing interface.
	// - Add and List keep the same behavior from callers' perspective.
	// - Tests prove data survives repository reinitialization.
	// Non-Goals:
	// - Do not add filtering, pagination, or migrations in this evolution.
	// - Do not redesign the handler layer unless the repository contract blocks persistence.
	result := make([]Movie, len(r.movies))
	copy(result, r.movies)
	return result, nil
}
```

## When No Code Location Fits

**Evolutions should live in the source file closest to the code they will change**.

Missing files are not a reason to use `Evolutions.txt`. If the planned work has a natural code owner, create the smallest honest placeholder for that owner and put the evolution there. A future package can start as an empty package, a future fixture set can start as a fixture directory, and a future entrypoint can start as a stub.

Use `Evolutions.txt` only when the step has no specific code owner. Good examples include validating the probe with an external stakeholder, choosing between two operational deployment constraints, or recording a project-level decision that affects several parts of the probe equally.

In that case, put the evolution in an `Evolutions.txt` file in the closest relevant directory. If no directory owns the work yet, use `Evolutions.txt` at the project root.

In `Evolutions.txt`, the evolution body continues until a blank line, the next evolution marker, or the end of the file.

The same structure still applies:

```text
TODO(EVO-030): Validate repository durability expectations with operations
Why:
- The probe assumes local durable storage is acceptable, but operations may require managed storage.
- This decision affects repository code, deployment configuration, and acceptance criteria equally.
Done:
- The agreed storage constraint is recorded in the requirement source.
- Follow-up evolutions are moved into the specific files that must change.
Non-Goals:
- Do not implement storage changes in this evolution.
- Do not introduce a generic deployment abstraction before the constraint is known.
```

Move or rewrite the evolution when the probe changes and a better code location appears.

## The Workflow

### Express

Express the requirement clearly enough to probe.

BDD scenarios are a strong option because they describe observable behavior before architecture is chosen.
A README, issue, or design note can also work.

PDD does not own this step. It only depends on the result being clear enough to guide a probe.

### Probe

Build the smallest executable architecture that can satisfy or illuminate the requirement.

Use real boundaries and fake behavior where implementation detail is not the current uncertainty.

### Challenge

You should review and challenge the probe against the requirement.

Ask:

- Does this architecture satisfy the scenarios or intent?
- Did the probe expose a better shape?
- Are the entities, interfaces, and boundaries still credible?
- Are missing implementation steps captured as evolutions?
- Are the evolutions ordered and close to the code they change?

Challenge can produce changes to the probe, changes to the evolutions, or a decision to throw the probe away.

This is the moment the **development team and the coding agents come to alignment** over how the software should be built,
such that there is one shared vision on what the architecture should look like and what is the plan to build the software.

### Evolve

Apply one evolution at a time.

Each evolution should:

- implement exactly the selected step
- remove its `TODO(EVO-###)` marker
- keep nearby evolutions accurate
- add follow-up evolutions only when the work reveals new necessary steps
- run the most targeted useful verification

### Graduate

The current scope is graduated when no active `TODO(EVO-###)` markers remain for that scope.

Graduation does not mean the product is finished forever. It means the agreed scope represented by the probe has become real software.

New requirements start the cycle again.

## Tooling

PDD does not require a specific tool.

A useful PDD tool should be able to:

- find `TODO(EVO-###)` markers
- show the ordered plan
- preserve stable evolution IDs
- open the code location for a selected evolution
- keep the plan derived from the codebase

Tools may help manage the workflow, but they should not replace the code-local plan.

The `probedev` tool is an example implementation of a tool to manage the evolutions plan.

## Glossary

### Architectural Probe

A deliberately incomplete but executable implementation that reveals whether an architectural direction fits the real codebase.

### Evolution

An ordered, code-local planned change anchored by a `TODO(EVO-###)` marker and described with `Why`, `Done`, and `Non-Goals`.

### Current Scope

The requirement or capability currently represented by the executable probe and its active evolution markers.

### Challenge

The act of comparing the requirement, probe, and evolutions to find missing behavior, stale markers, unclear architecture, or drift.

### Graduation

The point where all active `TODO(EVO-###)` markers for the current scope have been resolved and removed.
