Feature: LLM model pattern detection
  The scanner should detect LLM models and embeddings
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
      | model_name = "claude-opus-4"              | claude-opus-4              | anthropic | llm        |
      | model_name = "claude-opus-4-20250514"     | claude-opus-4-20250514     | anthropic | llm        |
      | model_name = "claude-sonnet-4"            | claude-sonnet-4            | anthropic | llm        |
      | model_name = "claude-sonnet-4-20250514"   | claude-sonnet-4-20250514   | anthropic | llm        |
      | model: claude-3.5-sonnet         | claude-3.5-sonnet  | anthropic | llm        |
      | model: claude-3.5-haiku          | claude-3.5-haiku   | anthropic | llm        |
      | model: claude-3-opus             | claude-3-opus      | anthropic | llm        |
      | model: claude-3-sonnet           | claude-3-sonnet    | anthropic | llm        |
      | model: claude-3-haiku            | claude-3-haiku     | anthropic | llm        |
      | model: claude-3-7-sonnet         | claude-3-7-sonnet  | anthropic | llm        |
      | model = "claude-2.1"            | claude-2.1         | anthropic | llm        |
      | model: claude-1.3               | claude-1.3         | anthropic | llm        |
      | model = "claude-instant-1.2"    | claude-instant-1.2 | anthropic | llm        |
      | model = "gemini-2.0-flash"       | gemini-2.0-flash   | google    | llm        |
      | model: gemini-1.5-pro            | gemini-1.5-pro     | google    | llm        |
      | model = "gemini-1.5-flash"       | gemini-1.5-flash   | google    | llm        |
      | model: gemini-pro                | gemini-pro         | google    | llm        |

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
      | model = "voyage-large-2"                  | voyage-large-2            | voyage   |
      | model: voyage-code-3                       | voyage-code-3             | voyage   |
      | model = "voyage-lite-3"                    | voyage-lite-3             | voyage   |
      | model = "voyage-finance-2"                 | voyage-finance-2          | voyage   |
      | model: voyage-3                            | voyage-3                  | voyage   |
      | model = "voyage-3-lite"                    | voyage-3-lite             | voyage   |
      | model = "gemini-embedding-001"             | gemini-embedding-001      | google   |
      | model: gemini-embedding-exp                 | gemini-embedding-exp      | google   |
      | model = "embedding-001"                    | embedding-001             | google   |
      | model: embedding-gecko-001                  | embedding-gecko-001       | google   |
      | model = "embedding-2-preview"              | embedding-2-preview       | google   |
      | model = "text-embedding-004"               | text-embedding-004        | google   |

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
      | model = "o1-2024-12-17"               | 1     |
      | model = "o1-pro-2025-03-19"           | 1     |
      | model = "o3-mini-2025-01-31"          | 1     |
      | model = "o3-deep-research-2025-06-26" | 1     |
      | openai model: computer-use-preview-2025-03-11 | 1 |
      | The o1 visa is required               | 0     |
      | Section o3 of the document            | 0     |
      | o1 without any context                | 0     |
      | computer-use-preview-2025-03-11 in some unrelated text | 0 |

  Scenario Outline: Detect new OpenAI models (GPT-4.1, GPT-4.5, GPT-5, o4-mini, codex-mini, etc.)
    Given a line containing "<line>"
    When I scan the line for matches
    Then I should find model "<model>" from provider "openai"
    And the match type should be "llm"

    Examples:
      | line                                              | model                              |
      | model = "gpt-4.1"                                | gpt-4.1                            |
      | model = "gpt-4.1-mini"                           | gpt-4.1-mini                       |
      | model = "gpt-4.1-nano"                           | gpt-4.1-nano                       |
      | model: gpt-5                                      | gpt-5                              |
      | model = "gpt-5.1"                                | gpt-5.1                            |
      | model = "gpt-5.2"                                | gpt-5.2                            |
      | model: gpt-5-mini                                 | gpt-5-mini                         |
      | model = "o4-mini"                                 | o4-mini                            |
      | model = "o4-mini-2025-04-16"                      | o4-mini-2025-04-16                 |
      | model = "o4-mini-deep-research-2025-06-26"        | o4-mini-deep-research-2025-06-26   |
      | model = "codex-mini"                              | codex-mini                         |
      | model = "codex-mini-latest"                       | codex-mini-latest                  |
      | model = "gpt-4.5-preview"                        | gpt-4.5-preview                    |
      | model: gpt-4-32k                                  | gpt-4-32k                          |
      | model = "gpt-4o-audio-preview-2024-10-01"        | gpt-4o-audio-preview-2024-10-01    |
      | model: gpt-4o-realtime-preview-2024-10-01         | gpt-4o-realtime-preview-2024-10-01 |
      | model = "chatgpt-4o-latest"                       | chatgpt-4o-latest                  |
      | model: text-moderation                            | text-moderation                    |
      | model = "gpt-3.5-turbo-instruct"                 | gpt-3.5-turbo-instruct             |
      | model = "gpt-3.5-turbo-16k-0613"                 | gpt-3.5-turbo-16k-0613             |
      | model = "gpt-3.5-turbo-16k"                      | gpt-3.5-turbo-16k                  |
      | model = "gpt-4-0314"                             | gpt-4-0314                         |
      | model = "gpt-4-1106-preview"                     | gpt-4-1106-preview                 |
      | model = "gpt-4-0125-preview"                     | gpt-4-0125-preview                 |
      | model = "gpt-4-1106-vision-preview"              | gpt-4-1106-vision-preview          |
      | model = "gpt-4-32k-0314"                         | gpt-4-32k-0314                     |
      | model = "gpt-4-32k-0613"                         | gpt-4-32k-0613                     |
      | model = "gpt-4-vision-preview"                   | gpt-4-vision-preview               |
      | model = "gpt-4-turbo-preview-completions"        | gpt-4-turbo-preview-completions    |
      | model = "gpt-4o-mini-audio-preview"              | gpt-4o-mini-audio-preview          |
      | model = "gpt-4o-mini-realtime-preview"           | gpt-4o-mini-realtime-preview       |
      | model = "gpt-4o-mini-audio-preview-2024-12-17"   | gpt-4o-mini-audio-preview-2024-12-17    |
      | model = "gpt-4o-mini-realtime-preview-2024-12-17" | gpt-4o-mini-realtime-preview-2024-12-17 |
      | model = "gpt-4o-mini-search-preview-2025-03-11"  | gpt-4o-mini-search-preview-2025-03-11   |
      | model = "gpt-4o-search-preview-2025-03-11"       | gpt-4o-search-preview-2025-03-11   |
      | model = "gpt-4o-mini-tts-2025-03-20"             | gpt-4o-mini-tts-2025-03-20         |
      | model = "gpt-image-1"                            | gpt-image-1                        |
      | model = "gpt-image-1-mini"                       | gpt-image-1-mini                   |
      | model = "gpt-image-1.5"                          | gpt-image-1.5                      |
      | model = "chatgpt-image-latest"                   | chatgpt-image-latest               |
      | model = "gpt-audio-mini-2025-10-06"              | gpt-audio-mini-2025-10-06          |
      | model = "gpt-realtime-mini-2025-10-06"           | gpt-realtime-mini-2025-10-06       |
      | model = "gpt-audio"                              | gpt-audio                          |
      | model = "gpt-realtime"                           | gpt-realtime                       |
      | model = "gpt-audio-mini"                         | gpt-audio-mini                     |
      | model = "gpt-4o-audio"                           | gpt-4o-audio                       |
      | model = "gpt-4o-realtime"                        | gpt-4o-realtime                    |
      | model = "gpt-4o-mini-audio"                      | gpt-4o-mini-audio                  |
      | model = "gpt-4o-mini-realtime"                   | gpt-4o-mini-realtime               |
      | model = "gpt-4o-mini-transcribe-2025-03-20"      | gpt-4o-mini-transcribe-2025-03-20  |
      | model = "gpt-5.3-chat-latest"                    | gpt-5.3-chat-latest                |
      | model = "gpt-3.5-turbo-completions"              | gpt-3.5-turbo-completions          |
      | model = "gpt-4-completions"                      | gpt-4-completions                  |
      | model = "gpt-4-0613-completions"                 | gpt-4-0613-completions             |
      | model = "gpt-4-turbo-completions"                | gpt-4-turbo-completions            |
      | model = "gpt-5-chat-latest"                       | gpt-5-chat-latest                  |
      | model = "gpt-5.1-chat-latest"                     | gpt-5.1-chat-latest                |
      | model = "gpt-5.1-codex-mini"                      | gpt-5.1-codex-mini                 |
      | model = "gpt-5.1-codex-max"                       | gpt-5.1-codex-max                  |
      | model = "ft-gpt-3.5-turbo"                        | ft-gpt-3.5-turbo                   |
      | model = "ft-gpt-4"                                | ft-gpt-4                           |
      | model = "ft-gpt-4.1-nano-2025-04-14"              | ft-gpt-4.1-nano-2025-04-14         |
      | model = "ft-o4-mini-2025-04-16"                   | ft-o4-mini-2025-04-16              |
      | model = "ft-babbage-002"                          | ft-babbage-002                     |
      | model = "ft-davinci-002"                          | ft-davinci-002                     |
      | model = "dall-e-2"                               | dall-e-2                           |
      | model = "dall-e-3"                               | dall-e-3                           |
      | model = "sora-2"                                  | sora-2                             |
      | model = "sora-2-pro"                             | sora-2-pro                         |
      | model = "sora-2-2025-10-06"                      | sora-2-2025-10-06                  |
      | model = "sora-2-pro-2025-10-06"                  | sora-2-pro-2025-10-06              |
      | model = "text-davinci-003"                       | text-davinci-003                   |
      | model = "text-ada-001"                           | text-ada-001                       |
      | model = "text-curie-001"                         | text-curie-001                     |
      | model = "text-davinci-edit-001"                  | text-davinci-edit-001              |
      | model = "text-moderation-007"                    | text-moderation-007                |
      | model = "text-moderation-latest"                 | text-moderation-latest             |
      | model = "text-moderation-stable"                 | text-moderation-stable             |
      | model = "code-davinci-002"                       | code-davinci-002                   |
      | model = "code-cushman-001"                       | code-cushman-001                   |
      | model = "code-davinci-edit-001"                  | code-davinci-edit-001              |
      | model = "code-search-ada-code-001"               | code-search-ada-code-001           |
      | model = "code-search-babbage-text-001"           | code-search-babbage-text-001       |
      | model = "text-search-ada-doc-001"                | text-search-ada-doc-001            |
      | model = "text-search-davinci-query-001"          | text-search-davinci-query-001      |
      | model = "text-similarity-babbage-001"            | text-similarity-babbage-001        |
      | model = "text-similarity-davinci-001"            | text-similarity-davinci-001        |

  Scenario Outline: Detect legacy OpenAI base models (require context)
    Given a line containing "<line>"
    When I scan the line for matches
    Then I should find model "<model>" from provider "openai"
    And the match type should be "llm"

    Examples:
      | line                    | model        |
      | model = "ada"           | ada          |
      | model = "babbage"       | babbage      |
      | model = "babbage-002"   | babbage-002  |
      | model = "curie"         | curie        |
      | model = "davinci"       | davinci      |
      | model = "davinci-002"   | davinci-002  |

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
      | model = "claude-3-7-sonnet-20250219"    | claude-3-7-sonnet-20250219 | anthropic |

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

  Scenario Outline: Detect new Google models (Gemini 2.5, 2.0 variants, imagen, veo)
    Given a line containing "<line>"
    When I scan the line for matches
    Then I should find model "<model>" from provider "google"
    And the match type should be "llm"

    Examples:
      | line                                                     | model                                           |
      | model = "gemini-2.5-pro"                                | gemini-2.5-pro                                  |
      | model: gemini-2.5-flash                                 | gemini-2.5-flash                                |
      | model = "gemini-2.5-pro-preview-03-25"                  | gemini-2.5-pro-preview-03-25                    |
      | model: gemini-2.5-flash-preview-04-17                   | gemini-2.5-flash-preview-04-17                  |
      | model = "gemini-2.5-flash-exp-native-audio-thinking-dialog" | gemini-2.5-flash-exp-native-audio-thinking-dialog |
      | model = "gemini-2.0-flash-001"                          | gemini-2.0-flash-001                            |
      | model: gemini-2.0-flash-thinking-exp-1219               | gemini-2.0-flash-thinking-exp-1219              |
      | model = "gemini-2.0-pro-exp"                            | gemini-2.0-pro-exp                              |
      | model: gemini-1.0-pro                                   | gemini-1.0-pro                                  |
      | model = "gemini-1.0-pro-vision"                         | gemini-1.0-pro-vision                           |
      | model: gemini-live-2.5-flash-preview                    | gemini-live-2.5-flash-preview                   |
      | model = "gemini-live"                                    | gemini-live                                     |
      | model = "imagen-3.0-generate-002"                       | imagen-3.0-generate-002                         |
      | model: veo-3.0-fast-generate-preview                    | veo-3.0-fast-generate-preview                   |
      | model = "gemini-3-pro-preview"                          | gemini-3-pro-preview                            |
      | model: gemini-robotics-er-1.5-preview                   | gemini-robotics-er-1.5-preview                  |
      | model = "gemini-robotics-er-1.6-preview"                | gemini-robotics-er-1.6-preview                  |

  Scenario Outline: No false positives on overlapping patterns
    Given a line containing "<line>"
    When I scan the line for matches
    Then I should find <count> matches

    Examples:
      | line                                          | count |
      | The commander reported the results            | 0     |
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

  Scenario: Un mot-cle lointain ne valide pas un nom de modele court
    Given a line containing "Ada-inc has two imports from two different sources, and needs to post sales to an API"
    When I scan the line for matches
    Then I should find 0 matches

  Scenario: Un mot-cle proche valide bien le nom de modele
    Given a line containing "response = openai.Embedding.create(model='ada')"
    When I scan the line for matches
    Then I should find model "ada" from provider "openai"
