@allure.label.epic:Authentication @allure.label.suite:Authentication @allure.label.subSuite:JWT_Decode
Feature: JWT Decode (POST /jwt/decode)

  # Public inspector: decodes ANY JWT and reports signature_valid / expired without rejecting it.
  # Nullable keys (signature_valid, expired, expires_at, issued_at) are always present — null, never missing.
  # Format errors here are 400 INVALID_JWT_FORMAT (me/refresh say 401 INVALID_TOKEN_FORMAT).

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: Decode a genuine access token — valid signature, not expired
    Given a shared JWT session
    When Decode JWT "jwtAccess" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "signature_valid" equals "true" in response "response"
    And Assert field "expired" equals "false" in response "response"
    And Assert field "header.alg" equals "HS256" in response "response"
    And Assert field "payload.type" equals "access" in response "response"
    And Assert field "payload.sub" equals "jwtUserId" in response "response"
    And Assert field "expires_at" is not null in response "response"
    And Assert field "issued_at" is not null in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Decode an expired genuine token — valid signature, expired
    Given a shared JWT session
    When Decode JWT "jwtExpiredAccess" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "signature_valid" equals "true" in response "response"
    And Assert field "expired" equals "true" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: Decode a forged token (<kind>) — signature_valid false, expired <expired>
    Given a shared JWT session
    And Craft "<kind>" JWT from "jwtAccess" and save as "forged"
    When Decode JWT "forged" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "signature_valid" equals "false" in response "response"
    And Assert field "expired" equals "<expired>" in response "response"
    Examples:
      | kind             | expired |
      | wrong secret     | false   |
      | tampered payload | false   |
      | alg none         | false   |
      | forged expired   | true    |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: Decode a token whose exp is <label> — expiry keys present and null
    Given a shared JWT session
    And Craft "<kind>" JWT from "jwtAccess" and save as "token"
    When Decode JWT "token" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "expired" is null in response "response"
    And Assert field "expires_at" is null in response "response"
    Examples:
      | label    | kind         |
      | missing  | no exp       |
      | a string | exp string   |
      | absent   | empty object |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Decode a non-JWT value (<kind>) returns 400 INVALID_JWT_FORMAT
    Given a shared JWT session
    And Craft "<kind>" JWT from "jwtAccess" and save as "badToken"
    When Decode JWT "badToken" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "INVALID_JWT_FORMAT" in response "response"
    Examples:
      | kind             |
      | opaque           |
      | one segment      |
      | two segments     |
      | padded           |
      | bad base64       |
      | non-JSON payload |
      | oversized        |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Decode body validation — <label> returns 400 VALIDATION_ERROR
    When Decode JWT with raw body "<body>" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"
    Examples:
      | label        | body             |
      | empty object | {}               |
      | empty token  | {\"token\":\"\"} |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Decode body larger than 16 KiB returns 413 PAYLOAD_TOO_LARGE
    When Send JWT "decode" request with an oversized body and save response as "response"
    Then Get and check status code 413 from "response"
    And Assert error code is "PAYLOAD_TOO_LARGE" in response "response"
