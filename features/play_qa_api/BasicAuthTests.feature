@allure.label.epic:Authentication @allure.label.suite:Authentication @allure.label.subSuite:Basic_Auth
Feature: Basic Auth

  # GET /auth/basic is a QA practice endpoint with hardcoded admin/admin credentials.
  # It does NOT use the standard error envelope: 401 bodies are { error, message }.

  @Run @Smoke @Positive @allure.label.severity:normal @allure.label.story:Positive_Scenario
  Scenario: Basic auth with correct credentials returns 200
    When Send GET basic auth request with credentials "admin:admin" and save as "response"
    Then Get and check status code 200 from "response"
    And Assert field "success" equals "true" in response "response"
    And Assert field "user" equals "admin" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Basic auth without Authorization header returns 401 with WWW-Authenticate
    When Send GET basic auth request with no auth header and save as "response"
    Then Get and check status code 401 from "response"
    And Assert response header "www-authenticate" contains "Basic realm" in "response"
    And Assert field "error" equals "Unauthorized" in response "response"
    And Assert field "message" equals "Basic authentication required" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Basic auth with wrong password returns 401
    When Send GET basic auth request with credentials "admin:wrong" and save as "response"
    Then Get and check status code 401 from "response"
    And Assert field "error" equals "Unauthorized" in response "response"
    And Assert field "message" equals "Invalid username or password" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Basic auth with malformed header <label> returns 401
    When Send GET basic auth request with raw auth header "<header>" and save as "response"
    Then Get and check status code 401 from "response"
    And Assert field "error" equals "Unauthorized" in response "response"
    And Assert field "message" equals "<message>" in response "response"
    Examples:
      | label             | header             | message                       |
      | Bearer scheme     | Bearer sometoken   | Invalid authentication format |
      | bad base64        | Basic !!!notbase64 | Invalid base64 encoding       |
      | no colon in creds | Basic YWRtaW4=     | Invalid credentials format    |
