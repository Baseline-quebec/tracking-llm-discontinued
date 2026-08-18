Feature: Scan exclusions declared by the scanned repository
  A repository can declare, in a .llm-scan-ignore file at its root, the paths
  that hold data rather than configuration. The scanner matches strings, not
  meaning, so prose quoting a model name is indistinguishable from a model
  being configured.

  Scenario: A file listed in .llm-scan-ignore is not scanned
    Given a temporary directory with the following files:
      | path              | content                                        |
      | config.py         | MODEL = "gpt-4o"                               |
      | seed_articles.py  | TLDR = "il faut migrer vers o4-mini avant juin"|
      | .llm-scan-ignore  | seed_articles.py                               |
    When I scan the directory for repo "test-repo"
    Then I should find 1 scan matches
    And the results should contain model "gpt-4o"

  Scenario: A bare filename excludes that file at any depth
    Given a temporary directory with the following files:
      | path                          | content            |
      | src/app.py                    | model = "gpt-4o"   |
      | src/data/deep/seed.py         | model = "gpt-4"    |
      | .llm-scan-ignore              | seed.py            |
    When I scan the directory for repo "test-repo"
    Then I should find 1 scan matches
    And the results should contain model "gpt-4o"

  Scenario: A directory pattern excludes everything under it
    Given a temporary directory with the following files:
      | path                       | content              |
      | src/app.py                 | model = "gpt-4o"     |
      | fixtures/a.py              | model = "gpt-4"      |
      | fixtures/nested/b.py       | model = "gpt-4-turbo"|
      | .llm-scan-ignore           | fixtures/            |
    When I scan the directory for repo "test-repo"
    Then I should find 1 scan matches
    And the results should contain model "gpt-4o"

  Scenario: A glob pattern excludes matching files
    Given a temporary directory with the following files:
      | path                  | content            |
      | src/app.py            | model = "gpt-4o"   |
      | src/app_seed.py       | model = "gpt-4"    |
      | .llm-scan-ignore      | *_seed.py          |
    When I scan the directory for repo "test-repo"
    Then I should find 1 scan matches
    And the results should contain model "gpt-4o"

  Scenario: Comments and blank lines are ignored in the exclusion file
    Given a temporary directory with the following files:
      | path              | content                                       |
      | src/app.py        | model = "gpt-4o"                              |
      | src/seed.py       | model = "gpt-4"                               |
      | .llm-scan-ignore  | # donnee de veille, pas de la config\n\nseed.py |
    When I scan the directory for repo "test-repo"
    Then I should find 1 scan matches
    And the results should contain model "gpt-4o"

  Scenario: Without an exclusion file every file is still scanned
    Given a temporary directory with the following files:
      | path              | content            |
      | src/app.py        | model = "gpt-4o"   |
      | src/seed.py       | model = "gpt-4"    |
    When I scan the directory for repo "test-repo"
    Then I should find 2 scan matches

  Scenario: Patterns passed by the action add to those of the repository
    Given a temporary directory with the following files:
      | path              | content            |
      | src/app.py        | model = "gpt-4o"   |
      | src/seed.py       | model = "gpt-4"    |
      | .llm-scan-ignore  | seed.py            |
    When I scan the directory for repo "test-repo" excluding "src/app.py"
    Then I should find 0 scan matches

  Scenario: An unreadable exclusion file does not stop the scan
    Given a temporary directory with the following files:
      | path        | content          |
      | src/app.py  | model = "gpt-4o" |
    And the exclusion file is a directory
    When I scan the directory for repo "test-repo"
    Then I should find 1 scan matches

  Scenario Outline: Pattern matching against a relative path
    Given the exclusion patterns "<patterns>"
    Then the path "<path>" should be <verdict>

    Examples:
      | patterns          | path                        | verdict  |
      | seed.py           | src/data/seed.py            | excluded |
      | seed.py           | src/data/seed_other.py      | kept     |
      | src/data/         | src/data/deep/seed.py       | excluded |
      | src/data          | src/database.py             | kept     |
      | *.json            | data/registry.json          | excluded |
      | docs/*.md         | docs/guide.md               | excluded |
      | data              | src/data_seed.py            | kept     |
      | /                 | src/app.py                  | kept     |

  # Regression du 2026-08-18 dans Ventes : la PR #154 a remonte la racine du
  # depot d'un niveau, le fichier d'exclusion s'est retrouve dans ODS/, et les
  # issues #155 a #159 sont revenues sur les memes offres de service.
  Scenario: An exclusion file in a subdirectory covers that subtree
    Given a temporary directory with the following files:
      | path                  | content                                       |
      | ODS/.llm-scan-ignore  | # offres de service, pas de la configuration\n* |
      | ODS/Evolia/audit.md   | Le systeme audite utilise le modele gpt-4o.   |
      | ODS/note.md           | model = "gemini-pro"                          |
      | formations/app.py     | MODEL = "claude-3-opus"                       |
    When I scan the directory for repo "test-repo"
    Then I should find 1 scan matches
    And the results should contain model "claude-3-opus"

  Scenario: Patterns of a subdirectory are relative to that subdirectory
    Given a temporary directory with the following files:
      | path                  | content                  |
      | ODS/.llm-scan-ignore  | Mandat/                  |
      | ODS/Mandat/sow.md     | model = "gpt-4o"         |
      | Mandat/app.py         | MODEL = "claude-3-opus"  |
    When I scan the directory for repo "test-repo"
    Then I should find 1 scan matches
    And the results should contain model "claude-3-opus"

  Scenario: A subdirectory already excluded at the root is not reopened
    Given a temporary directory with the following files:
      | path                  | content            |
      | .llm-scan-ignore      | ODS/               |
      | ODS/.llm-scan-ignore  | *.py               |
      | ODS/audit.md          | model = "gpt-4o"   |
      | app.py                | MODEL = "gpt-4"    |
    When I scan the directory for repo "test-repo"
    Then I should find 1 scan matches
    And the results should contain model "gpt-4"
