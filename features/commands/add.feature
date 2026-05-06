@feature:F-COMMANDS-ADD
Feature: Add an evolution

  Developers use add to record one new ordered evolution in a specific source file.

  Rules:
    - Add assigns the next unique id in the default evolution sequence.
    - Add requires a source file and an evolution description.
    - Add records the requested description without applying the evolution.
    - Add appends the marker at the end of the requested file.
    - Add keeps the resulting marker visible to list.
    - Add refuses to allocate an id when the plan scan skipped unreadable source files.

  @id:F-COMMANDS-ADD-S001
  Scenario: Add records the next evolution
    Given a workspace with README intent
    And the workspace has ordered evolution markers
    When the developer runs `probedev add` with a file and new evolution description
    Then the system records a new evolution marker
    And the marker is appended at the end of the requested file
    And the marker is visible to `probedev list`
    And the command succeeds.

  @id:F-COMMANDS-ADD-S002
  Scenario: Add records the first evolution in an empty plan
    Given a workspace with no probe evolution markers
    When the developer runs `probedev add` with a file and new evolution description
    Then the system assigns the first evolution id
    And the marker is visible to `probedev list`
    And the command succeeds.

  @id:F-COMMANDS-ADD-S003
  Scenario: Add records an evolution at a requested path
    Given a workspace with README intent
    And the workspace has ordered evolution markers
    When the developer runs `probedev add` with a target file and new evolution description
    Then the marker is written to the requested path
    And the command succeeds.

  @id:F-COMMANDS-ADD-S004
  Scenario: Add refuses to write when plan scan is incomplete
    Given a workspace with a readable marker and an unreadable source file
    When the developer runs `probedev add` with a file and new evolution description
    Then the system reports that add could not scan the complete plan
    And no new marker is appended to the requested file
    And the command fails.
