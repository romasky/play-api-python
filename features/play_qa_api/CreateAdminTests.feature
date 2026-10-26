@allure.label.epic:Administration @allure.label.suite:Administration @allure.label.subSuite:Create_Admin
Feature: Create Admin (POST /users/create-admin)

  # The seed code is published in the UI on purpose (every student gets their own admin); what keeps it safe is the
  # data boundary — admin mutations are scoped to the caller's own account (see AdminTests).
  # Check order: body validation (400) → seed code (403) → uniqueness (409).

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: Create admin with the published seed code returns 201 with role admin
    When Create admin user and save response as "response"
    Then Get and check status code 201 from "response"
    And Assert user response has all core fields in "response"
    And Assert field "metadata.role" equals "admin" in response "response"
    And Assert field "access_token" is not null in response "response"

  @Run @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: Public create ignores role and metadata.role — no privilege escalation
    Given Generate email and save as "email"
    And Generate username and save as "username"
    When Create user with raw body "{\"email\":\"${email}\",\"username\":\"${username}\",\"password\":\"Passw0rd!x\",\"profile\":{\"first_name\":\"Eve\",\"last_name\":\"Escalate\"},\"role\":\"admin\",\"metadata\":{\"role\":\"admin\"}}" and save response as "response"
    Then Get and check status code 201 from "response"
    And Assert field "metadata.role" equals "user" in response "response"

  @Run @Negative @allure.label.severity:critical @allure.label.story:Negative_Scenario
  Scenario Outline: Wrong seed code "<seed>" returns 403 INVALID_SEED_CODE
    When Create admin with seed code "<seed>" and save response as "response"
    Then Get and check status code 403 from "response"
    And Assert error code is "INVALID_SEED_CODE" in response "response"
    Examples:
      | seed          |
      | nope          |
      | PLAY-QA-ADMIN |

  # Gherkin trims table cells, so the whitespace case cannot be an Examples row
  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Seed code with a leading space is not trimmed and returns 403 INVALID_SEED_CODE
    When Create admin with seed code " play-qa-admin" and save response as "response"
    Then Get and check status code 403 from "response"
    And Assert error code is "INVALID_SEED_CODE" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Empty seed code gets the same answer as a wrong one (not an oracle)
    When Create admin with seed code "" and save response as "response"
    Then Get and check status code 403 from "response"
    And Assert error code is "INVALID_SEED_CODE" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Absent seed code gets the same answer as a wrong one (not an oracle)
    When Create admin without seed code and save response as "response"
    Then Get and check status code 403 from "response"
    And Assert error code is "INVALID_SEED_CODE" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Seed code longer than 128 characters returns 400 VALIDATION_ERROR
    Given Generate string of length 129 and save as "longSeed"
    When Create admin with seed code "longSeed" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Body validation runs before the seed check — missing email with a wrong seed returns 400
    When Create admin with raw body "{\"username\":\"nobody1\",\"password\":\"Passw0rd!x\",\"profile\":{\"first_name\":\"No\",\"last_name\":\"Body\"},\"seed_code\":\"nope\"}" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Seed code of the wrong JSON type returns 400 VALIDATION_ERROR
    Given Generate email and save as "email"
    And Generate username and save as "username"
    When Create admin with raw body "{\"email\":\"${email}\",\"username\":\"${username}\",\"password\":\"Passw0rd!x\",\"profile\":{\"first_name\":\"No\",\"last_name\":\"Body\"},\"seed_code\":123}" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Duplicate email with the valid seed code returns 409 DUPLICATE_USER
    Given Create minimal user and save response as "existingRes"
    When Create admin with email "generatedEmail" and the published seed code and save response as "response"
    Then Get and check status code 409 from "response"
    And Assert error code is "DUPLICATE_USER" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: The seed is checked before uniqueness — duplicate email with a wrong seed returns 403
    Given Create minimal user and save response as "existingRes"
    When Create admin with email "generatedEmail" and seed code "nope" and save response as "response"
    Then Get and check status code 403 from "response"
    And Assert error code is "INVALID_SEED_CODE" in response "response"
