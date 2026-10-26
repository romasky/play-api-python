@allure.label.epic:Chaos_Engineering @allure.label.suite:Chaos_Engineering @allure.label.subSuite:Chaos_Echo
Feature: Chaos — echo (GET|POST /chaos/echo)

  # Reflects the request back (httpbin /anything style). `body` is the parsed JSON for a JSON content type,
  # otherwise null with the text in `raw_body`; binary bodies come back base64. Sensitive headers are masked.
  # Bodies over 64 KiB are truncated; over 1 MiB → 413.

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: Echo reflects the method, the path and the query (repeated keys joined)
    When Send "GET" chaos echo with query "a=1&a=2&b=x" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "method" equals "GET" in response "response"
    And Assert field "path" equals "/api/v1/chaos/echo" in response "response"
    And Assert field "query.a" equals "1,2" in response "response"
    And Assert field "query.b" equals "x" in response "response"
    And Assert field "truncated" equals "false" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: A custom header is echoed verbatim
    When Send GET chaos echo with header "X-Custom" value "v1" and save response as "response"
    Then Assert field "headers.X-Custom" equals "v1" in response "response"

  @Run @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario Outline: The <header> header is echoed masked
    When Send GET chaos echo with header "<header>" value "<value>" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "headers.<header>" equals "***" in response "response"
    Examples:
      | header        | value         |
      | Authorization | Bearer s3cr3t |
      | Cookie        | session=abc   |
      | X-Api-Key     | key-123       |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: A client X-Request-ID is propagated to the body and the response header
    Given Generate fake uuid and save as "requestId"
    When Send GET chaos echo with header "X-Request-ID" value "requestId" and save response as "response"
    Then Assert field "request_id" equals "requestId" in response "response"
    And Assert response header "X-Request-ID" equals "requestId" in "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: A JSON POST is parsed into body and kept verbatim in raw_body
    When Post chaos echo as "application/json" with body "{\"x\":1}" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "body.x" equals "1" in response "response"
    And Assert field "raw_body" equals "sentBody" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: A text/plain POST stays raw
    When Post chaos echo as "text/plain" with body "hello" and save response as "response"
    Then Assert field "body" is null in response "response"
    And Assert field "raw_body" equals "hello" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: A binary POST comes back base64-encoded
    When Post chaos echo with the bytes "000102ff" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "encoding" equals "base64" in response "response"
    And Assert field "body_base64" equals "AAEC/w==" in response "response"
    And Assert field "raw_body" is null in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: A body over 64 KiB is truncated to its first 65536 characters
    When Post chaos echo with a text body of 70000 bytes and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "truncated" equals "true" in response "response"
    And Assert field "raw_body" has length 65536 in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: A body over 1 MiB returns 413 PAYLOAD_TOO_LARGE
    When Post chaos echo with a text body of 1048577 bytes and save response as "response"
    Then Get and check status code 413 from "response"
    And Assert error code is "PAYLOAD_TOO_LARGE" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: <method> /chaos/echo is not routed — 404 plain text
    When Send "<method>" chaos echo with query "" and save response as "response"
    Then Get and check status code 404 from "response"
    And Assert response "response" is plain text "404 page not found"
    Examples:
      | method |
      | PUT    |
      | DELETE |
