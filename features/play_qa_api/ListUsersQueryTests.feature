@allure.label.epic:User_Lifecycle @allure.label.suite:User_Management @allure.label.subSuite:List_Users_Query
Feature: List Users — limit, sort, filter, search, X-Total-Count and Link

  # The users collection is shared with every other client of play-qa.com and changes every few seconds.
  # Exact counts are only asserted inside a filter that isolates our own user (a unique address.country);
  # global invariants (total == X-Total-Count, total_pages == ceil(total / per_page)) are checked within ONE response.

  # ─────────────────── PAGINATION: limit vs legacy per_page ───────────────────

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: List users with limit returns that many users and total metadata
    When Send GET users list request with query "limit=3" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "per_page" equals "3" in response "response"
    And Assert list "users" has 3 items in response "response"
    And Assert header "X-Total-Count" equals field "total" in response "response"
    And Assert users list total_pages matches total and per_page in "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: List users page size <label>
    When Send GET users list request with query "<query>" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "per_page" equals "<per_page>" in response "response"
    And Assert list "users" has at most <per_page> items in response "response"
    Examples:
      | label                          | query             | per_page |
      | limit above 100 is clamped     | limit=101         | 100      |
      | limit wins over per_page       | limit=5&per_page=2 | 5       |
      | legacy per_page still works    | per_page=2        | 2        |
      | default page size is 10        | page=1            | 10       |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Page beyond the last one returns 200 with an empty users array
    When Send GET users list request with query "page=1000000&limit=1" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "page" equals "1000000" in response "response"
    And Assert list "users" has 0 items in response "response"

  # ─────────────────── LINK HEADER (RFC 8288) ───────────────────

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Link header on page 2 has first, prev, next and last and keeps the sort
    When Send GET users list request with query "page=2&limit=2&sort=username:asc" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert Link header relation "first" contains "page=1" in "response"
    And Assert Link header relation "prev" contains "page=1" in "response"
    And Assert Link header relation "next" contains "page=3" in "response"
    And Assert Link header relation "last" contains "limit=2" in "response"
    And Assert Link header relation "next" contains "sort=username%3Aasc" in "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Link header on page 1 has no prev and canonicalises per_page to limit
    When Send GET users list request with query "page=1&per_page=2" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert Link header has no relation "prev" in "response"
    And Assert Link header relation "next" contains "limit=2" in "response"
    And Assert Link header relation "next" does not contain "per_page" in "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: A 400 response carries no X-Total-Count or Link header
    When Send GET users list request with query "sort=bogus" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "INVALID_SORT_FIELD" in response "response"
    And Assert response header "X-Total-Count" is absent in "response"
    And Assert response header "Link" is absent in "response"

  # ─────────────────── SORT ───────────────────

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: Sort by username <direction> returns usernames in <direction>ending byte order
    When Send GET users list request with query "limit=20&sort=username:<direction>" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert list "users" is sorted by "username" "<direction>" in response "response"
    Examples:
      | direction |
      | asc       |
      | desc      |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Default sort is created_at descending
    When Send GET users list request with query "limit=20" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert list "users" is sorted by "metadata.created_at" "desc" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: Every sortable field is accepted: <sort>
    When Send GET users list request with query "limit=1&sort=<sort>" and save response as "response"
    Then Get and check status code 200 from "response"
    Examples:
      | sort                |
      | created_at          |
      | updated_at:asc      |
      | login_count:desc    |
      | last_login_at:asc   |
      | username            |
      | email:desc          |

  # ─────────────────── FILTER ───────────────────

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: Filter by a unique country returns exactly the created user
    Given Generate unique country and save as "country"
    And Create user in country "country" and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    When Send GET users list request with query "filter=address.country:${country}" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "total" equals "1" in response "response"
    And Assert response header "X-Total-Count" equals "1" in "response"
    And Assert field "users.0.id" equals "userId" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Country filter is an exact, case-sensitive match
    Given Generate unique country and save as "country"
    And Create user in country "country" and save response as "createRes"
    And Save upper-cased "country" as "countryUpper"
    When Send GET users list request with query "filter=address.country:${countryUpper}" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "total" equals "0" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: Filters on different fields are ANDed: <label>
    Given Generate unique country and save as "country"
    And Create user in country "country" and save response as "createRes"
    When Send GET users list request with query "filter=address.country:${country}&filter=<second>" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "total" equals "<total>" in response "response"
    Examples:
      | label                | second              | total |
      | country + role user  | role:user           | 1     |
      | country + role admin | role:admin          | 0     |
      | country + is_active  | is_active:true      | 1     |
      | country + premium    | is_premium:true     | 0     |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Theme filter follows a PATCH of settings.theme
    Given Generate unique country and save as "country"
    And Create user in country "country" and save response as "createRes"
    And Extract "id" from "createRes" and save as "userId"
    And Extract "access_token" from "createRes" and save as "token"
    When Patch user "userId" with raw body "{\"settings\":{\"theme\":\"dark\"}}" token "token" and save response as "patchRes"
    Then Get and check status code 200 from "patchRes"
    When Send GET users list request with query "filter=address.country:${country}&filter=settings.theme:dark" and save response as "darkRes"
    Then Assert field "total" equals "1" in response "darkRes"
    When Send GET users list request with query "filter=address.country:${country}&filter=settings.theme:light" and save response as "lightRes"
    Then Assert field "total" equals "0" in response "lightRes"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Filter role:user returns only users with role user
    When Send GET users list request with query "limit=20&filter=role:user" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert every item of "users" has field "metadata.role" equals "user" in response "response"

  # ─────────────────── SEARCH ───────────────────

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Search is a case-insensitive substring match on username
    Given Generate unique country and save as "country"
    And Create user in country "country" and save response as "createRes"
    And Extract "username" from "createRes" and save as "username"
    And Save upper-cased "username" as "usernameUpper"
    When Send GET users list request with query "search=${usernameUpper}" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "total" equals "1" in response "response"
    And Assert field "users.0.username" equals "username" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Search combined with a filter is ANDed and surrounding spaces are trimmed
    Given Generate unique country and save as "country"
    And Create user in country "country" and save response as "createRes"
    And Extract "username" from "createRes" and save as "username"
    When Send GET users list request with query "search=%20${username}%20&filter=address.country:${country}" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "total" equals "1" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Regex metacharacters in search are literal
    When Send GET users list request with query "search=.*" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "total" equals "0" in response "response"

  # ─────────────────── VALIDATION (first error wins: page → limit → per_page → sort → filter → search) ───────────────────

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Invalid pagination <query> returns 400 INVALID_PAGINATION
    When Send GET users list request with query "<query>" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "INVALID_PAGINATION" in response "response"
    Examples:
      | query               |
      | page=0              |
      | page=               |
      | page=1000001        |
      | page=abc            |
      | limit=0             |
      | limit=              |
      | limit=-1            |
      | limit=2.5           |
      | per_page=           |
      | limit=5&per_page=abc |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Invalid sort field <query> returns 400 INVALID_SORT_FIELD
    When Send GET users list request with query "<query>" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "INVALID_SORT_FIELD" in response "response"
    Examples:
      | query                    |
      | sort=                    |
      | sort=bogus               |
      | sort=password            |
      | sort=Username            |
      | sort=metadata.created_at |
      | sort=:asc                |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Invalid sort direction <query> returns 400 INVALID_SORT_DIR
    When Send GET users list request with query "<query>" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "INVALID_SORT_DIR" in response "response"
    Examples:
      | query               |
      | sort=username:      |
      | sort=username:up    |
      | sort=username:ASC   |
      | sort=username:asc:x |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Eleven filters return 400 TOO_MANY_FILTERS
    When Send GET users list request with query "filter=role:user&filter=is_active:true&filter=is_verified:false&filter=is_premium:false&filter=employment.status:employed&filter=settings.theme:dark&filter=settings.language:en&filter=address.country:US&filter=role:admin&filter=is_active:false&filter=is_premium:true" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "TOO_MANY_FILTERS" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Invalid filter field <query> returns 400 INVALID_FILTER_FIELD
    When Send GET users list request with query "<query>" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "INVALID_FILTER_FIELD" in response "response"
    Examples:
      | query                     |
      | filter=                   |
      | filter=role               |
      | filter=:user              |
      | filter=bogus:1            |
      | filter=password:x         |
      | filter=metadata.role:user |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: The same filter field twice returns 400 DUPLICATE_FILTER_FIELD
    When Send GET users list request with query "filter=role:user&filter=role:admin" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "DUPLICATE_FILTER_FIELD" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Invalid filter value <query> returns 400 INVALID_FILTER_VALUE
    Given Generate string of length 65 and save as "long65"
    When Send GET users list request with query "<query>" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "INVALID_FILTER_VALUE" in response "response"
    Examples:
      | query                            |
      | filter=role:root                 |
      | filter=role:Admin                |
      | filter=role:                     |
      | filter=is_active:1               |
      | filter=is_active:TRUE            |
      | filter=employment.status:pirate  |
      | filter=settings.theme:neon       |
      | filter=settings.language:eng     |
      | filter=address.country:          |
      | filter=address.country:${long65} |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Invalid search <label> returns 400 INVALID_SEARCH
    Given Generate string of length 65 and save as "long65"
    When Send GET users list request with query "<query>" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "INVALID_SEARCH" in response "response"
    Examples:
      | label           | query              |
      | empty           | search=            |
      | whitespace only | search=%20%20%20   |
      | 65 characters   | search=${long65}   |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Validation order — <query> fails with <code> first
    When Send GET users list request with query "<query>" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "<code>" in response "response"
    And Assert field "error.details" contains "<detail>" in response "response"
    Examples:
      | query                   | code                 | detail |
      | page=0&limit=0          | INVALID_PAGINATION   | 'page' |
      | limit=0&sort=bad        | INVALID_PAGINATION   | limit  |
      | sort=x&filter=bogus:1   | INVALID_SORT_FIELD   | sortable |
      | filter=bogus:1&search=  | INVALID_FILTER_FIELD | bogus  |
