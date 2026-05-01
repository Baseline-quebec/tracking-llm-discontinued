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

  Scenario: Le flux prime sur le registre statique
    Given a registry with model "gpt-4o" status "retiring"
    And a feed returning model "gpt-4o" with status "shutdown"
    When I run the registry update
    Then the registry should contain "gpt-4o" with status "shutdown"

  Scenario: update_readme met a jour le tableau
    Given a README with registry markers
    And a registry with 2 models
    When I call update_readme
    Then the README should contain a registry table

  Scenario: update_readme sans marqueurs retourne False
    Given a README without registry markers
    And a registry with 2 models
    When I call update_readme
    Then update_readme should return False

  Scenario: Un flux vide declenche la creation d'issue
    Given a registry with 2 models
    And a feed returning no data
    When I run the registry update
    Then _create_feed_failure_issue should have been called

  Scenario: Le flux avec modele duplique garde la derniere entree
    Given a registry with 2 models
    And a feed with duplicate model "gpt-4o"
    When I run the registry update
    Then the registry should contain "gpt-4o" with status "shutdown"

  Scenario: update_readme retourne False si le fichier est introuvable
    Given a README path that does not exist
    And a registry with 2 models
    When I call update_readme
    Then update_readme should return False
