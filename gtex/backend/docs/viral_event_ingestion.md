# GTEX Viral Event Ingestion

## Kafka topics

- `clip.view`
- `clip.watch_time`
- `clip.complete`
- `clip.loop`
- `clip.share`
- `clip.comment`
- `clip.like`
- `clip.scroll`

The API producer and the aggregation worker both call the same topic bootstrapper, so missing topics are created on startup when Kafka is configured.

## Event schema

`POST /events/clip` accepts either:

- a single event object
- an array of event objects
- an envelope with `{ "events": [...] }`

Each event is validated against this contract:

```json
{
  "event_id": "UUID",
  "clip_id": "string",
  "user_id": "string | null",
  "session_id": "string",
  "timestamp": "ISO-8601 datetime",
  "event_type": "view | watch_time | complete | loop | share | comment | like | scroll",
  "watch_time_ms": "int | null",
  "video_length_ms": "int | null",
  "metadata": {
    "device": "string",
    "country": "string",
    "referrer": "string"
  }
}
```

## Redis schema

Metrics are aggregated into:

- `clip:{clip_id}:metrics`

Hash fields:

- `views`
- `total_watch_time`
- `completions`
- `loops`
- `shares`
- `comments`
- `likes`
- `skips`

Deduplication keys:

- `clip:event:{event_id}`

The worker uses an atomic Redis script that applies the dedupe check and the hash increments in the same operation. Fields that have never been incremented may be absent and should be treated as `0`.
