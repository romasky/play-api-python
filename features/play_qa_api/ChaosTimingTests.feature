@allure.label.epic:Chaos_Engineering @allure.label.suite:Chaos_Engineering @allure.label.subSuite:Chaos_Timing
Feature: Chaos — delays and timeouts (GET /chaos/delay/{seconds}, GET /chaos/timeout)

  # delay: holds N seconds (float, max 9 — clamped) and answers 200. timeout: holds `after` seconds, then 504 —
  # Cloudflare replaces the documented GATEWAY_TIMEOUT JSON with its own error page, so only the
  # status and the hold time are asserted. A client read timeout shorter than the hold is an outcome, not an error.
  # Timing bounds are generous: the round trip alone is ≈ 0.7-1.1 s.

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: Delay 1 second answers 200 after at least one second
    When Get chaos delay "1" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "delayed_seconds" equals "1" in response "response"
    And Assert field "clamped" equals "false" in response "response"
    And Assert request "response" took between 1 and 5 seconds

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: A fractional delay is honoured
    When Get chaos delay "0.5" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "delayed_seconds" equals "0.5" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Delay "<seconds>" returns 400 INVALID_DELAY
    When Get chaos delay "<seconds>" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "INVALID_DELAY" in response "response"
    Examples:
      | seconds |
      | -1      |
      | abc     |
      | NaN     |
      | Inf     |

  @Run @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: A client read timeout shorter than the delay gives up before the answer
    When Get chaos delay "3" with a read timeout of 1 second and save response as "response"
    Then Assert request "response" timed out
    And Assert request "response" took between 1 and 3 seconds

  # @Positive on purpose: answering 504 after the hold IS the endpoint's success behaviour
  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: The gateway timeout holds, then answers 504 (with a Cloudflare page, not the documented JSON)
    When Get chaos timeout with query "after=1" and save response as "response"
    Then Get and check status code 504 from "response"
    And Assert response "response" is a Cloudflare error page for status 504
    And Assert request "response" took between 1 and 6 seconds

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: A client read timeout fires before the gateway timeout
    When Get chaos timeout with query "after=3" and a read timeout of 1 second and save response as "response"
    Then Assert request "response" timed out

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Timeout with after=<after> returns 400 INVALID_TIMEOUT (empty is not the default)
    When Get chaos timeout with query "after=<after>" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "INVALID_TIMEOUT" in response "response"
    Examples:
      | after |
      | -1    |
      | abc   |
      | NaN   |
      | Inf   |
      |       |
