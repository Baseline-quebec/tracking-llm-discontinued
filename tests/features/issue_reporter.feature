Feature: GitHub Issue creation for deprecated models
  The issue reporter should create well-formatted GitHub issues
  for deprecated models, with deduplication and dry-run support.

  Scenario: Build title for retiring model
    Given a model lifecycle for "gpt-4o" with status "retiring"
    When I build the issue title
    Then the title should contain "gpt-4o"
    And the title should start with "⚠️"

  Scenario: Build title for deprecated model
    Given a model lifecycle for "gpt-3.5-turbo" with status "deprecated"
    When I build the issue title
    Then the title should contain "gpt-3.5-turbo"
    And the title should start with "🚫"

  Scenario: Build title for shutdown model
    Given a model lifecycle for "o1-preview" with status "shutdown"
    When I build the issue title
    Then the title should contain "o1-preview"
    And the title should start with "🔴"

  Scenario: Build body contains required sections
    Given a deprecation alert for "gpt-4o" in file "config.py" at line 5
    When I build the issue body
    Then the body should contain "gpt-4o"
    And the body should contain "### Affected files"
    And the body should contain "config.py"
    And the body should contain "### Action required"

  Scenario: Dry run does not call gh CLI
    Given a list of deprecation alerts for models "gpt-4o,gpt-3.5-turbo"
    When I create issues in dry-run mode
    Then 2 issues should be reported as created
    And gh CLI should not have been called

  Scenario: Issues are grouped by model
    Given a list of deprecation alerts with "gpt-4o" in 3 different files
    When I create issues in dry-run mode
    Then 1 issues should be reported as created

  Scenario: Empty alerts list creates no issues
    Given an empty list of deprecation alerts
    When I create issues in dry-run mode
    Then 0 issues should be reported as created

  Scenario: Validate assignees filters invalid usernames
    Given assignees "dominique,invalid user!,bob"
    When I validate the assignees
    Then valid assignees should be "dominique,bob"
