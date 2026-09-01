@allure.label.epic:User_Lifecycle @allure.label.suite:User_Management @allure.label.subSuite:Get_User
Feature: Get User

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: Get existing user returns 200 with full data
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    When Send GET user request for "userId" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "id" equals "userId" in response "response"
    And Assert field "email" is not null in response "response"
    And Assert field "username" is not null in response "response"
    And Assert field "access_token" is absent in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Get user by ID returns the same id and all core fields
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    When Send GET user request for "userId" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert user response has all core fields in "response"
    And Assert field "id" equals "userId" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Get user with non-existent ID returns 404
    Given Generate fake mongo id and save as "fakeId"
    When Send GET user request for "fakeId" and save response as "response"
    Then Get and check status code 404 from "response"
    And Assert error code is "USER_NOT_FOUND" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Get user with malformed ID returns 404
    When Send GET user request for "<id>" and save response as "response"
    Then Get and check status code 404 from "response"
    And Assert error code is "USER_NOT_FOUND" in response "response"
    Examples:
      | id           |
      | notanid      |
      | 123          |
      | !!!          |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Get user response does not include password
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    When Send GET user request for "userId" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "password" is absent in response "response"
