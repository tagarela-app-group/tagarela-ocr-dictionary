import json
from unittest.mock import MagicMock

from django.test import SimpleTestCase, override_settings
from redis.exceptions import RedisError

from apps.lexical.cache import LexicalCache

FOX = {"word": "fox", "definitions": ["A canine."], "source": "dictionary"}


class LexicalCacheTests(SimpleTestCase):
    def setUp(self):
        self.client = MagicMock()
        self.cache = LexicalCache(client=self.client)

    def test_get_many_reads_keys_by_language_and_skips_miss(self):
        self.client.mget.return_value = [json.dumps(FOX), None]

        result = self.cache.get_many(["fox", "cat"], "en")

        self.assertEqual(result, {"fox": FOX})
        self.client.mget.assert_called_once_with(["lexical:en:fox", "lexical:en:cat"])

    def test_get_many_with_redis_down_returns_miss(self):
        self.client.mget.side_effect = RedisError("down")

        self.assertEqual(self.cache.get_many(["fox"], "en"), {})

    @override_settings(LEXICAL_CACHE_TTL_SECONDS=60)
    def test_set_many_writes_json_with_ttl(self):
        pipeline = self.client.pipeline.return_value

        self.cache.set_many([FOX], "en")

        pipeline.setex.assert_called_once_with("lexical:en:fox", 60, json.dumps(FOX))
        pipeline.execute.assert_called_once()

    def test_set_many_without_entries_skips_redis(self):
        self.cache.set_many([], "en")

        self.client.pipeline.assert_not_called()

    def test_set_many_with_redis_down_does_not_raise(self):
        self.client.pipeline.return_value.execute.side_effect = RedisError("down")

        self.cache.set_many([FOX], "en")
