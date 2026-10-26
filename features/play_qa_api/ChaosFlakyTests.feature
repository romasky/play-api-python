@allure.label.epic:Chaos_Engineering @allure.label.suite:Chaos_Engineering @allure.label.subSuite:Chaos_Flaky
Feature: Chaos — seeded flakiness (GET /chaos/flaky, /flaky/sequence, /flaky/step/{index})

  # The roll depends ONLY on the seed (failed = roll < fail_rate), so a seed makes every outcome reproducible.
  # Without a seed the status is genuinely random — never asserted except with fail_rate 0 / 1.
  # The flaky body is returned on EVERY status, even a 4xx/5xx from the roll (no error envelope then).
  # seed=20 is stable: flaky → 500; sequence (count 10) → 500,500,200,200,500,200,500,200,200,200.

  # @Positive on purpose: the 500 is the planned outcome of seed 20 — reproducing it is the feature
  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: A seeded roll is reproducible
    When Get chaos flaky with query "seed=20" and save response as "first"
    And Get chaos flaky with query "seed=20" and save response as "second"
    Then Get and check status code 500 from "first"
    And Get and check status code 500 from "second"
    And Assert field "deterministic" equals "true" in response "first"
    And Assert field "failed" equals "true" in response "first"
    And Assert field "roll" of "first" equals field "roll" of "second"
    And Assert response header "X-Chaos-Seed" equals "20" in "first"
    And Assert response header "X-Chaos-Deterministic" equals "true" in "first"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: A seed whose roll is above the fail rate succeeds
    When Get chaos flaky with query "seed=1" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "ok" equals "true" in response "response"
    And Assert field "failed" equals "false" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: fail_rate <rate> forces <status>
    When Get chaos flaky with query "fail_rate=<rate>" and save response as "response"
    Then Get and check status code <status> from "response"
    And Assert field "deterministic" equals "false" in response "response"
    And Assert field "seed" is null in response "response"
    And Assert response header "X-Chaos-Seed" equals "random" in "response"
    Examples:
      | rate | status |
      | 0    | 200    |
      | 1    | 500    |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: A custom fail_status <status> carries the flaky body, not an error envelope
    When Get chaos flaky with query "seed=20&fail_rate=1&fail_status=<status>" and save response as "response"
    Then Get and check status code <status> from "response"
    And Assert field "failed" equals "true" in response "response"
    And Assert field "error" is absent in response "response"
    And Assert field "success" is absent in response "response"
    Examples:
      | status |
      | 418    |
      | 400    |
      | 599    |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Flaky with <query> returns 400 <code>
    When Get chaos flaky with query "<query>" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "<code>" in response "response"
    Examples:
      | query                    | code                |
      | seed=abc                 | INVALID_SEED        |
      | seed=                    | INVALID_SEED        |
      | seed=9223372036854775808 | INVALID_SEED        |
      | fail_rate=1.1            | INVALID_FAIL_RATE   |
      | fail_rate=x              | INVALID_FAIL_RATE   |
      | fail_status=399          | INVALID_FAIL_STATUS |
      | fail_status=600          | INVALID_FAIL_STATUS |

  # ─────────────────── SEQUENCE + STEP (retry exercise) ───────────────────

  @Run @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: The seed-20 plan is stable
    When Get chaos flaky sequence with query "seed=20&count=10" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert flaky plan statuses are "500,500,200,200,500,200,500,200,200,200" in response "response"
    And Assert field "first_success_index" equals "2" in response "response"
    And Assert field "fails_total" equals "4" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Step 0 of a plan rolls exactly like /chaos/flaky with the same seed
    When Get chaos flaky sequence with query "seed=20&count=3" and save response as "plan"
    And Get chaos flaky with query "seed=20" and save response as "flaky"
    Then Assert field "steps.0.roll" of "plan" equals field "roll" of "flaky"

  @Run @Flow @allure.label.severity:critical @allure.label.story:End_to_End_Flow
  Scenario: Every step answers its planned status — a retry loop succeeds on attempt first_success_index + 1
    When Get chaos flaky sequence with query "seed=20&count=5" and save response as "plan"
    And Retry chaos flaky steps of plan "plan" with query "seed=20" until success and save as "attempts"
    Then Assert "attempts" equals "3"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: An all-fail plan has no first success
    When Get chaos flaky sequence with query "seed=1&count=3&fail_rate=1&fail_status=503" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "first_success_index" equals "-1" in response "response"
    And Assert field "fails_total" equals "3" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Sequence with <query> returns 400 <code>
    When Get chaos flaky sequence with query "<query>" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "<code>" in response "response"
    Examples:
      | query                 | code                |
      | count=5               | SEED_REQUIRED       |
      | seed=x                | INVALID_SEED        |
      | seed=1&count=0        | INVALID_COUNT       |
      | seed=1&count=51       | INVALID_COUNT       |
      | seed=1&fail_rate=2    | INVALID_FAIL_RATE   |
      | seed=1&fail_status=200 | INVALID_FAIL_STATUS |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Step <index> with "<query>" returns 400 <code>
    When Get chaos flaky step "<index>" with query "<query>" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "<code>" in response "response"
    Examples:
      | index | query  | code          |
      | 50    | seed=1 | INVALID_INDEX |
      | -1    | seed=1 | INVALID_INDEX |
      | 50    |        | INVALID_INDEX |
      | 0     |        | SEED_REQUIRED |
      | 0     | seed=x | INVALID_SEED  |
