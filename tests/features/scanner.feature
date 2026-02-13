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

  Scenario: Broad test - librairies-martin-chatbot full project structure
    Given a temporary directory with the following files:
      | path                                              | content                                                                                                    |
      | config.yml                                        | completion_model: "gpt-4o-mini"\nfallback_model: "gpt-4o"\nembedding_model: "text-embedding-ada-002"       |
      | pyproject.toml                                    | [tool.poetry.dependencies]\nopenai = "^1.0"                                                                |
      | src/chatbot/chain.py                              | from openai import OpenAI\nllm = OpenAI(model="gpt-4o-mini")                                              |
      | src/chatbot/embedding.py                          | from openai import OpenAI\nembedding = OpenAI(model="text-embedding-ada-002")                              |
      | tests/unit_testing/test_chain.py                  | mock_llm = OpenAI(model="gpt-4", temperature=0)                                                           |
      | tests/unit_testing/test_callbacks.py              | model = "gpt-4o-mini"                                                                                      |
      | CHANGELOG.md                                      | ## v1.0\n- Migrated from gpt-4 to gpt-4o-mini                                                             |
    When I scan the directory for repo "librairies-martin-chatbot"
    Then I should find at least 6 scan matches
    And the results should contain model "gpt-4o-mini"
    And the results should contain model "gpt-4o"
    And the results should contain model "text-embedding-ada-002"
    And the results should contain model "gpt-4"

  Scenario: Broad test - yvan full project structure
    Given a temporary directory with the following files:
      | path                                              | content                                                                                          |
      | apps/backend/src/yvan/containers/config.py        | model: ClassVar[str] = "gpt-5.1"\ntemperature: float = 0.7                                       |
      | apps/backend/src/yvan/infra/embedding/openai.py   | from openai import OpenAI\nembedding_model = "text-embedding-3-large"                            |
      | apps/backend/src/yvan/infra/llm/openai_llm.py     | client = OpenAI()\nresponse = client.chat.completions.create(model="gpt-5.1")                    |
      | apps/backend/pyproject.toml                       | [tool.poetry.dependencies]\nopenai = "^1.0"                                                      |
      | apps/backend/CHANGELOG.md                         | ## v2.0\n- Upgraded to gpt-5-chat from gpt-4o                                                   |
      | apps/frontend/package.json                        | {"dependencies": {"next": "14.0"}}                                                               |
    When I scan the directory for repo "yvan"
    Then I should find at least 4 scan matches
    And the results should contain model "gpt-5.1"
    And the results should contain model "text-embedding-3-large"
    And the results should contain model "gpt-5-chat"

  Scenario: Broad test - mixed project with deprecated and active models
    Given a temporary directory with the following files:
      | path                    | content                                                                                              |
      | config/llm.yml          | primary_model: "gpt-4.1"\nfallback_model: "gpt-4o"\nlegacy_model: "gpt-3.5-turbo"                    |
      | config/embeddings.yml   | model: "text-embedding-3-small"\nlegacy: "text-embedding-ada-002"                                    |
      | src/agent.py            | from openai import OpenAI\nllm = OpenAI(model="gpt-4.1-mini")                                        |
      | src/rag/retriever.py    | embedding = OpenAI(model="text-embedding-3-small")                                                    |
      | src/legacy/old_bot.py   | model = "o1-preview"\nfallback = "gpt-4-turbo"                                                       |
      | docker-compose.yml      | environment:\n  - MODEL_NAME=claude-sonnet-4\n  - EMBEDDING=text-embedding-3-large                   |
    When I scan the directory for repo "mixed-project"
    Then I should find at least 8 scan matches
    And the results should contain model "gpt-4.1"
    And the results should contain model "gpt-4o"
    And the results should contain model "gpt-3.5-turbo"
    And the results should contain model "o1-preview"
    And the results should contain model "gpt-4-turbo"
    And the results should contain model "claude-sonnet-4"
