@allure.label.epic:User_Lifecycle @allure.label.suite:User_Management @allure.label.subSuite:User_Exists
Feature: User Exists

  @Run @Smoke @Positive @allure.label.severity:normal @allure.label.story:Positive_Scenario
  Scenario: HEAD exists for existing user returns 200 with X-User-Exists true
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    When Send HEAD exists request for "userId" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert response header "x-user-exists" equals "true" in "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: GET exists (CDN alias) for existing user returns 200
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    When Send GET exists request for "userId" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert response header "x-user-exists" equals "true" in "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: HEAD exists for non-existent user returns 404 with X-User-Exists false
    Given Generate fake mongo id and save as "fakeId"
    When Send HEAD exists request for "fakeId" and save response as "response"
    Then Get and check status code 404 from "response"
    And Assert response header "x-user-exists" equals "false" in "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: GET exists for non-existent user returns 404
    Given Generate fake mongo id and save as "fakeId"
    When Send GET exists request for "fakeId" and save response as "response"
    Then Get and check status code 404 from "response"
    And Assert response header "x-user-exists" equals "false" in "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Exists for invalid ObjectID returns 404
    When Send HEAD exists request for "notanobjectid" and save response as "response"
    Then Get and check status code 404 from "response"
    And Assert response header "x-user-exists" equals "false" in "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Exists response always has X-User-Exists header
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    When Send HEAD exists request for "userId" and save response as "response"
    Then Assert response header "x-user-exists" is present in "response"

  @Run @Flow @allure.label.story:End_to_End_Flow
  Scenario: After delete user exists returns false
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    And Extract "access_token" from "createRes" and save as "token"
    When Delete user "userId" with token "token" and save response as "deleteRes"
    Then Get and check status code 204 from "deleteRes"
    When Send HEAD exists request for "userId" and save response as "existsRes"
    Then Get and check status code 404 from "existsRes"
    And Assert response header "x-user-exists" equals "false" in "existsRes"
