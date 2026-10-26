@allure.label.epic:Authentication @allure.label.suite:Authentication @allure.label.subSuite:Store_Login
Feature: Store Login (POST /store/login, SauceDemo personas)

  # Every persona shares the password secret_sauce; credentials are case- and whitespace-sensitive.
  # The lock is checked only AFTER the password, so a wrong password never reveals a locked account.

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario Outline: Store login as <persona> returns 200 with its behaviour flags
    When Store login as "<persona>" with password "secret_sauce" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "success" equals "true" in response "response"
    And Assert field "persona" equals "<persona>" in response "response"
    And Assert field "message" equals "Welcome, <persona>" in response "response"
    And Assert field "session" contains "store_<persona>_" in response "response"
    And Assert field "behavior.visual_bugs" equals "<visual_bugs>" in response "response"
    And Assert field "behavior.flaky_add_to_cart" equals "<flaky_add_to_cart>" in response "response"
    And Assert response header "cache-control" contains "no-store" in "response"
    Examples:
      | persona       | visual_bugs | flaky_add_to_cart |
      | standard_user | false       | false             |
      | problem_user  | true        | false             |
      | flaky_user    | false       | true              |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: performance_glitch_user logs in after a real server-side delay
    When Store login as "performance_glitch_user" with password "secret_sauce" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "behavior.login_latency_ms" equals "3000" in response "response"
    And Assert field "behavior.catalog_latency_ms" equals "2500" in response "response"
    And Assert response "response" took at least 3 seconds

  @Run @Negative @allure.label.severity:critical @allure.label.story:Negative_Scenario
  Scenario: locked_out_user returns 403 USER_LOCKED_OUT
    When Store login as "locked_out_user" with password "secret_sauce" and save response as "response"
    Then Get and check status code 403 from "response"
    And Assert error code is "USER_LOCKED_OUT" in response "response"
    And Assert field "error.message" equals "Sorry, this user has been locked out." in response "response"
    And Assert response header "cache-control" contains "no-store" in "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: locked_out_user with a wrong password returns 401 — the lock is not revealed
    When Store login as "locked_out_user" with password "wrong_sauce" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_CREDENTIALS" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Wrong password and unknown user get the same 401 message
    When Store login as "standard_user" with password "wrong_sauce" and save response as "wrongPassword"
    And Store login as "no_such_user" with password "secret_sauce" and save response as "unknownUser"
    Then Get and check status code 401 from "wrongPassword"
    And Assert error code is "INVALID_CREDENTIALS" in response "wrongPassword"
    And Get and check status code 401 from "unknownUser"
    And Assert error code is "INVALID_CREDENTIALS" in response "unknownUser"
    And Extract "error.message" from "wrongPassword" and save as "wrongPasswordMessage"
    And Assert field "error.message" equals "wrongPasswordMessage" in response "unknownUser"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Store credentials are case- and whitespace-sensitive (<label>)
    When Store login as "<username>" with password "<password>" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_CREDENTIALS" in response "response"
    Examples:
      | label              | username      | password     |
      | capitalised user   | Standard_User | secret_sauce |
      | upper-case password | standard_user | SECRET_SAUCE |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: A leading space in the username is not trimmed
    When Store login as " standard_user" with password "secret_sauce" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_CREDENTIALS" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Store login validation — <label> returns 400 VALIDATION_ERROR
    Given Generate string of length 65 and save as "long65"
    And Generate string of length 129 and save as "long129"
    When Store login as "<username>" with password "<password>" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"
    And Assert field "error.details" contains "<detail>" in response "response"
    Examples:
      | label             | username      | password     | detail                       |
      | empty username    |               | secret_sauce | username is required         |
      | empty password    | standard_user |              | password is required         |
      | username too long | long65        | secret_sauce | at most 64 characters        |
      | password too long | standard_user | long129      | at most 128 characters       |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Store login with raw body <label> returns 400 VALIDATION_ERROR
    When Store login with raw body "<body>" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"
    Examples:
      | label             | body                                       |
      | empty object      | {}                                         |
      | missing password  | {\"username\":\"standard_user\"}           |
      | numeric username  | {\"username\":123,\"password\":\"x\"}      |
      | truncated JSON    | {\"username\":\"standard_user\"            |
