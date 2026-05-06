# Probe-Driven Development

Probe-Driven Development is a code-first software development workflow where executable architectural probes replace most upfront specification work.

The central claim is simple:

> Agents speak code. Developers speak code. Specs were invented to communicate between humans; probes are for communication between humans and agents.

In Probe-Driven Development, the software plan lives in the codebase as ordered evolutions anchored by `TODO(EVO-...)` markers. The README gives product intent. The probe gives architecture. The evolutions give execution order.

## Foundations

### Code Is The Shared Language

Natural-language specs are useful for human alignment, but they are vague and easy for agents to satisfy superficially. Code is harder to fake. Executable code shows names, boundaries, entrypoints, dependencies, data flow, and tradeoffs directly.

Probe-Driven Development uses prose only where prose is strongest:

- describing product intent
- capturing user value
- clarifying scope
- challenging assumptions

Architecture and implementation planning live in code.

### The Probe Is The Architecture

An architectural probe is a deliberately incomplete but executable implementation of an idea inside the real codebase.

It is not a mock, sketch, detached prototype, or architecture document. It must run through the most realistic entrypoint available and reveal how the software wants to be shaped.

The probe should be small enough to review in minutes. If the probe takes hours to understand, it failed as a probe.

### Evolutions Are The Plan

`TODO(EVO-...)` markers are not incidental debt comments, but they are also not the whole evolution. They are anchors for ordered code-local planned changes.

An evolution is closer to an issue in an issue tracker. It has an ID, order, and short title in the `TODO(EVO-...)` marker, and it gets most of its context from nearby code: names, types, comments, tests, integration points, and optional linked BDD feature files.

Each evolution should describe a concrete step from the current probe toward the real implementation. Each marker belongs at the code location where the future work should happen.

Ideally, moving from probe to production is mostly applying evolutions and removing their `TODO(EVO-...)` markers while preserving the architecture shape that the probe validated.

### The Workflow Never Leaves Code

Probe-Driven Development does not require a separate project plan, issue tracker, architecture document, or requirements database.

The source of truth is:

- README for intent
- executable code for architecture
- ordered evolutions for the plan

External tools may visualize or validate the plan, but they should derive from the codebase rather than replace it.

## Lifecycle

### 1. Intent Seed

Start with a short README description.

The seed should explain what the software is, who it serves, and why it exists. It does not need complete requirements.

### 2. Discussion

Challenge the README until the software is understandable as a whole.

Discussion should focus on product questions:

- who uses it
- what problem it solves
- what the first useful workflow is
- what belongs out of scope
- what "complete enough" means

Avoid technical design questions unless they block understanding the product.

### 3. Refinement

Create or evolve the architectural probe.

The probe must:

- live in the real codebase
- execute as real code
- use realistic entrypoints and integration points
- expose component boundaries and responsibilities
- stay reviewable in minutes
- remain easy to remove if rejected

Refinement also creates, updates, removes, or reorders evolutions.

### 4. Challenge

Challenge the probe plan against the README.

This step asks whether the code and evolutions still express the intended software:

- does the probe cover the core workflows?
- are important gaps represented by evolutions?
- are evolutions concrete and ordered?
- is the plan still small enough to execute step by step?
- has the code drifted away from the README?

Challenge produces suggested refinements, not implementation by default.

### 5. Applying Evolutions

Apply one ordered evolution at a time.

Each application of an evolution should:

- implement exactly the selected evolution
- remove or update that evolution
- add follow-up evolutions only when the work reveals necessary new steps
- optionally define or update BDD feature files for the selected evolution before implementation
- run targeted verification
- avoid unrelated hardening or refactoring

### 6. Graduation

The software is complete for the current agreed scope when no `TODO(EVO-...)` markers remain.

If new features are requested later, the project returns to discussion, refinement, challenge, and applying evolutions for that new scope.

## Rules

### README Rules

- The README describes product intent, not detailed architecture.
- It should be clear enough to challenge whether the code is building the right thing.
- It should evolve when the user's understanding of the software changes.
- It should not become a traditional requirements document.

### Probe Rules

- The probe must execute.
- The probe must live in the real codebase.
- The probe must use the realistic entrypoint for the software.
- The probe should use existing infrastructure when the codebase provides it.
- The probe should stay concrete unless the idea being probed is a generalization.
- The probe should surface concerns in code as evolutions anchored by `TODO(EVO-...)`.
- The probe should stay reviewable in minutes.
- The probe should be easy to remove.

### Evolution Rules

Use this default syntax:

```text
TODO(EVO-010): Concrete implementation step.
```

Rules:

- IDs must be ordered.
- IDs should be zero-padded.
- IDs should usually increment by tens.
- Each marker should be a short issue title, not the whole issue body.
- Each evolution must describe one concrete step.
- Each marker must be placed where the work belongs.
- Nearby code must provide enough context for an agent and developer to apply the evolution.
- Evolutions must be updated when the plan changes.
- An evolution may be replaced by more precise evolutions if applying it reveals necessary substeps.

Use one ordered `EVO-XXX` sequence for the current agreed scope. If the project has multiple independent architectural scopes, keep them in the same sequence and make the scope clear in the marker title and nearby code.

### Command Rules

- `probedev list` reads the ordered plan from code.
- `probedev add` records one new ordered evolution marker with a unique ID at the end of a requested file.

Keep this separation strict. The command line tool manages project-state visibility. Coding agents handle discussion, refinement, challenge, and applying evolutions because those activities require judgment and code changes.

## Optional BDD Integration

Probe-Driven Development works without BDD. BDD is optional.

When BDD is useful, it should be introduced while a coding agent applies a selected evolution, not before the architectural probe exists.

The probe discovers where behavior belongs in the software. BDD describes the user-observable behavior that one selected evolution must satisfy.

### Why BDD Comes After The Probe

Writing feature files before the probe can force behavior language, nouns, workflows, and boundaries too early.

First use a coding agent to create or evolve the executable architecture. Then, when applying a specific evolution, define the BDD feature for that evolution's behavior.

This keeps the responsibilities separate:

- README describes product intent
- probe code discovers architecture
- evolutions give ordered implementation changes
- BDD feature files describe user-observable behavior for a selected step
- implementation makes that selected behavior pass

### BDD While Applying An Evolution

When applying an evolution that has user-observable behavior, the coding agent may:

- inspect the selected evolution and its surrounding code context
- create or update the smallest relevant feature file
- link the evolution and feature file
- ask the user only when behavior is ambiguous
- implement the evolution
- run the feature or the most targeted available verification
- remove or update the marker when the behavior is implemented

Do not create a broad feature suite for the whole product. Define only the behavior needed for the selected evolution.

If the evolution is purely internal and has no meaningful user-observable behavior, BDD can be skipped.

### Linking Evolutions And Features

Link code-local evolutions to BDD feature files explicitly.

In code:

```text
TODO(EVO-030): Add edit and remove flows to the movie library.
Feature: features/movie_library/manage_movies.feature
```

In the feature file:

```gherkin
# Evolution: EVO-030
Feature: Manage movies
```

Keep the link simple and searchable. The evolution remains the project-plan unit. The feature file is the behavior contract for applying that evolution.

### BDD Challenge Checks

When BDD is used, challenge work should also check:

- each user-observable evolution has a linked feature file
- linked feature files match README intent
- feature scenarios are no broader than the selected evolution
- feature language matches the nouns and workflows discovered by the probe
- stale feature files are updated or removed when evolutions change

BDD should clarify behavior. It should not become a second project plan that competes with `TODO(EVO-...)`.

## Glossary

### Architectural Probe

A deliberately incomplete but executable implementation that reveals whether an architectural direction fits the real codebase.

### Probe-Driven Development

A software development workflow where the product description lives in README, the architecture is discovered through executable probes, and the implementation plan lives as ordered evolutions in code.

### Intent Seed

The first small README description of the software.

### Discussion

The process of challenging and improving the README-level product description before technical design.

### Refinement

The process of creating or evolving an architectural probe and its ordered evolution plan.

### Challenge

The process of comparing README intent, executable code, and evolution plan to find drift, missing flows, stale evolutions, or weak architecture.

### Applying An Evolution

The process of applying one ordered evolution.

When BDD is used, applying an evolution may first define or update the feature file for the selected evolution's user-observable behavior.

### Graduation

The point where all `TODO(EVO-...)` markers for the current agreed scope have been applied and removed.

### Evolution

An ordered code-local planned change anchored by `TODO(EVO-...)` syntax.

The marker gives the evolution ID, execution order, and short title. The surrounding code provides most of the detail needed to apply it.

### Current Scope

The currently agreed product or capability scope described by the README and represented by the active evolution sequence.

## Known Risks

### Evolutions Can Become Stale

Address this by challenging the probe regularly and by keeping evolutions concrete, ordered, and colocated with the code they affect.

### Code May Miss Product Intent

Address this by keeping the README short but meaningful, and by challenging the code against it.

### Agents May Overbuild

Address this by keeping the CLI limited to plan visibility and marker creation, and by applying one evolution at a time through coding agents.

### One Ordered List May Not Fit Every Project

Address this by using one ordered sequence per coherent scope. Add named sequences only when multiple independent architectural fronts exist.

### Completion Can Be Misleading

No evolutions means complete only for the current agreed scope. New product intent restarts the lifecycle.
