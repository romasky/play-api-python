@allure.label.epic:User_Lifecycle @allure.label.suite:User_Management @allure.label.subSuite:Create_User
Feature: Create User

  # ─────────────────── POSITIVE ───────────────────

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: Create user with minimal required fields returns 201
    Given Generate email and save as "email"
    And Generate username and save as "username"
    And Generate password and save as "password"
    And Generate first name and save as "firstName"
    And Generate last name and save as "lastName"
    When Create user with body and save response as "response"
    Then Get and check status code 201 from "response"
    And Assert field "email" equals "email" in response "response"
    And Assert field "username" equals "username" in response "response"
    And Assert field "access_token" is not null in response "response"
    And Assert field "id" is not null in response "response"
    And Assert field "password" is absent in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Create user with all optional fields returns 201
    When Create user with all optional fields and save response as "response"
    Then Get and check status code 201 from "response"
    And Assert field "access_token" is not null in response "response"
    And Assert field "contacts" is present in response "response"
    And Assert field "address" is present in response "response"
    And Assert field "employment.status" equals "employed" in response "response"
    And Assert field "settings.theme" equals "dark" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Created user has correct metadata defaults
    Given Generate email and save as "email"
    And Generate username and save as "username"
    And Generate password and save as "password"
    And Generate first name and save as "firstName"
    And Generate last name and save as "lastName"
    When Create user with body and save response as "response"
    Then Get and check status code 201 from "response"
    And Assert field "metadata.is_active" equals "true" in response "response"
    And Assert field "metadata.is_verified" equals "false" in response "response"
    And Assert field "metadata.login_count" equals "0" in response "response"
    And Assert field "metadata.role" equals "user" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Access token has correct format after create
    Given Generate email and save as "email"
    And Generate username and save as "username"
    And Generate password and save as "password"
    And Generate first name and save as "firstName"
    And Generate last name and save as "lastName"
    When Create user with body and save response as "response"
    Then Get and check status code 201 from "response"
    And Extract "access_token" from "response" and save as "token"
    And Assert "token" matches regex "^usr_\d+_[a-f0-9]{32}$"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: Create user with username at length boundary <length> returns 201
    Given Generate email and save as "email"
    And Generate username of length <length> and save as "username"
    And Generate password and save as "password"
    And Generate first name and save as "firstName"
    And Generate last name and save as "lastName"
    When Create user with body and save response as "response"
    Then Get and check status code 201 from "response"
    And Assert field "username" equals "username" in response "response"
    Examples:
      | length |
      | 3      |
      | 30     |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Create user with empty interests array returns 201
    Given Generate email and save as "email"
    And Generate username and save as "username"
    And Generate password and save as "password"
    And Generate first name and save as "firstName"
    And Generate last name and save as "lastName"
    And Set interests ""
    When Create user with full body and save response as "response"
    Then Get and check status code 201 from "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Create user with multiple interests returns 201
    Given Generate email and save as "email"
    And Generate username and save as "username"
    And Generate password and save as "password"
    And Generate first name and save as "firstName"
    And Generate last name and save as "lastName"
    And Set interests "coding,travel,music"
    When Create user with full body and save response as "response"
    Then Get and check status code 201 from "response"
    And Assert field "profile.interests.2" equals "music" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: Create user with valid gender enum value
    Given Generate email and save as "email"
    And Generate username and save as "username"
    And Generate password and save as "password"
    And Generate first name and save as "firstName"
    And Generate last name and save as "lastName"
    And Save string "<gender>" as "gender"
    When Create user with full body and save response as "response"
    Then Get and check status code 201 from "response"
    Examples:
      | gender            |
      | male              |
      | female            |
      | other             |
      | prefer_not_to_say |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: Create user with valid employment status
    Given Generate email and save as "email"
    And Generate username and save as "username"
    And Generate password and save as "password"
    And Generate first name and save as "firstName"
    And Generate last name and save as "lastName"
    And Set employment status "<status>"
    When Create user with full body and save response as "response"
    Then Get and check status code 201 from "response"
    Examples:
      | status     |
      | employed   |
      | unemployed |
      | student    |
      | retired    |
      | freelancer |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: Create user with valid theme setting
    Given Generate email and save as "email"
    And Generate username and save as "username"
    And Generate password and save as "password"
    And Generate first name and save as "firstName"
    And Generate last name and save as "lastName"
    And Set theme "<theme>"
    When Create user with full body and save response as "response"
    Then Get and check status code 201 from "response"
    Examples:
      | theme  |
      | light  |
      | dark   |
      | system |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Response headers include x-request-id after create
    Given Generate email and save as "email"
    And Generate username and save as "username"
    And Generate password and save as "password"
    And Generate first name and save as "firstName"
    And Generate last name and save as "lastName"
    When Create user with body and save response as "response"
    Then Get and check status code 201 from "response"
    And Assert response header "x-request-id" is present in "response"

  # ─────────────────── NEGATIVE ───────────────────

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Create user without email returns 400
    When Create user with raw body "{\"username\":\"testuser\",\"password\":\"Pass_test123!1\",\"profile\":{\"first_name\":\"John\",\"last_name\":\"Doe\"}}" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Create user with invalid email returns 400
    Given Generate invalid email and save as "email"
    And Generate username and save as "username"
    And Generate password and save as "password"
    And Generate first name and save as "firstName"
    And Generate last name and save as "lastName"
    When Create user with body and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Create user without password returns 400
    When Create user with raw body "{\"email\":\"test@play-qa.com\",\"username\":\"testuser\",\"profile\":{\"first_name\":\"John\",\"last_name\":\"Doe\"}}" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Create user with short password returns 400
    When Create user with raw body "{\"email\":\"test@play-qa.com\",\"username\":\"testuser\",\"password\":\"short\",\"profile\":{\"first_name\":\"John\",\"last_name\":\"Doe\"}}" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Create user without profile returns 400
    When Create user with raw body "{\"email\":\"test@play-qa.com\",\"username\":\"testuser\",\"password\":\"Pass_test123!1\"}" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Create user without first_name returns 400
    When Create user with raw body "{\"email\":\"test@play-qa.com\",\"username\":\"testuser\",\"password\":\"Pass_test123!1\",\"profile\":{\"last_name\":\"Doe\"}}" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Create user with short first_name returns 400
    When Create user with raw body "{\"email\":\"test@play-qa.com\",\"username\":\"testuser\",\"password\":\"Pass_test123!1\",\"profile\":{\"first_name\":\"A\",\"last_name\":\"Doe\"}}" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Create user with short username returns 400
    When Create user with raw body "{\"email\":\"test@play-qa.com\",\"username\":\"ab\",\"password\":\"Pass_test123!1\",\"profile\":{\"first_name\":\"John\",\"last_name\":\"Doe\"}}" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Create user with username longer than 30 chars returns 400
    Given Generate email and save as "email"
    And Generate username of length 31 and save as "username"
    And Generate password and save as "password"
    And Generate first name and save as "firstName"
    And Generate last name and save as "lastName"
    When Create user with body and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Create user with bio longer than 500 chars returns 400
    Given Generate email and save as "email"
    And Generate username and save as "username"
    And Generate password and save as "password"
    And Generate first name and save as "firstName"
    And Generate last name and save as "lastName"
    And Set bio of length 501
    When Create user with full body and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: VALIDATION_ERROR response contains request_id and names the offending field
    Given Generate email and save as "email"
    And Generate username and save as "username"
    And Generate password and save as "password"
    And Generate first name and save as "firstName"
    And Generate last name and save as "lastName"
    And Set bio of length 501
    When Create user with full body and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"
    And Assert response has request_id in "response"
    And Assert field "error.details" contains "bio" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Create user with invalid employment status returns 400
    Given Generate email and save as "email"
    And Generate username and save as "username"
    And Generate password and save as "password"
    And Generate first name and save as "firstName"
    And Generate last name and save as "lastName"
    And Set employment status "king"
    When Create user with full body and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Create user with invalid theme returns 400
    Given Generate email and save as "email"
    And Generate username and save as "username"
    And Generate password and save as "password"
    And Generate first name and save as "firstName"
    And Generate last name and save as "lastName"
    And Set theme "pink"
    When Create user with full body and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Create user with invalid gender value returns 400
    When Create user with raw body "{\"email\":\"test@play-qa.com\",\"username\":\"testuser\",\"password\":\"Pass_test123!1\",\"profile\":{\"first_name\":\"John\",\"last_name\":\"Doe\",\"gender\":\"unknown\"}}" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Create duplicate user returns 409
    Given Generate email and save as "email_g"
    And Generate username and save as "username"
    And Generate password and save as "password"
    And Generate first name and save as "firstName"
    And Generate last name and save as "lastName"
    When Create user with body and save response as "firstResponse"
    Then Get and check status code 201 from "firstResponse"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Create user with duplicate email returns 409
    Given Save context value "email_g" as "email"
    And Generate username and save as "username"
    And Generate password and save as "password"
    And Generate first name and save as "firstName"
    And Generate last name and save as "lastName"
    When Create user with body and save response as "response"
    Then Get and check status code 409 from "response"
    And Assert error code is "DUPLICATE_USER" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Create user with duplicate username returns 409
    Given Generate email and save as "email"
    And Generate username and save as "username"
    And Generate password and save as "password"
    And Generate first name and save as "firstName"
    And Generate last name and save as "lastName"
    When Create user with body and save response as "firstResponse"
    Then Get and check status code 201 from "firstResponse"
    Given Generate email and save as "email"
    When Create user with body and save response as "secondResponse"
    Then Get and check status code 409 from "secondResponse"
    And Assert error code is "DUPLICATE_USER" in response "secondResponse"

  # ─────────────────── FLOW ───────────────────

  @Run @Flow @allure.label.story:End_to_End_Flow
  Scenario: Create user then retrieve by ID
    Given Generate email and save as "email"
    And Generate username and save as "username"
    And Generate password and save as "password"
    And Generate first name and save as "firstName"
    And Generate last name and save as "lastName"
    When Create user with body and save response as "createResponse"
    Then Get and check status code 201 from "createResponse"
    And Extract "id" from "createResponse" and save as "userId"
    When Send GET user request for "userId" and save response as "getResponse"
    Then Get and check status code 200 from "getResponse"
    And Assert field "id" equals "userId" in response "getResponse"
