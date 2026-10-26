@allure.label.epic:Authentication @allure.label.suite:Authentication @allure.label.subSuite:JWT_Login
Feature: JWT Login (POST /jwt/login)

  # A second auth scheme next to the opaque usr_… token: HS256 access (900 s) + refresh (86400 s) pair.
  # /jwt/login has its own 5-per-minute bucket and EVERY call counts (400s too) — paced in play_api.pacing.

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: JWT login returns a Bearer token pair with the default lifetimes
    Given Create minimal user and save response as "createRes"
    When JWT login with "generatedEmail" and "generatedPassword" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "token_type" equals "Bearer" in response "response"
    And Assert field "access_expires_in" equals "900" in response "response"
    And Assert field "refresh_expires_in" equals "86400" in response "response"
    And Assert field "email" equals "generatedEmail" in response "response"
    And Assert response header "cache-control" contains "no-store" in "response"
    And Extract "access_token" from "response" and save as "accessToken"
    And Assert JWT "accessToken" has claim "type" equals "access"
    And Assert JWT "accessToken" has claim "iss" equals "play-qa.com"
    And Assert JWT "accessToken" has claim "email" equals "generatedEmail"
    And Assert JWT "accessToken" lifetime is 900 seconds

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: JWT login with access_ttl_seconds shortens only the access token
    Given Create minimal user and save response as "createRes"
    When JWT login with "generatedEmail" and "generatedPassword" and access ttl "60" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "access_expires_in" equals "60" in response "response"
    And Assert field "refresh_expires_in" equals "86400" in response "response"
    And Extract "refresh_token" from "response" and save as "refreshToken"
    And Assert JWT "refreshToken" has claim "type" equals "refresh"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: JWT login does not rotate the opaque token
    Given a shared JWT session
    When Send GET user request for "jwtUserId" with token "jwtOpaqueToken" and save response as "response"
    Then Get and check status code 200 from "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: A JWT access token is rejected by opaque-token endpoints (the schemes do not mix)
    Given a shared JWT session
    When Send GET user request for "jwtUserId" with token "jwtAccess" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_TOKEN" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: JWT login validation — <label> returns 400 VALIDATION_ERROR
    When JWT login with raw body "<body>" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"
    Examples:
      | label             | body                                                                         |
      | missing email     | {\"password\":\"Passw0rd!x\"}                                                |
      | invalid email     | {\"email\":\"not-an-email\",\"password\":\"Passw0rd!x\"}                     |
      | missing password  | {\"email\":\"a@play-qa.com\"}                                                |
      | ttl zero          | {\"email\":\"a@play-qa.com\",\"password\":\"x\",\"access_ttl_seconds\":0}    |
      | ttl above 900     | {\"email\":\"a@play-qa.com\",\"password\":\"x\",\"access_ttl_seconds\":901}  |
      | ttl as a string   | {\"email\":\"a@play-qa.com\",\"password\":\"x\",\"access_ttl_seconds\":\"60\"} |

  @Run @Negative @allure.label.severity:critical @allure.label.story:Negative_Scenario
  Scenario Outline: JWT login with <label> returns 401 INVALID_CREDENTIALS (same answer for both)
    Given Create minimal user and save response as "createRes"
    When JWT login with "<email>" and "<password>" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_CREDENTIALS" in response "response"
    Examples:
      | label          | email                    | password          |
      | wrong password | generatedEmail           | WrongPassw0rd!    |
      | unknown email  | nobody_xyz@play-qa.com   | generatedPassword |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: JWT login body larger than 16 KiB returns 413 PAYLOAD_TOO_LARGE
    When Send JWT "login" request with an oversized body and save response as "response"
    Then Get and check status code 413 from "response"
    And Assert error code is "PAYLOAD_TOO_LARGE" in response "response"
