@allure.label.epic:Authentication @allure.label.suite:User_Management @allure.label.subSuite:Token_Security
Feature: Token Security

  # Guards against authentication-bypass and cross-account (IDOR) defects on the
  # mutating user endpoints (PUT / PATCH / DELETE / logout). Every scenario asserts
  # BOTH the status code AND the error code so a silent 200/204 would be caught.
  #
  # NOTE ON THE "empty Bearer" report: an "Authorization: Bearer " header (empty
  # token, trailing space) was suspected of bypassing auth. Verified against
  # https://www.play-qa.com — the server correctly REJECTS it with
  #   HTTP 401 { error.code: "INVALID_TOKEN_FORMAT" }
  # The scenarios below lock in that behavior as green regression guards.
  #
  # Wire-level note: axios trims surrounding whitespace from header values, and
  # RFC 7230 servers strip optional whitespace anyway, so "Bearer " reaches the
  # middleware as "Bearer" — exactly what a real client sending "Bearer " produces.

  # ─────────────────── EMPTY BEARER TOKEN ───────────────────

  @Run @Negative @allure.label.severity:critical @allure.label.story:Negative_Scenario
  Scenario: PATCH with empty Bearer token is rejected 401 INVALID_TOKEN_FORMAT
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    When Patch user "userId" with raw auth header "Bearer " and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_TOKEN_FORMAT" in response "response"

  @Run @Negative @allure.label.severity:critical @allure.label.story:Negative_Scenario
  Scenario: PUT with empty Bearer token is rejected 401 INVALID_TOKEN_FORMAT
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    When Update user "userId" with raw auth header "Bearer " and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_TOKEN_FORMAT" in response "response"

  @Run @Negative @allure.label.severity:critical @allure.label.story:Negative_Scenario
  Scenario: DELETE with empty Bearer token is rejected 401 INVALID_TOKEN_FORMAT
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    When Delete user "userId" with raw auth header "Bearer " and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_TOKEN_FORMAT" in response "response"

  @Run @Negative @allure.label.severity:critical @allure.label.story:Negative_Scenario
  Scenario: Logout with empty Bearer token is rejected 401 INVALID_TOKEN_FORMAT
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    When Logout user "userId" with raw auth header "Bearer " and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_TOKEN_FORMAT" in response "response"

  # ─────────────────── IDOR: logged-out attacker targets ANOTHER account ───────────────────

  @Run @Negative @allure.label.severity:critical @allure.label.story:Negative_Scenario
  Scenario: Logged-out user with empty Bearer token cannot DELETE another account
    Given Create minimal user and save response as "victimRes"
    And Extract "id" from "victimRes" and save as "victimId"
    And Create minimal user and save response as "attackerRes"
    And Extract "id" from "attackerRes" and save as "attackerId"
    And Extract "access_token" from "attackerRes" and save as "attackerToken"
    When Logout user "attackerId" with token "attackerToken" and save response as "logoutRes"
    Then Get and check status code 200 from "logoutRes"
    When Delete user "victimId" with raw auth header "Bearer " and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_TOKEN_FORMAT" in response "response"

  @Run @Negative @allure.label.severity:critical @allure.label.story:Negative_Scenario
  Scenario: Logged-out user with empty Bearer token cannot PATCH another account
    Given Create minimal user and save response as "victimRes"
    And Extract "id" from "victimRes" and save as "victimId"
    And Create minimal user and save response as "attackerRes"
    And Extract "id" from "attackerRes" and save as "attackerId"
    And Extract "access_token" from "attackerRes" and save as "attackerToken"
    When Logout user "attackerId" with token "attackerToken" and save response as "logoutRes"
    Then Get and check status code 200 from "logoutRes"
    When Patch user "victimId" with raw auth header "Bearer " and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_TOKEN_FORMAT" in response "response"

  # ─────────────────── MALFORMED AUTHORIZATION HEADERS ───────────────────

  @Run @Negative @allure.label.severity:critical @allure.label.story:Negative_Scenario
  Scenario Outline: PATCH with malformed Authorization header <label> is rejected 401 <code>
    Given Create minimal user and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    When Patch user "userId" with raw auth header "<header>" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "<code>" in response "response"
    Examples:
      | label                 | header               | code                 |
      | garbage token         | Bearer notarealtoken | INVALID_TOKEN        |
      | missing Bearer prefix | deadbeefdeadbeef     | INVALID_TOKEN_FORMAT |
      | wrong scheme Basic    | Basic dXNlcjpwYXNz   | INVALID_TOKEN_FORMAT |
      | Bearer only no space  | Bearer               | INVALID_TOKEN_FORMAT |
      | numeric junk          | Bearer 000000000000  | INVALID_TOKEN        |

  # ─────────────────── CROSS-ACCOUNT WITH A VALID TOKEN ───────────────────

  @Run @Negative @allure.label.severity:critical @allure.label.story:Negative_Scenario
  Scenario: Valid token of user B cannot logout user A
    Given Create minimal user and save response as "userARes"
    And Extract "id" from "userARes" and save as "userAId"
    And Create minimal user and save response as "userBRes"
    And Extract "access_token" from "userBRes" and save as "userBToken"
    When Logout user "userAId" with token "userBToken" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_TOKEN" in response "response"
