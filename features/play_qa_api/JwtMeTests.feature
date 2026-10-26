@allure.label.epic:Authentication @allure.label.suite:Authentication @allure.label.subSuite:JWT_Me
Feature: JWT Me (GET /jwt/me)

  # Check order: header → length (8 KiB) → format → signature → expiry → claims → token type.
  # Forged tokens are derived from a genuine one (wrong secret, tampered payload, alg none/HS512) — the server
  # secret is unknown, so INVALID_TOKEN (genuine signature, bad claims) is not reachable from outside.

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: JWT me with an access token returns the caller's claims
    Given a shared JWT session
    When Get JWT me with token "jwtAccess" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "success" equals "true" in response "response"
    And Assert field "sub" equals "jwtUserId" in response "response"
    And Assert field "email" equals "jwtEmail" in response "response"
    And Assert field "claims.type" equals "access" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: JWT me without Authorization header returns 401 MISSING_TOKEN
    When Get JWT me with no auth token and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "MISSING_TOKEN" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: JWT me with malformed header "<label>" returns 401 INVALID_TOKEN_FORMAT
    Given a shared JWT session
    When Get JWT me with raw auth header "<header>" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_TOKEN_FORMAT" in response "response"
    Examples:
      | label        | header       |
      | bare Bearer  | Bearer       |
      | Basic scheme | Basic abc    |
      | no prefix    | ${jwtAccess} |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: JWT me with a non-JWT value (<kind>) returns 401 INVALID_TOKEN_FORMAT
    Given a shared JWT session
    And Craft "<kind>" JWT from "jwtAccess" and save as "badToken"
    When Get JWT me with token "badToken" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_TOKEN_FORMAT" in response "response"
    Examples:
      | kind             |
      | opaque           |
      | one segment      |
      | two segments     |
      | four segments    |
      | garbage          |
      | padded           |
      | bad base64       |
      | non-JSON payload |
      | oversized        |

  @Run @Negative @allure.label.severity:critical @allure.label.story:Negative_Scenario
  Scenario Outline: JWT me with a forged token (<kind>) returns 401 INVALID_SIGNATURE
    Given a shared JWT session
    And Craft "<kind>" JWT from "jwtAccess" and save as "forged"
    When Get JWT me with token "forged" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_SIGNATURE" in response "response"
    Examples:
      | kind             |
      | wrong secret     |
      | tampered payload |
      | alg none         |
      | alg HS512        |
      | forged expired   |

  @Run @Negative @allure.label.severity:critical @allure.label.story:Negative_Scenario
  Scenario: JWT me with an expired genuine token returns 401 TOKEN_EXPIRED
    Given a shared JWT session
    When Get JWT me with token "jwtExpiredAccess" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "TOKEN_EXPIRED" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: JWT me with a refresh token returns 401 WRONG_TOKEN_TYPE
    Given a shared JWT session
    When Get JWT me with token "jwtRefresh" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "WRONG_TOKEN_TYPE" in response "response"
