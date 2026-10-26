@allure.label.epic:Bug_Hunting @allure.label.suite:Bug_Hunting @allure.label.subSuite:Buggy_API
Feature: Buggy API (GET /buggy, /buggy/items, POST /buggy/cart/total, GET /buggy/schedule)

  # Practice endpoints with INTENTIONAL, permanent bugs (no toggle). These scenarios pin the wrong values
  # exactly, so a regression in the bug — or a silent fix — is visible:
  #   items:    a FULL page drops its last item (a partial last page is correct by accident)
  #   cart:     total = Σ price × qty over all positions EXCEPT THE LAST (items_count is right)
  #   schedule: 09:00 is built in UTC, so event_start is shifted by the zone's UTC offset

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario Outline: The catalog lists <bug_id> on <method> <path>
    When Get buggy catalog and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "total" equals "3" in response "response"
    And Assert field "bugs.<index>.bug_id" equals "<bug_id>" in response "response"
    And Assert field "bugs.<index>.method" equals "<method>" in response "response"
    And Assert field "bugs.<index>.path" equals "<path>" in response "response"
    Examples:
      | index | bug_id                | method | path              |
      | 0     | pagination-off-by-one | GET    | /buggy/items      |
      | 1     | cart-total-wrong      | POST   | /buggy/cart/total |
      | 2     | timezone-shift        | GET    | /buggy/schedule   |

  # ─────────────────── OFF-BY-ONE ───────────────────

  @Run @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: The first full page is one item short — item 10 is never returned
    When Get buggy items with query "" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "per_page" equals "10" in response "response"
    And Assert field "total" equals "25" in response "response"
    And Assert item ids are "1..9" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: Page <page> of <per_page> returns ids "<ids>"
    When Get buggy items with query "page=<page>&per_page=<per_page>" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert item ids are "<ids>" in response "response"
    Examples:
      | page | per_page | ids    |
      | 2    | 10       | 11..19 |
      | 3    | 10       | 21..25 |
      | 4    | 10       |        |
      | 1    | 25       | 1..24  |
      | 1    | 50       | 1..25  |
      | 2    | 24       | 25     |
      | 1    | 1        |        |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Item shape — SKU, name and a price of id × 1.25
    When Get buggy items with query "per_page=50" and save response as "response"
    Then Assert field "items.0.sku" equals "ITEM-001" in response "response"
    And Assert field "items.0.name" equals "Practice item 01" in response "response"
    And Assert every buggy item costs its id times 1.25 in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Items with <query> returns 400 VALIDATION_ERROR
    When Get buggy items with query "<query>" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"
    Examples:
      | query        |
      | page=0       |
      | page=1000001 |
      | page=abc     |
      | per_page=0   |
      | per_page=51  |
      | per_page=x   |

  # ─────────────────── WRONG CART TOTAL ───────────────────

  @Run @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario Outline: Cart <items> totals <total> (correct would be <correct>)
    When Post buggy cart with items "<items>" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "items_count" equals "<count>" in response "response"
    And Assert field "currency" equals "USD" in response "response"
    And Assert cart total is "<total>" in response "response"
    Examples:
      | items             | count | total | correct |
      | 10x2, 5x3         | 2     | 20.00 | 35.00   |
      | 10x2              | 1     | 0.00  | 20.00   |
      | 5x3, 10x2         | 2     | 15.00 | 35.00   |
      | 1x1, 2x2, 4x3     | 3     | 5.00  | 17.00   |
      | 0.1x3, 0.2x1      | 2     | 0.30  | 0.50    |
      | 10.00x2, 5.50x3   | 2     | 20.00 | 36.50   |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Cart <label> returns 400 VALIDATION_ERROR
    When Post buggy cart with raw body "<body>" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"
    Examples:
      | label                 | body                                          |
      | with no items         | {\"items\":[]}                                |
      | without items         | {}                                            |
      | that is not JSON      | {\"items\":                                   |
      | with 3 price decimals | {\"items\":[{\"price\":1.234,\"qty\":1}]}     |
      | with a negative price | {\"items\":[{\"price\":-1,\"qty\":1}]}        |
      | with a string price   | {\"items\":[{\"price\":\"10\",\"qty\":1}]}    |
      | with qty 0            | {\"items\":[{\"price\":1,\"qty\":0}]}         |
      | with qty 1001         | {\"items\":[{\"price\":1,\"qty\":1001}]}      |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: A cart of 51 positions returns 400 VALIDATION_ERROR
    When Post buggy cart with 51 items and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  # ─────────────────── TIMEZONE SHIFT ───────────────────

  @Run @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario Outline: A 09:00 event in <tz> on <date> starts at <event_start> (shifted by the UTC offset)
    When Get buggy schedule with query "date=<date>&tz=<tz>" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "event_local" equals "09:00" in response "response"
    And Assert field "event_start" equals "<event_start>" in response "response"
    And Assert field "event_start_utc" equals "<date>T09:00:00Z" in response "response"
    Examples:
      | date       | tz                | event_start               |
      | 2026-03-29 | Europe/Moscow     | 2026-03-29T12:00:00+03:00 |
      | 2026-03-29 | Europe/Berlin     | 2026-03-29T11:00:00+02:00 |
      | 2026-07-01 | America/New_York  | 2026-07-01T05:00:00-04:00 |
      | 2026-07-01 | Pacific/Pago_Pago | 2026-06-30T22:00:00-11:00 |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: The bug is invisible in UTC
    When Get buggy schedule with query "date=2026-07-01&tz=UTC" and save response as "response"
    Then Assert field "event_start" equals "2026-07-01T09:00:00Z" in response "response"
    And Assert field "event_start_utc" equals "2026-07-01T09:00:00Z" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Schedule with <label> returns 400 VALIDATION_ERROR
    When Get buggy schedule with query "<query>" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"
    Examples:
      | label                | query                               |
      | no date              | tz=UTC                              |
      | an impossible date   | date=2026-02-30&tz=UTC              |
      | a non-ISO date       | date=01-07-2026&tz=UTC              |
      | no tz                | date=2026-07-01                     |
      | an unknown zone      | date=2026-07-01&tz=Mars/Base        |
      | a lower-cased zone   | date=2026-07-01&tz=europe/berlin    |
