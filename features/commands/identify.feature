@feature:F-COMMANDS-IDENTIFY
Feature: Identify evolutions

  Developers use identify to assign stable unique ids to pending evolution markers that do not already have valid unique ids.

  Rules:
    - Identify discovers evolution markers from scannable source files.
    - Identify assigns ids using the `EVO-XXX` format.
    - Identify preserves the evolution descriptions and source file placement.
    - Identify replaces missing, placeholder, invalid, or conflicting ids.
    - Identify leaves already valid unique ids unchanged.
    - Identify keeps the resulting markers visible to list.

  @id:F-COMMANDS-IDENTIFY-S001
  Scenario: Missing ids are assigned
    Given a workspace with pending evolutions that have no ids
    When the developer runs `probedev identify`
    Then the system assigns unique evolution ids
    And each identified marker keeps its description and file location
    And the markers are visible to `probedev list`
    And the command succeeds.

  @id:F-COMMANDS-IDENTIFY-S002
  Scenario: Placeholder and invalid ids are replaced
    Given a workspace with pending evolutions that have placeholder or invalid ids
    When the developer runs `probedev identify`
    Then the system replaces them with unique evolution ids
    And each identified marker keeps its description and file location
    And the command succeeds.

  @id:F-COMMANDS-IDENTIFY-S003
  Scenario: Conflicting ids are made unique
    Given a workspace with duplicate evolution ids
    When the developer runs `probedev identify`
    Then the system keeps one existing id
    And the system assigns new unique ids to the conflicting markers
    And the markers are visible to `probedev list`
    And the command succeeds.

  @id:F-COMMANDS-IDENTIFY-S004
  Scenario: Valid unique ids are unchanged
    Given a workspace with only valid unique evolution ids
    When the developer runs `probedev identify`
    Then the system reports that no markers needed identifiers
    And the command succeeds.
