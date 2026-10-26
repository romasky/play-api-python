@allure.label.epic:System @allure.label.suite:Realtime @allure.label.subSuite:SSE_and_WebSocket
Feature: Realtime — Server-Sent Events (GET /sse/progress) and WebSocket echo (GET /ws/echo)

  # SSE: `steps` (5-100) progress events every `interval_ms` (100-2000), then a `done` event; the bounds are
  # not in the spec. WebSocket: a welcome frame, then every text or binary frame is echoed back unchanged;
  # a plain GET without the Upgrade handshake answers 426 UPGRADE_REQUIRED.

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: An SSE progress stream counts to 100 percent and completes
    When Stream SSE progress with query "steps=5&interval_ms=100" and save the events as "events"
    Then Assert SSE "events" has 5 progress events counting up to 100 percent
    And Assert SSE "events" ends with a done event with status "completed" and total 5

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: The SSE response is an uncached event stream
    When Request SSE progress with query "steps=5&interval_ms=100" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert response header "Content-Type" contains "text/event-stream" in "response"
    And Assert response header "Cache-Control" contains "no-cache" in "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: SSE with <query> returns 400 VALIDATION_ERROR
    When Request SSE progress with query "<query>" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"
    Examples:
      | query           |
      | steps=4         |
      | steps=101       |
      | steps=abc       |
      | interval_ms=99  |
      | interval_ms=2001 |
      | interval_ms=x   |

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: The WebSocket welcomes the client and echoes text and binary frames
    When Open the WebSocket echo and save the welcome as "welcome"
    Then Assert WebSocket welcome "welcome" field "type" equals "welcome"
    And Assert WebSocket welcome "welcome" field "echo" equals "true"
    And Assert WebSocket welcome "welcome" field "session_id" starts with "ws_"
    When Send the text "hello" over the WebSocket and save the reply as "textReply"
    Then Assert "textReply" equals "hello"
    When Send the bytes "0001ff" over the WebSocket and save the reply as "binaryReply"
    Then Assert "binaryReply" equals "0001ff"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: A plain GET without the Upgrade handshake returns 426 UPGRADE_REQUIRED
    When Send a plain GET to the WebSocket echo and save response as "response"
    Then Get and check status code 426 from "response"
    And Assert error code is "UPGRADE_REQUIRED" in response "response"
    And Assert response header "Sec-WebSocket-Version" equals "13" in "response"
