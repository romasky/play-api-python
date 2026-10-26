@allure.label.epic:System @allure.label.suite:Recaptcha @allure.label.subSuite:Verify_Recaptcha
Feature: reCAPTCHA verification (POST /verify-recaptcha)

  # Non-standard envelope {success, error: <string>} — no error.code, so these assert the status and the
  # message (the convention's documented exception, like GET /auth/basic). API_REFERENCE said "Token is
  # required"; live every 400 says "Invalid request body". A bogus token round-trips to Google: 200, success false.

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: reCAPTCHA with <label> returns 400 "Invalid request body"
    When Verify reCAPTCHA with raw body "<body>" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert field "success" equals "false" in response "response"
    And Assert field "error" equals "Invalid request body" in response "response"
    Examples:
      | label             | body             |
      | no token          | {}               |
      | an empty token    | {\"token\":\"\"} |
      | a numeric token   | {\"token\":123}  |
      | a non-JSON body   | {\"token\":      |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: A bogus token is verified by Google and rejected (200, success false)
    When Verify reCAPTCHA with raw body "{\"token\":\"test-recaptcha-token\"}" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "success" equals "false" in response "response"
    And Assert field "error_codes.0" equals "invalid-input-response" in response "response"
