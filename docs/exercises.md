# Exercises and reviews

Minigames live in two apps. `exercises` owns the content the AI writes for a term; `reviews` decides which terms to practice and records how each round went.

## Configuration

```env
EXERCISE_VARIATIONS=3
REVIEW_SESSION_SIZE=10
```

## API

`GET /api/v1/terms/<id>/exercises/<kind>` returns every variation of one kind for a term, least served first. The first request generates them with one Gemini call and saves them; later requests never call Gemini. Unknown kind or term: 404.

```json
{"exercises": [{"id": "…", "kind": "listen_write", "variant": 0, "payload": {}}]}
```

`GET /api/v1/reviews?kinds=listen_write` builds a session for the active course. `kinds` lists the kinds the app can play (repeat the parameter for more); unknown kinds are ignored and an empty list gives no rounds. Without `kinds`, every kind is allowed.

```json
{"due": 12, "rounds": [{"term": {"id": "…", "text": "on the fence", "translation": "", "kind": "expression", "level": 2}, "kind": "listen_write"}]}
```

`POST /api/v1/reviews/attempts` records a finished round and returns the term with its new level (201).

```json
{"term": "<uuid>", "kind": "listen_write", "exercise": "<uuid or null>", "outcome": "first"}
```

`outcome` is `first`, `retry` (right after a mistake), `hint` (used a hint) or `missed` (saw the answer). The exercise's `served_count` goes up, so the next review serves another variation.

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
2. Create `apps/exercises/kinds/<kind>.py` with a subclass of `ExerciseKind`: system prompt, item serializer (the schema comes from it) and `to_payload`, which turns one validated AI item into the stored payload (or `None` to drop it). Name learning-language fields `source_*` and base-language fields `target_*`.
3. Register it in `KINDS` (`apps/exercises/kinds/__init__.py`). A test fails while `Exercise.Kind` and `KINDS` differ.
4. Document the payload here. Old apps never receive it: they only ask for the kinds they know.
