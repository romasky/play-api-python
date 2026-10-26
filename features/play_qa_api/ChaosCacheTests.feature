@allure.label.epic:Chaos_Engineering @allure.label.suite:Chaos_Engineering @allure.label.subSuite:Chaos_Cache
Feature: Chaos — conditional requests (GET /chaos/cache)

  # A fixed resource: ETag "chaos-v1", Last-Modified Tue, 01 Sep 2026 00:00:00 GMT, Cache-Control public, max-age=60.
  # If-None-Match uses the weak comparison and takes precedence over If-Modified-Since (RFC 7232).

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: The resource carries its validators
    When Get chaos cache and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "etag" equals "chaos-v1" in response "response"
    And Assert response header "ETag" equals ""chaos-v1"" in "response"
    And Assert response header "Last-Modified" equals "Tue, 01 Sep 2026 00:00:00 GMT" in "response"
    And Assert response header "Cache-Control" equals "public, max-age=60" in "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: If-None-Match <label> answers 304 with no body but the validators
    When Get chaos cache with header "If-None-Match" value "<etag>" and save response as "response"
    Then Get and check status code 304 from "response"
    And Assert response body is empty in "response"
    And Assert response header "ETag" equals ""chaos-v1"" in "response"
    Examples:
      | label          | etag                      |
      | strong match   | \"chaos-v1\"              |
      | weak match     | W/\"chaos-v1\"            |
      | in a list      | \"x\", \"chaos-v1\"       |
      | wildcard       | *                         |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: A non-matching If-None-Match answers 200 with the body
    When Get chaos cache with header "If-None-Match" value "\"other\"" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "etag" equals "chaos-v1" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: If-Modified-Since <label> answers <status>
    When Get chaos cache with header "If-Modified-Since" value "<since>" and save response as "response"
    Then Get and check status code <status> from "response"
    Examples:
      | label                    | since                         | status |
      | equal to Last-Modified   | Tue, 01 Sep 2026 00:00:00 GMT | 304    |
      | older than Last-Modified | Mon, 31 Aug 2026 00:00:00 GMT | 200    |
      | not a date (ignored)     | garbage                       | 200    |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: If-None-Match takes precedence over If-Modified-Since
    When Get chaos cache with If-None-Match "\"other\"" and If-Modified-Since "Tue, 01 Sep 2026 00:00:00 GMT" and save response as "response"
    Then Get and check status code 200 from "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: POST /chaos/cache is not routed — 404 plain text, never 405
    When Send "POST" chaos cache request and save response as "response"
    Then Get and check status code 404 from "response"
    And Assert response "response" is plain text "404 page not found"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: HEAD /chaos/cache is not routed either (404, and HEAD never has a body)
    When Send "HEAD" chaos cache request and save response as "response"
    Then Get and check status code 404 from "response"
    And Assert response body is empty in "response"
