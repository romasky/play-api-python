@allure.label.epic:Chaos_Engineering @allure.label.suite:Chaos_Engineering @allure.label.subSuite:Chaos_Transport
Feature: Chaos — compression and redirect chains (GET /chaos/gzip, GET|POST /chaos/redirect/{n})

  # gzip: behind Cloudflare the encoding FOLLOWS the client's Accept-Encoding (the spec says "always gzip"),
  # so the scenarios send Accept-Encoding explicitly. redirect: n hops of status `type` (301/302/307/308,
  # the spec lists only 302) with a RELATIVE Location, then /done reports what arrived. The client does not
  # follow redirects unless asked; 301/302 make the client turn POST into GET, 307/308 preserve method and body.

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: With Accept-Encoding gzip the body is gzip-encoded and decoded transparently
    When Get chaos gzip with Accept-Encoding "gzip" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert response header "Content-Encoding" equals "gzip" in "response"
    And Assert field "gzipped" equals "true" in response "response"
    And Assert field "method" equals "GET" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: The raw gzip bytes on the wire start with the gzip magic number
    When Read the raw chaos gzip body with Accept-Encoding "gzip" and save its first bytes as "magic"
    Then Assert "magic" equals "1f8b"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Without gzip in Accept-Encoding the body is not compressed (spec says it always is)
    When Get chaos gzip with Accept-Encoding "identity" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert response header "Content-Encoding" is absent in "response"

  # ─────────────────── REDIRECT ───────────────────

  @Run @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario Outline: Hop <hops> is not followed and points to <location>
    When Send "GET" chaos redirect "<hops>" with query "" and save response as "response"
    Then Get and check status code 302 from "response"
    And Assert response header "Location" equals "<location>" in "response"
    Examples:
      | hops | location                                 |
      | 3    | /api/v1/chaos/redirect/2?type=302        |
      | 1    | /api/v1/chaos/redirect/done?type=302     |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: Redirect type <type> answers <type> and propagates the type to the next hop
    When Send "GET" chaos redirect "2" with query "type=<type>" and save response as "response"
    Then Get and check status code <type> from "response"
    And Assert response header "Location" contains "type=<type>" in "response"
    Examples:
      | type |
      | 301  |
      | 307  |
      | 308  |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Following a 10-hop chain reaches /done after 10 redirects
    When Send "GET" chaos redirect "10" with query "" and body "" following redirects and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert response "response" followed 10 redirects
    And Assert field "message" equals "Reached final destination" in response "response"

  @Run @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario Outline: A <type> redirect <verdict> the POST body
    When Send "POST" chaos redirect "2" with query "type=<type>" and body "hello" following redirects and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "method" equals "<method>" in response "response"
    And Assert field "body_length" equals "<length>" in response "response"
    And Assert field "body_sha256" equals "<sha256>" in response "response"
    Examples:
      | type | verdict           | method | length | sha256                                                           |
      | 307  | preserves         | POST   | 5      | 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824 |
      | 308  | preserves         | POST   | 5      | 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824 |
      | 302  | drops (POST→GET)  | GET    | 0      | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
      | 301  | drops (POST→GET)  | GET    | 0      | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: /done called directly with <method> still claims redirected=true (it cannot detect redirects)
    When Send "<method>" directly to chaos redirect done and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "redirected" equals "true" in response "response"
    And Assert field "method" equals "<method>" in response "response"
    And Assert field "body_length" equals "0" in response "response"
    Examples:
      | method |
      | GET    |
      | POST   |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: A body over 1 MiB posted to /done returns 413 PAYLOAD_TOO_LARGE
    When Post directly to chaos redirect done a body of 1048577 bytes and save response as "response"
    Then Get and check status code 413 from "response"
    And Assert error code is "PAYLOAD_TOO_LARGE" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Redirect count "<hops>" returns 400 <code>
    When Send "GET" chaos redirect "<hops>" with query "" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "<code>" in response "response"
    Examples:
      | hops | code                   |
      | 0    | INVALID_REDIRECT_COUNT |
      | -1   | INVALID_REDIRECT_COUNT |
      | abc  | INVALID_REDIRECT_COUNT |
      | 11   | TOO_MANY_REDIRECTS     |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Redirect type "<type>" returns 400 INVALID_REDIRECT_TYPE
    When Send "GET" chaos redirect "2" with query "type=<type>" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "INVALID_REDIRECT_TYPE" in response "response"
    Examples:
      | type |
      | 303  |
      | abc  |
      |      |
