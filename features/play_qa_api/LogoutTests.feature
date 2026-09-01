@allure.label.epic:Authentication @allure.label.suite:Authentication @allure.label.subSuite:Logout
Feature: Logout

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: Logout returns 200 with success message
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    And Extract "access_token" from "createRes" and save as "token"
    When Logout user "userId" with token "token" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "success" equals "true" in response "response"
    And Assert field "message" contains "Logged out" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Token is revoked after logout
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    And Extract "access_token" from "createRes" and save as "token"
    When Logout user "userId" with token "token" and save response as "logoutRes"
    Then Get and check status code 200 from "logoutRes"
    When Patch user "userId" with raw body "{\"username\":\"changedname1\"}" token "token" and save response as "patchRes"
    Then Get and check status code 401 from "patchRes"
    And Assert error code is "INVALID_TOKEN" in response "patchRes"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Delete is rejected with revoked token after logout
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    And Extract "access_token" from "createRes" and save as "token"
    When Logout user "userId" with token "token" and save response as "logoutRes"
    Then Get and check status code 200 from "logoutRes"
    When Delete user "userId" with token "token" and save response as "deleteRes"
    Then Get and check status code 401 from "deleteRes"
    And Assert error code is "INVALID_TOKEN" in response "deleteRes"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Double logout — second attempt returns 401 INVALID_TOKEN
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    And Extract "access_token" from "createRes" and save as "token"
    When Logout user "userId" with token "token" and save response as "firstLogout"
    Then Get and check status code 200 from "firstLogout"
    When Logout user "userId" with token "token" and save response as "secondLogout"
    Then Get and check status code 401 from "secondLogout"
    And Assert error code is "INVALID_TOKEN" in response "secondLogout"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Logout without auth header returns 401 MISSING_TOKEN
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    When Logout user "userId" with no auth token and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "MISSING_TOKEN" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Logout with wrong token returns 401
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    And Save string "usr_0000000000_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" as "wrongToken"
    When Logout user "userId" with token "wrongToken" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_TOKEN" in response "response"

  @Run @Flow @allure.label.story:End_to_End_Flow
  Scenario: Full login-logout-login flow
    Given Create minimal user and save response as "createRes"
    And Extract "email" from "createRes" and save as "userEmail"
    And Extract "id" from "createRes" and save as "userId"
    And Extract "access_token" from "createRes" and save as "token"
    When Logout user "userId" with token "token" and save response as "logoutRes"
    Then Get and check status code 200 from "logoutRes"
    When Login with "userEmail" and "generatedPassword" and save response as "loginRes"
    Then Get and check status code 200 from "loginRes"
    And Assert field "access_token" is not null in response "loginRes"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Logout non-existent user returns 401 INVALID_TOKEN
    Given Generate fake mongo id and save as "fakeId"
    When Logout user "fakeId" with token "fake_token" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_TOKEN" in response "response"
