@feature:F-COMMANDS-SHOW
Feature: Show an evolution

  Developers use show to jump from an evolution id to the exact code location where that evolution is anchored.

  Rules:
    - Show requires one evolution id argument in `EVO-XXX` format.
    - Show discovers pending evolution markers from scannable source files.
    - Show opens the configured editor at the matching marker file and line.
    - Show chooses the editor from `CODE_EDITOR`, then `EDITOR`, then an available default editor.
    - Show reports the selected editor command before launching the editor.
    - Show does not print an after-launch success message.
    - Show reports a missing evolution id without opening an editor.
    - Show reports duplicate evolution ids without opening an editor.
    - Show reports editor launch failures after reporting the selected editor command.

  @id:F-COMMANDS-SHOW-S001
  Scenario: Matching evolution opens at its marker line
    Given a workspace with ordered evolution markers
    And the developer has a configured code editor
    When the developer runs `probedev show EVO-020`
    Then the system opens the configured editor at the file containing `EVO-020`
    And the system reports the selected editor command
    And the editor is positioned on the `EVO-020` marker line
    And the system does not print an after-launch success message
    And the command succeeds.

  @id:F-COMMANDS-SHOW-S002
  Scenario: Code editor environment variable is preferred
    Given a workspace with ordered evolution markers
    And the developer has both `CODE_EDITOR` and `EDITOR` configured
    When the developer runs `probedev show EVO-020`
    Then the system opens `CODE_EDITOR` at the file containing `EVO-020`
    And the editor is positioned on the `EVO-020` marker line
    And the command succeeds.

  @id:F-COMMANDS-SHOW-S003
  Scenario: Editor environment variable is used when code editor is missing
    Given a workspace with ordered evolution markers
    And the developer has `EDITOR` configured
    And the developer does not have `CODE_EDITOR` configured
    When the developer runs `probedev show EVO-020`
    Then the system opens `EDITOR` at the file containing `EVO-020`
    And the editor is positioned on the `EVO-020` marker line
    And the command succeeds.

  @id:F-COMMANDS-SHOW-S004
  Scenario: Available default editor is used when no editor is configured
    Given a workspace with ordered evolution markers
    And the developer has no configured editor
    And the workspace has an available default editor
    When the developer runs `probedev show EVO-020`
    Then the system opens the available default editor at the file containing `EVO-020`
    And the editor is positioned on the `EVO-020` marker line
    And the command succeeds.

  @id:F-COMMANDS-SHOW-S005
  Scenario: Missing evolution id fails show
    Given a workspace with ordered evolution markers
    When the developer runs `probedev show EVO-999`
    Then the system reports that `EVO-999` was not found
    And no editor is opened
    And the command fails.

  @id:F-COMMANDS-SHOW-S006
  Scenario: Duplicate evolution id fails show
    Given a workspace with duplicate evolution ids
    When the developer runs `probedev show EVO-010`
    Then the system reports that `EVO-010` is ambiguous
    And no editor is opened
    And the command fails.

  @id:F-COMMANDS-SHOW-S007
  Scenario: Invalid evolution id fails show
    Given a workspace with ordered evolution markers
    When the developer runs `probedev show EVO`
    Then the system reports that the requested evolution id is invalid
    And no editor is opened
    And the command fails.

  @id:F-COMMANDS-SHOW-S008
  Scenario: Editor launch failure fails show after reporting the selected command
    Given a workspace with ordered evolution markers
    And the developer has a configured code editor
    And the configured editor launch fails
    When the developer runs `probedev show EVO-020`
    Then the system reports the selected editor command
    And the system reports the editor launch error
    And the system does not print an after-launch success message
    And the command fails.

  @id:F-COMMANDS-SHOW-S009
  Scenario: Configured editor line template controls file and line arguments
    Given a workspace with ordered evolution markers
    And the developer has `CODE_EDITOR` configured as `zed --reuse-window {path}:{line}`
    When the developer runs `probedev show EVO-020`
    Then the system opens `CODE_EDITOR` using the configured line template for `EVO-020`
    And the system reports the selected editor command
    And the command succeeds.
