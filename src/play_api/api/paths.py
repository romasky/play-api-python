"""Single source of truth for every endpoint path (port of src/api/apiPaths.js)."""

BASE = "/api/v1"

HEALTH = f"{BASE}/health"
LOGIN = f"{BASE}/login"
AUTH_BASIC = f"{BASE}/auth/basic"
USERS_CREATE = f"{BASE}/users/create"
USERS_CREATE_ADMIN = f"{BASE}/users/create-admin"
USERS_LIST = f"{BASE}/users/list"
USERS_OPTIONS = f"{BASE}/users/options"
MAIL_CREATE = f"{BASE}/mail/create"
JWT_LOGIN = f"{BASE}/jwt/login"
JWT_ME = f"{BASE}/jwt/me"
JWT_REFRESH = f"{BASE}/jwt/refresh"
JWT_DECODE = f"{BASE}/jwt/decode"
STORE_LOGIN = f"{BASE}/store/login"
FILES = f"{BASE}/files"
FILES_UPLOAD = f"{BASE}/files/upload"
WEBHOOKS_INBOX = f"{BASE}/webhooks/inbox"
ADMIN_STATS = f"{BASE}/admin/stats"
ADMIN_USERS = f"{BASE}/admin/users"


def file(file_id: str) -> str:
    return f"{BASE}/files/{file_id}"


def file_download(file_id: str) -> str:
    return f"{BASE}/files/{file_id}/download"


def webhook(token: str) -> str:
    return f"{BASE}/webhooks/{token}"


def webhook_events(token: str) -> str:
    return f"{BASE}/webhooks/{token}/events"


def webhook_event(token: str, event_id: str) -> str:
    return f"{BASE}/webhooks/{token}/events/{event_id}"


def webhook_ingest(ingest_token: str) -> str:
    return f"{BASE}/webhooks/in/{ingest_token}"


def admin_user(user_id: str) -> str:
    return f"{BASE}/admin/users/{user_id}"


def admin_user_role(user_id: str) -> str:
    return f"{BASE}/admin/users/{user_id}/role"


def users_get(user_id: str) -> str:
    return f"{BASE}/users/get/{user_id}"


def users_exists(user_id: str) -> str:
    return f"{BASE}/users/exists/{user_id}"


def users_update(user_id: str) -> str:
    return f"{BASE}/users/update/{user_id}"


def users_patch(user_id: str) -> str:
    return f"{BASE}/users/patch/{user_id}"


def users_delete(user_id: str) -> str:
    return f"{BASE}/users/delete/{user_id}"


def users_logout(user_id: str) -> str:
    return f"{BASE}/users/logout/{user_id}"


def mail_get(token: str) -> str:
    return f"{BASE}/mail/{token}"


def mail_messages(token: str) -> str:
    return f"{BASE}/mail/{token}/messages"


def mail_message(token: str, message_id: str) -> str:
    return f"{BASE}/mail/{token}/messages/{message_id}"


def mail_send(token: str) -> str:
    return f"{BASE}/mail/{token}/send"
