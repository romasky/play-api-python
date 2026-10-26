@allure.label.epic:File_Storage @allure.label.suite:File_Storage @allure.label.subSuite:File_Upload
Feature: File Upload (POST /files/upload)

  # multipart/form-data with a `file` part (+ optional `description` ≤ 200). Auth is optional: a valid token
  # makes the caller the owner, no header uploads anonymously, a present-but-bad header is refused (never a
  # silent anonymous upload). content_type is SNIFFED from the bytes; declared_type echoes the part's type.
  # Check order: body size → multipart → NO_FILE → part size → EMPTY_FILE → description → extension → sniff.
  # 10 uploads per minute (burst 5) — paced per call; every uploaded file is deleted after the scenario.

  @Run @Smoke @Positive @allure.label.severity:critical @allure.label.story:Positive_Scenario
  Scenario: Upload a PNG with a token — owner user, sniffed type, 24 h lifetime
    Given a user with token "token"
    When Upload sample "tiny.png" with token "token" and save response as "response"
    Then Get and check status code 201 from "response"
    And Assert field "owner" equals "user" in response "response"
    And Assert field "filename" equals "tiny.png" in response "response"
    And Assert field "content_type" equals "image/png" in response "response"
    And Assert field "size" equals the size of sample "tiny.png" in response "response"
    And Assert field "file_id" contains "fil_" in response "response"
    And Extract "file_id" from "response" and save as "fileId"
    And Assert field "download_url" equals "/api/v1/files/${fileId}/download" in response "response"
    And Assert response header "cache-control" contains "no-store" in "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: Anonymous upload — owner anonymous, empty description
    When Upload sample "note.txt" anonymously and save response as "response"
    Then Get and check status code 201 from "response"
    And Assert field "owner" equals "anonymous" in response "response"
    And Assert field "description" equals "" in response "response"
    And Assert field "content_type" equals "text/plain" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: The detected type wins over the declared one — PNG bytes declared as text/plain
    When Upload sample "tiny.png" declared as "text/plain" anonymously and save response as "response"
    Then Get and check status code 201 from "response"
    And Assert field "content_type" equals "image/png" in response "response"
    And Assert field "declared_type" equals "text/plain" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario Outline: Upload <name> — sniffed as <content_type>, declared <declared> echoed
    When Upload sample "<name>" anonymously and save response as "response"
    Then Get and check status code 201 from "response"
    And Assert field "content_type" equals "<content_type>" in response "response"
    And Assert field "declared_type" equals "<declared>" in response "response"
    Examples:
      | name      | content_type    | declared         |
      | data.csv  | text/plain      | text/csv         |
      | data.json | text/plain      | application/json |
      | tiny.pdf  | application/pdf | application/pdf  |

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: A description of exactly 200 characters is accepted and echoed
    Given Generate string of length 200 and save as "desc200"
    When Upload sample "note.txt" with description "desc200" anonymously and save response as "response"
    Then Get and check status code 201 from "response"
    And Assert field "description" equals "desc200" in response "response"

  @Run @Positive @allure.label.story:Positive_Scenario
  Scenario: A file of exactly 5 MiB is accepted (inclusive boundary)
    When Upload sample "exactly-5mib.txt" anonymously and save response as "response"
    Then Get and check status code 201 from "response"
    And Assert field "size" equals "5242880" in response "response"

  # ─────────────────── NEGATIVE ───────────────────

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: A JSON body instead of multipart returns 400 INVALID_MULTIPART
    When Upload a JSON body instead of multipart and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "INVALID_MULTIPART" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: Multipart without a file part returns 400 NO_FILE
    When Upload a multipart body without a file part and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "NO_FILE" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: A file in a part not named "file" returns 400 NO_FILE
    When Upload sample "note.txt" in multipart field "upload" anonymously and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "NO_FILE" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: An empty file returns 400 EMPTY_FILE
    When Upload sample "empty.txt" anonymously and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "EMPTY_FILE" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario: A description of 201 characters returns 400 VALIDATION_ERROR
    Given Generate string of length 201 and save as "desc201"
    When Upload sample "note.txt" with description "desc201" anonymously and save response as "response"
    Then Get and check status code 400 from "response"
    And Assert error code is "VALIDATION_ERROR" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Upload <name> returns 415 UNSUPPORTED_MEDIA_TYPE
    When Upload sample "<name>" anonymously and save response as "response"
    Then Get and check status code 415 from "response"
    And Assert error code is "UNSUPPORTED_MEDIA_TYPE" in response "response"
    And Assert field "error.details" contains "<detail>" in response "response"
    Examples:
      | name        | detail                   |
      | program.exe | .exe is not accepted     |
      | noextension | application/octet-stream |

  @Run @Negative @allure.label.severity:critical @allure.label.story:Negative_Scenario
  Scenario: Text content behind a .png extension returns 422 CORRUPTED_FILE
    When Upload sample "fake.png" anonymously and save response as "response"
    Then Get and check status code 422 from "response"
    And Assert error code is "CORRUPTED_FILE" in response "response"

  @Run @Negative @allure.label.story:Negative_Scenario
  Scenario Outline: Upload <label> returns 413 FILE_TOO_LARGE
    When Upload sample "<name>" anonymously and save response as "response"
    Then Get and check status code 413 from "response"
    And Assert error code is "FILE_TOO_LARGE" in response "response"
    Examples:
      | label                          | name                |
      | a file part of 5 MiB + 1 byte  | 5mib-plus-1.txt     |
      | a body beyond the multipart cap | 5mib-plus-70kib.txt |

  @Run @Negative @allure.label.severity:critical @allure.label.story:Negative_Scenario
  Scenario Outline: Upload with a bad Authorization header (<header>) returns 401 <code>, never an anonymous upload
    When Upload sample "note.txt" with raw auth header "<header>" and save response as "response"
    Then Get and check status code 401 from "response"
    And Assert error code is "<code>" in response "response"
    Examples:
      | header           | code                 |
      | Bearer usr_bogus | INVALID_TOKEN        |
      | Basic abc        | INVALID_TOKEN_FORMAT |
