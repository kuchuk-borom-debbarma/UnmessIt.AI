# Docker Networking

This app runs two containers in the default Docker Compose setup:

- `web`: nginx serving the built React app.
- `server`: FastAPI on port `2317`.

Both services publish ports on `0.0.0.0`, so the host machine and other devices on the LAN can reach them if the host firewall allows it:

```txt
http://<host-ip>:2831  # web app
http://<host-ip>:2317  # API
```

## Web to API

The Docker web image uses same-origin API calls by default. Browser requests go to the nginx container first:

```txt
browser
-> http://<host-ip>:2831/api/...
-> web nginx
-> http://server:2317/api/...
```

This avoids baking `localhost:2317` into the frontend. A remote browser would treat `localhost` as the remote user's own machine, not the machine running Docker.

For custom deployments, `VITE_API_BASE_URL` can still override this behavior at build time.

## Server to Host-Local AI Providers

Local AI tools such as LM Studio often listen on the host at:

```txt
http://127.0.0.1:1234/v1
```

Inside Docker, `127.0.0.1` means the container itself, not the host. To reach the host from the `server` container, the app uses:

```txt
http://host.docker.internal:1234/v1
```

Compose adds this host mapping:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

The server also sets:

```txt
UNMESSIT_DOCKER=1
```

When that flag is set, runtime settings rewrite loopback AI base URLs:

```txt
http://127.0.0.1:1234/v1 -> http://host.docker.internal:1234/v1
http://localhost:1234/v1 -> http://host.docker.internal:1234/v1
http://[::1]:1234/v1     -> http://host.docker.internal:1234/v1
```

External provider URLs are left unchanged, for example:

```txt
https://integrate.api.nvidia.com/v1
https://api.openai.com/v1
```

This means rotation lanes can keep the familiar LM Studio URL from the Settings UI. Docker deployments make it reachable at runtime.

## LM Studio Checklist

1. Start LM Studio's OpenAI-compatible server.
2. If LM Studio offers a bind-host setting, use `0.0.0.0` so Docker can connect.
3. In UnmessIt Settings, use:

```txt
http://127.0.0.1:1234/v1
```

or directly:

```txt
http://host.docker.internal:1234/v1
```

4. Use a model name exactly as LM Studio exposes it.
5. Resume or recreate failed ingest jobs after changing processing settings or rotation lanes.

## Troubleshooting

If ingest jobs fail with `Connection error` during embeddings:

- Confirm the embedding base URL points to the LM Studio server.
- Confirm LM Studio is running and serving embeddings for the configured processing embedding model.
- From Docker, loopback URLs must resolve through `host.docker.internal`; this happens automatically only when `UNMESSIT_DOCKER=1`.
- If running the server outside Docker, use normal host loopback URLs such as `http://127.0.0.1:1234/v1`.

If the app works on the Docker host but not from another device:

- Open `http://<host-ip>:2831`, not `localhost`.
- Confirm the host firewall allows `WEB_PORT` and optionally `SERVER_PORT`.
- Prefer using the web app port; nginx proxies API calls to the server container.
