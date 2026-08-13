Feature: Organisation-wide sweep for deprecated models
  The per-repository action only runs on pull requests, so it catches a
  deprecated model being introduced. It cannot catch drift: when a provider
  deprecates a model, the registry changes but the repository code does not,
  no pull request is opened, and nothing runs. The monthly sweep clones every
  repository in the organisation and scans it against the current registry.

  Scenario: Archived repositories are excluded from the sweep
    Given the organisation lists an active repository and an archived repository
    When I list the repositories to sweep
    Then only the active repository should be listed

  Scenario: Repositories with issues disabled are skipped
    Given the organisation lists a repository with issues disabled
    When I list the repositories to sweep
    Then no repository should be listed

  Scenario: Explicitly excluded repositories are skipped
    Given the organisation lists repositories "org/alpha" and "org/beta"
    When I list the repositories excluding "beta"
    Then only "org/alpha" should be listed

  Scenario: A failed repository listing returns nothing rather than crashing
    Given the repository listing command fails
    When I list the repositories to sweep
    Then no repository should be listed

  Scenario: Issues are created in the scanned repository, not the runner repository
    Given a repository referencing a deprecated model
    When I sweep that repository
    Then the issue should be created in that repository
    And one issue should be reported as created

  Scenario: A repository that cannot be cloned does not stop the sweep
    Given a repository that cannot be cloned
    When I sweep that repository
    Then the result should report a clone failure
    And the repository should not be marked as scanned

  Scenario: A clean repository produces no issue
    Given a repository referencing only supported models
    When I sweep that repository
    Then no issue should be created
    And the repository should be marked as scanned

  Scenario: The summary lists affected repositories
    Given sweep results with one affected repository and one failure
    When I build the summary
    Then the summary should name the affected repository
    And the summary should name the failed repository

  Scenario: A clean organisation says so explicitly
    Given sweep results with no affected repository
    When I build the summary
    Then the summary should state that no deprecated model was found

  Scenario: An empty repository listing fails the run instead of passing green
    Given no repository can be listed
    When I run the sweep
    Then the run should fail
