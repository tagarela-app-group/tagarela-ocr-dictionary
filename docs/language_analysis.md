# Language analysis

`language_analysis` provides a stateless Gemini-backed analysis for a word, phrase, or short text. It does not create database records or caches. The term card (`apps/cards`, `GET /api/v1/terms/<id>`) calls it once per term and saves the result.

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
    "usage_notes": [],
    "phonetic": "/rʌn/",
    "source_definition": "to manage or operate",
    "source_meaning_in_context": "To manage a small business.",
    "source_explanation": "Run is often used for being in charge of a company.",
    "pitfall": "Não traduza como correr quando o assunto é uma empresa.",
    "pitfall_wrong": null,
    "pitfall_right": null,
    "literal": null,
    "imagine": "Alguém no balcão, cuidando de tudo na própria loja.",
    "collocations": ["run a business"],
    "synonyms": ["manage", "operate"],
    "antonyms": [],
    "formality": "neutral",
    "formality_note": "Fine in conversation and at work.",
    "contexts": [{"context": "Contract", "fits": false, "alternative": "operate"}],
    "dialogue": [
      {"speaker": "A", "text": "What does your aunt do?", "translation": "O que sua tia faz?"},
      {"speaker": "B", "text": "She runs a bakery downtown.", "translation": "Ela administra uma padaria no centro."}
    ]
  },
  "metadata": {
    "model": "gemini-3.5-flash-lite",
    "prompt_version": "2.2"
  }
}
```

Prompt 2.0 added the fields after `usage_notes`; 2.2 added `pitfall_wrong`, `pitfall_right`, `literal`, `imagine` and `dialogue`. `source_*`, `phonetic`, `collocations`, `synonyms`, `antonyms`, `formality_note`, `contexts`, `pitfall_wrong`, `pitfall_right` and `dialogue[].text` are in the source language; `pitfall`, `literal`, `imagine` and `dialogue[].translation` are in the target language. `dialogue[].speaker` is `A` or `B`, two to four lines. `formality` is one of `slang`, `informal`, `neutral`, `formal`.

Provider configuration or availability failures return `503`; timeouts return `504`; invalid provider output returns `502`. Request-validation failures return `400`.

## Tests

Run the standard Django test suite with `python manage.py test`. Gemini calls are mocked in automated tests.

## Known limitations and future work

The endpoint has no persistence, cache, history, exercises, learning-progress tracking, or prompt-quality evaluation. Only the term card saves results.
