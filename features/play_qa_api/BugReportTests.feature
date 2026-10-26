@allure.label.epic:Bug_Hunting @allure.label.suite:Bug_Hunting @allure.label.subSuite:Bug_Reports
Feature: Bug Reports (POST/GET /bug-reports, auto-scored)

  # A report on one of the catalogued intentional bugs is scored out of 100 on five criteria:
  # has_steps 25 · steps_reproducible 20 · expected_actual 25 · severity_reasonable 15 · title_quality 15.
  # Anonymous submissions answer 200 and are not saved; with a valid token they answer 201 and are kept 24 h.
  # A present-but-invalid token is refused (401) before the body is validated. 30 per minute (400s count too).

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: An anonymous perfect report scores 100 and is not saved
    When Submit a perfect "cart-total-wrong" bug report anonymously and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "owner" equals "anonymous" in response "response"
    And Assert field "saved" equals "false" in response "response"
    And Assert field "report_id" is absent in response "response"
    And Assert field "score.total" equals "100" in response "response"
    And Assert field "score.max" equals "100" in response "response"
    And Assert every score criterion is "true" in response "response"

  @Run @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: An authenticated report is saved (201) with a report id and a 24 h lifetime
    Given a user with token "token"
    When Submit a perfect "pagination-off-by-one" bug report with token "token" and save response as "response"
    Then Get and check status code 201 from "response"
    And Assert field "owner" equals "user" in response "response"
    And Assert field "saved" equals "true" in response "response"
    And Assert field "report_id" is not null in response "response"
    And Assert field "expires_at" is not null in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: A zero-score report is still accepted and every criterion explains itself
    When Submit a "zero score" bug report anonymously and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "score.total" equals "0" in response "response"
    And Assert every score criterion is "false" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: Severity <severity> for <bug_id> is <verdict>
    When Submit a "<bug_id>" bug report with severity "<severity>" anonymously and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert score criterion "severity_reasonable" is "<ok>" in response "response"
    And Assert field "score.breakdown.severity_reasonable" equals "<points>" in response "response"
    Examples:
      | bug_id                | severity | verdict     | ok    | points |
      | pagination-off-by-one | medium   | reasonable  | true  | 15     |
      | pagination-off-by-one | critical | overblown   | false | 0      |
      | cart-total-wrong      | critical | reasonable  | true  | 15     |
      | cart-total-wrong      | low      | understated | false | 0      |
      | timezone-shift        | high     | reasonable  | true  | 15     |
      | timezone-shift        | low      | understated | false | 0      |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: The method in the steps matches case-insensitively
    When Submit a "lowercase method in steps" bug report anonymously and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "score.breakdown.steps_reproducible" equals "20" in response "response"

  @Run @Flow @allure.label.story:End_to_End_Flow
  Scenario: Saved reports are listed and readable by their owner only
    Given a user with token "ownerToken"
    And a user with token "otherToken"
    When Submit a perfect "timezone-shift" bug report with token "ownerToken" and save response as "submitRes"
    And Extract "report_id" from "submitRes" and save as "reportId"
    And Submit a perfect "timezone-shift" bug report anonymously and save response as "anonRes"
    And List my bug reports with token "ownerToken" and save response as "listRes"
    Then Get and check status code 200 from "listRes"
    And Assert field "total" equals "1" in response "listRes"
    And Assert field "reports.0.report_id" equals "reportId" in response "listRes"
    And Assert field "reports.0.score_total" equals "100" in response "listRes"
    When Get bug report "reportId" with token "ownerToken" and save response as "detailRes"
    Then Get and check status code 200 from "detailRes"
    And Assert field "bug_id" equals "timezone-shift" in response "detailRes"
    And Assert field "score.total" equals "100" in response "detailRes"
    When Get bug report "reportId" with token "otherToken" and save response as "foreignRes"
    Then Get and check status code 404 from "foreignRes"
    And Assert error code is "REPORT_NOT_FOUND" in response "foreignRes"
    When List my bug reports with token "otherToken" and save response as "otherListRes"
    Then Assert field "total" equals "0" in response "otherListRes"

  # ─────────────────── NEGATIVE ───────────────────

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: An unknown bug id returns 404 UNKNOWN_BUG_ID
    When Submit a perfect "no-such-bug" bug report anonymously and save response as "response"
    Then Get and check status code 404 from "response"
    And Assert error code is "UNKNOWN_BUG_ID" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: A report with <variant> returns 400 VALIDATION_ERROR
    When Submit a "<variant>" bug report anonymously and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"
    Examples:
      | variant              |
      | missing bug_id       |
      | bug_id 65 chars      |
      | missing severity     |
      | blocker severity     |
      | capitalised severity |
      | blank title          |
      | title 201 chars      |
      | expected 2001 chars  |
      | no steps             |
      | 21 steps             |
      | a blank step         |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: A malformed report body (<label>) returns 400 VALIDATION_ERROR
    When Submit a bug report with raw body "<body>" anonymously and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"
    Examples:
      | label          | body                     |
      | truncated JSON | {\"bug_id\":\"cart       |
      | a JSON array   | [1,2,3]                  |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: A report larger than 64 KiB returns 413 PAYLOAD_TOO_LARGE
    When Submit a "oversized body" bug report anonymously and save response as "response"
    Then Get and check status code 413 from "response"
    And Assert error code is "PAYLOAD_TOO_LARGE" in response "response"

  @Run @Negative @allure.label.severity:critical @allure.label.story:Negative_Scenario
  Scenario Outline: A bad Authorization header (<header>) returns 401 <code>, never an anonymous 200
    When Submit a perfect "cart-total-wrong" bug report with raw auth header "<header>" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "<code>" in response "response"
    Examples:
      | header           | code                 |
      | Bearer usr_bogus | INVALID_TOKEN        |
      | Basic xyz        | INVALID_TOKEN_FORMAT |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Listing my reports without a token returns 401 MISSING_TOKEN
    When List my bug reports with no auth token and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "MISSING_TOKEN" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Listing my reports with <query> returns 400 VALIDATION_ERROR
    Given a user with token "token"
    When List my bug reports with query "<query>" and token "token" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"
    Examples:
      | query     |
      | limit=0   |
      | limit=51  |
      | limit=abc |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Reading a report without a token returns 401 MISSING_TOKEN
    When Get bug report "000000000000000000000000" with no auth token and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "MISSING_TOKEN" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Reading a <label> report id returns 404 REPORT_NOT_FOUND
    Given a user with token "token"
    When Get bug report "<id>" with token "token" and save response as "response"
    Then Get and check status code 404 from "response"
    And Assert error code is "REPORT_NOT_FOUND" in response "response"
    Examples:
      | label     | id                       |
      | zero      | 000000000000000000000000 |
      | malformed | garbage                  |
