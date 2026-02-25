Feature: GitHub Issue creation for deprecated models
  The issue reporter should create well-formatted GitHub issues
  for deprecated models, with deduplication and dry-run support.
  Issue content is in French.

  Scenario: Build title for retiring model
    Given a model lifecycle for "gpt-4o" with status "retiring"
    When I build the issue title
    Then the title should contain "gpt-4o"
    And the title should start with "Modèle déprécié"

  Scenario: Build title for deprecated model
    Given a model lifecycle for "gpt-3.5-turbo" with status "deprecated"
    When I build the issue title
    Then the title should contain "gpt-3.5-turbo"
    And the title should start with "Modèle déprécié"

  Scenario: Build title for shutdown model
    Given a model lifecycle for "o1-preview" with status "shutdown"
    When I build the issue title
    Then the title should contain "o1-preview"
    And the title should start with "Modèle déprécié"

  Scenario: Build body contains required sections
    Given a deprecation alert for "gpt-4o" in file "config.py" at line 5
    When I build the issue body
    Then the body should contain "gpt-4o"
    And the body should contain "### Fichiers affectés"
    And the body should contain "config.py"
    And the body should contain "### Action requise"

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

  Scenario: gh CLI failure is handled gracefully
    Given a list of deprecation alerts for models "gpt-4o"
    When I create issues with gh CLI failing
    Then 0 issues should be reported as created

  Scenario: gh CLI timeout is handled gracefully
    Given a list of deprecation alerts for models "gpt-4o"
    When I create issues with gh CLI timing out
    Then 0 issues should be reported as created

  Scenario: Webhook is called after issue creation
    Given a list of deprecation alerts for models "gpt-4o"
    When I create issues with webhook enabled
    Then 1 issues should be reported as created
    And webhook should have been called 1 time

  Scenario: Webhook failure does not block issue creation
    Given a list of deprecation alerts for models "gpt-4o"
    When I create issues with webhook failing
    Then 1 issues should be reported as created
