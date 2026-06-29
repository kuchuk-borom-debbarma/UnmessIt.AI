# Beta Deploy Notes

For a hosted beta, set these server runtime variables:

- `JWT_SECRET`: HMAC secret for local JWT auth. Use a long random value.
- `CORS_ORIGINS`: comma-separated allowed frontend origins, for example `https://beta.example.com`.
- `ENABLE_DEV_ROUTES=0`: disables `/dev/*` inspection and wipe routes.

AI provider, model, embedding, and API key settings are configured per user in the app Settings screen. Do not put those values in server runtime config.

Keep `/api/advanced/*` protected by bearer auth; it exposes user-scoped memory, recall, raw source inspection, and indexing job controls for the beta UI.
