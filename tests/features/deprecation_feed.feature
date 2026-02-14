Feature: Deprecation feed fetching with retry
  The feed fetcher should retry on transient failures and return
  results once a successful attempt completes.

  Scenario: Retry succeeds after transient failures
    Given a feed endpoint that fails 2 times then succeeds
    When I fetch deprecations
    Then I should receive deprecation data

  Scenario: All retries exhausted returns empty list
    Given a feed endpoint that always fails
    When I fetch deprecations
    Then I should receive an empty list
