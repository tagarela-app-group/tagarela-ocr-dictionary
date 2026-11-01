# Exercises and reviews

Minigames live in two apps. `exercises` owns the content the AI writes for a term; `reviews` decides which terms to practice and records how each round went.

## Configuration

```env
EXERCISE_VARIATIONS=3
REVIEW_SESSION_SIZE=10
```

Every value of the memory model is a `REVIEW_*` setting (see `.env.dsv.example`). `REVIEW_SECONDS_PER_DAY=60` makes one "day" last a minute to test in dsv; in that mode the day comes from the API clock, not from the device. Tests assume the real day: put it back to 86400 before running them.

## API

`GET /api/v1/terms/<id>/exercises/<kind>` returns every variation of one kind for a term, least served first. The first request generates them with one Gemini call and saves them; later requests never call Gemini. Unknown kind or term: 404.

```json
{"exercises": [{"id": "…", "kind": "listen_write", "variant": 0, "payload": {}}]}
```

`GET /api/v1/reviews?kinds=listen_write&date=2026-11-01&offset=-180` builds today's session for the active course. `kinds` lists the kinds the app can play (repeat the parameter for more); unknown kinds are ignored and an empty list gives no rounds. Without `kinds`, every kind is allowed. `date` and `offset` (minutes from UTC) are the device's day; a date further than `REVIEW_DATE_TOLERANCE_DAYS` from the server's is a 400.

```json
{
  "due": 12,
  "limit": 10,
  "done": 3,
  "waiting": 4,
  "unread": 2,
  "next_due_at": "2026-11-02T12:00:00-03:00",
  "rounds": [{"term": {"id": "…", "text": "on the fence", "translation": "", "kind": "expression", "level": 2, "interval_days": 8.0, "due_at": "…"}, "kind": "listen_write", "retest": false}]
}
```

`due` is what is still planned for today, `done` the different terms reviewed today, `waiting` what is due but did not fit, `unread` the terms whose card was never read.

`POST /api/v1/reviews/attempts` records a finished round (201). Only `term`, `kind` and `outcome` are required.

```json
{
  "term": "<uuid>",
  "kind": "listen_write",
  "exercise": "<uuid or null>",
  "outcome": "first",
  "played_at": "2026-11-01T15:00:00Z",
  "local_date": "2026-11-01",
  "used_slow": false,
  "errors": 0,
  "hints": 0,
  "audio_replays": 1,
  "response_ms": 8200
}
```

`outcome` is `first`, `retry` (right after a mistake), `hint` (used a hint) or `missed` (saw the answer). The exercise's `served_count` goes up, so the next review serves another variation. The response brings the term and what the round did:

```json
{"term": {}, "effect": {"role": "session", "points": 15.0, "rating": "great", "level_before": 2, "level": 3, "interval_before": 8.0, "interval_days": 20.0, "due_at": "…"}}
```

`role` is `first_review`, `session`, `retest` or `extra` (no effect on the term). `rating` is `poor`, `fair`, `good` or `great`, only for the screen.

`POST /api/v1/reviews/more` adds `REVIEW_SESSION_SIZE` to today's limit (204).

`POST /api/v1/terms/<id>/study` with `{"event": "read"}` or `{"event": "listened"}` registers the card being read or its audio being heard. Each one counts once and gives points to the next session; `read` schedules the first review.

## Payloads

`listen_write`: the learner hears `sentence` and types `sentence[start:end]`.

```json
{
  "sentence": "I'm still on the fence about moving to Lisbon.",
  "start": 10,
  "end": 22,
  "syllables": "on the fence",
  "translation": "Ainda tô em cima do muro sobre me mudar pra Lisboa.",
  "extra": {"note": "Depois vem *about*: *on the fence about* alguma coisa.", "say": "on the fence about"}
}
```

`syllables` is the answer with `|` where a long word may break across lines (`Pro|cras|ti|na|tion`). `extra.note` is in the base language, with learning-language parts between asterisks; `extra.say` is what the app reads aloud.

## Adding a kind

1. Add the value to `Exercise.Kind` and run `makemigrations`.
2. Create `apps/exercises/kinds/<kind>.py` with a subclass of `ExerciseKind`: its `effort` (`Effort.READ`, `LISTEN` or `PRODUCE`, the only thing the memory model needs from it), system prompt, item serializer (the schema comes from it) and `to_payload`, which turns one validated AI item into the stored payload (or `None` to drop it). Name learning-language fields `source_*` and base-language fields `target_*`.
3. Register it in `KINDS` (`apps/exercises/kinds/__init__.py`). A test fails while `Exercise.Kind` and `KINDS` differ.
4. Document the payload here. Old apps never receive it: they only ask for the kinds they know.
