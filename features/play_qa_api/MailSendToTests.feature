@allure.label.epic:Mail_Service @allure.label.suite:Mail_Service @allure.label.subSuite:Mail_Send_To
Feature: SMTP Response Simulator (POST /mail/{token}/send-to)

  # Always HTTP 200 — a failed delivery is data, not an error. A "magic" recipient (matched on the local part
  # only, case-insensitive, any domain) returns a canned SMTP failure (accepted=false, no message_id, nothing
  # stored). Any other recipient is accepted (250) and the message is stored in the SENDER's own mailbox —
  # it is never delivered to the recipient. Magic local parts cannot be created as mailboxes (409).

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario Outline: Magic recipient <local_part> returns SMTP <smtp_code> <enhanced_status> (<category>)
    When Create mailbox and save response as "mailboxRes"
    And Extract "token" from "mailboxRes" and save as "mailToken"
    And Send to "<local_part>@play-qa.com" from mailbox "mailToken" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "accepted" equals "false" in response "response"
    And Assert field "smtp_code" equals "<smtp_code>" in response "response"
    And Assert field "enhanced_status" equals "<enhanced_status>" in response "response"
    And Assert field "category" equals "<category>" in response "response"
    And Assert field "message" equals "<message>" in response "response"
    And Assert field "message_id" is absent in response "response"
    Examples:
      | local_part            | smtp_code | enhanced_status | category  | message                                               |
      | mailbox-full          | 552       | 5.2.2           | recipient | Requested mail action aborted: mailbox full          |
      | user-unknown          | 550       | 5.1.1           | recipient | Requested action not taken: user unknown             |
      | mailbox-disabled      | 550       | 5.2.1           | recipient | Mailbox disabled, not accepting messages             |
      | mailbox-unavailable   | 550       | 5.2.0           | recipient | Mailbox temporarily unavailable                      |
      | recipient-rejected    | 550       | 5.1.1           | recipient | Recipient address rejected                           |
      | rejected-by-policy    | 554       | 5.7.1           | policy    | Message rejected by policy (spam/content)            |
      | relay-denied          | 554       | 5.7.1           | policy    | Relay access denied                                  |
      | access-denied         | 550       | 5.7.1           | policy    | Access denied — not allowed to send to this domain   |
      | sender-blocked        | 554       | 5.7.1           | policy    | Sender address blocked                               |
      | blacklisted           | 554       | 5.7.1           | policy    | IP/domain blacklisted                                |
      | auth-failed           | 535       | 5.7.8           | auth      | Authentication credentials invalid                   |
      | starttls-required     | 530       | 5.7.0           | auth      | Must issue a STARTTLS command first                  |
      | invalid-credentials   | 535       | 5.7.8           | auth      | Invalid SMTP credentials                             |
      | spf-fail              | 550       | 5.7.26          | auth      | Message failed SPF/DKIM/DMARC authentication checks  |
      | too-many-messages     | 451       | 4.7.0           | throttle  | Too many messages — sending rate exceeded            |
      | quota-exceeded        | 452       | 4.5.3           | throttle  | Daily sending quota exceeded                         |
      | connection-rate-limit | 421       | 4.7.0           | throttle  | Connection rate limit exceeded                       |
      | greylisted            | 451       | 4.7.1           | throttle  | Greylisted — please try again later                  |
      | service-unavailable   | 421       | 4.3.0           | temporary | Service temporarily unavailable                      |
      | temporary-failure     | 450       | 4.2.0           | temporary | Requested action aborted: temporary failure          |
      | delivery-timeout      | 451       | 4.4.2           | temporary | Timeout during delivery                              |
      | connection-refused    | 421       | 4.4.1           | temporary | Connection refused                                   |
      | message-too-large     | 552       | 5.3.4           | content   | Message size exceeds fixed maximum message size      |
      | content-rejected      | 554       | 5.6.0           | content   | Message content rejected                             |
      | invalid-mime          | 554       | 5.6.0           | content   | Invalid or malformed MIME message                    |
      | attachment-rejected   | 552       | 5.7.0           | content   | Attachment type rejected by server                   |
      | host-not-found        | 550       | 5.4.4           | routing   | Host not found / unable to route to domain           |
      | domain-not-found      | 550       | 5.4.4           | routing   | Domain does not exist (DNS failure)                  |
      | no-mx-record          | 550       | 5.4.4           | routing   | No MX record found for domain                        |
      | routing-error         | 551       | 5.1.2           | routing   | User not local; invalid delivery route               |
      | insufficient-storage  | 452       | 4.3.1           | system    | Insufficient system storage                          |
      | server-error          | 451       | 4.3.5           | system    | Server internal error                                |
      | queue-overflow        | 452       | 4.3.1           | system    | Mail queue overflow                                  |
      | server-shutdown       | 421       | 4.3.2           | system    | Service shutting down                                |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: Magic matching ignores case and domain — <to>
    When Create mailbox and save response as "mailboxRes"
    And Extract "token" from "mailboxRes" and save as "mailToken"
    And Send to "<to>" from mailbox "mailToken" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "accepted" equals "false" in response "response"
    And Assert field "smtp_code" equals "552" in response "response"
    And Assert field "to" equals "<to>" in response "response"
    Examples:
      | to                            |
      | MAILBOX-FULL@play-qa.com      |
      | Mailbox-Full@MAIL.PLAY-QA.COM |
      | mailbox-full@inbox.play-qa.com |
      | mailbox-full@gmail.com        |
      | mailbox-full                  |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Sub-addressing breaks the magic match — the message is accepted
    When Create mailbox and save response as "mailboxRes"
    And Extract "token" from "mailboxRes" and save as "mailToken"
    And Send to "mailbox-full+tag@play-qa.com" from mailbox "mailToken" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "accepted" equals "true" in response "response"

  @Run @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: A normal recipient is accepted (250) and stored in the sender's mailbox
    When Create mailbox and save response as "mailboxRes"
    And Extract "token" from "mailboxRes" and save as "mailToken"
    And Send to "someone@example.com" from mailbox "mailToken" with subject "Hello simulator" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "accepted" equals "true" in response "response"
    And Assert field "smtp_code" equals "250" in response "response"
    And Assert field "category" equals "accepted" in response "response"
    And Assert field "message" equals "Message accepted for delivery" in response "response"
    And Assert field "enhanced_status" is absent in response "response"
    And Extract "message_id" from "response" and save as "messageId"
    When Get message "messageId" for token "mailToken" and save response as "messageRes"
    Then Get and check status code 200 from "messageRes"
    And Assert field "subject" equals "Hello simulator" in response "messageRes"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: A magic recipient is not stored
    When Create mailbox and save response as "mailboxRes"
    And Extract "token" from "mailboxRes" and save as "mailToken"
    And Send to "user-unknown@play-qa.com" from mailbox "mailToken" and save response as "response"
    And Get messages for token "mailToken" and save response as "messagesRes"
    Then Assert field "count" equals "0" in response "messagesRes"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Sending to another live temp mailbox does not deliver there
    When Create mailbox and save response as "senderRes"
    And Extract "token" from "senderRes" and save as "senderToken"
    And Create mailbox and save response as "recipientRes"
    And Extract "token" from "recipientRes" and save as "recipientToken"
    And Extract "email_address" from "recipientRes" and save as "recipientAddress"
    And Send to "recipientAddress" from mailbox "senderToken" and save response as "response"
    Then Assert field "accepted" equals "true" in response "response"
    When Get messages for token "recipientToken" and save response as "recipientMessages"
    Then Assert field "count" equals "0" in response "recipientMessages"

  # ─────────────────── NEGATIVE ───────────────────

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Send-to with <label> returns 400 VALIDATION_ERROR
    When Create mailbox and save response as "mailboxRes"
    And Extract "token" from "mailboxRes" and save as "mailToken"
    And Send to from mailbox "mailToken" with raw body "<body>" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"
    Examples:
      | label             | body          |
      | no recipient      | {}            |
      | an empty to       | {\"to\":\"\"} |
      | a numeric to      | {\"to\":123}  |
      | truncated JSON    | {\"to\":      |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Send-to with an unknown mailbox token returns 404 MAILBOX_NOT_FOUND
    Given Generate fake uuid and save as "fakeToken"
    When Send to "someone@example.com" from mailbox "fakeToken" and save response as "response"
    Then Get and check status code 404 from "response"
    And Assert error code is "MAILBOX_NOT_FOUND" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Body validation runs before the mailbox lookup
    Given Generate fake uuid and save as "fakeToken"
    When Send to from mailbox "fakeToken" with raw body "{}" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  @Run @Negative @allure.label.severity:critical @allure.label.story:Negative_Scenario
  Scenario Outline: A magic local part cannot become a mailbox — <local_part>@<domain> returns 409 RESERVED_LOCAL_PART
    When Create mailbox with domain "<domain>" local_part "<local_part>" and save response as "response"
    Then Get and check status code 409 from "response"
    And Assert error code is "RESERVED_LOCAL_PART" in response "response"
    Examples:
      | local_part      | domain            |
      | mailbox-full    | play-qa.com       |
      | server-shutdown | inbox.play-qa.com |
