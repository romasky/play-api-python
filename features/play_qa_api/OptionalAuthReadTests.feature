@allure.label.epic:User_Lifecycle @allure.label.suite:User_Management @allure.label.subSuite:Optional_Auth_Reads
Feature: Optional authentication on reads (Feature 17)

  # GET /users/get/{id} and GET /users/list stay public — omit the header and you get 200 — but a PRESENT
  # Authorization header that is malformed, unknown or revoked is refused (401) rather than silently ignored.
  # A valid token never yields 403 on a read; only the owner additionally sees metadata.last_login_ip.

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: Get user without Authorization header is still public
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    When Send GET user request for "userId" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "metadata.last_login_ip" is absent in response "response"

  @Run @Negative @allure.label.severity:critical @allure.label.story:Negative_Scenario
  Scenario Outline: Get user with malformed Authorization "<label>" returns 401 INVALID_TOKEN_FORMAT
    Given a user with id "userId" and token "token"
    When Send GET user request for "userId" with raw auth header "<header>" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_TOKEN_FORMAT" in response "response"
    Examples:
      | label             | header             |
      | bare Bearer       | Bearer             |
      | Basic scheme      | Basic abc          |
      | no prefix         | ${token}           |
      | lowercase bearer  | bearer ${token}    |
      | trailing garbage  | Bearer ${token} x  |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Users list with malformed Authorization "<label>" returns 401 INVALID_TOKEN_FORMAT
    When Send GET users list request with query "limit=1" and raw auth header "<header>" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_TOKEN_FORMAT" in response "response"
    Examples:
      | label        | header    |
      | bare Bearer  | Bearer    |
      | Basic scheme | Basic abc |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Get user with an unknown bearer token returns 401 INVALID_TOKEN
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    When Send GET user request for "userId" with raw auth header "Bearer xyz" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_TOKEN" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Users list with an unknown bearer token returns 401 INVALID_TOKEN even with bad params
    When Send GET users list request with query "page=0" and raw auth header "Bearer xyz" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_TOKEN" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: A bad token is checked before the id format
    When Send GET user request for "nothex" with raw auth header "Bearer xyz" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_TOKEN" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Reads with a revoked token (after logout) return 401 INVALID_TOKEN
    Given a user with id "userId" and token "token"
    When Logout user "userId" with token "token" and save response as "logoutRes"
    Then Get and check status code 200 from "logoutRes"
    When Send GET user request for "userId" with token "token" and save response as "getRes"
    Then Get and check status code 401 from "getRes"
    And Assert error code is "INVALID_TOKEN" in response "getRes"
    When Send GET users list request with query "limit=1" and token "token" and save response as "listRes"
    Then Get and check status code 401 from "listRes"
    And Assert error code is "INVALID_TOKEN" in response "listRes"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Get user with the old token after re-login returns 401 INVALID_TOKEN
    Given a user with id "userId" and token "oldToken"
    When Login with "generatedEmail" and "generatedPassword" and save response as "loginRes"
    Then Get and check status code 200 from "loginRes"
    When Send GET user request for "userId" with token "oldToken" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_TOKEN" in response "response"

  @Run @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: Only the owner sees metadata.last_login_ip after a login
    Given Generate unique country and save as "country"
    And Create user in country "country" and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    When Login with "generatedEmail" and "generatedPassword" and save response as "loginRes"
    Then Get and check status code 200 from "loginRes"
    And Extract "access_token" from "loginRes" and save as "token"
    When Send GET user request for "userId" with token "token" and save response as "ownerRes"
    Then Get and check status code 200 from "ownerRes"
    And Assert field "metadata.last_login_ip" is not null in response "ownerRes"
    And Assert field "metadata.login_count" equals "1" in response "ownerRes"
    When Send GET users list request with query "filter=address.country:${country}" and token "token" and save response as "ownerListRes"
    Then Assert field "users.0.metadata.last_login_ip" is not null in response "ownerListRes"
    When Send GET user request for "userId" and save response as "anonRes"
    Then Get and check status code 200 from "anonRes"
    And Assert field "metadata.last_login_ip" is absent in response "anonRes"
    And Assert field "metadata.last_login_at" is not null in response "anonRes"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Another user's valid token reads the user (200, no 403 on reads) without last_login_ip
    Given Create minimal user and save response as "userARes"
    And Extract "id" from "userARes" and save as "userAId"
    When Login with "generatedEmail" and "generatedPassword" and save response as "loginRes"
    Then Get and check status code 200 from "loginRes"
    Given a user with token "userBToken"
    When Send GET user request for "userAId" with token "userBToken" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "metadata.last_login_ip" is absent in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: An admin token is not exempt — admins do not see another user's last_login_ip
    Given Create minimal user and save response as "userARes"
    And Extract "id" from "userARes" and save as "userAId"
    When Login with "generatedEmail" and "generatedPassword" and save response as "loginRes"
    Then Get and check status code 200 from "loginRes"
    Given an admin with token "adminToken"
    When Send GET user request for "userAId" with token "adminToken" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "metadata.last_login_ip" is absent in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: A valid token with a non-existent id returns 404 USER_NOT_FOUND
    Given a user with token "token"
    And Generate fake mongo id and save as "fakeId"
    When Send GET user request for "fakeId" with token "token" and save response as "response"
    Then Get and check status code 404 from "response"
    And Assert error code is "USER_NOT_FOUND" in response "response"
