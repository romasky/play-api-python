# play-qa-api — API Reference

**Base path:** `/api/v1`  
**Production URLs:**
- `https://play-qa.com/api/v1`

**Swagger UI:** `/swagger/index.html`

> **Test coverage (2026-10-26):** every operation of the Swagger spec (snapshot `docs/openapi.json`, 79 operations)
> is called by at least one scenario — `tools/spec_coverage.py`. Part 1 below is the original user / mail API;
> [Part 2](#part-2--domains-added-in-2026) summarises the domains added since, with the live-verified error codes.

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
6. [Part 2 — domains added in 2026](#part-2--domains-added-in-2026)
7. [All Error Codes Reference](#all-error-codes-reference)

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
| 4 | Token unknown, revoked or expired | 401 `INVALID_TOKEN` — "Token does not match user or has expired" |
| 5 | Token is valid but belongs to a **different** user | 403 `FORBIDDEN` — "You can only modify your own account" (since 2026-10-23, "Feature 17": 401 = credential not accepted, 403 = accepted but not permitted) |

A token is invalidated (revoked to empty string in DB) on logout. Any subsequent request with a revoked token returns `401 INVALID_TOKEN`.

---

## Rate Limiting

| Limiter | Scope | Rate | Burst | 429 Message |
|> Per-endpoint buckets for the endpoints added since (create-admin and challenge start share the create-user
> bucket; JWT, uploads, inboxes, store login, bug reports have their own; `TOO_MANY_INBOXES` is a second 429 code):
> see [Part 2 — Rate limits](#rate-limits-per-ip-token-buckets-no-retry-after--x-ratelimit--on-any-429).

---|---|---|---|---|
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
| 400 | `{"success":false,"error":"Invalid request body"}` | `token` missing, empty, not a string, or a non-JSON body (live 2026-10; earlier docs said "Token is required") |
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

**Auth:** optional — see [Optional authentication on reads](#optional-authentication-on-reads-feature-17)  
**Response headers:** `X-Total-Count` (= `total`), `Link` (RFC 8288, relative URLs: `first`, `prev`, `next`, `last`; every
link keeps sort/filter/search and rewrites `per_page` to `limit`), `Cache-Control: no-store, …`. Not set on 4xx.

#### Query parameters

Defaults apply only when a parameter is ABSENT — a present-but-empty value (`sort=`, `limit=` …) is a 400.
Validation order (first error wins): page → limit → per_page → sort → filter → search.

| Param | Default | Rule |
|---|---|---|
| `page` | `1` | 1–1 000 000; beyond the last page → 200 with `users: []` |
| `limit` | `10` | ≥ 1, above 100 clamped to 100 |
| `per_page` | — | legacy alias of `limit` (limit wins, but per_page is still validated) |
| `sort` | `created_at:desc` | `field[:asc\|desc]`, case-sensitive; fields `created_at, updated_at, login_count, last_login_at, username, email`; binary string order |
| `filter` | — | `field:value`, repeatable, AND across fields, max 10, the same field twice rejected; `role` (user/admin/moderator), `is_active`/`is_verified`/`is_premium` (`true`/`false`), `employment.status`, `settings.theme`, `settings.language` (2 letters, lower-cased first), `address.country` (exact, 1–64) |
| `search` | — | 1–64 chars after trimming; case-insensitive substring of username, email, first and last name; regex metacharacters are literal |

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
  "total": 412,
  "total_pages": 42
}
```

> `access_token` is not included in list items. The collection is shared with every client: `total` changes between
> calls — assert exact counts only inside a filter that isolates your own users (a unique `address.country`).

#### Error responses

| Status | Code | Trigger |
|---|---|---|
| 400 | `INVALID_PAGINATION` | `page` / `limit` / `per_page` empty, non-integer, ≤ 0, or `page` > 1 000 000 |
| 400 | `INVALID_SORT_FIELD` | empty `sort`, unknown or non-sortable field (`password`, `Username`, `metadata.created_at`) |
| 400 | `INVALID_SORT_DIR` | direction other than `asc`/`desc` (`username:`, `username:ASC`, `username:asc:x`) |
| 400 | `TOO_MANY_FILTERS` | more than 10 `filter` entries |
| 400 | `INVALID_FILTER_FIELD` | not `field:value`, or a field outside the whitelist |
| 400 | `DUPLICATE_FILTER_FIELD` | the same field twice |
| 400 | `INVALID_FILTER_VALUE` | a value outside the field's allowed set (`role:root`, `is_active:1`, country > 64 chars) |
| 400 | `INVALID_SEARCH` | empty, whitespace-only or > 64 chars |
| 401 | `INVALID_TOKEN_FORMAT` / `INVALID_TOKEN` | a PRESENT bad Authorization header (checked before the parameters) |
| 500 | `INTERNAL_ERROR` | Database query failure |

---

### 7. GET /api/v1/users/get/:id

**Auth:** optional — see [Optional authentication on reads](#optional-authentication-on-reads-feature-17)

#### Path parameters

| Param | Type | Notes |
|---|---|---|
| `id` | string | MongoDB ObjectID (24 hex characters) |

#### Response 200

Full `UserResponse` object (same shape as a list item, without `access_token`).

#### Error responses

| Status | Code | Trigger |
|---|---|---|
| 401 | `INVALID_TOKEN_FORMAT` / `INVALID_TOKEN` | a PRESENT bad Authorization header (checked before the id) |
| 404 | `USER_NOT_FOUND` | Invalid ObjectID format or user not found |
| 500 | `INTERNAL_ERROR` | Database error |

#### Optional authentication on reads (Feature 17)

`GET /users/get/:id` and `GET /users/list` stay public, but a present `Authorization` header must be valid:

| Authorization | Result |
|---|---|
| absent, or an empty value | 200 (anonymous) |
| `Bearer`, `Basic …`, no prefix, lowercase `bearer`, extra parts | 401 `INVALID_TOKEN_FORMAT` |
| `Bearer <unknown / revoked / superseded token>` | 401 `INVALID_TOKEN` |
| the owner's valid token | 200 **plus `metadata.last_login_ip`** (once the user has logged in) |
| another user's or an admin's valid token | 200 without `last_login_ip` — reads never answer 403 |

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
| 403 | `FORBIDDEN` | Valid token of a different user |
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
| 403 | `FORBIDDEN` | Valid token of a different user |
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
| 403 | `FORBIDDEN` | Valid token of a different user |
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

## Part 2 — domains added in 2026

Verified live 2026-10-26 against `https://play-qa.com/api/v1`; the Swagger snapshot is `docs/openapi.json`.
Only behaviour that matters for tests is listed — request/response shapes are in the spec and in the
pydantic contracts (`src/play_api/models/responses/`). "not in spec" marks a live finding the spec does not state.

### Rate limits (per IP, token buckets; no `Retry-After` / `X-RateLimit-*` on any 429)

| Bucket | Endpoints | Refill / burst |
|---|---|---|
| create-user | `POST /users/create`, `/users/create-admin`, `/challenges/{id}/start` (creates a sandbox) | 1 / 600 ms, 100 |
| login | `POST /login` | 1 / 12 s, 5 |
| jwt-login | `POST /jwt/login` — every call counts, 400s included | 1 / 12 s, 5 |
| jwt-decode | `POST /jwt/decode` | 1 / 2 s, 10 |
| upload / inbox | `POST /files/upload`, `POST /webhooks/inbox` | 10 / min, 5 |
| store / bug report | `POST /store/login`, `POST /bug-reports` (400s count) | 30 / min, 10 |
| global | everything | 10 / s, 20 |

### Admin — `POST /users/create-admin`, `/admin/*`

| Case | Status | Code |
|---|---|---|
| create-admin: body invalid (checked first) | 400 | `VALIDATION_ERROR` |
| create-admin: seed wrong, absent or empty (same answer — not an oracle); seed `play-qa-admin` is published in the UI | 403 | `INVALID_SEED_CODE` (not in spec) |
| create-admin: duplicate email with a valid seed (seed checked before uniqueness) | 409 | `DUPLICATE_USER` |
| `/admin/*` with a valid non-admin token (checked before scope and body) | 403 | `ADMIN_REQUIRED` (not in spec) |
| role / delete on ANY id but your own — foreign, non-existent or malformed (the 404 is unreachable) | 403 | `FORBIDDEN` |
| role body not `{"role":"user"\|"admin"}` | 400 | `VALIDATION_ERROR` |

`/admin/users` accepts `limit` (not in spec), validates like `/users/list` and sends no `X-Total-Count` / `Link`;
rows add `has_active_token` and never carry `access_token` or `last_login_ip`. Self-demotion is irreversible.
`/users/create` silently ignores `role` / `metadata.role` (always role `user`).

### JWT — `/jwt/login`, `/jwt/me`, `/jwt/refresh`, `/jwt/decode`

| Case | Status | Code |
|---|---|---|
| login: missing/invalid email, missing password, `access_ttl_seconds` outside 1–900 or not an integer | 400 | `VALIDATION_ERROR` |
| login: wrong password or unknown email (no password min length here) | 401 | `INVALID_CREDENTIALS` |
| any JWT endpoint: body > 16 KiB | 413 | `PAYLOAD_TOO_LARGE` |
| me: no header / malformed header / non-JWT value / token > 8 KiB | 401 | `MISSING_TOKEN` / `INVALID_TOKEN_FORMAT` |
| me, refresh: wrong secret, tampered payload, `alg: none`, `alg: HS512` (signature checked before expiry) | 401 | `INVALID_SIGNATURE` |
| me, refresh: genuine but expired (expiry checked before type) | 401 | `TOKEN_EXPIRED` |
| me with a refresh token / refresh with an access token | 401 | `WRONG_TOKEN_TYPE` |
| refresh: no / empty `refresh_token` in the BODY (the Authorization header is ignored) | 400 | `VALIDATION_ERROR` |
| decode: not a JWT (1/2/4 segments, padding, bad base64, non-JSON payload, > 8 KiB) | 400 | `INVALID_JWT_FORMAT` |

Access tokens live 900 s (or the requested TTL), refresh tokens 86 400 s; **the refresh token is reusable** and every
refreshed access token gets 900 s. A JWT login does not rotate the opaque token; the two schemes never mix
(a JWT on `/users/get` → 401 `INVALID_TOKEN`). decode always returns `signature_valid`, `expired`, `expires_at`,
`issued_at` — `null`, never missing.

### Store — `POST /store/login` (SauceDemo personas, password `secret_sauce`)

`standard_user`, `problem_user` (`visual_bugs`), `flaky_user` (`flaky_add_to_cart`), `performance_glitch_user`
(≈ 3 s server delay) → 200. `locked_out_user` → 403 `USER_LOCKED_OUT` — but only with the right password: the lock
is checked after it (wrong password → 401 `INVALID_CREDENTIALS`). Credentials are case- and whitespace-sensitive;
username ≤ 64, password ≤ 128, both required → 400 `VALIDATION_ERROR`.

### Files — `/files/*`

| Case | Status | Code |
|---|---|---|
| not multipart | 400 | `INVALID_MULTIPART` |
| no `file` part (or another field name) | 400 | `NO_FILE` |
| 0-byte file / description > 200 | 400 | `EMPTY_FILE` / `VALIDATION_ERROR` |
| extension outside .png .jpg .jpeg .pdf .txt .csv .json, or extension-less binary | 415 | `UNSUPPORTED_MEDIA_TYPE` |
| content does not match the extension (text in a .png) | 422 | `CORRUPTED_FILE` |
| part > 5 MiB (5 242 880 inclusive is fine) or whole body > 5 MiB + 64 KiB | 413 | `FILE_TOO_LARGE` |
| upload/delete with a present bad header (never a silent anonymous upload) | 401 | `INVALID_TOKEN` / `INVALID_TOKEN_FORMAT` |
| my files: no token / page outside 1–1000 / per_page outside 1–50 | 401 / 400 | `MISSING_TOKEN` / `VALIDATION_ERROR` |
| download `inline` other than `true`/`false` | 400 | `VALIDATION_ERROR` |
| unknown id; another user's file deleted by anyone else or with no token | 404 | `FILE_NOT_FOUND` |

`content_type` is sniffed, `declared_type` echoes the part. Metadata and download are public and ignore a bad
token; download is byte-exact with `Content-Disposition` (ASCII fallback + RFC 5987 `filename*`), `nosniff` and a
sandbox CSP, and has no checksum header. Anonymous files can be deleted by anyone. HEAD on a download → 404.

### Webhooks — `/webhooks/*`

Private `token` (read / delete) and public `ingest_token` (capture only) are not interchangeable (404 `WEBHOOK_NOT_FOUND`).
Capture: GET/POST/PUT/PATCH/DELETE → 202 `{received, event_id}`; HEAD → 202, empty body, `X-PlayQA-Event-Id`;
OPTIONS → 204, not captured. Body ≤ 64 KiB (65 537 → 413 `PAYLOAD_TOO_LARGE`, nothing stored); repeated headers and
query keys kept; `Authorization` / `Cookie` masked `***`; binary bodies base64. Signature `t=<unix>,v1=<hmac-sha256>`
→ `signature_valid` true / false (wrong HMAC, tampered, timestamp outside ±300 s — not in spec) / null (absent or
empty header); it never blocks a capture. Events: `page` invalid → 400 `VALIDATION_ERROR`, `per_page` invalid →
silently 20, > 100 clamped; unknown or foreign event → 404 `EVENT_NOT_FOUND`. Inboxes live 2 h, 20 active per IP
(429 `TOO_MANY_INBOXES`; the creation rate limit is 429 `RATE_LIMIT_EXCEEDED`). No `success` key on any 2xx.

### SMTP response simulator — `POST /mail/{token}/send-to`

Always 200. 34 magic local parts (`mailbox-full` 552 5.2.2 … `server-shutdown` 421 4.3.2, full table in
`features/play_qa_api/MailSendToTests.feature`) answer `accepted:false` with `smtp_code`, `enhanced_status`, `category`,
`message` and no `message_id`; they match case-insensitively on ANY domain or none (not in spec), sub-addressing
breaks the match. Any other recipient → `accepted:true`, 250, `message_id`; the message is stored in the SENDER's
mailbox and never delivered. `to` missing/empty/not a string → 400 `VALIDATION_ERROR` (checked before the mailbox:
unknown token → 404 `MAILBOX_NOT_FOUND`). `POST /mail/create` with a magic local part → 409 `RESERVED_LOCAL_PART`.

### Bug reports — `/bug-reports` (scored against `/buggy`)

Score out of 100: has_steps 25 (≥ 2 steps) · steps_reproducible 20 (a step names the bug's method + path, method
case-insensitive) · expected_actual 25 (both ≥ 10 chars, different) · severity_reasonable 15 (pagination-off-by-one
low/medium, cart-total-wrong high/critical, timezone-shift medium/high) · title_quality 15 (≥ 12 chars). Anonymous →
200 not saved; with a token → 201 saved 24 h. Unknown `bug_id` → 404 `UNKNOWN_BUG_ID`; field violations → 400
`VALIDATION_ERROR` (messages are cosmetically garbled — assert codes); > 64 KiB → 413; a present bad token → 401 before
validation; another user's report → 404 `REPORT_NOT_FOUND`.

### Buggy API — `/buggy/*` (intentional, permanent bugs)

`GET /buggy/items`: a FULL page drops its last item (page 1 / 10 → ids 1–9). `POST /buggy/cart/total`: the total
ignores the last position (`[10×2, 5×3]` → 20.00). `GET /buggy/schedule`: 09:00 is built in UTC (`event_start_utc`
always `<date>T09:00:00Z`, `event_start` shifted by the zone offset; invisible in UTC). All validation → 400 `VALIDATION_ERROR`.

### Chaos — `/chaos/*`

| Endpoint | Behaviour | Errors (400 unless noted) |
|---|---|---|
| `cache` | ETag `"chaos-v1"`, weak/list/`*` If-None-Match → 304; INM beats IMS | — |
| `delay/{s}` | float seconds, max 9 (clamped) | `INVALID_DELAY` |
| `timeout?after=` | holds, then 504 — **Cloudflare page, not the documented JSON** (not in spec) | `INVALID_TIMEOUT` (empty `after=` too) |
| `echo` | parsed `body` for JSON, `raw_body` text, base64 for binary, masks secrets, truncates > 64 KiB | 413 `PAYLOAD_TOO_LARGE` > 1 MiB |
| `flaky` / `sequence` / `step/{i}` | roll depends only on the seed; the flaky body comes on every status | `INVALID_SEED`, `SEED_REQUIRED`, `INVALID_FAIL_RATE`, `INVALID_FAIL_STATUS`, `INVALID_COUNT`, `INVALID_INDEX` (index before seed) |
| `gzip` | encoding follows Accept-Encoding (spec: always gzip) | — |
| `redirect/{n}` | status = `type` 301/302/307/308 (spec: 302), relative Location; `/done` always `redirected:true` | `INVALID_REDIRECT_COUNT`, `TOO_MANY_REDIRECTS` (> 10), `INVALID_REDIRECT_TYPE` |
| `status/{code}` | 200–599, `{status_code, message}`; 204/205/304 bodyless; 502/504/52x replaced by Cloudflare | `INVALID_STATUS_CODE` |

### Challenges — `/challenges/*`

Four challenges (delete-user-404 10, patch-first-name 10, logout-revokes-token 20, login-rotates-token 20).
Auth before id. `start` → 201 with a sandbox user and its token; a repeat → 200 without the token; a deleted
sandbox → 200 `target_missing` + `can_reset` (only then); `reset` accepts only `true`/`false`. `verify` before start, or
with an unknown / malformed `attempt_id` → 409 `NO_OPEN_ATTEMPT`; unknown params → 400. Hints in order (409
`HINT_LEVEL_OUT_OF_ORDER`), idempotent, never cost points. Unknown id → 404 `CHALLENGE_NOT_FOUND`.

### Documents, streaming, misc

`/openapi.json`, `/openapi.yaml`, `/postman/collection.json` (19 variables; spec lists 7), `/postman/environment.json`:
attachments by default, inline with `?download=false`. `GET /sse/progress`: `steps` 5–100, `interval_ms` 100–2000
(bounds not in spec) → `event: progress` × steps, then `event: done`. `GET /ws/echo`: welcome frame, text and binary
echo; a plain GET → 426 `UPGRADE_REQUIRED`; messages > 32 KiB close with 1009 (not in spec). Unrouted methods →
`404 text/plain "404 page not found"`, never 405 (HEAD `/health` included).

---

## All Error Codes Reference

| Code | HTTP Status | Description |
|---|---|---|
| `VALIDATION_ERROR` | 400 | Request body failed validation (missing required field, invalid format, bad enum value, etc.) |
| `MISSING_USER_ID` | 400 | `:id` path parameter is empty (checked by BearerAuth middleware) |
| `INVALID_PAGINATION` | 400 | `page`/`limit`/`per_page` invalid on `GET /users/list`, `/admin/users` |
| `INVALID_SORT_FIELD` / `INVALID_SORT_DIR` | 400 | `sort` field / direction not allowed (users and admin lists) |
| `TOO_MANY_FILTERS` / `INVALID_FILTER_FIELD` / `DUPLICATE_FILTER_FIELD` / `INVALID_FILTER_VALUE` | 400 | `filter` violations (users and admin lists) |
| `INVALID_SEARCH` | 400 | `search` empty, blank or > 64 chars |
| `INVALID_MULTIPART` / `NO_FILE` / `EMPTY_FILE` | 400 | file upload body problems |
| `INVALID_JWT_FORMAT` | 400 | `/jwt/decode`: the value is not a JWT |
| `INVALID_DELAY` / `INVALID_TIMEOUT` / `INVALID_SEED` / `SEED_REQUIRED` / `INVALID_FAIL_RATE` / `INVALID_FAIL_STATUS` / `INVALID_COUNT` / `INVALID_INDEX` / `INVALID_REDIRECT_COUNT` / `TOO_MANY_REDIRECTS` / `INVALID_REDIRECT_TYPE` / `INVALID_STATUS_CODE` | 400 | `/chaos/*` parameter validation |
| `INVALID_SIGNATURE` / `TOKEN_EXPIRED` / `WRONG_TOKEN_TYPE` | 401 | JWT checks (signature → expiry → type) |
| `ADMIN_REQUIRED` | 403 | valid token without the admin role on `/admin/*` |
| `INVALID_SEED_CODE` | 403 | `POST /users/create-admin` with a wrong / absent seed |
| `USER_LOCKED_OUT` | 403 | `POST /store/login` as `locked_out_user` (right password) |
| `FILE_NOT_FOUND` / `WEBHOOK_NOT_FOUND` / `EVENT_NOT_FOUND` / `REPORT_NOT_FOUND` / `UNKNOWN_BUG_ID` / `CHALLENGE_NOT_FOUND` | 404 | unknown (or not yours) |
| `NO_OPEN_ATTEMPT` / `HINT_LEVEL_OUT_OF_ORDER` / `RESERVED_LOCAL_PART` | 409 | challenge attempt / hint order / magic mailbox name |
| `PAYLOAD_TOO_LARGE` / `FILE_TOO_LARGE` | 413 | body over the endpoint's limit |
| `UNSUPPORTED_MEDIA_TYPE` | 415 | upload extension or sniffed type not accepted |
| `CORRUPTED_FILE` | 422 | upload content does not match its extension |
| `UPGRADE_REQUIRED` | 426 | `/ws/echo` without a WebSocket handshake |
| `TOO_MANY_INBOXES` | 429 | 20 active webhook inboxes per IP |
| `MISSING_TOKEN` | 401 | `Authorization` header is absent |
| `INVALID_TOKEN_FORMAT` | 401 | `Authorization` header present but not in `Bearer <token>` format |
| `INVALID_TOKEN` | 401 | Token does not match the user's stored token or has been revoked |
| `FORBIDDEN` | 403 | Valid token, but not for this account: another user on PUT/PATCH/DELETE/logout, or an admin on a foreign id |
| `INVALID_CREDENTIALS` | 401 | Wrong email or password on login |
| `USER_NOT_FOUND` | 404 | No user found for the given ID, or ID is not a valid ObjectID |
| `MAILBOX_NOT_FOUND` | 404 | No mailbox found for the given token (expired, deleted, or never existed) |
| `MESSAGE_NOT_FOUND` | 404 | No message found for the given ID in this mailbox |
| `DUPLICATE_USER` | 409 | Email or username already registered |
| `ADDRESS_TAKEN` | 409 | Requested mailbox email address already in use |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests (global, login, or create-user limiter) |
| `DATABASE_LIMIT_REACHED` | 503 | Maximum user count (1,000,000) reached |
| `INTERNAL_ERROR` | 500 | Unexpected server-side error (database failure, etc.) |
