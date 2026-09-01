@allure.label.epic:System @allure.label.suite:Health_Check @allure.label.subSuite:Availability
Feature: Health Check

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: Health endpoint returns 200 with ok status
    When Send GET health request and save as "response"
    Then Get and check status code 200 from "response"
    And Assert field "status" equals "ok" in response "response"
    And Assert field "time" is not null in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Health endpoint returns correct content type
    When Send GET health request and save as "response"
    Then Get and check status code 200 from "response"
    And Assert response header "content-type" contains "application/json" in "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Health endpoint returns request-id header
    When Send GET health request and save as "response"
    Then Get and check status code 200 from "response"
    And Assert response header "x-request-id" is present in "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Health endpoint echoes provided X-Request-ID header
    Given Save string "my-custom-request-id-123" as "myRequestId"
    When Send GET health request with X-Request-ID "myRequestId" and save as "response"
    Then Get and check status code 200 from "response"
    And Assert response header "x-request-id" equals "myRequestId" in "response"
