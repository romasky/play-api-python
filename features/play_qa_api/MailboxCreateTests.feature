@allure.label.epic:Mail_Service @allure.label.suite:Mail_Service @allure.label.subSuite:Mailbox_Create
Feature: Mailbox Create

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: Create mailbox with empty body returns 201
    When Create mailbox and save response as "response"
    Then Get and check status code 201 from "response"
    And Assert field "token" is not null in response "response"
    And Assert field "email_address" is not null in response "response"
    And Assert field "domain" equals "play-qa.com" in response "response"
    And Assert field "expires_at" is not null in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Create mailbox with custom local_part
    Given Generate local part and save as "localPart"
    When Create mailbox with context local_part "localPart" and save response as "response"
    Then Get and check status code 201 from "response"
    And Assert field "email_address" contains "localPart" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: Create mailbox with valid domain
    When Create mailbox with domain "<domain>" and save response as "response"
    Then Get and check status code 201 from "response"
    And Assert field "domain" equals "<domain>" in response "response"
    Examples:
      | domain              |
      | play-qa.com         |
      | mail.play-qa.com    |
      | temp.play-qa.com    |
      | inbox.play-qa.com   |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: Create mailbox with local_part at length boundary <length> returns 201
    Given Generate string of length <length> and save as "localPart"
    When Create mailbox with context local_part "localPart" and save response as "response"
    Then Get and check status code 201 from "response"
    And Assert field "email_address" contains "localPart" in response "response"
    Examples:
      | length |
      | 3      |
      | 30     |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Create mailbox with allowed special chars underscore and hyphen returns 201
    Given Generate local part with underscore and hyphen and save as "localPart"
    When Create mailbox with context local_part "localPart" and save response as "response"
    Then Get and check status code 201 from "response"
    And Assert field "email_address" contains "localPart" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Create mailbox with invalid domain returns 400
    When Create mailbox with domain "invalid.example.com" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "INVALID_DOMAIN" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Create mailbox with too-short local_part returns 400
    When Create mailbox with local_part "ab" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "INVALID_LOCAL_PART" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Create mailbox with invalid chars in local_part returns 400
    When Create mailbox with local_part "My_Test_BOX!" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "INVALID_LOCAL_PART" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Create duplicate mailbox address returns 409
    Given Generate local part and save as "dupLocalPart"
    When Create mailbox with context local_part "dupLocalPart" and save response as "firstRes"
    Then Get and check status code 201 from "firstRes"
    When Create mailbox with context local_part "dupLocalPart" and save response as "secondRes"
    Then Get and check status code 409 from "secondRes"
    And Assert error code is "ADDRESS_TAKEN" in response "secondRes"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Mailbox token is a UUID format
    When Create mailbox and save response as "response"
    Then Get and check status code 201 from "response"
    And Extract "token" from "response" and save as "mailToken"
    And Assert "mailToken" matches regex "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Mailbox response has request-id header
    When Create mailbox and save response as "response"
    Then Get and check status code 201 from "response"
    And Assert response header "x-request-id" is present in "response"

  @Run @Flow @allure.label.story:End_to_End_Flow
  Scenario: Create mailbox then retrieve it
    When Create mailbox and save response as "createRes"
    Then Get and check status code 201 from "createRes"
    And Extract "token" from "createRes" and save as "mailToken"
    When Get mailbox with token "mailToken" and save response as "getRes"
    Then Get and check status code 200 from "getRes"
    And Assert field "token" equals "mailToken" in response "getRes"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Create mailbox with too-long local_part returns 400
    Given Generate string of length 31 and save as "longLocalPart"
    When Create mailbox with context local_part "longLocalPart" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "INVALID_LOCAL_PART" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Create mailbox with uppercase in local_part returns 400
    When Create mailbox with local_part "TestBox123" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "INVALID_LOCAL_PART" in response "response"
