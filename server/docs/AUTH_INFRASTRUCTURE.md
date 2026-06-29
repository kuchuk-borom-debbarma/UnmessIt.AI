# Auth Infrastructure

This document outlines the authentication and notification architecture for UnmessIt.AI. 
Per `@server/docs/rules/codebase_rules.md`, this architecture follows strict protocol decoupling, enabling future cloud functionality without cluttering the local, single-tenant experience.

## The State Machine API Pattern

The `AuthService` interface exposes only two surface methods:
- `sign_up(payload: dict) -> dict`
- `sign_in(payload: dict) -> dict`

Rather than exposing distinct methods for `verify_otp`, `resend_link`, or `check_status`, all authentication flows are modelled as state machines handled internally by the implementation. The client iteratively posts to the same route, passing whatever state (like an `otp` code) it has. 

### Implementations

1. **`LocalAuthService`** (Current default)
   - Follows a simple 1-pass flow.
   - `sign_up` accepts `{"username", "password"}`, hashes the password, creates the SQLite user, and immediately yields a JWT token.
2. **`CloudOtpAuthService`** (Future)
   - Follows a multi-pass flow.
   - Pass 1: `sign_up({"email"})` -> Issues a notification and returns `{"status": "requires_otp"}`.
   - Pass 2: `sign_up({"email", "otp"})` -> Verifies the code and returns `{"status": "success", "token": "..."}`.
3. **`CloudMagicLinkAuthService`** (Future)
   - `sign_in({"email"})` -> Issues a notification with a magic link and returns `{"status": "check_email"}`.

## Event Bus and Notifications

To prevent the Auth layer from tightly coupling to email clients (like SendGrid or AWS SES), we introduced the `MemoryEventBus`.

When a cloud auth service needs to send an OTP or Magic Link, it does not call a Notification service. Instead, it publishes an event:
```python
get_event_bus().publish("notification.send", {
    "recipient": email,
    "subject": "Your Code",
    "message": "123456"
})
```

The `NotificationService` acts purely as an event listener. It subscribes to `notification.send` on startup. 
Currently, the `ConsoleNotificationService` listens to this event and simply logs the notification to the terminal. In the future, a `SendGridNotificationService` can simply replace it.

## Stateless Sessions (JWT)

We use `PyJWT` for fully stateless authentication. There is no `sessions` table in the database.
When a user authenticates, the server signs a JWT payload (containing `sub` and `exp`) with an HMAC secret. The client stores this token and passes it in the `Authorization` header for subsequent requests.
