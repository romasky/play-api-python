@allure.label.epic:Administration @allure.label.suite:Administration @allure.label.subSuite:Admin_Endpoints
Feature: Admin endpoints (/admin/stats, /admin/users, role, delete)

  # Auth order on every route: MISSING_TOKEN / INVALID_TOKEN_FORMAT / INVALID_TOKEN (401) → ADMIN_REQUIRED (403)
  # → scope: an admin may mutate ONLY its own account (403 FORBIDDEN for any other id — existing, missing or
  # malformed — so the documented 404 is unreachable and ids cannot be probed) → body validation (400).
  # Self-demote and self-delete are destructive: each such scenario creates its own admin.

  # ─────────────────── AUTH MATRIX ───────────────────

  @Run @Negative @allure.label.severity:critical @allure.label.story:Negative_Scenario
  Scenario Outline: Admin <route> without a token returns 401 MISSING_TOKEN
    When Send admin "<route>" request with no auth token and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "MISSING_TOKEN" in response "response"
    Examples:
      | route       |
      | stats       |
      | users       |
      | set role    |
      | delete user |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Admin <route> with malformed header "<header>" returns 401 INVALID_TOKEN_FORMAT
    When Send admin "<route>" request with raw auth header "<header>" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_TOKEN_FORMAT" in response "response"
    Examples:
      | route       | header    |
      | stats       | Bearer    |
      | users       | Basic abc |
      | set role    | Bearer    |
      | delete user | Basic abc |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Admin <route> with an unknown token returns 401 INVALID_TOKEN
    When Send admin "<route>" request with raw auth header "Bearer usr_0000000000_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "INVALID_TOKEN" in response "response"
    Examples:
      | route       |
      | stats       |
      | users       |
      | set role    |
      | delete user |

  @Run @Negative @allure.label.severity:critical @allure.label.story:Negative_Scenario
  Scenario Outline: Admin <route> with a valid user token returns 403 ADMIN_REQUIRED
    Given a user with token "userToken"
    When Send admin "<route>" request with token "userToken" and save response as "response"
    Then Get and check status code 403 from "response"
    And Assert error code is "ADMIN_REQUIRED" in response "response"
    Examples:
      | route       |
      | stats       |
      | users       |
      | set role    |
      | delete user |

  # ─────────────────── GET /admin/stats ───────────────────

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: Admin stats are consistent and count the caller as an admin
    Given an admin with token "adminToken"
    When Get admin stats with token "adminToken" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert admin stats are consistent in "response"
    And Assert response header "cache-control" contains "no-store" in "response"

  # ─────────────────── GET /admin/users ───────────────────

  @Run @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: Admin users rows carry has_active_token and never access_token or last_login_ip
    Given an admin with token "adminToken"
    When Get admin users with query "limit=20" and token "adminToken" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert every item of "users" has field "has_active_token" in response "response"
    And Assert every item of "users" has no field "access_token" in response "response"
    And Assert every item of "users" has no field "metadata.last_login_ip" in response "response"
    And Assert response header "X-Total-Count" is absent in "response"
    And Assert response header "Link" is absent in "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Admin users has_active_token flips to false after the user logs out
    Given Generate unique country and save as "country"
    And Create user in country "country" and save response as "userRes"
    And Extract "id" from "userRes" and save as "userId"
    And Extract "access_token" from "userRes" and save as "userToken"
    And an admin with token "adminToken"
    When Get admin users with query "filter=address.country:${country}" and token "adminToken" and save response as "beforeRes"
    Then Assert field "users.0.has_active_token" equals "true" in response "beforeRes"
    When Logout user "userId" with token "userToken" and save response as "logoutRes"
    Then Get and check status code 200 from "logoutRes"
    When Get admin users with query "filter=address.country:${country}" and token "adminToken" and save response as "afterRes"
    Then Assert field "total" equals "1" in response "afterRes"
    And Assert field "users.0.has_active_token" equals "false" in response "afterRes"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: Admin users honours <label>
    Given an admin with token "adminToken"
    When Get admin users with query "<query>" and token "adminToken" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "per_page" equals "<per_page>" in response "response"
    Examples:
      | label          | query             | per_page |
      | limit          | limit=3           | 3        |
      | legacy per_page | per_page=4       | 4        |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Admin users filter role:admin finds the caller's own row
    Given Create admin user and save response as "adminRes"
    And Extract "access_token" from "adminRes" and save as "adminToken"
    And Extract "username" from "adminRes" and save as "adminUsername"
    When Get admin users with query "filter=role:admin&search=${adminUsername}" and token "adminToken" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "total" equals "1" in response "response"
    And Assert field "users.0.metadata.role" equals "admin" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Admin users with <query> returns 400 <code> (same validation as /users/list)
    Given an admin with token "adminToken"
    When Get admin users with query "<query>" and token "adminToken" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "<code>" in response "response"
    Examples:
      | query                              | code                   |
      | page=0                             | INVALID_PAGINATION     |
      | sort=bogus                         | INVALID_SORT_FIELD     |
      | sort=username:up                   | INVALID_SORT_DIR       |
      | filter=role:root                   | INVALID_FILTER_VALUE   |
      | filter=role:user&filter=role:admin | DUPLICATE_FILTER_FIELD |
      | search=                            | INVALID_SEARCH         |

  # ─────────────────── PATCH /admin/users/{id}/role ───────────────────

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Setting the own role to admin is an idempotent no-op
    Given an admin with id "adminId" and token "adminToken"
    When Set role "admin" for user "adminId" with token "adminToken" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert user response has all core fields in "response"
    And Assert field "metadata.role" equals "admin" in response "response"

  @Run @Negative @allure.label.severity:critical @allure.label.story:Negative_Scenario
  Scenario: Setting the role of another user returns 403 FORBIDDEN
    Given Create minimal user and save response as "userRes"
    And Extract "id" from "userRes" and save as "userId"
    And an admin with token "adminToken"
    When Set role "admin" for user "userId" with token "adminToken" and save response as "response"
    Then Get and check status code 403 from "response"
    And Assert error code is "FORBIDDEN" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Setting the role of a <label> id returns 403 FORBIDDEN, never 404
    Given an admin with token "adminToken"
    When Set role "user" for user "<id>" with token "adminToken" and save response as "response"
    Then Get and check status code 403 from "response"
    And Assert error code is "FORBIDDEN" in response "response"
    Examples:
      | label        | id                       |
      | non-existent | 000000000000000000000000 |
      | malformed    | xyz                      |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Setting the own role to <body> returns 400 VALIDATION_ERROR
    Given an admin with id "adminId" and token "adminToken"
    When Set role for user "adminId" with raw body "<body>" token "adminToken" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"
    Examples:
      | body                     |
      | {\"role\":\"moderator\"} |
      | {\"role\":\"Admin\"}     |
      | {}                       |
      | {\"role\":\"\"}          |
      | {\"role\":1}             |

  @Run @Flow @allure.label.severity:critical @allure.label.story:End_to_End_Flow
  Scenario: Self-demotion is irreversible — the same token loses admin access
    Given an admin with id "adminId" and token "adminToken"
    When Set role "user" for user "adminId" with token "adminToken" and save response as "demoteRes"
    Then Get and check status code 200 from "demoteRes"
    And Assert field "metadata.role" equals "user" in response "demoteRes"
    When Get admin stats with token "adminToken" and save response as "statsRes"
    Then Get and check status code 403 from "statsRes"
    And Assert error code is "ADMIN_REQUIRED" in response "statsRes"
    When Set role "admin" for user "adminId" with token "adminToken" and save response as "promoteRes"
    Then Get and check status code 403 from "promoteRes"
    And Assert error code is "ADMIN_REQUIRED" in response "promoteRes"

  # ─────────────────── DELETE /admin/users/{id} ───────────────────

  @Run @Negative @allure.label.severity:critical @allure.label.story:Negative_Scenario
  Scenario Outline: Admin deleting a <label> account returns 403 FORBIDDEN
    Given Create minimal user and save response as "userRes"
    And Extract "id" from "userRes" and save as "otherUserId"
    And an admin with token "adminToken"
    When Admin delete user "<id>" with token "adminToken" and save response as "response"
    Then Get and check status code 403 from "response"
    And Assert error code is "FORBIDDEN" in response "response"
    Examples:
      | label        | id                       |
      | foreign      | otherUserId              |
      | non-existent | 000000000000000000000000 |
      | malformed    | xyz                      |

  @Run @Flow @allure.label.severity:critical @allure.label.story:End_to_End_Flow
  Scenario: Admin deletes its own account — 204, then its token and the account are gone
    Given an admin with id "adminId" and token "adminToken"
    When Admin delete user "adminId" with token "adminToken" and save response as "deleteRes"
    Then Get and check status code 204 from "deleteRes"
    And Assert response body is empty in "deleteRes"
    When Get admin stats with token "adminToken" and save response as "statsRes"
    Then Get and check status code 401 from "statsRes"
    And Assert error code is "INVALID_TOKEN" in response "statsRes"
    When Send GET user request for "adminId" and save response as "getRes"
    Then Get and check status code 404 from "getRes"
    And Assert error code is "USER_NOT_FOUND" in response "getRes"

  @Run @Flow @allure.label.story:End_to_End_Flow
  Scenario: Admin re-login keeps the role — the old token is revoked, the new one works
    Given an admin with token "oldToken"
    When Login with "generatedEmail" and "generatedPassword" and save response as "loginRes"
    Then Get and check status code 200 from "loginRes"
    And Extract "access_token" from "loginRes" and save as "newToken"
    When Get admin stats with token "oldToken" and save response as "oldRes"
    Then Get and check status code 401 from "oldRes"
    And Assert error code is "INVALID_TOKEN" in response "oldRes"
    When Get admin stats with token "newToken" and save response as "newRes"
    Then Get and check status code 200 from "newRes"
