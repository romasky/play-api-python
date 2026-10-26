@allure.label.epic:Challenges @allure.label.suite:Challenges @allure.label.subSuite:Challenge_Catalog
Feature: Challenges — catalog, hints, attempts and verification rules

  # Four static challenges (delete-user-404 10, patch-first-name 10, logout-revokes-token 20, login-rotates-token 20),
  # three hint levels each (nudge → approach → solution, revealed in order). A player is any created user;
  # `start` creates a sandbox user (it shares the user-creation rate limit). Auth is checked before the id.

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: The catalog lists the four challenges with points and three hints each
    When List challenges with query "" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "total" equals "4" in response "response"
    And Assert every item of "challenges" has field "hint_count" equals "3" in response "response"
    And Assert field "challenges.0.id" equals "delete-user-404" in response "response"
    And Assert field "challenges.0.points" equals "10" in response "response"
    And Assert field "challenges.3.id" equals "login-rotates-token" in response "response"
    And Assert field "challenges.3.points" equals "20" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: Catalog filter <query> returns <total> challenges (exact, case-sensitive, never 400)
    When List challenges with query "<query>" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "total" equals "<total>" in response "response"
    Examples:
      | query           | total |
      | category=crud   | 2     |
      | category=auth   | 2     |
      | difficulty=easy | 2     |
      | category=xxx    | 0     |
      | category=CRUD   | 0     |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Hint metadata is public and never contains the hint text
    When Get hints of challenge "delete-user-404" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "hint_count" equals "3" in response "response"
    And Assert field "levels.0.kind" equals "nudge" in response "response"
    And Assert field "levels.1.kind" equals "approach" in response "response"
    And Assert field "levels.2.kind" equals "solution" in response "response"
    And Assert every item of "levels" has no field "hint" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Hints of an unknown challenge return 404 CHALLENGE_NOT_FOUND
    When Get hints of challenge "no-such-challenge" and save response as "response"
    Then Get and check status code 404 from "response"
    And Assert error code is "CHALLENGE_NOT_FOUND" in response "response"

  @Run @Negative @allure.label.severity:critical @allure.label.story:Negative_Scenario
  Scenario Outline: Challenge <route> without a token returns 401 MISSING_TOKEN
    When Send challenge "<route>" request for "delete-user-404" with no auth token and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "MISSING_TOKEN" in response "response"
    Examples:
      | route    |
      | progress |
      | start    |
      | verify   |
      | reveal   |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Challenge <route> with <header> returns 401 <code> — even for an unknown id
    When Send challenge "<route>" request for "no-such-challenge" with raw auth header "<header>" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "<code>" in response "response"
    Examples:
      | route  | header        | code                 |
      | start  | Basic abc     | INVALID_TOKEN_FORMAT |
      | verify | Bearer usr_1_abc | INVALID_TOKEN     |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: A fresh player has no progress
    Given a user with token "playerToken"
    When Get challenge progress with token "playerToken" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "solved_count" equals "0" in response "response"
    And Assert field "total_challenges" equals "4" in response "response"
    And Assert field "total_points" equals "0" in response "response"
    And Assert list "solved" has 0 items in response "response"
    And Assert list "hints" has 0 items in response "response"

  @Run @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: Start issues an open attempt with a sandbox user and its token
    Given a user with token "playerToken"
    When Start challenge "delete-user-404" with token "playerToken" and save response as "response"
    Then Get and check status code 201 from "response"
    And Assert field "status" equals "open" in response "response"
    And Assert field "already_solved" equals "false" in response "response"
    And Assert field "target.access_token" is not null in response "response"
    And Assert field "target.email" contains "sandbox-" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: A repeated start returns the same open attempt without the sandbox token
    Given a user with token "playerToken"
    When Start challenge "patch-first-name" with token "playerToken" and save response as "firstRes"
    And Extract "attempt_id" from "firstRes" and save as "attemptId"
    And Start challenge "patch-first-name" with token "playerToken" and save response as "secondRes"
    Then Get and check status code 200 from "secondRes"
    And Assert field "attempt_id" equals "attemptId" in response "secondRes"
    And Assert field "target.access_token" is absent in response "secondRes"
    And Assert field "target.note" is not null in response "secondRes"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Starting an unknown challenge returns 404 CHALLENGE_NOT_FOUND
    Given a user with token "playerToken"
    When Start challenge "no-such-challenge" with token "playerToken" and save response as "response"
    Then Get and check status code 404 from "response"
    And Assert error code is "CHALLENGE_NOT_FOUND" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Start with reset=<reset> returns 400 VALIDATION_ERROR (only true/false)
    Given a user with token "playerToken"
    When Start challenge "delete-user-404" with query "reset=<reset>" and token "playerToken" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"
    Examples:
      | reset |
      | maybe |
      | 1     |
      | TRUE  |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Verify before any start returns 409 NO_OPEN_ATTEMPT
    Given a user with token "playerToken"
    When Verify challenge "delete-user-404" with token "playerToken" and save response as "response"
    Then Get and check status code 409 from "response"
    And Assert error code is "NO_OPEN_ATTEMPT" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Verify with attempt_id <label> returns 409 NO_OPEN_ATTEMPT (malformed is not 400)
    Given a user with token "playerToken"
    When Start challenge "delete-user-404" with token "playerToken" and save response as "startRes"
    And Verify challenge "delete-user-404" with raw body "{\"attempt_id\":\"<attempt>\"}" and token "playerToken" and save response as "response"
    Then Get and check status code 409 from "response"
    And Assert error code is "NO_OPEN_ATTEMPT" in response "response"
    Examples:
      | label     | attempt                  |
      | unknown   | 000000000000000000000000 |
      | malformed | zzz                      |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Verify with <label> returns 400 VALIDATION_ERROR
    Given a user with token "playerToken"
    When Start challenge "delete-user-404" with token "playerToken" and save response as "startRes"
    And Verify challenge "delete-user-404" with raw body "<body>" and token "playerToken" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"
    Examples:
      | label             | body                    |
      | an unknown param  | {\"params\":{\"x\":1}}  |
      | null params       | {\"params\":null}       |
      | a non-JSON body   | {\"params\":            |

  # ─────────────────── HINTS ───────────────────

  @Run @Flow @allure.label.story:End_to_End_Flow
  Scenario: Hints are revealed strictly in order and a repeat reveal is idempotent
    Given a user with token "playerToken"
    When Reveal hint 2 of challenge "delete-user-404" with token "playerToken" and save response as "outOfOrder"
    Then Get and check status code 409 from "outOfOrder"
    And Assert error code is "HINT_LEVEL_OUT_OF_ORDER" in response "outOfOrder"
    When Reveal hint 1 of challenge "delete-user-404" with token "playerToken" and save response as "first"
    Then Get and check status code 200 from "first"
    And Assert field "revealed_count" equals "1" in response "first"
    And Assert field "has_more" equals "true" in response "first"
    And Assert field "kind" equals "nudge" in response "first"
    When Reveal hint 1 of challenge "delete-user-404" with token "playerToken" and save response as "again"
    Then Get and check status code 200 from "again"
    And Assert field "revealed_count" equals "1" in response "again"
    When Get challenge progress with token "playerToken" and save response as "progressRes"
    Then Assert field "hints.0.revealed_count" equals "1" in response "progressRes"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Revealing a hint with <label> returns 400 VALIDATION_ERROR
    Given a user with token "playerToken"
    When Reveal a hint of challenge "delete-user-404" with raw body "<body>" and token "playerToken" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"
    Examples:
      | label          | body              |
      | level 0        | {\"level\":0}     |
      | level 4        | {\"level\":4}     |
      | a string level | {\"level\":\"1\"} |
      | level 1.5      | {\"level\":1.5}   |
      | no level       | {}                |
