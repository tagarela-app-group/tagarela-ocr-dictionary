import json

from django.conf import settings
from redis import Redis
from redis.exceptions import RedisError


class LexicalCache:
    def __init__(self, client: Redis | None = None) -> None:
        self.client = client or Redis.from_url(settings.REDIS_URL, decode_responses=True)

    def get_many(self, words: list[str], language: str) -> dict[str, dict]:
        keys = [self._key(language, word) for word in words]

        try:
            values = self.client.mget(keys)
        except RedisError:
            return {}

        cached = {}

        for word, value in zip(words, values, strict=True):
            if value:
                cached[word] = json.loads(value)

        return cached

    def set_many(self, entries: list[dict], language: str) -> None:
        if not entries:
            return

        pipeline = self.client.pipeline()

        for entry in entries:
            key = self._key(language, entry["word"])
            pipeline.setex(key, settings.LEXICAL_CACHE_TTL_SECONDS, json.dumps(entry))

        try:
            pipeline.execute()
        except RedisError:
            return

    def _key(self, language: str, word: str) -> str:
        return f"lexical:{language}:{word}"
