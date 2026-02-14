Feature: Validate pattern coverage against registry
  The validate_patterns module should check which registry
  models are matched by existing regex patterns.

  Scenario: All known models are covered
    Given a temporary registry with the following models:
      | model              | provider  | status     |
      | gpt-4o             | openai    | retiring   |
      | claude-3-opus      | anthropic | deprecated |
    When I validate pattern coverage
    Then I should have 0 unmatched models

  Scenario: Unknown models are reported as unmatched
    Given a temporary registry with the following models:
      | model              | provider  | status     |
      | gpt-4o             | openai    | retiring   |
      | fake-model-xyz     | openai    | deprecated |
    When I validate pattern coverage
    Then I should have 1 unmatched models

  Scenario: Category entries with spaces are ignored
    Given a temporary registry with the following models:
      | model              | provider  | status     |
      | Chat model updates | openai    | retiring   |
      | gpt-4o             | openai    | retiring   |
    When I validate pattern coverage
    Then I should have 0 unmatched models
    And "chat model updates" should not appear in matched or unmatched
