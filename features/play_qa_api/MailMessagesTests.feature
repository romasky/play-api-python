@allure.label.epic:Mail_Service @allure.label.suite:Mail_Service @allure.label.subSuite:Mail_Messages
Feature: Mail Messages

  @Run @Smoke @Positive @allure.label.severity:normal @allure.label.story:Positive_Scenario
  Scenario: List messages returns 200 with count
    When Create mailbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "mailToken"
    When Get messages for token "mailToken" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "count" is present in response "response"
    And Assert field "count" equals "0" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: List messages after sending one shows count 1
    When Create mailbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "mailToken"
    When Send message to token "mailToken" from "sender@example.com" subject "Test" body "Hello" and save response as "sendRes"
    Then Get and check status code 201 from "sendRes"
    When Get messages for token "mailToken" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "count" equals "1" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: List messages returns body_preview not full body
    When Create mailbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "mailToken"
    When Send message to token "mailToken" with raw body "{\"from\":\"sender@example.com\",\"subject\":\"Test\",\"body\":\"Hello World\",\"html_body\":\"<p>Hello</p>\"}" and save response as "sendRes"
    Then Get and check status code 201 from "sendRes"
    When Get messages for token "mailToken" and save response as "listRes"
    Then Get and check status code 200 from "listRes"
    And Assert messages list "listRes" items have no full body

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: List messages for non-existent mailbox returns 404
    Given Generate fake uuid and save as "fakeToken"
    When Get messages for token "fakeToken" and save response as "response"
    Then Get and check status code 404 from "response"
    And Assert error code is "MAILBOX_NOT_FOUND" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Get single message returns full body and html_body
    When Create mailbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "mailToken"
    When Send message to token "mailToken" with raw body "{\"from\":\"t@e.com\",\"subject\":\"Sub\",\"body\":\"Full body text\",\"html_body\":\"<p>HTML</p>\"}" and save response as "sendRes"
    Then Get and check status code 201 from "sendRes"
    And Extract "id" from "sendRes" and save as "msgId"
    When Get message "msgId" for token "mailToken" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "body" equals "Full body text" in response "response"
    And Assert field "html_body" equals "<p>HTML</p>" in response "response"
    And Assert field "received_at" is not null in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Get message with wrong mailbox token returns 404
    When Create mailbox and save response as "mailboxA"
    And Extract "token" from "mailboxA" and save as "tokenA"
    When Create mailbox and save response as "mailboxB"
    And Extract "token" from "mailboxB" and save as "tokenB"
    When Send message to token "tokenA" from "t@e.com" subject "Sub" body "Body" and save response as "sendRes"
    Then Get and check status code 201 from "sendRes"
    And Extract "id" from "sendRes" and save as "msgId"
    When Get message "msgId" for token "tokenB" and save response as "response"
    Then Get and check status code 404 from "response"
    And Assert error code is "MESSAGE_NOT_FOUND" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Get message with fake message ID returns 404
    When Create mailbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "mailToken"
    And Generate fake mongo id and save as "fakeMsgId"
    When Get message "fakeMsgId" for token "mailToken" and save response as "response"
    Then Get and check status code 404 from "response"
    And Assert error code is "MESSAGE_NOT_FOUND" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Messages are sorted newest first
    When Create mailbox and save response as "createRes"
    And Extract "token" from "createRes" and save as "mailToken"
    When Send message to token "mailToken" from "a@e.com" subject "First" body "Body 1" and save response as "msg1"
    Then Get and check status code 201 from "msg1"
    When Send message to token "mailToken" from "b@e.com" subject "Second" body "Body 2" and save response as "msg2"
    Then Get and check status code 201 from "msg2"
    When Get messages for token "mailToken" and save response as "listRes"
    Then Get and check status code 200 from "listRes"
    And Assert field "count" equals "2" in response "listRes"
    And Assert field "messages.0.subject" equals "Second" in response "listRes"
