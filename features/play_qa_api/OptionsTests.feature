@allure.label.epic:User_Lifecycle @allure.label.suite:User_Management @allure.label.subSuite:Options
Feature: Options

  @Run @Smoke @Positive @allure.label.severity:normal @allure.label.story:Positive_Scenario
  Scenario: OPTIONS returns 204
    When Send OPTIONS users request and save response as "response"
    Then Get and check status code 204 from "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: OPTIONS response has Allow header
    When Send OPTIONS users request and save response as "response"
    Then Get and check status code 204 from "response"
