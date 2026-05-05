# Features

This directory contains the canonical product behavior specification.

The `.feature` files are:

- product documentation
- executable BDD scenarios
- stable contracts between product intent and implementation

They are not:

- Python test implementation files
- implementation plans
- status trackers

## Layout

Recommended structure:

```text
features/
|-- README.md
|-- glossary.md
|-- <domain>/
|   `-- <feature>.feature
`-- ...
```

Use domains that match product concepts, not implementation packages.

Examples:

```text
features/auth/login.feature
features/projects/create-project.feature
features/permissions/workspace-roles.feature
```

## Authoring rules

- One feature per file.
- One externally visible behavior per scenario.
- Every feature file has a stable `@feature:<FEATURE-ID>` tag.
- Every scenario has a stable `@id:<SCENARIO-ID>` tag.
- IDs must not change after they are referenced by plans, tests, or documentation.
- Step wording is part of the spec API.
- Rewording a step may require updating test step definitions.
- Prefer concrete examples over abstract prose.
- Prefer product vocabulary from `glossary.md`.
- Do not track implementation status here.
- Do not describe internal implementation unless it is externally visible behavior.

## ID format

Use this format:

```text
@feature:F-<DOMAIN>-<NAME>
@id:F-<DOMAIN>-<NAME>-SNNN
```

The `kind:value` form is the Gherkin idiom and is treated as an opaque label by the spec. The section "Using with pytest-bdd" below explains how to keep pytest-bdd from treating these tags as pytest markers.

Example:

```gherkin
@feature:F-AUTH-LOGIN
Feature: Login

  @id:F-AUTH-LOGIN-S001
  Scenario: Valid credentials create a session
```

## Writing scenarios

Use compact Gherkin:

```gherkin
@feature:F-DOMAIN-NAME
Feature: Short feature name

  Short product-level description.

  Rules:
    - Required behavior in concise product language.
    - Another required behavior.

  @id:F-DOMAIN-NAME-S001
  Scenario: Observable behavior title
    Given initial product state
    When user-visible action happens
    Then user-visible outcome is true
```

Good scenarios describe behavior that a user, API client, or external observer can verify.

Avoid scenarios that only describe implementation details.

## Adding a new feature

1. Pick the product domain, for example `auth`, `projects`, or `billing`.
2. Create `features/<domain>/<feature>.feature`.
3. Add one `@feature` tag at the top.
4. Add scenarios with stable `@id` tags.
5. Reuse terms from `glossary.md`.
6. Keep each scenario focused on one behavior.

## Using with pytest-bdd

The feature files live outside the test suite on purpose. Tests may consume them, but the product spec remains in `features/`.

A project that uses `pytest-bdd` can point pytest-bdd at this directory. One possible setup is:

```toml
# pyproject.toml
[tool.pytest.ini_options]
bdd_features_base_dir = "features"
```

Then a BDD test module can load scenarios from the external feature directory:

```python
# tests/bdd/test_features.py
from pathlib import Path
from pytest_bdd import scenarios

ROOT = Path(__file__).resolve().parents[2]
scenarios(str(ROOT / "features"))
```

Step definitions should live in the test suite, not in `features/`.

Example:

```text
tests/bdd/
|-- conftest.py
|-- test_features.py
`-- steps/
    |-- auth.py
    `-- projects.py
```

This keeps the separation clear:

```text
features/        -> product truth
tests/bdd/       -> executable adapter for the spec
tests/bdd/steps/ -> Python glue
```

### Treat `.feature` tags as opaque labels

The Gherkin `@feature:<ID>` / `@id:<ID>` tags are spec metadata, not pytest markers. pytest-bdd's default, however, is to turn every tag into a pytest marker via `getattr(pytest.mark, tag)`. That default has two consequences we do not want:

- Tag names containing `:` cannot be registered as pytest markers at all, so every distinct tag emits a `PytestUnknownMarkWarning`.
- Scenario ids are unique per scenario, so registering them would add one marker per new scenario, which is busywork with no payoff.

The library-endorsed fix is to override the `pytest_bdd_apply_tag` hook and return `True` so pytest-bdd considers the tag handled and applies no marker:

```python
# tests/bdd/conftest.py
def pytest_bdd_apply_tag(tag, function):
    """Treat .feature tags as opaque spec labels, not pytest markers."""
    return True
```

With this hook in place:

- Feature files keep the readable `@feature:<ID>` / `@id:<ID>` convention.
- No warnings, no marker registration.
- Targeting a single scenario is done by test name or `-k`: `pytest tests/bdd/test_features.py::test_<scenario_name>` or `pytest -k <snippet>`.

Skip this hook only if you deliberately want to use tags as pytest markers for selection, in which case stick to marker-safe tag names and register each tag.

## Asking an agent to add a feature

Suggested prompt:

```text
Read README.md, features/README.md, and features/glossary.md.
Add a new product feature under features/<domain>/ as a Gherkin .feature file.
Follow the existing ID conventions.
Do not modify tests or implementation code.
Keep scenarios focused on externally visible behavior.
```

## Asking an agent to write tests for features

Suggested prompt:

```text
Read features/README.md and the relevant .feature files.
Implement pytest-bdd bindings for the scenarios.
Do not edit the feature files unless a scenario is ambiguous or impossible to bind.
Keep step definitions in the test suite.
Report any missing or ambiguous product behavior instead of guessing.
```
