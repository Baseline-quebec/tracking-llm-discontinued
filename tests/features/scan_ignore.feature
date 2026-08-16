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
