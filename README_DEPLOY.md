# Deploying this fork on the Docker / Dokploy Hermes host

Single-user deployment notes for Hermes Agent v0.23.0 (upstream `2bd378ed`, Python 3.14.9) running under Dokploy.

## Layout

| Thing | Value |
|---|---|
| Container | `hermes-hj3z0j-hermes-1` (Dokploy compose `hermes-hj3z0j`, compose id `isMqqFsLKYj74Zvi5t5cx`, service `hermes`) |
| Persistent volume | `hermes-hj3z0j_hermes_data` → `/opt/data` (`HERMES_HOME`). Everything else is wiped on redeploy. |
| Plugin | `/opt/data/plugins/linear-agent` (git checkout pinned by `--ref`) |
| Plugin deps | `/opt/data/installs/…` (Hermes package manager) |
| Token state | `/opt/data/plugin-state/linear-agent/oauth.json` (mode 0600) |
| Listener | `0.0.0.0:8651/hermes/linear-agent` inside the container; not published on the host |
| Ingress | Cloudflare tunnel (`dokploy-cloudflared`, remote-managed) → `http://dokploy-traefik:80` → Dokploy Domain `hermes.nath.tw` + path `/hermes/linear-agent` → container port 8651 over `dokploy-network` |
| Cloudflare Access | Self-hosted app "Hermes Agent (Linear webhook)" on `hermes.nath.tw/hermes/linear-agent` with the reusable **Bypass** policy (same as `/line`) |
| Linear webhook URL | `https://hermes.nath.tw/hermes/linear-agent` (Agent session events only) |

Run every Hermes command as the `hermes` user:

```sh
docker exec -u hermes hermes-hj3z0j-hermes-1 hermes …
```

Restart only the gateway service (interrupts Telegram/LINE for a few seconds):

```sh
docker exec -u hermes hermes-hj3z0j-hermes-1 /command/s6-svc -r /run/hermes-service/gateway-default
```

## Environment (`/opt/data/.env`, mode 600; Dokploy defines no Linear vars)

| Key | Notes |
|---|---|
| `LINEAR_AGENT_CLIENT_ID` | secret-ish; OAuth app client id |
| `LINEAR_AGENT_CLIENT_SECRET` | secret |
| `LINEAR_AGENT_WEBHOOK_SECRET` | secret; webhook signing secret |
| `LINEAR_AGENT_ALLOWED_USERS` | your Linear user id only |
| `LINEAR_AGENT_WORKSPACE_ID` | pinned workspace id |
| `LINEAR_AGENT_APP_USER_ID` | the app's own user id (self-echo filter) |

Never set `LINEAR_AGENT_ALLOW_ALL_USERS`.

Optional: `LINEAR_AGENT_WEBHOOK_HOST` / `_PORT` / `_PATH` (YAML wins), `LINEAR_AGENT_HOME_TARGET` (silences the per-session "No home channel" notice and enables cron delivery to that issue).

## Config (`hermes config set …`, never hand-edit)

```sh
hermes config set linear_agent.enabled true
hermes config set linear_agent.webhook_host 0.0.0.0
hermes config set linear_agent.webhook_port 8651
hermes config set linear_agent.webhook_path /hermes/linear-agent
hermes config set linear_agent.mutation_policy.create_comments true
hermes config set linear_agent.mutation_policy.update_issues true
hermes config set linear_agent.allow_all_users false
hermes config set linear_agent.allow_mcp false
hermes config set linear_agent.reply_in_source_thread true
hermes config set platform_toolsets.linear_agent '["linear_agent","web","clarify","todo","memory","skills","no_mcp"]'
```

The "not a recognized config key" warnings for `linear_agent.*` are expected (plugin-owned section).

The adapter enforces a hard toolset guard regardless of config: terminal, code_execution, file, delegation, cronjob, computer_use, browser, kanban, connections, session_search and any `hermes-*` composite are stripped, and `no_mcp` is appended unless `allow_mcp: true`.

## OAuth token caveat

The app's capabilities in Linear follow the scopes of its **latest** client-credentials token. Never mint a token with reduced scopes (e.g. `read` only) for debugging. Doing so removed `app:assignable` and delegation failed with "One or more app users lack the required capability" until a full-scope token was minted again. Always request `read,write,app:assignable,app:mentionable`.

## Updating the pinned SHA

```sh
# 1. land the change on the `hardening` branch, run the suite, push
# 2. install the new commit over the existing one (the install scanner flags
#    this repo's CI/docs/test fixtures, so --force is required; review the findings)
docker exec -u hermes hermes-hj3z0j-hermes-1 hermes plugins install \
  https://github.com/Nat1anWasTaken/hermes-linear-agent --ref <40-char-sha> --yes-deps --force
docker exec -u hermes hermes-hj3z0j-hermes-1 sh -c 'cd /opt/data/plugins/linear-agent && git rev-parse HEAD'
# 3. restart the gateway service (command above) and check logs:
docker exec -u hermes hermes-hj3z0j-hermes-1 sh -c 'grep linear_agent /opt/data/logs/gateway.log | tail'
docker exec -u hermes hermes-hj3z0j-hermes-1 hermes plugins list
```

Plugin auto-update is off; the pin only changes when you reinstall.

A Dokploy redeploy recreates the container and, because of `pull_policy: always` on `:stable`, may upgrade Hermes. Re-run the test suite against the new `/opt/hermes` before relying on it. Never pass `--freshVolumes` to `dokploy compose deploy`: it wipes `/opt/data`.

## Running the tests against the container's Hermes

From a checkout, copy the repo plus `pytest`, `pytest-asyncio`, `pyyaml` (py3.14 wheels) into `/opt/data/cache/scratch/<dir>` as the `hermes` user, then:

```sh
docker exec -u hermes -w <dir>/repo -e HERMES_HOME=<dir>/testhome \
  -e PYTHONPATH=<dir>/repo:<dir>/pydeps:/opt/hermes hermes-hj3z0j-hermes-1 \
  /opt/hermes/.venv/bin/python -m pytest -p no:cacheprovider -q
```

Use an empty `HERMES_HOME`: one with this plugin installed makes discovery load a second copy of the module.

## Rollback

```sh
H="docker exec -u hermes hermes-hj3z0j-hermes-1 hermes"
$H plugins disable linear-agent
$H config set linear_agent.enabled false
# remove the plugin entirely (optional)
$H plugins remove linear-agent
```

Then:

1. Remove the `LINEAR_AGENT_*` keys from `/opt/data/.env` (backup: `/opt/data/backups/.env.pre-linear-agent-20261109`). Config backup: `/opt/data/backups/config.yaml.pre-linear-agent-20261109`.
2. Delete the Dokploy domain (`/hermes/linear-agent` → 8651) and redeploy, or leave it (nothing listens once the plugin is disabled).
3. Delete the Cloudflare Access app "Hermes Agent (Linear webhook)".
4. Restart the gateway service.
5. Optionally revoke or delete the OAuth app in Linear → Settings → API → Applications.
