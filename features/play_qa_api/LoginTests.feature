@allure.label.epic:Authentication @allure.label.suite:Authentication @allure.label.subSuite:Login
Feature: Login

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: Login with valid credentials returns 200 with token
    Given Create minimal user and save response as "createRes"
    And Extract "email" from "createRes" and save as "userEmail"
    When Login with "userEmail" and "generatedPassword" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert login response is successful in "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Login response includes correct user info
    Given Create minimal user and save response as "createRes"
    And Extract "email" from "createRes" and save as "userEmail"
    And Extract "id" from "createRes" and save as "userId"
    When Login with "userEmail" and "generatedPassword" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "email" equals "userEmail" in response "response"
    And Assert field "user_id" equals "userId" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Login token has correct format
    Given Create minimal user and save response as "createRes"
    And Extract "email" from "createRes" and save as "userEmail"
    When Login with "userEmail" and "generatedPassword" and save response as "response"
    Then Get and check status code 200 from "response"
    And Extract "access_token" from "response" and save as "loginToken"
    And Assert "loginToken" matches regex "^usr_\d+_[a-f0-9]{32}$"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Login invalidates previous token
    Given Create minimal user and save response as "createRes"
    And Extract "access_token" from "createRes" and save as "firstToken"
    And Extract "email" from "createRes" and save as "userEmail"
    And Extract "id" from "createRes" and save as "userId"
    When Login with "userEmail" and "generatedPassword" and save response as "loginRes"
    Then Get and check status code 200 from "loginRes"
    And Extract "access_token" from "loginRes" and save as "secondToken"
    When Patch user "userId" with field "username" value "user_newname1" token "firstToken" and save response as "patchRes"
    Then Get and check status code 401 from "patchRes"
    And Assert error code is "INVALID_TOKEN" in response "patchRes"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Login with wrong password returns 401
    Given Create minimal user and save response as "createRes"
    And Extract "email" from "createRes" and save as "userEmail"
    And Save string "wrongpassword123" as "wrongPass"
    When Login with "userEmail" and "wrongPass" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_CREDENTIALS" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Login with non-existent email returns 401
    Given Generate email and save as "fakeEmail"
    And Save string "somepassword123" as "somePass"
    When Login with "fakeEmail" and "somePass" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_CREDENTIALS" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Login error response contains request_id in body
    Given Generate email and save as "fakeEmail"
    And Save string "somepassword123" as "somePass"
    When Login with "fakeEmail" and "somePass" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_CREDENTIALS" in response "response"
    And Assert response has request_id in "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Login error response has x-request-id header
    Given Generate email and save as "fakeEmail"
    And Save string "somepassword123" as "somePass"
    When Login with "fakeEmail" and "somePass" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert response header "x-request-id" is present in "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Login with missing email returns 400
    When Login with raw body "{\"password\":\"somepassword123\"}" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Login with missing password returns 400
    When Login with raw body "{\"email\":\"test@play-qa.com\"}" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Login with invalid email format returns 400
    When Login with raw body "{\"email\":\"notanemail\",\"password\":\"somepassword123\"}" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Login with short password returns 400
    When Login with raw body "{\"email\":\"test@play-qa.com\",\"password\":\"short\"}" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Login response has x-request-id header
    Given Create minimal user and save response as "createRes"
    And Extract "email" from "createRes" and save as "userEmail"
    When Login with "userEmail" and "generatedPassword" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert response header "x-request-id" is present in "response"
