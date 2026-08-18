Feature: CLI entry point and orchestration
  The main module should parse CLI arguments, orchestrate the scan,
  detect deprecated models, and produce GitHub Actions outputs.

  Scenario: Parse valid CLI arguments
    Given CLI arguments "--repo-name test-repo --scan-path /tmp --assignees dominique --dry-run"
    When I parse the arguments
    Then repo_name should be "test-repo"
    And scan_path should be "/tmp"
    And assignees should be "dominique"
    And dry_run should be true

  Scenario: Parse minimal CLI arguments
    Given CLI arguments "--repo-name my-repo"
    When I parse the arguments
    Then repo_name should be "my-repo"
    And scan_path should be "."
    And dry_run should be false

  Scenario: Find deprecated models in scan results
    Given scan matches with models "gpt-4o,gpt-5.1,text-embedding-ada-002"
    When I check for deprecated models
    Then I should find 2 deprecated alerts
    And the deprecated models should include "gpt-4o"
    And the deprecated models should include "text-embedding-ada-002"

  Scenario: Build deprecated summary deduplicates models
    Given deprecation alerts for "gpt-4o" appearing 3 times
    When I build the deprecated summary
    Then the summary should have 1 entries

  Scenario: Set GitHub output writes correct format
    Given a temporary GITHUB_OUTPUT file
    When I set output "match-count" to "5"
    Then the output file should contain "match-count<<EOF"
    And the output file should contain "5"

  Scenario: Scan directory with deprecated models end-to-end
    Given a temporary directory with the following files:
      | path        | content                      |
      | config.py   | model = "gpt-4o"             |
    When I run main in dry-run for repo "test-repo"
    Then the exit code should be 0

  Scenario: End-to-end librairies-martin-chatbot style project
    Given a temporary directory with the following files:
      | path                                  | content                                                                                                    |
      | config.yml                            | completion_model: "gpt-4o-mini"\nfallback_model: "gpt-4o"\nembedding_model: "text-embedding-ada-002"       |
      | src/chatbot/chain.py                  | from openai import OpenAI\nllm = OpenAI(model="gpt-4o-mini")                                              |
      | src/chatbot/embedding.py              | from openai import OpenAI\nembedding = OpenAI(model="text-embedding-ada-002")                              |
      | tests/unit_testing/test_chain.py      | mock_llm = OpenAI(model="gpt-4", temperature=0)                                                           |
    When I scan and check deprecations for repo "librairies-martin-chatbot"
    Then I should find at least 3 deprecated references
    And deprecated models should include "gpt-4o-mini"
    And deprecated models should include "gpt-4o"
    And deprecated models should include "text-embedding-ada-002"
    # Le `gpt-4` de la fixture ne sert qu'a faire passer un test : rien ne
    # l'appelle, et le migrer ne change rien a ce qui repond en production.
    And deprecated models should not include "gpt-4"

  Scenario: End-to-end yvan style project has no deprecations
    Given a temporary directory with the following files:
      | path                                              | content                                                          |
      | apps/backend/src/yvan/containers/config.py        | model: ClassVar[str] = "gpt-5.1"                                 |
      | apps/backend/src/yvan/infra/embedding/openai.py   | embedding_model = "text-embedding-3-large"                       |
      | apps/backend/pyproject.toml                       | [tool.poetry.dependencies]\nopenai = "^1.0"                      |
    When I scan and check deprecations for repo "yvan"
    Then I should find 0 deprecated references

  Scenario: End-to-end mixed project separates deprecated from active
    Given a temporary directory with the following files:
      | path                    | content                                                                          |
      | config/llm.yml          | primary_model: "gpt-4.1"\nfallback_model: "gpt-4o"\nlegacy_model: "gpt-3.5-turbo" |
      | config/embeddings.yml   | model: "text-embedding-3-small"\nlegacy: "text-embedding-ada-002"                 |
      | src/legacy/old_bot.py   | model = "o1-preview"\nfallback = "gpt-4-turbo"                                    |
    When I scan and check deprecations for repo "mixed-project"
    Then I should find at least 5 deprecated references
    And deprecated models should include "gpt-4o"
    And deprecated models should include "gpt-3.5-turbo"
    And deprecated models should include "text-embedding-ada-002"
    And deprecated models should include "o1-preview"
    And deprecated models should include "gpt-4-turbo"
    And active models should not be flagged: "gpt-4.1,text-embedding-3-small"
