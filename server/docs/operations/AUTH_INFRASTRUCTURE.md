# Auth Infrastructure

Auth is local and JWT-based.

## Flow

- `POST /api/auth/signup` creates a SQLite user and returns a token.
- `POST /api/auth/signin` verifies credentials and returns a token.
- `GET /api/auth/me` verifies the bearer token.
- `POST /api/auth/logout` is a no-op acknowledgement; the client forgets the token.

## Storage

Passwords are hashed before storage. Sessions are not stored in SQLite.

JWT payloads contain:

- `sub`: user id
- `exp`: expiry

The token is signed with the configured server secret and sent in the `Authorization` header.

## Boundary

Routes use `src/routes/auth_utils.py` for current-user lookup. Product data routes must require a user id and pass it to repositories or services so users stay isolated.
