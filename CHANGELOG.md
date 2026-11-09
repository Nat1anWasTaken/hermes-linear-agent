# Changelog

All notable changes to this project will be documented here.

## 0.4.3 — 2026-11-09 (hardening fork)

### Security

- Hard toolset guard: `toolsets_for_source()` strips `terminal`, `code_execution`, `file`, `delegation`, `cronjob`, `computer_use`, `browser`, `kanban`, `connections`, `session_search` and any `hermes-*` composite (or any toolset resolving to those tools) from Linear turns, and appends `no_mcp` unless `allow_mcp: true`. Safe default when unset: `linear_agent, web, clarify, todo`.
- Linear-sourced text (prompt context, guidance, previous comments, user request, follow-ups) is wrapped in `<untrusted-linear-*>` markers; embedded marker tags are neutralized.
- Dispatch failures post a generic error with a correlation id; exception details stay in local logs.
- `linear_agent_update_plan` / `linear_agent_set_session_links` only act on the current Linear Agent Session (from the gateway session context) and only accept http(s) links.
- `/p/<profile>/…` webhook routes are opt-in (`profile_routes: true`).

### Fixed

- Stop signal: the interrupt key is built by the base adapter's `_source_session_key` (profile namespace + identity canonicalization), so `stop` reaches turns on named profiles. Exactly one confirmation is posted; late output from the interrupted turn is dropped until the session is prompted again.
- Exec-approval prompts are posted as `elicitation` activities (session shows "awaiting input"), other interim sends as `thought`; neither consumes the one-shot source-thread mirror, which is reserved for the final response.
- Runtime OAuth scopes always include `app:assignable` and `app:mentionable` (default `read,write,app:assignable,app:mentionable`).
- `requires-python` widened to `>=3.11` (Hermes ships Python 3.14; the old `<3.14` pin made `hermes plugins enable` fail at dependency admission).
- Tests use the current lock API (`BasePlatformAdapter._release_platform_lock`).

### Added

- `LINEAR_AGENT_WEBHOOK_HOST` / `LINEAR_AGENT_WEBHOOK_PORT` / `LINEAR_AGENT_WEBHOOK_PATH` env fallbacks for the bind settings (YAML still wins); out-of-range ports are rejected.

## 0.4.2 — 2026-07-29

### Fixed

- Resolve a child `AgentSession.sourceCommentId` to its root comment before replying; Linear rejects child comments as `commentCreate.parentId` with `incorrect parent`.
- Mirror final Agent Session responses to the resolved source thread in adapter-controlled delivery instead of relying on the model to invoke a comment tool.

## 0.4.1 — 2026-07-29

### Fixed

- Preserve Linear's current `agentSession.sourceCommentId` webhook field so replies triggered from an existing issue-comment thread can be routed back to that original thread.
- Accept `agentActivity.sourceCommentId` as a compatible fallback for prompted activity payloads.

## 0.4.0 — 2026-07-29

### Added

- Standalone Hermes platform-plugin distribution for Linear Agent Sessions.
- Git-directory plugin manifest and pip entry point.
- 58 attributed `linear_agent_*` tools with fail-closed mutation policies.
- Linear client-credentials and authorization-code OAuth support.
- Signed webhook handling, replay protection, Agent Activities, plans, session links, clarification, stop signals, and standalone cron delivery.
- Plugin-owned, process-locked, atomic OAuth state storage with POSIX mode `0600`.
- Read-only migration fallback for earlier `providers.linear_agent` state in Hermes `auth.json`.
- Compatibility tests for current Hermes upstream and Python 3.11–3.13.
