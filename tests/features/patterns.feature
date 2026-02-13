Feature: LLM model pattern detection
  The scanner should detect LLM models, embeddings, and frameworks
  in lines of text using regex patterns.

  Scenario Outline: Detect standard LLM models
    Given a line containing "<line>"
    When I scan the line for matches
    Then I should find model "<model>" from provider "<provider>"
    And the match type should be "<match_type>"

    Examples:
      | line                             | model              | provider  | match_type |
      | model = "gpt-4o"                 | gpt-4o             | openai    | llm        |
      | model = "gpt-4o-mini"            | gpt-4o-mini        | openai    | llm        |
      | model: gpt-4-turbo               | gpt-4-turbo        | openai    | llm        |
      | model: gpt-4-turbo-preview       | gpt-4-turbo-preview | openai   | llm        |
      | model = "gpt-4"                  | gpt-4              | openai    | llm        |
      | model: gpt-3.5-turbo             | gpt-3.5-turbo      | openai    | llm        |
      | model_name = "claude-opus-4"     | claude-opus-4      | anthropic | llm        |
      | model_name = "claude-sonnet-4"   | claude-sonnet-4    | anthropic | llm        |
      | model: claude-3.5-sonnet         | claude-3.5-sonnet  | anthropic | llm        |
      | model: claude-3.5-haiku          | claude-3.5-haiku   | anthropic | llm        |
      | model: claude-3-opus             | claude-3-opus      | anthropic | llm        |
      | model: claude-3-sonnet           | claude-3-sonnet    | anthropic | llm        |
      | model: claude-3-haiku            | claude-3-haiku     | anthropic | llm        |
      | model = "gemini-2.0-flash"       | gemini-2.0-flash   | google    | llm        |
      | model: gemini-1.5-pro            | gemini-1.5-pro     | google    | llm        |
      | model = "gemini-1.5-flash"       | gemini-1.5-flash   | google    | llm        |
      | model: gemini-pro                | gemini-pro         | google    | llm        |
      | model = "mistral-large"          | mistral-large      | mistral   | llm        |
      | model: mistral-medium            | mistral-medium     | mistral   | llm        |
      | model = "mistral-small"          | mistral-small      | mistral   | llm        |
      | model: mixtral                   | mixtral            | mistral   | llm        |
      | model = "codestral"             | codestral          | mistral   | llm        |
      | model = "command-r-plus"         | command-r-plus     | cohere    | llm        |
      | model: command-r                 | command-r          | cohere    | llm        |
      | model = "llama-3"               | llama-3            | meta      | llm        |
      | model: llama-2                   | llama-2            | meta      | llm        |
      | model = "codellama"             | codellama          | meta      | llm        |

  Scenario Outline: Detect embedding models
    Given a line containing "<line>"
    When I scan the line for matches
    Then I should find model "<model>" from provider "<provider>"
    And the match type should be "embedding"

    Examples:
      | line                                      | model                     | provider |
      | embedding = "text-embedding-3-small"       | text-embedding-3-small    | openai   |
      | model: text-embedding-3-large              | text-embedding-3-large    | openai   |
      | model = "text-embedding-ada-002"           | text-embedding-ada-002    | openai   |
      | model: embed-english-v3.0                  | embed-english-v3.0        | cohere   |
      | embedding = "embed-multilingual-v2.0"      | embed-multilingual-v2.0   | cohere   |
      | model = "voyage-large-2"                  | voyage-large-2            | voyage   |
      | model: voyage-code-3                       | voyage-code-3             | voyage   |

  Scenario Outline: Detect frameworks
    Given a line containing "<line>"
    When I scan the line for matches
    Then I should find model "<model>" from provider "<provider>"
    And the match type should be "framework"

    Examples:
      | line                               | model       | provider   |
      | from langchain import ChatOpenAI    | langchain   | langchain  |
      | import llamaindex                   | llamaindex  | llamaindex |
      | pip install crewai                  | crewai      | crewai     |
      | from litellm import completion      | litellm     | litellm    |
      | from haystack import Pipeline       | haystack    | haystack   |
      | from autogen import Agent           | autogen     | autogen    |
      | import dspy                         | dspy        | dspy       |

  Scenario Outline: Short model names require context keywords
    Given a line containing "<line>"
    When I scan the line for matches
    Then I should find <count> matches

    Examples:
      | line                                  | count |
      | model = "o1"                          | 1     |
      | openai_model: o3-mini                 | 1     |
      | model: o1-preview                     | 1     |
      | model: o1-pro                         | 1     |
      | model = "o3-pro"                      | 1     |
      | api_model: o3-deep-research           | 1     |
      | The o1 visa is required               | 0     |
      | Section o3 of the document            | 0     |
      | o1 without any context                | 0     |

  Scenario Outline: Detect new OpenAI models (GPT-4.1, GPT-5, o4-mini, codex-mini)
    Given a line containing "<line>"
    When I scan the line for matches
    Then I should find model "<model>" from provider "openai"
    And the match type should be "llm"

    Examples:
      | line                             | model           |
      | model = "gpt-4.1"               | gpt-4.1         |
      | model = "gpt-4.1-mini"          | gpt-4.1-mini    |
      | model = "gpt-4.1-nano"          | gpt-4.1-nano    |
      | model: gpt-5                     | gpt-5           |
      | model = "gpt-5.1"               | gpt-5.1         |
      | model = "gpt-5.2"               | gpt-5.2         |
      | model: gpt-5-mini               | gpt-5-mini      |
      | model = "o4-mini"               | o4-mini         |
      | model = "codex-mini"            | codex-mini      |

  Scenario Outline: Detect models with date suffixes
    Given a line containing "<line>"
    When I scan the line for matches
    Then I should find model "<model>" from provider "<provider>"
    And the match type should be "llm"

    Examples:
      | line                                     | model                      | provider  |
      | model = "gpt-4o-2024-08-06"             | gpt-4o-2024-08-06          | openai    |
      | model: gpt-4-turbo-2024-04-09           | gpt-4-turbo-2024-04-09     | openai    |
      | model = "claude-3-opus-20240229"         | claude-3-opus-20240229     | anthropic |
      | model: claude-3.5-sonnet-20241022       | claude-3.5-sonnet-20241022 | anthropic |
      | model = "mistral-large-2024-01-01"      | mistral-large-2024-01-01   | mistral   |

  Scenario Outline: Detect models with alternative separators
    Given a line containing "<line>"
    When I scan the line for matches
    Then I should find model "<model>" from provider "<provider>"
    And the match type should be "llm"

    Examples:
      | line                             | model              | provider  |
      | model: claude-3-5-sonnet         | claude-3-5-sonnet  | anthropic |
      | model = "gemini-2-5-pro"        | gemini-2-5-pro     | google    |
      | model: gemini-1-5-flash         | gemini-1-5-flash   | google    |

  Scenario Outline: Detect new Google models (Gemini 2.5)
    Given a line containing "<line>"
    When I scan the line for matches
    Then I should find model "<model>" from provider "google"
    And the match type should be "llm"

    Examples:
      | line                             | model              |
      | model = "gemini-2.5-pro"        | gemini-2.5-pro     |
      | model: gemini-2.5-flash         | gemini-2.5-flash   |

  Scenario Outline: Detect DeepSeek and xAI models
    Given a line containing "<line>"
    When I scan the line for matches
    Then I should find model "<model>" from provider "<provider>"
    And the match type should be "llm"

    Examples:
      | line                             | model          | provider |
      | model = "deepseek-v3"           | deepseek-v3    | deepseek |
      | model: deepseek-r1              | deepseek-r1    | deepseek |
      | model = "deepseek-coder"        | deepseek-coder | deepseek |
      | model: grok-2                   | grok-2         | xai      |
      | model = "grok-3"               | grok-3         | xai      |

  Scenario Outline: No false positives on overlapping patterns
    Given a line containing "<line>"
    When I scan the line for matches
    Then I should find <count> matches

    Examples:
      | line                                          | count |
      | The commander reported the results            | 0     |
      | command-response handler in the API           | 0     |
      | llama3 without hyphen                         | 1     |
      | model = "gpt-4o" with only gpt-4o            | 1     |

  Scenario: gpt-4 pattern does not match gpt-4o
    Given a line containing "model = gpt-4o"
    When I scan the line for matches
    Then I should find 1 matches
    And I should find model "gpt-4o" from provider "openai"

  Scenario: gpt-4 pattern does not match gpt-4-turbo
    Given a line containing "model = gpt-4-turbo"
    When I scan the line for matches
    Then I should find 1 matches
    And I should find model "gpt-4-turbo" from provider "openai"

  Scenario: gpt-5 pattern does not match gpt-5.1
    Given a line containing "model = gpt-5.1"
    When I scan the line for matches
    Then I should find 1 matches
    And I should find model "gpt-5.1" from provider "openai"

  Scenario: Multiple models on one line
    Given a line containing "model=gpt-4o embedding=text-embedding-ada-002"
    When I scan the line for matches
    Then I should find model "gpt-4o" from provider "openai"
    And I should find model "text-embedding-ada-002" from provider "openai"

  Scenario: No matches in irrelevant text
    Given a line containing "Hello world, this is a normal line of code"
    When I scan the line for matches
    Then I should find 0 matches
