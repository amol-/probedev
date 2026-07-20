@feature:F-COMMANDS-ADD
Feature: Add an evolution

  Developers use add to record one new ordered evolution in a source file or existing directory.

  Rules:
    - Add assigns the next unique id in the default evolution sequence.
    - Add requires a source file or directory and an evolution description.
    - Add records the requested description without applying the evolution.
    - Add appends the marker at the end of the requested file or the directory's Evolutions.txt.
    - Add creates a missing requested file when it is a scannable source path.
    - Add creates or appends to Evolutions.txt when the target path is a directory.
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
  Scenario: Add creates a missing source file at a requested path
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

  @id:F-COMMANDS-ADD-S005
  Scenario: Add writes to Evolutions.txt when target path is a directory
    Given a workspace with README intent
    And the workspace has ordered evolution markers
    And the workspace has an existing source directory
    When the developer runs `probedev add` with a directory and new evolution description
    Then the system creates or appends to Evolutions.txt in that directory
    And the marker is visible to `probedev list`
    And the command succeeds.

  @id:F-COMMANDS-ADD-S006
  Scenario: Add inserts marker before specified line with target indentation
    Given a workspace with README intent
    And the workspace has ordered evolution markers
    And the workspace has a source file with content
    When the developer runs `probedev add` with a file:line target and new evolution description
    Then the system inserts the marker before the specified line
    And the marker uses the target line's leading whitespace
    And the marker is visible to `probedev list`
    And the command succeeds.

  @id:F-COMMANDS-ADD-S007
  Scenario: Add rejects directory targets with line numbers
    Given a workspace with README intent
    And the workspace has an existing source directory
    When the developer runs `probedev add` with a directory:line target and new evolution description
    Then the system reports that directories cannot have line numbers
    And no Evolutions.txt is created
    And the command fails.

  @id:F-COMMANDS-ADD-S008
  Scenario: Add rejects invalid line numbers
    Given a workspace with README intent
    And the workspace has a source file with content
    When the developer runs `probedev add` with a file:line target where line is not a number
    Then the system reports the invalid line number
    And the command fails.

  @id:F-COMMANDS-ADD-S009
  Scenario: Add rejects line numbers outside file range
    Given a workspace with README intent
    And the workspace has a source file with content
    When the developer runs `probedev add` with a file:line target where line is out of range
    Then the system reports the line number is out of range
    And the command fails.

  @id:F-COMMANDS-ADD-S010
  Scenario: Add rejects line numbers greater than 1 for non-existent files
    Given a workspace with README intent
    And the workspace has no file at the target path
    When the developer runs `probedev add` with a file:line target where line is greater than 1 for a non-existent file
    Then the system reports the line number is out of range for the new file
    And no file is created
    And the command fails.
