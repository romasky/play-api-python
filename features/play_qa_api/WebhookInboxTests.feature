@allure.label.epic:Webhooks @allure.label.suite:Webhooks @allure.label.subSuite:Webhook_Inbox
Feature: Webhook Inbox (create, read, delete, events list)

  # Two tokens per inbox, NOT interchangeable: the private `token` reads and deletes the inbox, the public
  # `ingest_token` (inside ingest_url) only receives captures. Inboxes live 2 h; 20 active per IP (each
  # scenario deletes its inbox); 10 creations per minute (paced per call).

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: Create inbox returns both tokens, the ingest URL, a signing secret and zero counters
    When Create webhook inbox and save response as "response"
    Then Get and check status code 201 from "response"
    And Assert field "id" contains "wh_" in response "response"
    And Assert field "signing_secret" contains "whsec_" in response "response"
    And Extract "ingest_token" from "response" and save as "ingestToken"
    And Extract "token" from "response" and save as "token"
    And Assert "token" matches regex "^[0-9a-f-]{36}$"
    And Assert "ingestToken" matches regex "^[0-9a-f-]{36}$"
    And Assert field "ingest_url" contains "/api/v1/webhooks/in/${ingestToken}" in response "response"
    And Assert field "event_count" equals "0" in response "response"
    And Assert field "total_received" equals "0" in response "response"
    And Assert field "dropped_count" equals "0" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Inbox metadata by the private token never returns the signing secret
    When Create webhook inbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "token"
    And Extract "id" from "createRes" and save as "inboxId"
    And Get webhook inbox "token" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "id" equals "inboxId" in response "response"
    And Assert field "signing_secret" is absent in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Counters follow the captures
    When Create webhook inbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "token"
    And Extract "ingest_token" from "createRes" and save as "ingestToken"
    And Send "POST" to webhook ingest "ingestToken" and save response as "first"
    And Send "PUT" to webhook ingest "ingestToken" and save response as "second"
    And Get webhook inbox "token" and save response as "response"
    Then Assert field "event_count" equals "2" in response "response"
    And Assert field "total_received" equals "2" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Events are listed newest first and paginated
    When Create webhook inbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "token"
    And Extract "ingest_token" from "createRes" and save as "ingestToken"
    And Send "POST" to webhook ingest "ingestToken" and save response as "first"
    And Send "PATCH" to webhook ingest "ingestToken" and save response as "second"
    And Send "DELETE" to webhook ingest "ingestToken" and save response as "third"
    And List webhook events of "token" with query "per_page=2" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "total" equals "3" in response "response"
    And Assert field "returned" equals "2" in response "response"
    And Assert field "page" equals "1" in response "response"
    And Assert field "per_page" equals "2" in response "response"
    And Assert field "events.0.method" equals "DELETE" in response "response"
    And Assert field "events.1.method" equals "PATCH" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: Events per_page <per_page> is <behaviour> (only page is validated)
    When Create webhook inbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "token"
    And List webhook events of "token" with query "per_page=<per_page>" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "per_page" equals "<effective>" in response "response"
    Examples:
      | per_page | behaviour            | effective |
      | 1000     | clamped to 100       | 100       |
      | 0        | silently defaulted   | 20        |
      | abc      | silently defaulted   | 20        |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: A page beyond the data returns an empty events array
    When Create webhook inbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "token"
    And Extract "ingest_token" from "createRes" and save as "ingestToken"
    And Send "POST" to webhook ingest "ingestToken" and save response as "captureRes"
    And List webhook events of "token" with query "page=99" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert list "events" has 0 items in response "response"
    And Assert field "total" equals "1" in response "response"

  # ─────────────────── NEGATIVE ───────────────────

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Events with page=<page> returns 400 VALIDATION_ERROR
    When Create webhook inbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "token"
    And List webhook events of "token" with query "page=<page>" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"
    Examples:
      | page |
      | 0    |
      | -1   |
      | abc  |
      | 1.5  |

  @Run @Negative @allure.label.severity:critical @allure.label.story:Negative_Scenario
  Scenario: The ingest token cannot read the inbox (tokens are not interchangeable)
    When Create webhook inbox and save response as "createRes"
    And Extract "ingest_token" from "createRes" and save as "ingestToken"
    And Get webhook inbox "ingestToken" and save response as "metaRes"
    Then Get and check status code 404 from "metaRes"
    And Assert error code is "WEBHOOK_NOT_FOUND" in response "metaRes"
    When List webhook events of "ingestToken" and save response as "eventsRes"
    Then Get and check status code 404 from "eventsRes"
    And Assert error code is "WEBHOOK_NOT_FOUND" in response "eventsRes"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: The private token cannot be used as an ingest URL
    When Create webhook inbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "token"
    And Send "POST" to webhook ingest "token" and save response as "response"
    Then Get and check status code 404 from "response"
    And Assert error code is "WEBHOOK_NOT_FOUND" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: An unknown inbox token returns 404 WEBHOOK_NOT_FOUND
    Given Generate fake uuid and save as "fakeToken"
    When Get webhook inbox "fakeToken" and save response as "response"
    Then Get and check status code 404 from "response"
    And Assert error code is "WEBHOOK_NOT_FOUND" in response "response"

  @Run @Flow @allure.label.severity:critical @allure.label.story:End_to_End_Flow
  Scenario: Deleted inbox — 204, then 404 everywhere, the ingest URL included
    When Create webhook inbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "token"
    And Extract "ingest_token" from "createRes" and save as "ingestToken"
    And Delete webhook inbox "token" and save response as "deleteRes"
    Then Get and check status code 204 from "deleteRes"
    And Assert response body is empty in "deleteRes"
    When Delete webhook inbox "token" and save response as "againRes"
    Then Get and check status code 404 from "againRes"
    And Assert error code is "WEBHOOK_NOT_FOUND" in response "againRes"
    When Get webhook inbox "token" and save response as "metaRes"
    Then Get and check status code 404 from "metaRes"
    When Send "POST" to webhook ingest "ingestToken" and save response as "ingestRes"
    Then Get and check status code 404 from "ingestRes"
    And Assert error code is "WEBHOOK_NOT_FOUND" in response "ingestRes"
