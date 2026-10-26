@allure.label.epic:Chaos_Engineering @allure.label.suite:Chaos_Engineering @allure.label.subSuite:Chaos_Status
Feature: Chaos — arbitrary status codes (GET /chaos/status/{code})

  # Any code 200-599 with body {status_code, message = Go http.StatusText ("" for non-standard codes)}.
  # 204/205/304 have no body; 3xx come without Location, 401 without WWW-Authenticate.
  # Cloudflare replaces the origin body of 502/504/520-526 with its own page — text, or HTML for a client that
  # accepts gzip (spec: JSON).

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario Outline: Status <code> answers <code> with message "<message>"
    When Get chaos status "<code>" and save response as "response"
    Then Get and check status code <code> from "response"
    And Assert field "status_code" equals "<code>" in response "response"
    And Assert field "message" equals "<message>" in response "response"
    Examples:
      | code | message               |
      | 200  | OK                    |
      | 201  | Created               |
      | 299  |                       |
      | 418  | I'm a teapot          |
      | 429  | Too Many Requests     |
      | 500  | Internal Server Error |
      | 503  | Service Unavailable   |
      | 599  |                       |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: Status <code> has no body
    When Get chaos status "<code>" and save response as "response"
    Then Get and check status code <code> from "response"
    And Assert response body is empty in "response"
    Examples:
      | code |
      | 204  |
      | 205  |
      | 304  |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: A 3xx from /chaos/status carries no Location (nothing to follow)
    When Get chaos status "302" and save response as "response"
    Then Get and check status code 302 from "response"
    And Assert response header "Location" is absent in "response"
    And Assert field "message" equals "Found" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: Cloudflare replaces the <code> body with its own error page (documents the spec discrepancy)
    When Get chaos status "<code>" and save response as "response"
    Then Get and check status code <code> from "response"
    And Assert response "response" is a Cloudflare error page for status <code>
    Examples:
      | code |
      | 502  |
      | 504  |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Status "<code>" returns 400 INVALID_STATUS_CODE
    When Get chaos status "<code>" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "INVALID_STATUS_CODE" in response "response"
    Examples:
      | code |
      | 199  |
      | 600  |
      | abc  |
      | 1e2  |
