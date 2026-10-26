@allure.label.epic:System @allure.label.suite:API_Discovery @allure.label.subSuite:API_Documents
Feature: API documents (OpenAPI 2.0 JSON/YAML, Postman collection/environment)

  # Downloads by default (Content-Disposition: attachment); ?download=false serves the same body inline.
  # The OpenAPI JSON is the spec the suite's docs/openapi.json snapshot is taken from (tools/spec_drift.py).

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario Outline: <name> downloads as <filename>
    When Download the API document "<name>" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert response header "Content-Type" contains "<content_type>" in "response"
    And Assert response header "Content-Disposition" equals "attachment; filename="<filename>"" in "response"
    Examples:
      | name                | content_type     | filename                         |
      | OpenAPI JSON        | application/json | play-qa-openapi.json             |
      | OpenAPI YAML        | application/yaml | play-qa-openapi.yaml             |
      | Postman collection  | application/json | play-qa.postman_collection.json  |
      | Postman environment | application/json | play-qa.postman_environment.json |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: <name> with download=false is served inline
    When Download the API document "<name>" with query "download=false" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert response header "Content-Disposition" is absent in "response"
    Examples:
      | name                |
      | OpenAPI JSON        |
      | Postman environment |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: The OpenAPI document is Swagger 2.0 for /api/v1 and covers the chaos endpoints
    When Download the API document "OpenAPI JSON" and save response as "response"
    Then Assert field "swagger" equals "2.0" in response "response"
    And Assert field "basePath" equals "/api/v1" in response "response"
    And Assert field "info.title" equals "User API" in response "response"
    And Assert field "paths./chaos/echo" is present in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: The Postman collection is v2.1 with bearer auth and the working variables
    When Download the API document "Postman collection" and save response as "response"
    Then Assert field "info.schema" contains "v2.1.0/collection.json" in response "response"
    And Assert field "auth.type" equals "bearer" in response "response"
    And Assert Postman variable "baseUrl" is defined in response "response"
    And Assert Postman variable "webhookIngestToken" is defined in response "response"
    And Assert Postman variable "adminToken" is defined in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: The Postman environment defines only the base URL
    When Download the API document "Postman environment" and save response as "response"
    Then Assert field "name" equals "Play QA API" in response "response"
    And Assert list "values" has 1 items in response "response"
    And Assert field "values.0.key" equals "baseUrl" in response "response"
