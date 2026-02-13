Feature: Repository file scanner
  The scanner should walk a directory tree and find LLM model references
  in source code and configuration files.

  Scenario: Scan a directory with Python files containing LLM references
    Given a temporary directory with the following files:
      | path             | content                          |
      | config.py        | MODEL = "gpt-4o"                 |
      | utils.py         | model = "claude-3.5-sonnet"      |
    When I scan the directory for repo "test-repo"
    Then I should find 2 scan matches
    And the results should contain model "gpt-4o"
    And the results should contain model "claude-3.5-sonnet"

  Scenario: Scanner deduplicates same model in same file
    Given a temporary directory with the following files:
      | path         | content                                        |
      | config.py    | MODEL = "gpt-4o"\nFALLBACK = "gpt-4o"          |
    When I scan the directory for repo "test-repo"
    Then I should find 1 scan matches

  Scenario: Scanner skips excluded directories
    Given a temporary directory with the following files:
      | path                         | content                   |
      | src/main.py                  | model = "gpt-4o"          |
      | node_modules/dep/index.js    | model = "gpt-4-turbo"     |
    When I scan the directory for repo "test-repo"
    Then I should find 1 scan matches
    And the results should contain model "gpt-4o"

  Scenario: Scanner skips files with unsupported extensions
    Given a temporary directory with the following files:
      | path           | content              |
      | image.png      | gpt-4o               |
      | config.py      | model = "gpt-4o"     |
    When I scan the directory for repo "test-repo"
    Then I should find 1 scan matches

  Scenario: Scanner handles empty directory
    Given an empty temporary directory
    When I scan the directory for repo "test-repo"
    Then I should find 0 scan matches

  Scenario: Synthetic test - YAML config (librairies-martin-chatbot style)
    Given a temporary directory with the following files:
      | path        | content                                                                                    |
      | config.yml  | completion_model: "gpt-4o-mini"\nfallback_model: "gpt-4o"\nembedding_model: "text-embedding-ada-002" |
    When I scan the directory for repo "librairies-martin-chatbot"
    Then I should find 3 scan matches
    And the results should contain model "gpt-4o-mini"
    And the results should contain model "gpt-4o"
    And the results should contain model "text-embedding-ada-002"

  Scenario: Synthetic test - Python config (competences-quebec style)
    Given a temporary directory with the following files:
      | path              | content                                                                              |
      | src/config.py     | OPENAI_COMPLETION_MODEL = config("OPENAI_COMPLETION_MODEL", default="gpt-4o")        |
    When I scan the directory for repo "competences-quebec-chatbot"
    Then I should find 1 scan matches
    And the results should contain model "gpt-4o"

  Scenario: Synthetic test - Python class config (yvan style)
    Given a temporary directory with the following files:
      | path                  | content                                                    |
      | src/config.py         | model: ClassVar[str] = "gpt-5.1"\nembedding_model = "text-embedding-3-small" |
    When I scan the directory for repo "yvan"
    Then I should find 2 scan matches
    And the results should contain model "gpt-5.1"
    And the results should contain model "text-embedding-3-small"

