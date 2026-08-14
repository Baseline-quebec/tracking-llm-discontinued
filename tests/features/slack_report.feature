Feature: Consolidated sweep report sent to Slack
  The monthly sweep ships its structured result to a Windmill webhook, which
  formats it and posts it to Slack. Formatting lives in baseline-automation, so
  this module only has to ship the data and never break the sweep when Slack or
  Windmill is unreachable.

  Scenario: The report is skipped when Windmill is not configured
    Given Windmill is not configured
    When I send the report
    Then no HTTP request should have been made
    And the result should be False

  Scenario: A partial configuration is treated as no configuration
    Given only the Windmill URL is configured
    When I send the report
    Then no HTTP request should have been made
    And the result should be False

  Scenario: The payload carries the report type and the affected repositories
    Given Windmill is configured
    When I send the report for 2 affected repositories out of 82
    Then the payload should declare the report type "modeles"
    And the payload should list 2 repositories
    And the payload should declare 82 scanned repositories
    And the request should carry the Windmill token

  Scenario: An empty report is still sent
    Given Windmill is configured
    When I send the report for 0 affected repositories out of 82
    Then the request should have been made
    And the payload should list 0 repositories

  Scenario: An HTTP error never breaks the sweep
    Given Windmill is configured
    And Windmill returns HTTP 500
    When I send the report
    Then the result should be False

  Scenario: An unreachable Windmill never breaks the sweep
    Given Windmill is configured
    And Windmill is unreachable
    When I send the report
    Then the result should be False
