Feature: Model deprecation detection
  The scanner should identify deprecated or retiring models
  and provide deprecation information including shutdown dates.

  Scenario Outline: Detect deprecated models
    Given a model name "<model>"
    When I check its deprecation status
    Then the model should be "<status>"

    Examples:
      | model                  | status     |
      | claude-3.5-haiku       | deprecated |
      | gpt-3.5-turbo          | retiring   |
      | gpt-4o                 | retiring   |
      | o1-preview             | shutdown   |
      | text-embedding-ada-002 | retiring   |

  Scenario Outline: Date-suffixed models match base deprecation
    Given a model name "<model>"
    When I check its deprecation status
    Then the model should be "<status>"

    Examples:
      | model                      | status   |
      | gpt-4o-2024-08-06          | retiring |
      | claude-3.5-sonnet-20241022 | shutdown |
      | claude-3-opus-20240229     | shutdown |

  Scenario Outline: Active models are not flagged
    Given a model name "<model>"
    When I check its deprecation status
    Then the model should not be deprecated

    Examples:
      | model                  |
      | gpt-4.1                |
      | claude-opus-4          |
      | claude-haiku-4         |
      | text-embedding-3-small |

  Scenario: Scan config with deprecated models flags them
    Given a temporary directory with the following files:
      | path        | content                                                                                    |
      | config.yml  | completion_model: "gpt-4o-mini"\nfallback_model: "gpt-4o"\nembedding_model: "text-embedding-ada-002" |
    When I scan and check deprecations for repo "test-repo"
    Then I should find 3 deprecation alerts
    And the alerts should include model "gpt-4o-mini" with status "retiring"
    And the alerts should include model "gpt-4o" with status "retiring"
    And the alerts should include model "text-embedding-ada-002" with status "retiring"

  Scenario: Scan config with only active models has no alerts
    Given a temporary directory with the following files:
      | path          | content                              |
      | config.py     | model: ClassVar[str] = "gpt-5.1"    |
    When I scan and check deprecations for repo "test-repo"
    Then I should find 0 deprecation alerts
