@feature:F-COMMANDS-REFINE
Feature: Refine an architectural probe

  Developers use refinement to move from README intent toward executable architecture and ordered evolutions.

  Rules:
    - Refinement requires README intent.
    - Refinement reports the current intent source, process source, and active evolution count.
    - Refinement can record one new ordered evolution marker without applying it.
    - Refinement keeps the user focused on a realistic executable entrypoint.

  @id:F-COMMANDS-REFINE-S001
  Scenario: README intent produces a refinement target
    Given a workspace with README intent
    When the developer runs `probe refine`
    Then the system reports the refinement target
    And the system includes the intent file, process file, and active evolution count.

  @id:F-COMMANDS-REFINE-S002
  Scenario: Missing README intent blocks refinement
    Given a workspace without README intent
    When the developer runs `probe refine`
    Then the system tells the developer to add intent before refinement
    And the command fails.

  @id:F-COMMANDS-REFINE-S003
  Scenario: Refinement records one requested evolution
    Given a workspace with README intent
    And the workspace has ordered evolution markers
    When the developer runs `probe refine` with a new evolution title
    Then the system records a new evolution marker
    And the marker is visible to `probe list`
    And the command succeeds.
