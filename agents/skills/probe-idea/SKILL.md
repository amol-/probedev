---
name: probe-idea
description: Implement an idea in Architectural Probe style to reveal the proposed architecture before committing to the full implementation.
---

# Architectural Probe Style

An Architectural Probe is a deliberately incomplete but executable implementation of one idea, built inside the real target codebase, whose purpose is to reveal whether the proposed architecture belongs there before committing to the full implementation.

The deliverable is the code. A probe is an alternative to an architecture document, not a prompt to write one.

A probe is allowed to defer production completeness, but not design discipline.
It must already be shaped like code we would be willing to evolve. Do not use
"this is only a probe" to justify shallow modules, vague names, fake boundaries,
test-only architecture, dependency injection for convenience, or code that would
need to be thrown away if the idea is accepted.

A successful probe should be evolved, not rewritten. If the probe would need to
be discarded and reimplemented properly after acceptance, it is a prototype, not
an Architectural Probe.

## Definition

An Architectural Probe must:

- live in the real codebase being changed
- execute as real code, not pseudocode or a detached prototype
- use the most realistic existing entrypoint or interaction boundary for the idea
- cover the smallest coherent version of the idea
- include a complete ordered evolution plan from the probe to graduation
- reuse existing project infrastructure and integration points whenever they exist
- expose the key components, responsibilities, names, boundaries, and data/control flow
- stay small enough for a human to review in minutes
- be easy to remove if the idea is rejected

A detached demo, mock-only prototype, architecture note, code sketch, or non-executable design is not an Architectural Probe.

The executable probe may be deliberately small, but the evolution plan may not be partial. A reviewer should be able to read the probe plus its `TODO(EVO-...)` markers and understand the intended path from the current probe to the finished scope.

## Architectural Question

Before writing any code, name the architectural question the probe is supposed to answer, distinct from the feature goal. The feature goal is what the user asked for ("HTTPS works"); the architectural question is what the probe must reveal ("can the existing harness absorb TLS cheaply?", "do these boundaries hold once a second signal type is added?", "does this responsibility belong in the scheduler or the worker?").

Choose the probe shape to answer that question in the smallest way. If the question is about fit with existing infrastructure, the probe must touch that infrastructure. If the question is about new boundaries, the probe must place those boundaries where they would really live.

A probe that satisfies the feature goal while sidestepping the architectural question is not a successful probe, even if it runs.

## Scope

Implement the smallest coherent slice that makes the idea real enough to evaluate.

Small scope applies to implemented behavior, not to planning coverage. The code should avoid production hardening and broad implementation, but it must still place all currently known evolutions needed to graduate the requested scope.

For a refactoring idea, move only enough existing behavior to exercise the proposed structure through a representative real path. Do not perform a broad migration unless the architecture cannot be evaluated without it.

For a new feature or component, implement enough user-visible or API-visible behavior to show how it fits into the existing system. Do not build the full product surface.

For a new complete software idea, create the miniature real shape of the software: project structure, runtime, entrypoint, main flow, and first meaningful component boundaries. The goal is to reveal what components must interact for the software to exist and live.

Do not reduce the probe to one operation when the idea itself is a small capability set. For example, probing "manage movies" may require minimal add, edit, remove, and view flows because those flows define "manage." Omit robustness and edge cases, not flows that are inherent to the idea.

When the requested idea describes a full tool, application, or workflow, include enough executable skeleton to reveal the main components and include ordered evolution markers for every major missing capability described by the intent source. Do not leave known README/product requirements unrepresented just because they are not implemented in the probe.

## Entrypoints And Integration

A probe must use the interaction boundary the real implementation would naturally use.

If the system has a GUI, TUI, API, CLI, background workflow, service boundary, or other external interaction model, probe through that same model. Do not add a separate command or fake entrypoint when that would avoid the real integration question.

Create a small temporary entrypoint only when no suitable one exists yet, or when the entrypoint itself is part of the architectural question.

Use real integration points where practical. Reuse existing persistence, routing, dependency injection, job systems, clients, UI patterns, and test harnesses when the codebase already provides them.

If an existing fixture, harness, helper, or module already owns the boundary the idea touches, extend it rather than creating a sibling. Creating a parallel fixture, a parallel helper, or a parallel test file is the same mistake as creating a fake entrypoint — it avoids the real integration question by standing up an isolated copy next to the thing the probe should be pressing on. The ease of deleting a new file is not a reason to add one when the architectural question is whether the existing code can absorb the idea.

Substitutes are acceptable only when the external dependency is not what is being probed and the substitute preserves the intended boundary. For example, an in-memory cache may stand in for Redis if the cache backend is not the architectural question.

## Review Budget

The probe must be reviewable in minutes, not hours.

Use this as a hard design pressure:

- aim for a 5-15 minute human review
- touch a small number of files
- keep the diff to the smallest size that honestly exposes the architecture
- split or narrow the idea if the probe grows beyond quick review

If a reviewer must invest hours to understand whether the idea fits, the probe failed even if it runs.

## Code Shape

Prefer:

- concrete code over speculative abstractions
- comments that describe the intended responsibility, flow, or omitted production behavior
- real names for the concepts being evaluated
- explicit wiring over hidden magic
- existing project conventions over new patterns
- localized changes over broad rewrites
- visible constraints in code over explanatory documents

Avoid:

- production hardening
- comprehensive error handling
- retries, fallbacks, recovery paths
- support for edge cases
- broad configuration systems
- plugin systems unless the plugin system is the idea being probed
- premature abstractions
- backward compatibility layers
- performance optimization
- unrelated refactoring
- sweeping migrations
- broad test matrices

Stay concrete by default. Introduce generalized abstractions only when generalization is the actual idea being probed, or when the existing codebase already requires that shape.

Do not name real architecture objects as probes. Avoid names like `MovieProbeService` or `ProbeMovieManager`. Use the real names being evaluated, such as `MovieLibrary` or `MovieRepository`.

## Comments As Pseudocode

Probe code should include concise comments that make the agent's intended architecture legible even where the executable slice is deliberately small.

Use comments as code-local pseudocode for:

- the responsibility of each new component, entrypoint, or boundary introduced by the probe
- the intended control flow when the probe implements only the shortest happy path
- important production behavior intentionally omitted to keep the probe reviewable
- integration assumptions that a reviewer must understand before accepting the architecture

Comments should explain intent and destination, not restate syntax. A reviewer should be able to skim the comments plus names and understand what the agent was trying to build, even if some implementation details are still represented only by `TODO(EVO-...)` markers.

Do not replace executable code with comments. The probe must still run. Comments are supporting pseudocode for the architecture, while `TODO(EVO-...)` markers are the ordered graduation plan.

## TODO(EVO)

Surface the complete graduation plan in the code with editor-recognizable ordered TODOs:

```text
TODO(EVO-010): Use Redis for cache sharing across concurrent workers.
               Why: The probe's in-memory cache proves the call flow, but it would lose consistency once multiple workers handle requests.
               Done: Cache reads/writes use the existing Redis client path, the in-memory cache is gone from production flow, and the focused concurrency smoke test passes.
               Non-Goals: Do not add a general cache abstraction, broad invalidation policy, or unrelated retry/backoff behavior in this step.
```

Use `TODO(EVO-010)` style markers for concrete evolution steps from probe toward real implementation. Place each marker at the exact code location where the future work belongs. The marker title must be short and immediately obvious, then the body must include `Why`, `Done`, and `Non-Goals` guidance.

Evolution markers are not optional debt notes. They are the code-local implementation plan. For the requested scope, the probe is incomplete unless the ordered markers cover the known path to graduation. Each evolution should contain enough information for an agent or developer to implement it independently using only the marker and the code it relates to. If an implementer would need product context, design intent, acceptance criteria, or scope boundaries from outside the marker and the code it touches, the evolution is not well written yet.

Before finishing a probe, compare the intent source such as README, issue, or user request against the code and verify that every described product capability is either:

- minimally represented by executable probe behavior, or
- represented by a specific ordered `TODO(EVO-...)` marker located where the future work belongs.

If a requirement is too ambiguous to place, add the smallest clarifying command/path/code boundary that exposes the ambiguity, or ask the user. Do not silently omit it.

Build a lightweight intent ledger while working: extract the named capabilities, integration points, production concerns, and known follow-up phases from the user request and any referenced artifact, then check them off against either executable code or a specific ordered marker before reporting completion. If an item does not map cleanly to a file location, add a narrow marker at the closest natural boundary where the future implementation would start.

Good `TODO(EVO)` markers:

- start with a short title that makes the evolution immediately recognizable
- explain Why the evolution should be done
- define Done with the concrete finish line or acceptance signal
- name Non-Goals that prevent the implementer from taking the wrong path
- identify a specific production gap
- describe the long-term direction
- act as checkpoints for evolving probe -> proof of concept -> MVP -> production
- make constraints reviewable in the code itself
- let a reviewer predict the intended sequence of implementation
- preserve the project plan as code-local work items rather than relying on the final chat summary

Avoid vague markers such as `TODO(EVO): clean this up`.

Avoid oversized markers that hide multiple phases such as `TODO(EVO-010): Implement the rest of the app`. Split them into ordered evolutions that a future `probe evolve` style workflow could apply one at a time.

Do not add TODOs mechanically. Add them where a reviewer needs to understand an intentional omission, constraint, concern, or future replacement.

Ideally, evolving a successful probe toward the real implementation should mostly mean replacing or resolving `TODO(EVO-...)` markers while keeping the proven architecture shape. Graduation for the current scope means no active `TODO(EVO-...)` markers remain.

## Graduation Plan Review

Before completing the probe, perform a short self-review:

- Does the executable code expose the intended entrypoint, main components, and control flow?
- Do the comments make each new boundary's intended responsibility understandable without a separate design doc?
- Does the ordered evolution list cover all README/user-request capabilities through graduation?
- Is each evolution placed where the implementation belongs?
- Does every item from the intent ledger map to executable behavior, an intent comment, or a `TODO(EVO-...)` marker?
- Is each evolution small enough to be applied independently?
- Does each evolution have a short obvious title, Why, Done, and Non-Goals, with enough guidance to implement independently without outside product context, design intent, acceptance criteria, or scope boundaries?
- Are there missing product capabilities, production-readiness gaps, or integration points that are neither implemented nor represented by an evolution?

If any answer is no, refine the probe or add/rewrite evolution markers before reporting completion.

## Verification

A probe is not a test-design exercise.

Do not add broad or polished test coverage for the probed idea. Add or run only enough verification to prove the probe executes, such as:

- one narrow smoke test
- one focused happy-path test
- one example
- one manual command or interaction path

The existing test suite for the surrounding system should continue to pass. Update existing tests only when the probed idea intentionally changes that behavior.

## Iterating On A Probe

When the user asks to continue, adjust, refine, or iterate on an existing Architectural Probe, treat the current probe code as the artifact under review.

Do not start a second probe unless the user explicitly asks to compare alternatives.

Do not implement a "probe of the changes." Evolve the existing probe in place to answer the new architectural question while preserving Architectural Probe constraints.

Before editing an existing probe, identify which iteration mode applies:

- refine the same probe: adjust boundaries, names, responsibilities, entrypoints, or missing core flows in the existing probe
- fork an alternative probe: keep the existing probe understandable and create a separate small alternative only when the user wants to compare architectural directions
- graduate the probe: stop probing and begin turning the accepted direction into production implementation by resolving `TODO(EVO-...)` markers and adding production hardening

Default to refining the same probe.

When refining, keep the total result reviewable in minutes. If the requested iteration would make the probe too large, narrow the question, replace part of the probe, or tell the user that the probe is ready to graduate or split.

Keep existing `TODO(EVO-...)` markers accurate and complete. Remove markers whose gaps have been resolved, update markers whose direction changed, and add markers for missing graduation steps discovered during the iteration.

Do not let iteration drift into production completion. Unless the user explicitly asks to graduate the probe, continue to avoid broad hardening, full test coverage, compatibility layers, large migrations, and unrelated refactoring.

## Success Criteria

Success is not measured by production completeness.

Success is measured by whether quick code review can answer:

- Does this idea belong in this codebase?
- Are these the right boundaries?
- Are these the right names?
- Are these the right integration points?
- Is the flow understandable?
- Is the code easy to remove if the idea is rejected?
- Does the ordered evolution plan cover all known work needed to graduate the requested scope?
- Can a human predict where the agent intends to take the implementation next?
- Would we be happy to evolve this into the real implementation?
- Does each evolution provide a short obvious title, Why, Done, and Non-Goals with all guidance needed for independent developers or agents to implement it?

A probe can succeed by showing that the idea should be rejected, split, renamed, moved, or redesigned. Making architectural friction visible early is a successful outcome.

## Completion Note

When done, keep the written summary brief. Do not write an architecture document.

Mention only:

- what coherent slice was implemented
- where the realistic entrypoint is
- how to run or verify it
- any major intentional omissions that are also marked in code

The code remains the primary artifact.
