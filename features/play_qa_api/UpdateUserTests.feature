@allure.label.epic:User_Lifecycle @allure.label.suite:User_Management @allure.label.subSuite:Update_User
Feature: Update User

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: Full update user returns 200 with updated data
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    And Extract "access_token" from "createRes" and save as "token"
    And Generate email and save as "email"
    And Generate username and save as "username"
    And Generate first name and save as "firstName"
    And Generate last name and save as "lastName"
    When Update user "userId" with token "token" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "email" equals "email" in response "response"
    And Assert field "username" equals "username" in response "response"
    And Assert field "access_token" is absent in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Update user without auth header returns 401 MISSING_TOKEN
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    When Update user "userId" with no auth token and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "MISSING_TOKEN" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Update user with wrong token returns 401
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    And Save string "usr_0000000000_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" as "badToken"
    When Update user "userId" with raw body "{\"email\":\"test@play-qa.com\",\"username\":\"testuser\",\"profile\":{\"first_name\":\"John\",\"last_name\":\"Doe\"}}" token "badToken" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_TOKEN" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Update non-existent user returns 401 INVALID_TOKEN
    Given Generate fake mongo id and save as "fakeId"
    And Save string "usr_0000000000_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" as "badToken"
    When Update user "fakeId" with raw body "{\"email\":\"test@play-qa.com\",\"username\":\"testuser\",\"profile\":{\"first_name\":\"John\",\"last_name\":\"Doe\"}}" token "badToken" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_TOKEN" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Update user with missing email returns 400
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    And Extract "access_token" from "createRes" and save as "token"
    When Update user "userId" with raw body "{\"username\":\"testuser\",\"profile\":{\"first_name\":\"John\",\"last_name\":\"Doe\"}}" token "token" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Update user with invalid email returns 400
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    And Extract "access_token" from "createRes" and save as "token"
    When Update user "userId" with raw body "{\"email\":\"notanemail\",\"username\":\"testuser\",\"profile\":{\"first_name\":\"John\",\"last_name\":\"Doe\"}}" token "token" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  @Run @Flow @allure.label.story:End_to_End_Flow
  Scenario: Create then update then verify changes
    Given Generate email and save as "email"
    And Generate username and save as "username"
    And Generate password and save as "password"
    And Generate first name and save as "firstName"
    And Generate last name and save as "lastName"
    When Create user with body and save response as "createRes"
    Then Get and check status code 201 from "createRes"
    And Extract "id" from "createRes" and save as "userId"
    And Extract "access_token" from "createRes" and save as "token"
    Given Generate email and save as "email"
    And Generate username and save as "username"
    And Generate first name and save as "firstName"
    And Generate last name and save as "lastName"
    When Update user "userId" with token "token" and save response as "updateRes"
    Then Get and check status code 200 from "updateRes"
    When Send GET user request for "userId" and save response as "getRes"
    Then Get and check status code 200 from "getRes"
    And Assert field "email" equals "email" in response "getRes"

  @Run @Flow @allure.label.story:End_to_End_Flow
  Scenario: PUT update after logout returns 401 INVALID_TOKEN
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    And Extract "access_token" from "createRes" and save as "token"
    When Logout user "userId" with token "token" and save response as "logoutRes"
    Then Get and check status code 200 from "logoutRes"
    Given Generate email and save as "email"
    And Generate username and save as "username"
    And Generate first name and save as "firstName"
    And Generate last name and save as "lastName"
    When Update user "userId" with token "token" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_TOKEN" in response "response"

  # ─────────────────── CROSS-ACCOUNT (Feature 17: 401 = credential refused, 403 = credential accepted, not permitted) ───────────────────

  @Run @Negative @allure.label.severity:critical @allure.label.story:Negative_Scenario
  Scenario: Update with another user token returns 403 FORBIDDEN
    Given Create minimal user and save response as "userARes"
    And Extract "id" from "userARes" and save as "userAId"
    And Create minimal user and save response as "userBRes"
    And Extract "access_token" from "userBRes" and save as "userBToken"
    And Generate email and save as "email"
    And Generate username and save as "username"
    And Generate first name and save as "firstName"
    And Generate last name and save as "lastName"
    When Update user "userAId" with token "userBToken" and save response as "response"
    Then Get and check status code 403 from "response"
    And Assert error code is "FORBIDDEN" in response "response"
    And Assert field "error.message" equals "You can only modify your own account" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Ownership is checked before body validation — invalid body with another user token returns 403
    Given Create minimal user and save response as "userARes"
    And Extract "id" from "userARes" and save as "userAId"
    And Create minimal user and save response as "userBRes"
    And Extract "access_token" from "userBRes" and save as "userBToken"
    When Update user "userAId" with raw body "{}" token "userBToken" and save response as "response"
    Then Get and check status code 403 from "response"
    And Assert error code is "FORBIDDEN" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Update a non-existent id with a valid token returns 403 FORBIDDEN, not 404
    Given Create minimal user and save response as "createRes"
    And Extract "access_token" from "createRes" and save as "token"
    And Generate fake mongo id and save as "fakeId"
    When Update user "fakeId" with raw body "{\"email\":\"test@play-qa.com\",\"username\":\"testuser\",\"profile\":{\"first_name\":\"John\",\"last_name\":\"Doe\"}}" token "token" and save response as "response"
    Then Get and check status code 403 from "response"
    And Assert error code is "FORBIDDEN" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: An admin token has no write override on another account
    Given Create minimal user and save response as "userARes"
    And Extract "id" from "userARes" and save as "userAId"
    And Create admin user and save response as "adminRes"
    And Extract "access_token" from "adminRes" and save as "adminToken"
    When Update user "userAId" with raw body "{\"email\":\"test@play-qa.com\",\"username\":\"testuser\",\"profile\":{\"first_name\":\"John\",\"last_name\":\"Doe\"}}" token "adminToken" and save response as "response"
    Then Get and check status code 403 from "response"
    And Assert error code is "FORBIDDEN" in response "response"
