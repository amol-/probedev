@feature:F-COMMANDS-CHALLENGE
Feature: Challenge the probe plan

  Developers use challenge to identify drift and marker problems before evolving the probe further.

  Rules:
    - Challenge checks for README intent.
    - Challenge checks for the process reference.
    - Challenge reports malformed and duplicate evolution markers.
    - Challenge fails when findings are present.

  @id:F-COMMANDS-CHALLENGE-S001
  Scenario: Missing intent and malformed markers are reported
    Given a workspace without README intent
    And the workspace contains a malformed probe marker
    When the developer runs `probe challenge`
    Then the system prints challenge findings
    And the findings include missing README intent
    And the findings include the malformed marker location
    And the command fails.

  @id:F-COMMANDS-CHALLENGE-S002
  Scenario: Duplicate markers are reported
    Given a workspace with duplicate probe markers
    When the developer runs `probe challenge`
    Then the system prints challenge findings
    And the findings include the duplicate marker id
    And the command fails.

  @id:F-COMMANDS-CHALLENGE-S003
  Scenario: Complete baseline passes challenge
    Given a workspace with README intent
    And the workspace has the process reference
    And the workspace has ordered evolution markers
    When the developer runs `probe challenge`
    Then the system reports that the baseline probe materials are present
    And the command succeeds.
