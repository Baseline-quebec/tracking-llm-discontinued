Feature: Model deprecation detection
  The scanner should identify deprecated or retiring models
  and provide lifecycle information including shutdown dates and replacements.

  Scenario Outline: Detect deprecated models
    Given a model name "<model>"
    When I check its deprecation status
    Then the model should be "<status>"
    And the replacement should be "<replacement>"

    Examples:
      | model                  | status     | replacement           |
      | gpt-3.5-turbo          | deprecated | gpt-4.1-mini          |
      | gpt-4                  | retiring   | gpt-4.1               |
      | gpt-4-turbo            | retiring   | gpt-4.1               |
      | gpt-4-turbo-preview    | retiring   | gpt-4.1               |
      | gpt-4o                 | retiring   | gpt-4.1               |
      | gpt-4o-mini            | retiring   | gpt-4.1-mini          |
      | o1                     | retiring   | o3                    |
      | o1-preview             | shutdown   | o3                    |
      | o1-mini                | shutdown   | o4-mini               |
      | text-embedding-ada-002 | retiring   | text-embedding-3-small |
      | claude-3.5-sonnet      | shutdown   | claude-sonnet-4       |
      | claude-3.5-haiku       | deprecated | claude-haiku-4-5      |
      | claude-3-opus          | shutdown   | claude-opus-4         |
      | claude-3-sonnet        | shutdown   | claude-sonnet-4       |
      | gemini-2.0-flash       | retiring   | gemini-2.5-flash      |
      | gemini-1.5-pro         | shutdown   | gemini-2.5-pro        |
      | gemini-1.5-flash       | shutdown   | gemini-2.5-flash      |
      | gemini-pro             | shutdown   | gemini-2.5-pro        |

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
      | gpt-4.1-mini           |
      | gpt-5                  |
      | gpt-5.1                |
      | o3                     |
      | o4-mini                |
      | claude-opus-4          |
      | claude-sonnet-4        |
      | gemini-2.5-pro         |
      | gemini-2.5-flash       |
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
