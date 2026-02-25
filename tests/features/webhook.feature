Feature: Webhook notifications for CRM integration
  After creating GitHub issues for deprecated models, the scanner
  can send issue details via HTTP POST to a webhook URL.
  The webhook is optional and failures never block issue creation.

  Scenario: Payload contains all required fields
    Given a webhook payload for model "gpt-4o" in repo "org/repo"
    Then the payload should contain field "repo_name" with value "org/repo"
    And the payload should contain field "model" with value "gpt-4o"
    And the payload should contain field "provider" with value "openai"
    And the payload should contain field "status" with value "retiring"
    And the payload should contain field "shutdown_date"
    And the payload should contain field "affected_files"
    And the payload should contain field "issue_url"
    And the payload should contain field "issue_title"
    And the payload should contain field "issue_body"
    And the payload should contain field "assignees"
    And the payload should contain field "timestamp"

  Scenario: Successful POST returns True
    Given a webhook URL that returns HTTP 200
    When I send the webhook
    Then the webhook result should be True

  Scenario: HTTP 500 returns False without raising
    Given a webhook URL that returns HTTP 500
    When I send the webhook
    Then the webhook result should be False

  Scenario: Network error returns False without raising
    Given a webhook URL that causes a network error
    When I send the webhook
    Then the webhook result should be False

  Scenario: Timeout returns False without raising
    Given a webhook URL that times out
    When I send the webhook
    Then the webhook result should be False

  Scenario: Dry run logs payload without POST
    Given a webhook URL that returns HTTP 200
    When I send the webhook in dry-run mode
    Then the webhook result should be True
    And no HTTP request should have been made
