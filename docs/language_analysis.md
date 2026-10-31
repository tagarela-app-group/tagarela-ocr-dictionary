# Language analysis

`language_analysis` asks Gemini to describe a term in the context of a capture. It has no route of its own and saves nothing: the term card (`apps/cards`, `GET /api/v1/terms/<id>`) calls it once per term and saves the result.

## Configuration

```env
LANGUAGE_ANALYSIS_MAX_TEXT_LENGTH=3000
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_TIMEOUT=30
```

`GEMINI_MODEL` selects another compatible model without code changes. `GEMINI_TIMEOUT` is measured in seconds. Every request goes with `store=False`, so no conversation history is kept.

## Languages

Fields prefixed with `source_`, `phonetic`, `collocations`, `synonyms`, `antonyms`, `contexts[].alternative`, and `dialogue[].text` are in the language being learned. The rest is in the base language. The prefix matters: without it, Gemini ignores the language asked for.

`dialogue[].speaker` is `A` or `B`, two to four lines. `formality` is one of `slang`, `informal`, `neutral`, `formal`.

## Failures

Provider configuration or availability failures return `503`, timeouts return `504`, and invalid provider output returns `502`. The card route passes them on.
