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
  # API_REFERENCE does not fix the exact code for invalid pagination params, so these
  # assert the weaker-but-true property (never 5xx, and either 200 or 400).
  # Observed live behavior: 400 INVALID_PAGINATION for non-positive / non-numeric values,
  # 200 (clamped) for per_page above the maximum.

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Users list with invalid pagination <label> does not 5xx
    When Send GET users list request with page "<page>" per_page "<per_page>" and save response as "response"
    Then Assert response is not a server error in "response"
    And Assert status code is one of "200,400" in "response"
    Examples:
      | label             | page | per_page |
      | per_page zero     | 1    | 0        |
      | per_page negative | 1    | -5       |
      | page zero         | 0    | 10       |
      | page negative     | -1   | 10       |
      | per_page over max | 1    | 100000   |
      | page non-numeric  | abc  | 10       |
      | perPage non-num   | 1    | xyz      |
