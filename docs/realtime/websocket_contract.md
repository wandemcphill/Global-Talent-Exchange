# GTEX Realtime WebSocket Contract

Status: canonical Thread 7 contract
Scope: production realtime clients, notification streams, activity streams

This document defines the client-facing realtime contract for GTEX WebSocket or equivalent server-push transports. It is intentionally transport-light: a compliant implementation may use WebSocket, Server-Sent Events, or a managed realtime gateway as long as the envelope, state model, replay semantics, and production safety rules remain identical.

## Client Connection States

Clients must expose exactly one of these connection states to product code at any time.

| State | Meaning | Required client behavior |
| --- | --- | --- |
| `disconnected` | No active transport exists and the client is not attempting to connect. | Do not render live-only freshness claims. Allow manual connect or wait for auth/network readiness. |
| `connecting` | Initial transport setup is in progress. | Queue subscriptions locally. Do not emit user-visible realtime events until the server confirms the session. |
| `live` | Transport is open, authenticated, subscribed, and receiving current events. | Apply events immediately after schema validation and dedupe checks. |
| `syncing` | Transport is open but the client is reconciling a cursor gap, cold-start snapshot, or replay window. | Prefer server snapshots/replay over local cache. Suppress duplicate notifications by event id. |
| `reconnecting` | A previously live transport failed and retry/backoff is active. | Keep the last known data visible with stale/reconnecting affordance. Do not clear timelines unless auth is revoked. |
| `degraded` | Transport is unavailable or unhealthy, but polling, cached data, or partial channels still provide limited freshness. | Mark realtime freshness as degraded. Use only server-backed fallback reads. |
| `error` | Connection cannot proceed without user action or a non-retryable failure occurred. | Surface a recoverable error where possible. Stop automatic retries for terminal auth, policy, or unsupported-version failures. |

Allowed transitions:

```text
disconnected -> connecting
connecting -> live
connecting -> syncing
connecting -> error
live -> syncing
live -> reconnecting
live -> degraded
syncing -> live
syncing -> reconnecting
syncing -> degraded
reconnecting -> connecting
reconnecting -> degraded
reconnecting -> error
degraded -> connecting
degraded -> disconnected
error -> disconnected
error -> connecting
```

Clients must not skip through `connecting` when opening a new transport. A client may move from `live` to `syncing` when it detects a missed sequence, receives a server `sync_required` control event, changes subscriptions, or resumes from app background.

## Transport Session

Production clients must authenticate the realtime session using the same account authority as the HTTP API. Authentication may be provided by an access token, a short-lived realtime token, or a signed session ticket.

Minimum connect request fields:

```json
{
  "protocol": "gtex.realtime.v1",
  "clientId": "uuid-or-installation-id",
  "sessionId": "uuid",
  "userId": "user_123",
  "token": "redacted",
  "lastEventId": "evt_01J...",
  "subscriptions": ["notifications.user.user_123", "activity.club.club_456"]
}
```

Server acknowledgement:

```json
{
  "type": "control.connected",
  "connectionId": "rt_01J...",
  "serverTime": "2026-05-29T12:00:00Z",
  "resumeAccepted": true,
  "replayFromEventId": "evt_01J...",
  "heartbeatIntervalMs": 25000,
  "connectionTtlSeconds": 1800
}
```

The client enters `live` only after `control.connected` and all required subscriptions are accepted. If `resumeAccepted` is false, the client enters `syncing` and must fetch a server snapshot or replay endpoint before treating the stream as current.

## Event Envelope

Every data event must use this envelope.

```json
{
  "id": "evt_01J...",
  "type": "notification.created",
  "version": 1,
  "occurredAt": "2026-05-29T12:00:00Z",
  "publishedAt": "2026-05-29T12:00:01Z",
  "sequence": 1042,
  "scope": {
    "kind": "user",
    "id": "user_123"
  },
  "actor": {
    "kind": "system",
    "id": "system"
  },
  "payload": {},
  "traceId": "trc_01J..."
}
```

Envelope rules:

- `id` is globally unique and stable. Clients must dedupe by `id`.
- `type` is a dot-delimited event name. Breaking schema changes require a new `version`.
- `sequence` is monotonically increasing within a subscription scope. Gaps require `syncing`.
- `occurredAt` is the domain event time. `publishedAt` is the server publish time.
- `scope` identifies the authorization and ordering boundary.
- `payload` must validate against the schema for `type` and `version`.
- Unknown event types must be ignored after logging telemetry, unless they are `control.*` events marked terminal.

## Notification Events

Notification events represent user-visible items in the notification center and push surfaces.

### `notification.created`

```json
{
  "id": "evt_01JNOTIFYCREATED",
  "type": "notification.created",
  "version": 1,
  "occurredAt": "2026-05-29T12:00:00Z",
  "publishedAt": "2026-05-29T12:00:01Z",
  "sequence": 1042,
  "scope": { "kind": "user", "id": "user_123" },
  "actor": { "kind": "club", "id": "club_456" },
  "payload": {
    "notificationId": "ntf_01J...",
    "recipientUserId": "user_123",
    "category": "match",
    "severity": "info",
    "title": "Match invite accepted",
    "body": "Academy XI accepted your friendly request.",
    "action": {
      "kind": "route",
      "label": "View match",
      "target": "/matches/match_789"
    },
    "entityRefs": [
      { "kind": "match", "id": "match_789" },
      { "kind": "club", "id": "club_456" }
    ],
    "readAt": null,
    "expiresAt": null
  },
  "traceId": "trc_01J..."
}
```

Required fields: `notificationId`, `recipientUserId`, `category`, `severity`, `title`, `body`.

Allowed `severity` values: `info`, `success`, `warning`, `critical`.

### `notification.updated`

Use when server state changes for an existing notification, including read, unread, archived, or expiry changes.

```json
{
  "id": "evt_01JNOTIFYUPDATED",
  "type": "notification.updated",
  "version": 1,
  "occurredAt": "2026-05-29T12:03:00Z",
  "publishedAt": "2026-05-29T12:03:01Z",
  "sequence": 1043,
  "scope": { "kind": "user", "id": "user_123" },
  "actor": { "kind": "user", "id": "user_123" },
  "payload": {
    "notificationId": "ntf_01J...",
    "recipientUserId": "user_123",
    "readAt": "2026-05-29T12:03:00Z",
    "archivedAt": null,
    "expiresAt": null
  },
  "traceId": "trc_01J..."
}
```

Clients must merge updates into the server-backed notification record by `notificationId`. Missing local records require a fetch by id or a transition to `syncing`.

### `notification.deleted`

Use only when the server removes a notification from the authoritative notification log.

```json
{
  "id": "evt_01JNOTIFYDELETED",
  "type": "notification.deleted",
  "version": 1,
  "occurredAt": "2026-05-29T12:05:00Z",
  "publishedAt": "2026-05-29T12:05:01Z",
  "sequence": 1044,
  "scope": { "kind": "user", "id": "user_123" },
  "actor": { "kind": "system", "id": "system" },
  "payload": {
    "notificationId": "ntf_01J...",
    "recipientUserId": "user_123",
    "reason": "expired"
  },
  "traceId": "trc_01J..."
}
```

Allowed `reason` values: `expired`, `moderated`, `user_deleted`, `system_retracted`.

## Activity Events

Activity events represent timeline or feed items. They may be visible to a user, club, competition, region, or system-level audience depending on scope.

### `activity.created`

```json
{
  "id": "evt_01JACTIVITYCREATED",
  "type": "activity.created",
  "version": 1,
  "occurredAt": "2026-05-29T12:10:00Z",
  "publishedAt": "2026-05-29T12:10:01Z",
  "sequence": 501,
  "scope": { "kind": "club", "id": "club_456" },
  "actor": { "kind": "user", "id": "user_123" },
  "payload": {
    "activityId": "act_01J...",
    "audience": "club",
    "verb": "match_result_posted",
    "summary": "Academy XI won 2-1.",
    "body": null,
    "visibility": "members",
    "entityRefs": [
      { "kind": "match", "id": "match_789" },
      { "kind": "club", "id": "club_456" }
    ],
    "metrics": {
      "commentCount": 0,
      "reactionCount": 0
    },
    "pinnedUntil": null,
    "deletedAt": null
  },
  "traceId": "trc_01J..."
}
```

Required fields: `activityId`, `audience`, `verb`, `summary`, `visibility`, `entityRefs`.

Allowed `audience` values: `user`, `club`, `competition`, `region`, `global`.

Allowed `visibility` values: `private`, `members`, `public`, `admin`.

### `activity.updated`

```json
{
  "id": "evt_01JACTIVITYUPDATED",
  "type": "activity.updated",
  "version": 1,
  "occurredAt": "2026-05-29T12:15:00Z",
  "publishedAt": "2026-05-29T12:15:01Z",
  "sequence": 502,
  "scope": { "kind": "club", "id": "club_456" },
  "actor": { "kind": "system", "id": "system" },
  "payload": {
    "activityId": "act_01J...",
    "summary": "Academy XI won 2-1.",
    "metrics": {
      "commentCount": 3,
      "reactionCount": 12
    },
    "pinnedUntil": null,
    "deletedAt": null
  },
  "traceId": "trc_01J..."
}
```

Clients must apply updates by `activityId`. If an update references an unknown `activityId`, clients must request a server-backed activity refresh for that scope.

### `activity.deleted`

```json
{
  "id": "evt_01JACTIVITYDELETED",
  "type": "activity.deleted",
  "version": 1,
  "occurredAt": "2026-05-29T12:20:00Z",
  "publishedAt": "2026-05-29T12:20:01Z",
  "sequence": 503,
  "scope": { "kind": "club", "id": "club_456" },
  "actor": { "kind": "moderator", "id": "mod_123" },
  "payload": {
    "activityId": "act_01J...",
    "reason": "moderated",
    "deletedAt": "2026-05-29T12:20:00Z"
  },
  "traceId": "trc_01J..."
}
```

Allowed `reason` values: `moderated`, `author_deleted`, `system_retracted`, `retention_policy`.

## Control Events

Control events are never user-visible activity. They coordinate health, replay, and protocol decisions.

| Type | Meaning | Client behavior |
| --- | --- | --- |
| `control.connected` | Session accepted. | Enter `live` or `syncing` based on replay status. |
| `control.heartbeat` | Server liveness signal. | Update last-seen timestamp. Do not show as an event. |
| `control.sync_required` | Server detected cursor, subscription, or auth drift. | Enter `syncing` and fetch replay/snapshot. |
| `control.degraded` | Server cannot provide full realtime freshness. | Enter `degraded`; use server-backed fallback reads. |
| `control.error` | Non-data protocol error. | Retry only when `retryable` is true. |
| `control.disconnect` | Server requested clean close. | Close transport and follow provided reason. |

Example terminal error:

```json
{
  "type": "control.error",
  "code": "auth_revoked",
  "message": "Realtime session is no longer authorized.",
  "retryable": false,
  "serverTime": "2026-05-29T12:30:00Z"
}
```

## Reconnect And Backoff Semantics

Clients must reconnect automatically for retryable network, heartbeat timeout, and server `retryable` errors.

Default backoff policy:

- Attempt 1: immediate retry after 250 ms plus jitter.
- Attempt 2: 1 second plus jitter.
- Attempt 3: 2 seconds plus jitter.
- Attempt 4: 4 seconds plus jitter.
- Attempt 5 and later: exponential backoff capped at 30 seconds plus jitter.
- Jitter must be 0-30 percent of the selected delay to prevent reconnect bursts.
- Reset the attempt counter after 60 continuous seconds in `live`.

Heartbeat policy:

- Use the server-provided `heartbeatIntervalMs` when available.
- Treat the connection as unhealthy after 2 missed heartbeat intervals.
- Move from `live` or `syncing` to `reconnecting` before opening a replacement transport.
- Keep `lastEventId` and the last accepted `sequence` per scope for resume.

Resume policy:

- Every reconnect request must include `lastEventId` when available.
- If the server can replay all missed events, it returns `resumeAccepted: true` and the client may return to `live`.
- If replay is unavailable or the event gap exceeds server retention, the server returns `resumeAccepted: false`; the client must enter `syncing`.
- During `syncing`, clients must fetch authoritative server data before rendering the stream as current.
- Duplicate replayed events are expected and must be ignored by `id`.

Terminal conditions:

- Do not retry automatically for `auth_revoked`, `account_disabled`, `unsupported_protocol`, `client_version_blocked`, or `permission_denied`.
- Enter `error` for terminal conditions and require login, upgrade, permission change, or manual user action.
- If the app is backgrounded or the OS suspends sockets, reconnect on foreground and begin in `connecting` with resume metadata.

## Production Authenticity Rule

Production clients must not generate fake, synthetic, mock, local-only, or optimistic realtime events for notification or activity streams.

Allowed local behavior is limited to UI state that is clearly not an event, such as pending spinners, disabled controls, stale indicators, or temporary form drafts. Any item displayed in a notification center, activity feed, live badge, unread count, or realtime timeline must originate from a server event, server replay, or server-backed HTTP snapshot. If realtime is unavailable, clients must enter `degraded`, `reconnecting`, `syncing`, or `error` and use server-backed fallback reads rather than inventing events.

Development fixtures may exist only in test harnesses or explicit non-production demo modes. They must be gated so that production builds and production API clients cannot import, request, or display them as realtime data.

## Client Validation Checklist

- Validate event envelope shape before reading payload fields.
- Dedupe every event by `id`.
- Track `sequence` per subscription scope and enter `syncing` on gaps.
- Ignore unknown non-control event types after telemetry logging.
- Apply notification records by `notificationId`.
- Apply activity records by `activityId`.
- Never treat `control.*` events as user-visible feed items.
- Never generate fake/local notification or activity events in production.
