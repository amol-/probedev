@feature:F-COMMANDS-LIST
Feature: List ordered evolutions

  Developers use list to see pending code-local evolutions grouped by the file where each evolution belongs.

  Rules:
    - List discovers evolution markers from scannable source files.
    - List groups pending evolutions by source file.
    - List orders files by path.
    - List orders evolutions within each file by sequence and marker id.
    - List highlights the next unapplied evolution in each sequence.
    - List treats immediately following comment lines as part of the same evolution description.
    - List aligns continued evolution description lines with the description column.
    - List reports duplicate marker ids.
    - List reports malformed marker candidates.
    - List warns about scannable files that could not be read.
    - List honors `probedev: ignore-*` pragmas in source files.
    - Markdown and ignored workspace directories are not part of the active plan scan.

  @id:F-COMMANDS-LIST-S001
  Scenario: Pending evolutions are grouped by file
    Given a workspace with multiple ordered probe markers
    When the developer runs `probedev list`
    Then the system prints the pending evolution files
    And the first marker in the sequence is marked as next
    And each marker includes its id, line number, and description.

  @id:F-COMMANDS-LIST-S002
  Scenario: Malformed marker candidates are reported
    Given a workspace with a malformed probe marker candidate
    When the developer runs `probedev list`
    Then the system prints a malformed marker warning
    And the command succeeds.

  @id:F-COMMANDS-LIST-S003
  Scenario: Duplicate marker ids are reported
    Given a workspace with duplicate probe markers
    When the developer runs `probedev list`
    Then the system prints a duplicate marker warning
    And the command succeeds.

  @id:F-COMMANDS-LIST-S004
  Scenario: No markers fails list
    Given a workspace with no probe evolution markers
    When the developer runs `probedev list`
    Then the system reports that no probe evolutions were found
    And the command fails.

  @id:F-COMMANDS-LIST-S005
  Scenario: Unreadable source files are reported without stopping list
    Given a workspace with a readable marker and an unreadable source file
    When the developer runs `probedev list`
    Then the system prints the readable evolution marker
    And the system prints an unreadable file warning
    And the command succeeds.

  @id:F-COMMANDS-LIST-S006
  Scenario: Multiline evolution markers keep aligned description text
    Given a workspace with a multiline evolution marker
    When the developer runs `probedev list`
    Then the system prints the marker id and marker line number once
    And the system prints all continuation lines as part of the same evolution
    And the continuation lines are aligned with the evolution description column
    And the command succeeds.

  @id:F-COMMANDS-LIST-S007
  Scenario: Ignored marker-shaped text is not listed
    Given a workspace with ignored marker-shaped fixture text
    When the developer runs `probedev list`
    Then the system prints only the non-ignored evolution marker
    And the command succeeds.

  @id:F-COMMANDS-LIST-S008
  Scenario: List and identify share source marker candidate discovery
    Given a workspace with evolution marker candidates across source languages and marker shapes
    When the developer runs `probedev list` and then `probedev identify`
    Then list and identify observe the same source marker candidate locations
    And the command succeeds.

  @id:F-COMMANDS-LIST-S009
  Scenario: Plain text Evolutions.txt markers keep body lines until a blank line
    Given a workspace with a plain text Evolutions.txt evolution body
    When the developer runs `probedev list`
    Then the system prints the Evolutions.txt evolution body
    And the system does not include text after the blank line
    And the command succeeds.

  @id:F-COMMANDS-LIST-S010
  Scenario: Source code marker bodies stop before non-comment code
    Given a workspace with a source evolution body followed by code
    When the developer runs `probedev list`
    Then the system prints the source evolution comment body
    And the system does not include executable code after the evolution body
    And the command succeeds.
