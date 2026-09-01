@allure.label.epic:Mail_Service @allure.label.suite:Mail_Service @allure.label.subSuite:Mailbox_Get
Feature: Mailbox Get

  @Run @Smoke @Positive @allure.label.severity:normal @allure.label.story:Positive_Scenario
  Scenario: Get existing mailbox returns 200 with correct data
    When Create mailbox and save response as "createRes"
    Then Get and check status code 201 from "createRes"
    And Extract "token" from "createRes" and save as "mailToken"
    When Get mailbox with token "mailToken" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "token" equals "mailToken" in response "response"
    And Assert field "email_address" is not null in response "response"
    And Assert field "expires_at" is not null in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Get mailbox with non-existent token returns 404
    Given Generate fake uuid and save as "fakeToken"
    When Get mailbox with token "fakeToken" and save response as "response"
    Then Get and check status code 404 from "response"
    And Assert error code is "MAILBOX_NOT_FOUND" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Get mailbox response has all required fields
    When Create mailbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "mailToken"
    When Get mailbox with token "mailToken" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "id" is not null in response "response"
    And Assert field "token" is not null in response "response"
    And Assert field "email_address" is not null in response "response"
    And Assert field "domain" is not null in response "response"
    And Assert field "created_at" is not null in response "response"
