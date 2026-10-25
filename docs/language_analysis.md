# Language analysis

`language_analysis` provides a stateless Gemini-backed analysis for a word, phrase, or short text. It does not create database records or caches.

## Configuration

```env
LANGUAGE_ANALYSIS_MAX_TEXT_LENGTH=3000
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_TIMEOUT=30
```

`GEMINI_MODEL` selects another compatible model without code changes. `GEMINI_TIMEOUT` is measured in seconds. The service sends every request with `store=False`; no conversation history is used.

## API

`POST /api/v1/language-analysis/analyze` requires the project's standard JWT authentication.

```json
{
  "text": "I run a small business.",
  "selected_term": "run",
  "source_language": "en",
  "target_language": "pt-BR",
  "level": "B1"
}
```

`text` is required and limited to 3000 characters by default. `selected_term` is optional. `source_language` defaults to `auto`, `target_language` defaults to `pt-BR`, and `level` accepts `A1`, `A2`, `B1`, `B2`, `C1`, or `C2`.

```json
{
  "input": {
    "text": "I run a small business.",
    "selected_term": "run",
    "source_language": "en",
    "target_language": "pt-BR",
    "level": "B1"
  },
  "analysis": {
    "focus": "run",
    "detected_language": "en",
    "translation": "administrar",
    "meaning_in_context": "Gerenciar uma empresa.",
    "explanation": "Nesta frase, run significa administrar, e não correr.",
    "part_of_speech": "verb",
    "is_ambiguous": false,
    "alternative_meanings": [],
    "examples": [],
    "usage_notes": []
  },
  "metadata": {
    "model": "gemini-3.5-flash-lite",
    "prompt_version": "1.0"
  }
}
```

Provider configuration or availability failures return `503`; timeouts return `504`; invalid provider output returns `502`. Request-validation failures return `400`.

## Tests

Run the standard Django test suite with `python manage.py test`. Gemini calls are mocked in automated tests.

## Known limitations and future work

The MVP has no persistence, cache, history, exercises, learning-progress tracking, or prompt-quality evaluation. Those features remain separate future phases.
