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

  Scenario: Scanner skips minified files
    Given a temporary directory with the following files:
      | path                          | content            |
      | src/main.py                   | model = "gpt-4o"   |
      | assets/ace.min.js             | model = "gpt-4"    |
      | assets/ext-min-modelist.js    | model = "gpt-4"    |
    When I scan the directory for repo "test-repo"
    Then I should find 1 scan matches
    And the results should contain model "gpt-4o"

  Scenario: Scanner ignores a machine-generated line
    Given a temporary directory with a very long line mentioning "ada" and the word model
    When I scan the directory for repo "test-repo"
    Then I should find 0 scan matches

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

  Scenario: Scanner skips files larger than 1MB
    Given a temporary directory with a large file "big.py" containing "gpt-4o"
    When I scan the directory for repo "test-repo"
    Then I should find 0 scan matches

  Scenario: Scanner handles non-existent directory
    Given a non-existent scan path
    When I scan the directory for repo "test-repo"
    Then I should find 0 scan matches

  Scenario: Scanner picks up files matched by name (Dockerfile, Makefile, .env)
    Given a temporary directory with the following files:
      | path        | content              |
      | Dockerfile  | ENV MODEL=gpt-4o     |
      | Makefile    | model: claude-3-opus |
      | .env        | MODEL=gpt-4-turbo    |
    When I scan the directory for repo "test-repo"
    Then I should find 3 scan matches
    And the results should contain model "gpt-4o"
    And the results should contain model "claude-3-opus"
    And the results should contain model "gpt-4-turbo"

  Scenario: Scanner honore l'exclusion complete declaree par le depot
    Given a temporary directory with the following files:
      | path                | content                                        |
      | .llm-scan-ignore    | # depot d'offres de service\n*                 |
      | ODS/audit.md        | La solution proposee utilise le modele gpt-4o. |
      | ODS/Mandat/sow.md   | model = "claude-3-opus"                        |
    When I scan the directory for repo "test-repo"
    Then I should find 0 scan matches

  Scenario: Une reinjection garde le code scanne dans un depot exclu
    Given a temporary directory with the following files:
      | path              | content                                        |
      | .llm-scan-ignore  | *\n!src/                                       |
      | ODS/audit.md      | La solution proposee utilise le modele gpt-4o. |
      | src/client.py     | MODEL = "gpt-4o"                               |
    When I scan the directory for repo "test-repo"
    Then I should find 1 scan matches
    And the results should contain model "gpt-4o"

  Scenario: Une regle de dossier exclut tout ce qui se trouve dessous
    Given a temporary directory with the following files:
      | path                 | content                  |
      | .llm-scan-ignore     | docs/                    |
      | docs/deep/spec.md    | model = "gpt-4o"         |
      | app.py               | MODEL = "claude-3-opus"  |
    When I scan the directory for repo "test-repo"
    Then I should find 1 scan matches
    And the results should contain model "claude-3-opus"

  Scenario: Une regle sans separateur vise un nom a toute profondeur
    Given a temporary directory with the following files:
      | path                 | content                  |
      | .llm-scan-ignore     | *.md                     |
      | ODS/Mandat/audit.md  | model = "gpt-4o"         |
      | app.py               | MODEL = "claude-3-opus"  |
    When I scan the directory for repo "test-repo"
    Then I should find 1 scan matches
    And the results should contain model "claude-3-opus"

  Scenario: Une ligne commentee n'exclut rien
    Given a temporary directory with the following files:
      | path              | content            |
      | .llm-scan-ignore  | # *\n\n            |
      | app.py            | MODEL = "gpt-4o"   |
    When I scan the directory for repo "test-repo"
    Then I should find 1 scan matches
    And the results should contain model "gpt-4o"

  Scenario: Un depot sans fichier d'exclusion reste scanne en entier
    Given a temporary directory with the following files:
      | path              | content            |
      | app.py            | MODEL = "gpt-4o"   |
    When I scan the directory for repo "test-repo"
    Then I should find 1 scan matches
