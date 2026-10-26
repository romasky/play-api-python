@allure.label.epic:Authentication @allure.label.suite:Authentication @allure.label.subSuite:JWT_Refresh
Feature: JWT Refresh (POST /jwt/refresh)

  # The refresh token travels in the BODY (an Authorization header is ignored), is NOT rotated (reusable),
  # and every new access token gets the default 900 s whatever TTL the login asked for.

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: Refresh returns a new access token and no new refresh token
    Given a shared JWT session
    When Refresh JWT with token "jwtRefresh" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "token_type" equals "Bearer" in response "response"
    And Assert field "access_expires_in" equals "900" in response "response"
    And Assert field "refresh_token" is absent in response "response"
    And Extract "access_token" from "response" and save as "newAccess"
    And Assert JWT "newAccess" has claim "type" equals "access"
    And Assert JWT "newAccess" has claim "sub" equals "jwtUserId"

  @Run @Flow @allure.label.story:End_to_End_Flow
  Scenario: The refresh token is reusable and every refreshed access token works on /jwt/me
    Given a shared JWT session
    When Refresh JWT with token "jwtRefresh" and save response as "firstRes"
    Then Get and check status code 200 from "firstRes"
    And Extract "access_token" from "firstRes" and save as "firstAccess"
    When Refresh JWT with token "jwtRefresh" and save response as "secondRes"
    Then Get and check status code 200 from "secondRes"
    And Extract "access_token" from "secondRes" and save as "secondAccess"
    When Get JWT me with token "firstAccess" and save response as "meFirst"
    Then Get and check status code 200 from "meFirst"
    When Get JWT me with token "secondAccess" and save response as "meSecond"
    Then Get and check status code 200 from "meSecond"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Refresh with an access token returns 401 WRONG_TOKEN_TYPE
    Given a shared JWT session
    When Refresh JWT with token "jwtAccess" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "WRONG_TOKEN_TYPE" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Refresh with an expired access token returns 401 TOKEN_EXPIRED (expiry is checked before type)
    Given a shared JWT session
    When Refresh JWT with token "jwtExpiredAccess" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "TOKEN_EXPIRED" in response "response"

  @Run @Negative @allure.label.severity:critical @allure.label.story:Negative_Scenario
  Scenario Outline: Refresh with a forged token (<kind>) returns 401 INVALID_SIGNATURE
    Given a shared JWT session
    And Craft "<kind>" JWT from "jwtRefresh" and save as "forged"
    When Refresh JWT with token "forged" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_SIGNATURE" in response "response"
    Examples:
      | kind             |
      | wrong secret     |
      | tampered payload |
      | alg none         |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Refresh with a malformed token (<kind>) returns 401 INVALID_TOKEN_FORMAT
    Given a shared JWT session
    And Craft "<kind>" JWT from "jwtRefresh" and save as "badToken"
    When Refresh JWT with token "badToken" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_TOKEN_FORMAT" in response "response"
    Examples:
      | kind         |
      | opaque       |
      | garbage      |
      | two segments |
      | padded       |
      | oversized    |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Refresh body validation — <label> returns 400 VALIDATION_ERROR
    When Refresh JWT with raw body "<body>" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"
    Examples:
      | label          | body                     |
      | empty object   | {}                       |
      | empty token    | {\"refresh_token\":\"\"} |
      | number         | {\"refresh_token\":42}   |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: A refresh token sent only in the Authorization header is ignored
    Given a shared JWT session
    When Refresh JWT with token "jwtRefresh" in the Authorization header only and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Refresh body larger than 16 KiB returns 413 PAYLOAD_TOO_LARGE
    When Send JWT "refresh" request with an oversized body and save response as "response"
    Then Get and check status code 413 from "response"
    And Assert error code is "PAYLOAD_TOO_LARGE" in response "response"
