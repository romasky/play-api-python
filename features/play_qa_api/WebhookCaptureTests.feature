@allure.label.epic:Webhooks @allure.label.suite:Webhooks @allure.label.subSuite:Webhook_Capture
Feature: Webhook Capture (ANY /webhooks/in/{ingest_token})

  # GET/POST/PUT/PATCH/DELETE → 202 {received, event_id}; HEAD → 202 with an empty body and X-PlayQA-Event-Id;
  # OPTIONS → 204 (CORS) and is NOT captured. Bodies of any type up to 64 KiB; repeated headers and query keys
  # are kept; Authorization / Cookie are masked. Signature: t=<unix>,v1=hmac_sha256(secret, "t.body"),
  # ±300 s tolerance; it never blocks a capture — it only sets signature_valid true / false / null.

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: A JSON POST is captured in full
    When Create webhook inbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "token"
    And Extract "ingest_token" from "createRes" and save as "ingestToken"
    And Send POST to webhook ingest "ingestToken" with JSON body "{\"event\":\"order.created\",\"id\":42}" and save response as "captureRes"
    Then Get and check status code 202 from "captureRes"
    And Assert field "received" equals "true" in response "captureRes"
    And Extract "event_id" from "captureRes" and save as "eventId"
    When Get webhook event "eventId" of "token" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "method" equals "POST" in response "response"
    And Assert field "body" equals "sentBody" in response "response"
    And Assert field "body_encoding" equals "utf8" in response "response"
    And Assert field "body_size" equals "33" in response "response"
    And Assert field "content_type" equals "application/json" in response "response"
    And Assert field "path" equals "/api/v1/webhooks/in/${ingestToken}" in response "response"
    And Assert field "signature_valid" is null in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: <method> is captured with its method
    When Create webhook inbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "token"
    And Extract "ingest_token" from "createRes" and save as "ingestToken"
    And Send "<method>" to webhook ingest "ingestToken" and save response as "captureRes"
    Then Get and check status code 202 from "captureRes"
    And Extract "event_id" from "captureRes" and save as "eventId"
    When Get webhook event "eventId" of "token" and save response as "response"
    Then Assert field "method" equals "<method>" in response "response"
    Examples:
      | method |
      | GET    |
      | PUT    |
      | PATCH  |
      | DELETE |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: HEAD is captured with an empty body; the event id comes in a header
    When Create webhook inbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "token"
    And Extract "ingest_token" from "createRes" and save as "ingestToken"
    And Send "HEAD" to webhook ingest "ingestToken" and save response as "captureRes"
    Then Get and check status code 202 from "captureRes"
    And Assert response body is empty in "captureRes"
    And Assert response header "X-PlayQA-Event-Id" contains "evt_" in "captureRes"
    And Extract header "X-PlayQA-Event-Id" from "captureRes" and save as "eventId"
    When Get webhook event "eventId" of "token" and save response as "response"
    Then Assert field "method" equals "HEAD" in response "response"
    And Assert field "body" is absent in response "response"
    And Assert field "body_size" equals "0" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: OPTIONS answers 204 and is not captured
    When Create webhook inbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "token"
    And Extract "ingest_token" from "createRes" and save as "ingestToken"
    And Send "OPTIONS" to webhook ingest "ingestToken" and save response as "optionsRes"
    Then Get and check status code 204 from "optionsRes"
    When List webhook events of "token" and save response as "response"
    Then Assert field "total" equals "0" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Repeated headers and repeated query keys are both kept
    When Create webhook inbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "token"
    And Extract "ingest_token" from "createRes" and save as "ingestToken"
    And Send POST to webhook ingest "ingestToken" with header "X-Custom" values "one" and "two" and query "a=1&a=2" and save response as "captureRes"
    And Extract "event_id" from "captureRes" and save as "eventId"
    And Get webhook event "eventId" of "token" and save response as "response"
    Then Assert field "headers.X-Custom.0" equals "one" in response "response"
    And Assert field "headers.X-Custom.1" equals "two" in response "response"
    And Assert field "query.a.0" equals "1" in response "response"
    And Assert field "query.a.1" equals "2" in response "response"

  @Run @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario Outline: The <header> header is captured masked
    When Create webhook inbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "token"
    And Extract "ingest_token" from "createRes" and save as "ingestToken"
    And Send POST to webhook ingest "ingestToken" with header "<header>" value "<value>" and save response as "captureRes"
    And Extract "event_id" from "captureRes" and save as "eventId"
    And Get webhook event "eventId" of "token" and save response as "response"
    Then Assert field "headers.<header>.0" equals "***" in response "response"
    Examples:
      | header        | value              |
      | Authorization | Bearer s3cr3t      |
      | Cookie        | session=top-secret |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: A binary body is stored base64-encoded
    When Create webhook inbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "token"
    And Extract "ingest_token" from "createRes" and save as "ingestToken"
    And Send POST to webhook ingest "ingestToken" with a binary body and save response as "captureRes"
    And Extract "event_id" from "captureRes" and save as "eventId"
    And Get webhook event "eventId" of "token" and save response as "response"
    Then Assert field "body_encoding" equals "base64" in response "response"
    And Assert field "body" is the base64 of the binary body in response "response"

  @Run @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario Outline: A <kind> signature gives signature_valid <valid>
    When Create webhook inbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "token"
    And Extract "ingest_token" from "createRes" and save as "ingestToken"
    And Extract "signing_secret" from "createRes" and save as "secret"
    And Send POST to webhook ingest "ingestToken" signed with "secret" as "<kind>" and save response as "captureRes"
    Then Get and check status code 202 from "captureRes"
    And Extract "event_id" from "captureRes" and save as "eventId"
    When Get webhook event "eventId" of "token" and save response as "response"
    Then Assert field "signature_valid" equals "<valid>" in response "response"
    Examples:
      | kind             | valid |
      | valid            | true  |
      | wrong hmac       | false |
      | stale timestamp  | false |
      | future timestamp | false |
      | garbage          | false |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: <label> signature header gives signature_valid null
    When Create webhook inbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "token"
    And Extract "ingest_token" from "createRes" and save as "ingestToken"
    And Extract "signing_secret" from "createRes" and save as "secret"
    And Send POST to webhook ingest "ingestToken" signed with "secret" as "<kind>" and save response as "captureRes"
    And Extract "event_id" from "captureRes" and save as "eventId"
    And Get webhook event "eventId" of "token" and save response as "response"
    Then Assert field "signature_valid" is null in response "response"
    Examples:
      | label     | kind  |
      | A missing | none  |
      | An empty  | empty |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: A body of exactly 64 KiB is captured; the list shows a 200-byte preview
    When Create webhook inbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "token"
    And Extract "ingest_token" from "createRes" and save as "ingestToken"
    And Send POST to webhook ingest "ingestToken" with a body of size "64 KiB" and save response as "captureRes"
    Then Get and check status code 202 from "captureRes"
    When List webhook events of "token" and save response as "response"
    Then Assert field "events.0.body_size" equals "65536" in response "response"
    And Assert field "events.0.body_preview" has length 200 in response "response"

  # ─────────────────── NEGATIVE ───────────────────

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: A body of 64 KiB + 1 byte returns 413 PAYLOAD_TOO_LARGE and nothing is stored
    When Create webhook inbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "token"
    And Extract "ingest_token" from "createRes" and save as "ingestToken"
    And Send POST to webhook ingest "ingestToken" with a body of size "64 KiB + 1" and save response as "response"
    Then Get and check status code 413 from "response"
    And Assert error code is "PAYLOAD_TOO_LARGE" in response "response"
    When List webhook events of "token" and save response as "eventsRes"
    Then Assert field "total" equals "0" in response "eventsRes"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Capture with an unknown ingest token returns 404 WEBHOOK_NOT_FOUND
    Given Generate fake uuid and save as "fakeIngest"
    When Send "POST" to webhook ingest "fakeIngest" and save response as "response"
    Then Get and check status code 404 from "response"
    And Assert error code is "WEBHOOK_NOT_FOUND" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: An unknown event id returns 404 EVENT_NOT_FOUND
    When Create webhook inbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "token"
    And Get webhook event "evt_0000000000000000" of "token" and save response as "response"
    Then Get and check status code 404 from "response"
    And Assert error code is "EVENT_NOT_FOUND" in response "response"

  @Run @Negative @allure.label.severity:critical @allure.label.story:Negative_Scenario
  Scenario: Events are isolated per inbox — another inbox cannot read the event
    When Create webhook inbox and save response as "inboxA"
    And Extract "ingest_token" from "inboxA" and save as "ingestA"
    And Create webhook inbox and save response as "inboxB"
    And Extract "token" from "inboxB" and save as "tokenB"
    And Send "POST" to webhook ingest "ingestA" and save response as "captureRes"
    And Extract "event_id" from "captureRes" and save as "eventId"
    And Get webhook event "eventId" of "tokenB" and save response as "response"
    Then Get and check status code 404 from "response"
    And Assert error code is "EVENT_NOT_FOUND" in response "response"
