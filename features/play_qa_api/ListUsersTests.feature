@allure.label.epic:User_Lifecycle @allure.label.suite:User_Management @allure.label.subSuite:List_Users
Feature: List Users

  @Run @Smoke @Positive @allure.label.severity:normal @allure.label.story:Positive_Scenario
  Scenario: List users returns 200 with pagination fields
    When Send GET users list request and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "users" is present in response "response"
    And Assert field "page" is present in response "response"
    And Assert field "per_page" is present in response "response"
    And Assert field "total_pages" is present in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: List users returns non-empty result
    When Send GET users list request and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert users list is not empty in "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: List users with page and per_page params
    When Send GET users list request with page "1" per_page "5" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "page" equals "1" in response "response"
    And Assert field "per_page" equals "5" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: List users with per_page at maximum 100 returns 200
    When Send GET users list request with page "1" per_page "100" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "per_page" equals "100" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: List users response does not include access_token
    When Send GET users list request and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert users list items have no "access_token" field in "response"
    And Assert users list items have no "password" field in "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: List users response has cache-control header
    When Send GET users list request and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert response header "cache-control" contains "no-store" in "response"

  # ─────────────────── NEGATIVE / BOUNDARY PAGINATION ───────────────────
  # Swagger (2026-10) documents the codes: non-positive / non-numeric page or per_page → 400 INVALID_PAGINATION;
  # per_page above 100 is clamped to 100 (200).

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Users list with invalid pagination <label> returns 400 INVALID_PAGINATION
    When Send GET users list request with page "<page>" per_page "<per_page>" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "INVALID_PAGINATION" in response "response"
    Examples:
      | label             | page | per_page |
      | per_page zero     | 1    | 0        |
      | per_page negative | 1    | -5       |
      | page zero         | 0    | 10       |
      | page negative     | -1   | 10       |
      | page non-numeric  | abc  | 10       |
      | perPage non-num   | 1    | xyz      |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Users list with per_page over the maximum is clamped to 100
    When Send GET users list request with page "1" per_page "100000" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "per_page" equals "100" in response "response"
