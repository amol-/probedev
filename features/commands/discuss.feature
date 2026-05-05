@feature:F-COMMANDS-DISCUSS
Feature: Discuss README intent

  Developers use discussion to clarify product intent before choosing architecture.

  Rules:
    - Discussion works from README-level intent.
    - Discussion asks product questions rather than implementation questions.
    - Missing README intent is reported as a user-visible problem.

  @id:F-COMMANDS-DISCUSS-S001
  Scenario: Existing README intent produces product questions
    Given a workspace with README intent
    When the developer runs `probe discuss`
    Then the system reports the README being discussed
    And the system prints questions about users, workflows, scope, and completion.

  @id:F-COMMANDS-DISCUSS-S002
  Scenario: Missing README intent blocks discussion
    Given a workspace without README intent
    When the developer runs `probe discuss`
    Then the system reports that no README was found
    And the command fails.
