@feature:F-COMMANDS-LIST
Feature: List ordered evolutions

  Developers use list to see the code-local probe plan in execution order.

  Rules:
    - List discovers evolution markers from scannable source files.
    - List orders evolutions by sequence and marker id.
    - List highlights the next unapplied evolution in each sequence.
    - List reports malformed marker candidates.
    - Markdown and ignored workspace directories are not part of the active plan scan.

  @id:F-COMMANDS-LIST-S001
  Scenario: Ordered markers are printed with the next marker highlighted
    Given a workspace with multiple ordered probe markers
    When the developer runs `probedev list`
    Then the system prints the ordered probe plan
    And the first marker in the sequence is marked as next
    And each marker includes its file location and title.

  @id:F-COMMANDS-LIST-S002
  Scenario: Malformed marker candidates are reported
    Given a workspace with a malformed probe marker candidate
    When the developer runs `probedev list`
    Then the system prints a malformed marker warning
    And the command succeeds.

  @id:F-COMMANDS-LIST-S003
  Scenario: No markers fails list
    Given a workspace with no probe evolution markers
    When the developer runs `probedev list`
    Then the system reports that no probe evolutions were found
    And the command fails.
