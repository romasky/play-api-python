@allure.label.epic:User_Lifecycle @allure.label.suite:User_Management @allure.label.subSuite:Patch_User
Feature: Patch User

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: Partial update email returns 200 with new email
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    And Extract "access_token" from "createRes" and save as "token"
    And Generate email and save as "newEmail"
    When Patch user "userId" with field "email" value "newEmail" token "token" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "email" equals "newEmail" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Partial update username returns 200
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    And Extract "access_token" from "createRes" and save as "token"
    And Generate username and save as "newUsername"
    When Patch user "userId" with field "username" value "newUsername" token "token" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "username" equals "newUsername" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Patch with empty body returns 200 with no changes
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    And Extract "access_token" from "createRes" and save as "token"
    And Extract "email" from "createRes" and save as "originalEmail"
    When Patch user "userId" with empty body token "token" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "email" equals "originalEmail" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Patch response does not include access_token
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    And Extract "access_token" from "createRes" and save as "token"
    And Generate email and save as "newEmail"
    When Patch user "userId" with field "email" value "newEmail" token "token" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "access_token" is absent in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Patch user without auth header returns 401 MISSING_TOKEN
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    When Patch user "userId" with no auth token and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "MISSING_TOKEN" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Patch user with invalid email returns 400
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    And Extract "access_token" from "createRes" and save as "token"
    When Patch user "userId" with raw body "{\"email\":\"notvalid\"}" token "token" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Patch non-existent user returns 401 INVALID_TOKEN (wrong token)
    Given Generate fake mongo id and save as "fakeId"
    When Patch user "fakeId" with raw body "{\"email\":\"test@play-qa.com\"}" token "fake_token" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_TOKEN" in response "response"

  @Run @Negative @allure.label.severity:critical @allure.label.story:Negative_Scenario
  Scenario: Patch with another user token returns 401 INVALID_TOKEN
    Given Create minimal user and save response as "userARes"
    And Extract "id" from "userARes" and save as "userAId"
    And Create minimal user and save response as "userBRes"
    And Extract "access_token" from "userBRes" and save as "userBToken"
    And Generate email and save as "newEmail"
    When Patch user "userAId" with field "email" value "newEmail" token "userBToken" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_TOKEN" in response "response"

  @Run @Flow @allure.label.story:End_to_End_Flow
  Scenario: Patch user and verify with GET
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    And Extract "access_token" from "createRes" and save as "token"
    And Generate email and save as "newEmail"
    When Patch user "userId" with field "email" value "newEmail" token "token" and save response as "patchRes"
    Then Get and check status code 200 from "patchRes"
    When Send GET user request for "userId" and save response as "getRes"
    Then Get and check status code 200 from "getRes"
    And Assert field "email" equals "newEmail" in response "getRes"

  @Run @Flow @allure.label.story:End_to_End_Flow
  Scenario: Patch after logout returns 401 INVALID_TOKEN
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    And Extract "access_token" from "createRes" and save as "token"
    When Logout user "userId" with token "token" and save response as "logoutRes"
    Then Get and check status code 200 from "logoutRes"
    And Generate email and save as "newEmail"
    When Patch user "userId" with field "email" value "newEmail" token "token" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_TOKEN" in response "response"
