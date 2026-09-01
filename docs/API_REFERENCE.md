# play-qa-api — API Reference

**Base path:** `/api/v1`  
**Production URLs:**
- `https://play-qa.com/api/v1`

**Swagger UI:** `/swagger/index.html`

> **Test coverage note (play-api-js):** every endpoint below has a feature file except `POST /verify-recaptcha`,
> which is out of scope (requires a live Google reCAPTCHA v2 token). `GET /auth/basic` is covered by `BasicAuthTests.feature`.

---

## Table of Contents

1. [Global Middleware](#global-middleware)
2. [Standard Response Envelope](#standard-response-envelope)
3. [Bearer Authentication](#bearer-authentication)
4. [Rate Limiting](#rate-limiting)
5. [Endpoints](#endpoints)
   - [Health](#1-get-apiv1health)
   - [Login](#2-post-apiv1login)
   - [Basic Auth](#3-get-apiv1authbasic)
   - [Verify reCAPTCHA](#4-post-apiv1verify-recaptcha)
   - [Create User](#5-post-apiv1userscreate)
   - [List Users](#6-get-apiv1userslist)
   - [Get User](#7-get-apiv1usersgetid)
   - [Check User Exists](#8-head--9-get-apiv1usersexistsid)
   - [User Options](#10-options-apiv1usersoptions)
   - [Update User (full)](#11-put-apiv1usersupdateid)
   - [Update User (partial)](#12-patch-apiv1userspatchid)
   - [Delete User](#13-delete-apiv1usersdeleteid)
   - [Logout](#14-post-apiv1userslogoutid)
   - [Create Mailbox](#15-post-apiv1mailcreate)
   - [Get Mailbox](#16-get-apiv1mailtoken)
   - [List Messages](#17-get-apiv1mailtokenmessages)
   - [Get Message](#18-get-apiv1mailtokenmessagesid)
   - [Send Message](#19-post-apiv1mailtokensend)
   - [Delete Mailbox](#20-delete-apiv1mailtoken)
6. [All Error Codes Reference](#all-error-codes-reference)

---

## Global Middleware

Every request passes through these middleware layers in order:

| Middleware | Behavior |
|---|---|
| **CORS** | Allows origins matching the `CORS_ORIGINS` env list or any `http://localhost*` prefix. Sets `Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS`. OPTIONS preflight returns 204. |
| **RequestLogger** | Logs `[METHOD] /path clientIP - statusCode (duration)` after each request. |
| **RequestID** | Reads `X-Request-ID` header; generates a UUID v4 if absent. Echoes the value in the `X-Request-ID` response header and includes it in every error response body as `request_id`. |
| **GlobalRateLimiter** | Token-bucket, **10 req/s per IP**, burst 20. Returns 429 `RATE_LIMIT_EXCEEDED` if exceeded. Disabled when env var `DISABLE_RATE_LIMIT=true`. |

---

## Standard Response Envelope

All endpoints (except `POST /verify-recaptcha` and `GET /auth/basic` — see those sections) return errors using this envelope:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description",
    "details": "Optional additional context",
    "field": "Optional: the field that caused the error",
    "validation": [
      {
        "field": "fieldname",
        "message": "why the value was rejected",
        "value": "the submitted value"
      }
    ]
  },
  "timestamp": "2024-01-01T00:00:00Z",
  "request_id": "uuid-string"
}
```

> **Note:** `details`, `field`, and `validation` are omitted when not applicable. Validation errors populate the `validation` array instead of `field`.

---

## Bearer Authentication

Required for: `PUT`, `PATCH`, `DELETE` user endpoints and `POST /users/logout/:id`.

**Request header:**
```
Authorization: Bearer usr_1700000000_abc123...
```

Token format: `usr_<unix_timestamp>_<32 hex chars>`

The middleware checks in this exact order:

| Step | Condition | Response |
|---|---|---|
| 1 | `Authorization` header missing | 401 `MISSING_TOKEN` |
| 2 | Header present but not `Bearer <token>` format | 401 `INVALID_TOKEN_FORMAT` |
| 3 | `:id` path param is empty | 400 `MISSING_USER_ID` |
| 4 | Token does not match stored token for the user | 401 `INVALID_TOKEN` — "Token does not match user or has expired" |

A token is invalidated (revoked to empty string in DB) on logout. Any subsequent request with a revoked token returns `401 INVALID_TOKEN`.

---

## Rate Limiting

| Limiter | Scope | Rate | Burst | 429 Message |
|---|---|---|---|---|
| **GlobalRateLimiter** | Every route, per IP | 10 req/s | 20 | "Maximum 10 requests per second allowed" |
| **LoginRateLimiter** | `POST /login` only, per IP | 5 req/min (1 per 12 s) | 5 | "Maximum 5 login attempts per minute allowed" |
| **CreateUserRateLimiter** | `POST /users/create` only, per IP | ~100/min (1 per 600 ms) | 100 | "Maximum 100 user creations per minute allowed" |

All limiters are skipped when `DISABLE_RATE_LIMIT=true`.

All rate limit errors use HTTP **429** with error code `RATE_LIMIT_EXCEEDED` in the standard error envelope.

---

## Endpoints

---

### 1. GET /api/v1/health

**Auth:** None

**Response 200:**
```json
{
  "status": "ok",
  "time": "2024-01-01T12:00:00Z"
}
```

No error paths beyond network-level failures.

---

### 2. POST /api/v1/login

**Auth:** None  
**Extra rate limit:** LoginRateLimiter (5 req/min per IP)

#### Request body

```json
{
  "email": "user@example.com",
  "password": "mypassword"
}
```

| Field | Type | Validation |
|---|---|---|
| `email` | string | Required. Valid email format. |
| `password` | string | Required. Minimum 8 characters. |

#### Response 200 — success

```json
{
  "success": true,
  "message": "Login successful",
  "access_token": "usr_1700000000_abc123...",
  "user_id": "507f1f77bcf86cd799439011",
  "email": "user@example.com",
  "username": "johndoe",
  "expires_at": "2024-01-02T12:00:00Z"
}
```

> Any previously issued token is invalidated on successful login.

#### Error responses

| Status | Code | Trigger |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Missing field or password shorter than 8 chars |
| 401 | `INVALID_CREDENTIALS` | Email not found or password mismatch |
| 429 | `RATE_LIMIT_EXCEEDED` | Exceeded 5 attempts/min |
| 500 | `INTERNAL_ERROR` | Database error |

---

### 3. GET /api/v1/auth/basic

**Auth:** HTTP Basic Authentication  
**Note:** Intentional QA practice endpoint — not in Swagger. Hardcoded credentials: `admin` / `admin`.

#### Request header

```
Authorization: Basic YWRtaW46YWRtaW4=
```

#### Response 200 — correct credentials

```json
{
  "success": true,
  "message": "Basic authentication successful",
  "user": "admin"
}
```

> **Non-standard error shape.** This endpoint does NOT use the standard error envelope.

#### Response 401 — all failure cases

Response header always present on 401:
```
WWW-Authenticate: Basic realm="Test Authentication", charset="UTF-8"
```

```json
{
  "error": "Unauthorized",
  "message": "<reason>"
}
```

| Condition | `message` value |
|---|---|
| No `Authorization` header | `"Basic authentication required"` |
| Not prefixed with `Basic ` | `"Invalid authentication format"` |
| Bad base64 encoding | `"Invalid base64 encoding"` |
| Decoded string not in `user:pass` form | `"Invalid credentials format"` |
| Wrong username or password | `"Invalid username or password"` |

---

### 4. POST /api/v1/verify-recaptcha

**Auth:** None

> **Non-standard error shape.** This endpoint does NOT use the standard error envelope. Errors return raw JSON without `success`, `timestamp`, or `request_id` fields.

#### Request body

```json
{
  "token": "<reCAPTCHA v2 client token>"
}
```

| Field | Type | Validation |
|---|---|---|
| `token` | string | Required. reCAPTCHA v2 token from the browser widget. |

#### Response 200 — verified

```json
{
  "success": true,
  "message": "reCAPTCHA verified successfully",
  "challenge_ts": "2024-01-01T12:00:00Z",
  "hostname": "play-qa.com"
}
```

#### Response 200 — Google rejected the token

```json
{
  "success": false,
  "error": "reCAPTCHA verification failed",
  "error_codes": ["invalid-input-response"]
}
```

#### Error responses (non-standard shape)

| Status | Body | Trigger |
|---|---|---|
| 400 | `{"success":false,"error":"Token is required"}` | `token` field missing |
| 500 | `{"success":false,"error":"<message>"}` | `RECAPTCHA_SECRET_KEY` env not set, Google unreachable, or parse failure |

---

### 5. POST /api/v1/users/create

**Auth:** None  
**Extra rate limit:** CreateUserRateLimiter (~100 req/min per IP)

#### Request body

```json
{
  "email": "user@example.com",
  "username": "johndoe",
  "password": "mypassword",
  "profile": {
    "first_name": "John",
    "last_name": "Doe",
    "middle_name": "Michael",
    "avatar_url": "https://example.com/avatar.jpg",
    "bio": "Short bio here.",
    "date_of_birth": "1990-01-15",
    "gender": "male",
    "interests": ["coding", "travel"]
  },
  "contacts": {
    "phone": "+1234567890",
    "phone_verified": false,
    "telegram": "@johndoe",
    "whatsapp": "+1234567890",
    "linkedin": "https://linkedin.com/in/johndoe",
    "github": "https://github.com/johndoe",
    "website": "https://johndoe.dev",
    "emergency_contact": "Jane Doe +1234567891"
  },
  "address": {
    "country": "US",
    "state": "California",
    "city": "San Francisco",
    "street": "Market St",
    "building": "100",
    "apartment": "5A",
    "zip_code": "94105",
    "coordinates": {
      "latitude": 37.7749,
      "longitude": -122.4194
    }
  },
  "employment": {
    "status": "employed",
    "company": "Acme Inc",
    "position": "Engineer",
    "department": "R&D",
    "start_date": "2020-03-01",
    "salary": {
      "amount": 120000,
      "currency": "USD"
    }
  },
  "settings": {
    "language": "en",
    "timezone": "America/Los_Angeles",
    "theme": "dark",
    "notifications_enabled": true,
    "email_notifications": true,
    "sms_notifications": false,
    "two_factor_enabled": false,
    "private_profile": false
  }
}
```

**Top-level fields:**

| Field | Type | Required | Validation |
|---|---|---|---|
| `email` | string | Yes | Valid email format |
| `username` | string | Yes | Min 3, max 30 characters |
| `password` | string | Yes | Min 8 characters. Never returned in any response. |
| `profile` | object | Yes | See profile fields below |
| `contacts` | object | No | All sub-fields optional |
| `address` | object | No | All sub-fields optional |
| `employment` | object | No | All sub-fields optional |
| `settings` | object | No | All sub-fields optional |

**`profile` sub-fields:**

| Field | Type | Required | Validation |
|---|---|---|---|
| `first_name` | string | Yes | Min 2 characters |
| `last_name` | string | Yes | Min 2 characters |
| `middle_name` | string | No | — |
| `avatar_url` | string | No | Valid URL if provided |
| `bio` | string | No | Max 500 characters |
| `date_of_birth` | string | No | — |
| `gender` | string | No | Enum: `male`, `female`, `other`, `prefer_not_to_say` |
| `interests` | []string | No | — |

**`contacts` sub-fields:**

| Field | Type | Validation |
|---|---|---|
| `phone` | string | — |
| `phone_verified` | bool | — |
| `telegram` | string | — |
| `whatsapp` | string | — |
| `linkedin` | string | Valid URL if provided |
| `github` | string | Valid URL if provided |
| `website` | string | Valid URL if provided |
| `emergency_contact` | string | — |

**`address` sub-fields:**

| Field | Type |
|---|---|
| `country` | string |
| `state` | string |
| `city` | string |
| `street` | string |
| `building` | string |
| `apartment` | string |
| `zip_code` | string |
| `coordinates` | object: `{"latitude": float, "longitude": float}` |

**`employment` sub-fields:**

| Field | Type | Validation |
|---|---|---|
| `status` | string | Enum: `employed`, `unemployed`, `student`, `retired`, `freelancer` |
| `company` | string | — |
| `position` | string | — |
| `department` | string | — |
| `start_date` | string | — |
| `salary` | object | `{"amount": float, "currency": "USD"}` — `currency` must be exactly 3 characters |

**`settings` sub-fields:**

| Field | Type | Validation |
|---|---|---|
| `language` | string | Exactly 2 characters if provided (e.g. `"en"`) |
| `timezone` | string | — |
| `theme` | string | Enum: `light`, `dark`, `system` |
| `notifications_enabled` | bool | — |
| `email_notifications` | bool | — |
| `sms_notifications` | bool | — |
| `two_factor_enabled` | bool | — |
| `private_profile` | bool | — |

#### Response 201 — created

```json
{
  "id": "507f1f77bcf86cd799439011",
  "email": "user@example.com",
  "username": "johndoe",
  "access_token": "usr_1700000000_abc123...",
  "profile": {
    "first_name": "John",
    "last_name": "Doe",
    "middle_name": "Michael",
    "avatar_url": "https://example.com/avatar.jpg",
    "bio": "Short bio here.",
    "date_of_birth": "1990-01-15",
    "gender": "male",
    "interests": ["coding", "travel"]
  },
  "contacts": { "..." : "..." },
  "address": { "..." : "..." },
  "employment": { "..." : "..." },
  "settings": { "..." : "..." },
  "metadata": {
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z",
    "expires_at": "2024-01-02T12:00:00Z",
    "last_login_at": null,
    "last_login_ip": "",
    "login_count": 0,
    "is_active": true,
    "is_verified": false,
    "is_premium": false,
    "role": "user",
    "tags": null,
    "source": "",
    "user_agent": ""
  }
}
```

> `access_token` is **only** returned on this 201 response. It is not returned on GET or update responses.  
> `password` is **never** returned in any response.

#### Error responses

| Status | Code | Trigger |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Missing required field, invalid email, password < 8 chars, invalid URL, bad enum value, invalid currency length, invalid language length |
| 409 | `DUPLICATE_USER` | Email or username already in use |
| 429 | `RATE_LIMIT_EXCEEDED` | Exceeded ~100 creations/min |
| 503 | `DATABASE_LIMIT_REACHED` | User count ≥ 1,000,000 |
| 500 | `INTERNAL_ERROR` | Database write error |

---

### 6. GET /api/v1/users/list

**Auth:** None  
**Response headers:** `Cache-Control: no-store, no-cache, must-revalidate, max-age=0`, `Pragma: no-cache`, `Surrogate-Control: no-store`

#### Query parameters

| Param | Type | Default | Notes |
|---|---|---|---|
| `page` | int | `1` | Page number |
| `per_page` | int | `10` | Items per page; clamped to 1–100 by the service |

> **Observed (not in the original spec):** non-positive or non-numeric `page`/`per_page` return
> `400 INVALID_PAGINATION` (`details`: "'page' must be a positive integer"); `per_page` above 100 is clamped and returns 200.
> `ListUsersTests.feature` asserts only the weaker "not 5xx, one of 200/400" property until the contract is confirmed.

#### Response 200

```json
{
  "users": [
    {
      "id": "507f1f77bcf86cd799439011",
      "email": "user@example.com",
      "username": "johndoe",
      "profile": { "..." : "..." },
      "contacts": { "..." : "..." },
      "address": { "..." : "..." },
      "employment": { "..." : "..." },
      "settings": { "..." : "..." },
      "metadata": { "..." : "..." }
    }
  ],
  "page": 1,
  "per_page": 10,
  "total_pages": 42
}
```

> `access_token` is not included in list items.

#### Error responses

| Status | Code | Trigger |
|---|---|---|
| 500 | `INTERNAL_ERROR` | Database query failure |

---

### 7. GET /api/v1/users/get/:id

**Auth:** None

#### Path parameters

| Param | Type | Notes |
|---|---|---|
| `id` | string | MongoDB ObjectID (24 hex characters) |

#### Response 200

Full `UserResponse` object (same shape as a list item, without `access_token`).

#### Error responses

| Status | Code | Trigger |
|---|---|---|
| 404 | `USER_NOT_FOUND` | Invalid ObjectID format or user not found |
| 500 | `INTERNAL_ERROR` | Database error |

---

### 8. HEAD / 9. GET /api/v1/users/exists/:id

**Auth:** None  
**Note:** Both methods map to the same handler. The GET alias exists because Cloudflare CDN converts some HEAD requests to GET.

#### Path parameters

| Param | Type | Notes |
|---|---|---|
| `id` | string | MongoDB ObjectID (24 hex characters) |

#### Response headers (always set)

| Header | Value |
|---|---|
| `X-User-Exists` | `"true"` or `"false"` |

#### Response 200 — user exists

Empty body.

#### Response 404 — user does not exist

Empty body. Any error (including DB errors) also returns 404 with `X-User-Exists: false`.

---

### 10. OPTIONS /api/v1/users/options

**Auth:** None  
**Response header:** `Allow: GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS`

#### Response 200

```json
{
  "allowed_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
  "endpoints": {
    "POST /users/create": "Create a new user",
    "GET /users/list": "List all users",
    "GET /users/get/:id": "Get user by ID",
    "PUT /users/update/:id": "Update user (full)",
    "PATCH /users/patch/:id": "Update user (partial)",
    "DELETE /users/delete/:id": "Delete user",
    "HEAD /users/exists/:id": "Check if user exists",
    "OPTIONS /users/options": "Get available methods"
  },
  "authentication": {
    "type": "Bearer Token",
    "header": "Authorization",
    "format": "Bearer <token>",
    "required_for": ["PUT", "PATCH", "DELETE"]
  }
}
```

---

### 11. PUT /api/v1/users/update/:id

**Auth:** Bearer token required

**Semantics:** Full replace — all core fields must be provided; omitting optional objects clears them.

#### Path parameters

| Param | Type | Notes |
|---|---|---|
| `id` | string | MongoDB ObjectID (24 hex characters) |

#### Request body

Same fields and validation as [POST /users/create](#5-post-apiv1userscreate) except `password` is not included.

Required fields: `email`, `username`, `profile` (with `first_name`, `last_name`).  
Optional objects: `contacts`, `address`, `employment`, `settings`.

#### Response 200

Full `UserResponse` (without `access_token`).

#### Error responses

| Status | Code | Trigger |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Missing required field or invalid format |
| 400 | `MISSING_USER_ID` | `:id` path param is empty (middleware check) |
| 401 | `MISSING_TOKEN` | No `Authorization` header |
| 401 | `INVALID_TOKEN_FORMAT` | Header not in `Bearer <token>` format |
| 401 | `INVALID_TOKEN` | Token does not match the user's stored token |
| 404 | `USER_NOT_FOUND` | User not found or invalid ObjectID |
| 500 | `INTERNAL_ERROR` | Database error |

---

### 12. PATCH /api/v1/users/patch/:id

**Auth:** Bearer token required

**Semantics:** Partial update — only the provided fields are updated; omitted fields remain unchanged.

#### Path parameters

Same as PUT.

#### Request body

All fields are optional. Only fields present in the JSON body are modified.

| Field | Type | Validation if provided |
|---|---|---|
| `email` | string | Valid email format |
| `username` | string | Min 3, max 30 characters |
| `profile` | object | Same sub-field validation as create |
| `contacts` | object | Same sub-field validation as create |
| `address` | object | — |
| `employment` | object | Same sub-field validation as create |
| `settings` | object | Same sub-field validation as create |

#### Response 200

Full `UserResponse` (without `access_token`).

#### Error responses

Same codes as [PUT /users/update/:id](#11-put-apiv1usersupdateid).

---

### 13. DELETE /api/v1/users/delete/:id

**Auth:** Bearer token required

#### Path parameters

| Param | Type | Notes |
|---|---|---|
| `id` | string | MongoDB ObjectID (24 hex characters) |

#### Response 204

Empty body. User permanently deleted.

#### Error responses

| Status | Code | Trigger |
|---|---|---|
| 400 | `MISSING_USER_ID` | `:id` path param is empty |
| 401 | `MISSING_TOKEN` | No `Authorization` header |
| 401 | `INVALID_TOKEN_FORMAT` | Header not in `Bearer <token>` format |
| 401 | `INVALID_TOKEN` | Token does not match the user |
| 404 | `USER_NOT_FOUND` | User not found or invalid ObjectID |
| 500 | `INTERNAL_ERROR` | Database error |

---

### 14. POST /api/v1/users/logout/:id

**Auth:** Bearer token required

#### Path parameters

| Param | Type | Notes |
|---|---|---|
| `id` | string | MongoDB ObjectID (24 hex characters) |

#### Request body

None.

#### Response 200

```json
{
  "success": true,
  "message": "Logged out successfully. Token has been revoked."
}
```

> After logout, the token is cleared in the database. Any subsequent request using that token returns `401 INVALID_TOKEN`.

#### Error responses

| Status | Code | Trigger |
|---|---|---|
| 400 | `MISSING_USER_ID` | `:id` path param is empty |
| 401 | `MISSING_TOKEN` | No `Authorization` header |
| 401 | `INVALID_TOKEN_FORMAT` | Header not in `Bearer <token>` format |
| 401 | `INVALID_TOKEN` | Token does not match the user |
| 500 | `INTERNAL_ERROR` | Database error revoking token |

---

### 15. POST /api/v1/mail/create

**Auth:** None (token-based access — see below)

#### Request body

Empty body `{}` is valid. All fields are optional.

```json
{
  "domain": "play-qa.com",
  "local_part": "mytestbox"
}
```

| Field | Type | Notes |
|---|---|---|
| `domain` | string | Optional. One of: `play-qa.com`, `mail.play-qa.com`, `temp.play-qa.com`, `inbox.play-qa.com`. Default: `play-qa.com`. |
| `local_part` | string | Optional. 3–30 chars, only lowercase `a-z`, `0-9`, `_`, `-`. If omitted, an 8-character random alphanumeric string is generated. |

#### Response 201

```json
{
  "id": "507f1f77bcf86cd799439011",
  "token": "550e8400-e29b-41d4-a716-446655440000",
  "email_address": "mytestbox@play-qa.com",
  "domain": "play-qa.com",
  "expires_at": "2024-01-01T12:15:00Z",
  "created_at": "2024-01-01T12:00:00Z"
}
```

> The `token` (UUID) is the access key for all subsequent `/mail/:token/*` operations. Mailbox TTL is **15 minutes** from creation.

#### Error responses

| Status | Code | Trigger |
|---|---|---|
| 400 | `INVALID_DOMAIN` | Domain provided but not in the allowed list |
| 400 | `INVALID_LOCAL_PART` | Custom `local_part` fails length or character check |
| 409 | `ADDRESS_TAKEN` | That email address already exists |
| 500 | `INTERNAL_ERROR` | Database error |

---

### 16. GET /api/v1/mail/:token

**Auth:** None (token in path is the access key)

#### Path parameters

| Param | Type | Notes |
|---|---|---|
| `token` | string | UUID returned by `POST /mail/create` |

#### Response 200

```json
{
  "id": "507f1f77bcf86cd799439011",
  "token": "550e8400-e29b-41d4-a716-446655440000",
  "email_address": "mytestbox@play-qa.com",
  "domain": "play-qa.com",
  "expires_at": "2024-01-01T12:15:00Z",
  "created_at": "2024-01-01T12:00:00Z"
}
```

#### Error responses

| Status | Code | Trigger |
|---|---|---|
| 404 | `MAILBOX_NOT_FOUND` | Token not found, mailbox expired, or deleted |
| 500 | `INTERNAL_ERROR` | Database error |

---

### 17. GET /api/v1/mail/:token/messages

**Auth:** None

#### Path parameters

| Param | Type | Notes |
|---|---|---|
| `token` | string | Mailbox UUID token |

#### Response 200

```json
{
  "messages": [
    {
      "id": "507f1f77bcf86cd799439012",
      "from": "sender@example.com",
      "subject": "Test Subject",
      "body_preview": "First 100 characters of the plain text body...",
      "received_at": "2024-01-01T12:05:00Z"
    }
  ],
  "count": 1
}
```

> List items include only `body_preview` (truncated to 100 characters). Full `body`, `html_body`, and `headers` are not included. Messages are sorted newest first.

#### Error responses

| Status | Code | Trigger |
|---|---|---|
| 404 | `MAILBOX_NOT_FOUND` | Token not found |
| 500 | `INTERNAL_ERROR` | Database error |

---

### 18. GET /api/v1/mail/:token/messages/:id

**Auth:** None

#### Path parameters

| Param | Type | Notes |
|---|---|---|
| `token` | string | Mailbox UUID token |
| `id` | string | Message ID (MongoDB ObjectID, 24 hex characters) |

#### Response 200

```json
{
  "id": "507f1f77bcf86cd799439012",
  "from": "sender@example.com",
  "subject": "Test Subject",
  "body_preview": "First 100 chars...",
  "body": "Full plain text body of the message.",
  "html_body": "<h1>HTML version of the body</h1>",
  "headers": {
    "Message-ID": "<abc@example.com>",
    "Reply-To": "reply@example.com",
    "CC": "cc@example.com",
    "X-Mailer": "MyMailer 1.0"
  },
  "received_at": "2024-01-01T12:05:00Z"
}
```

> Cross-mailbox access is blocked — a message ID that belongs to a different mailbox returns `404 MESSAGE_NOT_FOUND`.

#### Error responses

| Status | Code | Trigger |
|---|---|---|
| 404 | `MAILBOX_NOT_FOUND` | Token not found |
| 404 | `MESSAGE_NOT_FOUND` | Message ID not found or belongs to a different mailbox |
| 500 | `INTERNAL_ERROR` | Database error |

---

### 19. POST /api/v1/mail/:token/send

**Auth:** None

#### Path parameters

| Param | Type | Notes |
|---|---|---|
| `token` | string | Mailbox UUID token |

#### Request body

```json
{
  "from": "sender@example.com",
  "subject": "Hello",
  "body": "Plain text body of the message.",
  "html_body": "<p>HTML version of the body.</p>"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `from` | string | Yes | Sender address (not validated as email) |
| `subject` | string | Yes | — |
| `body` | string | Yes | Plain text content |
| `html_body` | string | No | HTML content |

#### Response 201

Full message object (same shape as [GET /mail/:token/messages/:id](#18-get-apiv1mailtokenmessagesid)).

#### Error responses

| Status | Code | Trigger |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Missing `from`, `subject`, or `body` |
| 404 | `MAILBOX_NOT_FOUND` | Token not found |
| 500 | `INTERNAL_ERROR` | Database write error |

---

### 20. DELETE /api/v1/mail/:token

**Auth:** None

#### Path parameters

| Param | Type | Notes |
|---|---|---|
| `token` | string | Mailbox UUID token |

#### Response 204

Empty body. Mailbox and all its messages permanently deleted.

#### Error responses

| Status | Code | Trigger |
|---|---|---|
| 404 | `MAILBOX_NOT_FOUND` | Token not found |
| 500 | `INTERNAL_ERROR` | Database error |

---

## All Error Codes Reference

| Code | HTTP Status | Description |
|---|---|---|
| `VALIDATION_ERROR` | 400 | Request body failed validation (missing required field, invalid format, bad enum value, etc.) |
| `MISSING_USER_ID` | 400 | `:id` path parameter is empty (checked by BearerAuth middleware) |
| `INVALID_PAGINATION` | 400 | *(observed, undocumented)* `page`/`per_page` not a positive integer on `GET /users/list` |
| `MISSING_TOKEN` | 401 | `Authorization` header is absent |
| `INVALID_TOKEN_FORMAT` | 401 | `Authorization` header present but not in `Bearer <token>` format |
| `INVALID_TOKEN` | 401 | Token does not match the user's stored token or has been revoked |
| `INVALID_CREDENTIALS` | 401 | Wrong email or password on login |
| `USER_NOT_FOUND` | 404 | No user found for the given ID, or ID is not a valid ObjectID |
| `MAILBOX_NOT_FOUND` | 404 | No mailbox found for the given token (expired, deleted, or never existed) |
| `MESSAGE_NOT_FOUND` | 404 | No message found for the given ID in this mailbox |
| `DUPLICATE_USER` | 409 | Email or username already registered |
| `ADDRESS_TAKEN` | 409 | Requested mailbox email address already in use |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests (global, login, or create-user limiter) |
| `DATABASE_LIMIT_REACHED` | 503 | Maximum user count (1,000,000) reached |
| `INTERNAL_ERROR` | 500 | Unexpected server-side error (database failure, etc.) |
