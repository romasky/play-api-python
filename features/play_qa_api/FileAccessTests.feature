@allure.label.epic:File_Storage @allure.label.suite:File_Storage @allure.label.subSuite:File_Access
Feature: File Access (list mine, public metadata, download, delete)

  # Metadata and download are public (an Authorization header is ignored) and never disclose the owner.
  # A token-owned file can be deleted only by its owner — anyone else, or no token, gets the same
  # 404 FILE_NOT_FOUND as a missing file. An anonymous file can be deleted by anyone.

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: Download is byte-exact with exact Content-Type, Content-Length and safe headers
    When Upload sample "tiny.png" anonymously and save response as "uploadRes"
    And Extract "file_id" from "uploadRes" and save as "fileId"
    And Download file "fileId" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert response "response" body equals sample "tiny.png"
    And Assert response header "Content-Type" equals "image/png" in "response"
    And Extract "size" from "uploadRes" and save as "fileSize"
    And Assert response header "Content-Length" equals "fileSize" in "response"
    And Assert response header "Content-Disposition" equals "attachment; filename="tiny.png"; filename*=UTF-8''tiny.png" in "response"
    And Assert response header "X-Content-Type-Options" equals "nosniff" in "response"
    And Assert response header "Content-Security-Policy" equals "default-src 'none'; sandbox" in "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: Download with inline=<inline> uses Content-Disposition <disposition>
    When Upload sample "note.txt" anonymously and save response as "uploadRes"
    And Extract "file_id" from "uploadRes" and save as "fileId"
    And Download file "fileId" with query "inline=<inline>" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert response header "Content-Disposition" contains "<disposition>;" in "response"
    Examples:
      | inline | disposition |
      | true   | inline      |
      | false  | attachment  |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: A non-ASCII filename gets an ASCII fallback and an RFC 5987 filename*
    When Upload sample "отчёт 1.txt" anonymously and save response as "uploadRes"
    And Extract "file_id" from "uploadRes" and save as "fileId"
    And Download file "fileId" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "filename" equals "отчёт 1.txt" in response "uploadRes"
    And Assert response header "Content-Disposition" contains "filename="_____ 1.txt"" in "response"
    And Assert response header "Content-Disposition" contains "filename*=UTF-8''%D0%BE%D1%82%D1%87%D1%91%D1%82%201.txt" in "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Metadata is public, ignores a bogus token and never discloses the owner
    Given a user with token "token"
    When Upload sample "note.txt" with token "token" and save response as "uploadRes"
    And Extract "file_id" from "uploadRes" and save as "fileId"
    And Get file "fileId" metadata with raw auth header "Bearer usr_bogus" and save response as "response"
    Then Get and check status code 200 from "response"
    And Assert field "file_id" equals "fileId" in response "response"
    And Assert field "owner" is absent in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: My files lists only my token uploads — not anonymous ones, not to other users
    Given a user with token "tokenA"
    And a user with token "tokenB"
    When Upload sample "note.txt" with token "tokenA" and save response as "ownRes"
    And Upload sample "data.csv" anonymously and save response as "anonRes"
    And List my files with token "tokenA" and save response as "listA"
    Then Get and check status code 200 from "listA"
    And Assert field "total" equals "1" in response "listA"
    And Assert field "files.0.filename" equals "note.txt" in response "listA"
    And Assert every item of "files" has no field "owner" in response "listA"
    When List my files with token "tokenB" and save response as "listB"
    Then Assert field "total" equals "0" in response "listB"

  @Run @Flow @allure.label.severity:critical @allure.label.story:End_to_End_Flow
  Scenario: Only the owner can delete a token-owned file; afterwards it is gone everywhere
    Given a user with token "tokenA"
    And a user with token "tokenB"
    When Upload sample "note.txt" with token "tokenA" and save response as "uploadRes"
    And Extract "file_id" from "uploadRes" and save as "fileId"
    And Delete file "fileId" with token "tokenB" and save response as "otherRes"
    Then Get and check status code 404 from "otherRes"
    And Assert error code is "FILE_NOT_FOUND" in response "otherRes"
    When Delete file "fileId" anonymously and save response as "anonRes"
    Then Get and check status code 404 from "anonRes"
    And Assert error code is "FILE_NOT_FOUND" in response "anonRes"
    When Delete file "fileId" with token "tokenA" and save response as "ownerRes"
    Then Get and check status code 204 from "ownerRes"
    And Assert response body is empty in "ownerRes"
    When Delete file "fileId" with token "tokenA" and save response as "againRes"
    Then Get and check status code 404 from "againRes"
    When Get file "fileId" metadata and save response as "metaRes"
    Then Get and check status code 404 from "metaRes"
    And Assert error code is "FILE_NOT_FOUND" in response "metaRes"
    When Download file "fileId" and save response as "downloadRes"
    Then Get and check status code 404 from "downloadRes"
    When List my files with token "tokenA" and save response as "listRes"
    Then Assert field "total" equals "0" in response "listRes"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Anyone can delete an anonymous file
    Given a user with token "token"
    When Upload sample "note.txt" anonymously and save response as "uploadRes"
    And Extract "file_id" from "uploadRes" and save as "fileId"
    And Delete file "fileId" with token "token" and save response as "response"
    Then Get and check status code 204 from "response"

  # ─────────────────── NEGATIVE ───────────────────

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: My files without a token returns 401 MISSING_TOKEN
    When List my files with no auth token and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "MISSING_TOKEN" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: My files with <query> returns 400 VALIDATION_ERROR
    Given a user with token "token"
    When List my files with query "<query>" and token "token" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"
    Examples:
      | query        |
      | page=0       |
      | page=1001    |
      | per_page=51  |
      | per_page=abc |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Download with inline=<inline> returns 400 VALIDATION_ERROR
    When Upload sample "note.txt" anonymously and save response as "uploadRes"
    And Extract "file_id" from "uploadRes" and save as "fileId"
    And Download file "fileId" with query "inline=<inline>" and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"
    Examples:
      | inline |
      | yes    |
      | 1      |
      | TRUE   |

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Metadata of an unknown file id returns 404 FILE_NOT_FOUND
    When Get file "fil_00000000000000000000000000000000" metadata and save response as "response"
    Then Get and check status code 404 from "response"
    And Assert error code is "FILE_NOT_FOUND" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Download of an unknown file id returns 404 FILE_NOT_FOUND with a JSON error body
    When Download file "fil_00000000000000000000000000000000" and save response as "response"
    Then Get and check status code 404 from "response"
    And Assert error code is "FILE_NOT_FOUND" in response "response"
