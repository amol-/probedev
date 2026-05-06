@feature:F-COMMANDS-EVOLVE
Feature: Select an evolution to apply

  Developers use evolve to select exactly one ordered evolution as the next implementation step.

  Rules:
    - Evolve fails when no evolution markers exist.
    - Evolve selects the first ordered evolution when there is one default sequence.
    - Evolve requires an explicit marker when multiple independent sequences exist.
    - Evolve reports the selected marker, title, and location.

  @id:F-COMMANDS-EVOLVE-S001
  Scenario: First marker is selected by default
    Given a workspace with multiple markers in one probe sequence
    When the developer runs `probedev evolve`
    Then the system selects the first ordered marker
    And the system tells the developer to apply exactly that evolution.

  @id:F-COMMANDS-EVOLVE-S002
  Scenario: Explicit marker selects across sequences
    Given a workspace with multiple probe sequences
    When the developer runs `probedev evolve` with one marker id
    Then the system selects the requested marker
    And the system prints its title and location.

  @id:F-COMMANDS-EVOLVE-S003
  Scenario: Multiple sequences require explicit selection
    Given a workspace with multiple probe sequences
    When the developer runs `probedev evolve` without a marker id
    Then the system tells the developer to specify the evolution marker
    And the command fails.

  @id:F-COMMANDS-EVOLVE-S004
  Scenario: Missing marker cannot be selected
    Given a workspace with probe evolution markers
    When the developer runs `probedev evolve` with an unknown marker id
    Then the system reports that the evolution was not found
    And the command fails.
