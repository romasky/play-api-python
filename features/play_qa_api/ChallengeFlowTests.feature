@allure.label.epic:Challenges @allure.label.suite:Challenges @allure.label.subSuite:Challenge_Solving
Feature: Challenges — solving each challenge end to end

  # start → act on the sandbox user with its own credentials → verify. A challenge is solved once per player,
  # so every scenario creates its own player. Hints never reduce the points.

  @Run @Smoke @Flow @allure.label.severity:critical @allure.label.story:End_to_End_Flow
  Scenario: Solve delete-user-404 — delete the sandbox with its own token
    Given a user with token "playerToken"
    When Start challenge "delete-user-404" with token "playerToken" and save response as "startRes"
    And Extract the sandbox from "startRes"
    And Verify challenge "delete-user-404" with token "playerToken" and save response as "notYet"
    Then Get and check status code 200 from "notYet"
    And Assert field "solved" equals "false" in response "notYet"
    And Assert field "points_awarded" equals "0" in response "notYet"
    And Assert field "detail" is not null in response "notYet"
    When Delete user "sandboxId" with token "sandboxToken" and save response as "deleteRes"
    Then Get and check status code 204 from "deleteRes"
    When Verify challenge "delete-user-404" with token "playerToken" and save response as "solved"
    Then Get and check status code 200 from "solved"
    And Assert field "solved" equals "true" in response "solved"
    And Assert field "points_awarded" equals "10" in response "solved"
    And Extract "solved_at" from "solved" and save as "solvedAt"
    When Verify challenge "delete-user-404" with token "playerToken" and save response as "again"
    Then Assert field "already_solved" equals "true" in response "again"
    And Assert field "points_awarded" equals "0" in response "again"
    And Assert field "solved_at" equals "solvedAt" in response "again"
    When Get challenge progress with token "playerToken" and save response as "progressRes"
    Then Assert field "solved_count" equals "1" in response "progressRes"
    And Assert field "total_points" equals "10" in response "progressRes"

  @Run @Flow @allure.label.story:End_to_End_Flow
  Scenario: Solve logout-revokes-token — log the sandbox out
    Given a user with token "playerToken"
    When Start challenge "logout-revokes-token" with token "playerToken" and save response as "startRes"
    And Extract the sandbox from "startRes"
    And Logout user "sandboxId" with token "sandboxToken" and save response as "logoutRes"
    Then Get and check status code 200 from "logoutRes"
    When Verify challenge "logout-revokes-token" with token "playerToken" and save response as "response"
    Then Assert field "solved" equals "true" in response "response"
    And Assert field "points_awarded" equals "20" in response "response"

  @Run @Flow @allure.label.story:End_to_End_Flow
  Scenario: Solve login-rotates-token — log in as the sandbox
    Given a user with token "playerToken"
    When Start challenge "login-rotates-token" with token "playerToken" and save response as "startRes"
    And Extract the sandbox from "startRes"
    And Login with "sandboxEmail" and "sandboxPassword" and save response as "loginRes"
    Then Get and check status code 200 from "loginRes"
    When Verify challenge "login-rotates-token" with token "playerToken" and save response as "response"
    Then Assert field "solved" equals "true" in response "response"
    And Assert field "points_awarded" equals "20" in response "response"

  @Run @Flow @allure.label.story:End_to_End_Flow
  Scenario: Solve patch-first-name after two hints — hints are recorded but do not cost points
    Given a user with token "playerToken"
    When Start challenge "patch-first-name" with token "playerToken" and save response as "startRes"
    And Extract the sandbox from "startRes"
    And Reveal hint 1 of challenge "patch-first-name" with token "playerToken" and save response as "hint1"
    And Reveal hint 2 of challenge "patch-first-name" with token "playerToken" and save response as "hint2"
    And Patch user "sandboxId" with raw body "{\"profile\":{\"first_name\":\"Playwright\",\"last_name\":\"User\"}}" token "sandboxToken" and save response as "patchRes"
    Then Get and check status code 200 from "patchRes"
    When Verify challenge "patch-first-name" with token "playerToken" and save response as "response"
    Then Assert field "solved" equals "true" in response "response"
    And Assert field "points_awarded" equals "10" in response "response"
    When Get challenge progress with token "playerToken" and save response as "progressRes"
    Then Assert field "solved.0.hints_used" equals "2" in response "progressRes"
    And Assert field "total_points" equals "10" in response "progressRes"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: The locale hint is wrong — PATCH with only first_name returns 400 (profile is validated whole)
    Given a user with token "playerToken"
    When Start challenge "patch-first-name" with token "playerToken" and save response as "startRes"
    And Extract the sandbox from "startRes"
    And Patch user "sandboxId" with raw body "{\"profile\":{\"first_name\":\"Playwright\"}}" token "sandboxToken" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  @Run @Flow @allure.label.story:End_to_End_Flow
  Scenario: A missing sandbox can be reset into a new attempt
    Given a user with token "playerToken"
    When Start challenge "patch-first-name" with token "playerToken" and save response as "startRes"
    And Extract "attempt_id" from "startRes" and save as "firstAttempt"
    And Extract the sandbox from "startRes"
    And Delete user "sandboxId" with token "sandboxToken" and save response as "deleteRes"
    And Start challenge "patch-first-name" with token "playerToken" and save response as "missingRes"
    Then Get and check status code 200 from "missingRes"
    And Assert field "target_missing" equals "true" in response "missingRes"
    And Assert field "can_reset" equals "true" in response "missingRes"
    When Start challenge "patch-first-name" with query "reset=true" and token "playerToken" and save response as "resetRes"
    Then Get and check status code 201 from "resetRes"
    And Assert field "attempt_id" is not null in response "resetRes"
    And Extract "attempt_id" from "resetRes" and save as "secondAttempt"
    And Assert "secondAttempt" matches regex "^[0-9a-f]{24}$"
