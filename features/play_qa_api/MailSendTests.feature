@allure.label.epic:Mail_Service @allure.label.suite:Mail_Service @allure.label.subSuite:Mail_Send
Feature: Mail Send

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: Send message returns 201 with full message object
    When Create mailbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "mailToken"
    And Generate sender email and save as "senderEmail"
    And Generate message subject and save as "subject"
    And Generate message body and save as "msgBody"
    When Send message to token "mailToken" from "senderEmail" subject "subject" body "msgBody" and save response as "response"
    Then Get and check status code 201 from "response"
    And Assert field "id" is not null in response "response"
    And Assert field "from" equals "senderEmail" in response "response"
    And Assert field "subject" equals "subject" in response "response"
    And Assert field "body" equals "msgBody" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Send message with html_body
    When Create mailbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "mailToken"
    When Send message to token "mailToken" with raw body "{\"from\":\"test@example.com\",\"subject\":\"HTML Test\",\"body\":\"Plain body\",\"html_body\":\"<b>Bold</b>\"}" and save response as "response"
    Then Get and check status code 201 from "response"
    And Assert field "html_body" is present in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Send message without from field returns 400
    When Create mailbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "mailToken"
    When Send message to token "mailToken" with raw body "{\"subject\":\"Test\",\"body\":\"Body\"}" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Send message without subject returns 400
    When Create mailbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "mailToken"
    When Send message to token "mailToken" with raw body "{\"from\":\"test@example.com\",\"body\":\"Body\"}" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Send message without body returns 400
    When Create mailbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "mailToken"
    When Send message to token "mailToken" with raw body "{\"from\":\"test@example.com\",\"subject\":\"Test\"}" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Send message to non-existent mailbox returns 404
    Given Generate fake uuid and save as "fakeToken"
    When Send message to token "fakeToken" with raw body "{\"from\":\"test@example.com\",\"subject\":\"Test\",\"body\":\"Body\"}" and save response as "response"
    Then Get and check status code 404 from "response"
    And Assert error code is "MAILBOX_NOT_FOUND" in response "response"

  @Run @Flow @allure.label.story:End_to_End_Flow
  Scenario: Send message then retrieve it from messages list
    When Create mailbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "mailToken"
    And Generate sender email and save as "senderEmail"
    And Generate message subject and save as "subject"
    And Generate message body and save as "msgBody"
    When Send message to token "mailToken" from "senderEmail" subject "subject" body "msgBody" and save response as "sendRes"
    Then Get and check status code 201 from "sendRes"
    When Get messages for token "mailToken" and save response as "listRes"
    Then Get and check status code 200 from "listRes"
    And Assert field "count" equals "1" in response "listRes"
