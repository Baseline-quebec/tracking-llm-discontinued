Feature: Mise a jour du registre depuis le flux deprecations.info
  Le script de mise a jour doit recuperer le flux, fusionner avec le
  registre existant et sauvegarder. Les entrees du flux priment sur
  les entrees existantes.

  Scenario: La mise a jour ajoute de nouveaux modeles depuis le flux
    Given a registry with 2 models
    And a feed returning 1 new model "claude-3-opus" from "Anthropic"
    When I run the registry update
    Then the registry should have 3 models
    And the registry should contain "claude-3-opus"

  Scenario: Un flux vide laisse le registre inchange
    Given a registry with 2 models
    And a feed returning no data
    When I run the registry update
    Then the registry should have 2 models
