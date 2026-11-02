import random
from collections.abc import Mapping, Sequence
from typing import TypedDict, cast

from django.conf import settings
from rest_framework import serializers

from apps.cards.models import TermCard
from apps.common.text import clean_text
from apps.exercises.kinds.base import (
    SHARED_RULES,
    Effort,
    ExerciseKind,
    Extra,
    Payload,
    extra_of,
    locate,
)
from apps.exercises.models import Exercise
from apps.vocabulary.models import Term

PROMPT_VERSION = "1.0"
OPTION_COUNT = 4
WRONG_COUNT = OPTION_COUNT - 1

USE = "use"
UNDERSTAND = "understand"
AUDIO = "audio"
MODES = (USE, UNDERSTAND, AUDIO)

SYSTEM_PROMPT = f"""You write short chat exchanges for language learners. The learner chats in the source language with
Nina, a friend, and completes their own reply by choosing one of four options. The input gives the focus (the word or
expression the learner is studying), its kind, the source language, the learner's target language, the meaning the
learner studied when known, and how many items to write.
Write the items in this order of mode, stopping at the requested count: use, understand, audio. Every item is a different
everyday situation that makes sense on its own, with no link to the other items.
Use simple words the learner surely knows in every field, except for the focus itself.
In source_nina, write Nina's message, of 5 to 15 words.
In source_reply, write the learner's answer, of 4 to 15 words.
In modes use and audio, source_nina must not contain the focus, and source_reply uses the focus with the studied meaning.
In source_answer, copy from source_reply, character by character, the focus as it appears there, inflected when the
sentence needs it. In mode audio, source_nina is heard and not read, so it must sound natural when spoken. Leave
source_wrong_1, source_wrong_2 and source_wrong_3 empty.
In mode understand, source_nina uses the focus with the studied meaning, wrapped between single asterisks, and uses
asterisks for nothing else. source_reply shows that the learner understood, like Oh, so you haven't decided yet? In
source_answer, copy from source_reply, character by character, the part that says the same as the focus in very simple
words, without using the focus. In source_wrong_1, source_wrong_2 and source_wrong_3, write three different simple
phrases with the same grammar as source_answer that fit the same place in source_reply but clearly mean something else.
In source_nina_reply, write Nina's short, natural reaction to source_reply.
In source_segue, write the few words Nina would say before source_nina to change the subject of a chat, ending in
punctuation, like Anyway! or Oh, by the way:
In target_translation, write in the target language the meaning of the focus in a few words, not a full sentence.
{SHARED_RULES}"""


class ReplyPayload(TypedDict):
    mode: str
    segue: str
    nina: str
    reply: str
    start: int
    end: int
    nina_reply: str
    translation: str
    extra: Extra
    wrong: list[str]


class ReplyItemSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=MODES)
    source_segue = serializers.CharField(max_length=60)
    source_nina = serializers.CharField(max_length=300)
    source_reply = serializers.CharField(max_length=300)
    source_answer = serializers.CharField(max_length=150)
    source_wrong_1 = serializers.CharField(max_length=150, allow_blank=True)
    source_wrong_2 = serializers.CharField(max_length=150, allow_blank=True)
    source_wrong_3 = serializers.CharField(max_length=150, allow_blank=True)
    source_nina_reply = serializers.CharField(max_length=300)
    target_translation = serializers.CharField(max_length=150)
    target_extra_note = serializers.CharField(max_length=300)
    source_extra_say = serializers.CharField(max_length=150)


def nina_fits(mode: str, nina: str, answer: str) -> bool:
    if mode == UNDERSTAND:
        return nina.count("*") == 2 and nina.split("*")[1].strip() != ""

    return "*" not in nina and locate(answer, nina) is None


def wrong_phrases(item: Mapping[str, str], answer: str) -> list[str] | None:
    phrases = [clean_text(item[f"source_wrong_{index}"]) for index in range(1, OPTION_COUNT)]
    keys = {phrase.casefold() for phrase in phrases}
    if "" in keys or answer.casefold() in keys or len(keys) < WRONG_COUNT:
        return None

    return phrases


def synonyms_of(term: Term) -> set[str]:
    card = TermCard.objects.filter(term=term).first()
    synonyms = card.analysis.get("synonyms") if card else None
    if not isinstance(synonyms, list):
        return set()

    return {synonym.casefold() for synonym in synonyms if isinstance(synonym, str)}


def vocabulary_pool(term: Term) -> list[tuple[str, str]]:
    avoid = synonyms_of(term)
    terms = Term.objects.filter(
        course_id=term.course_id, deleted_at__isnull=True, first_read_at__isnull=False
    ).exclude(pk=term.pk)

    return [
        (text, kind)
        for text, kind in terms.values_list("text", "kind")
        if text.casefold() not in avoid
    ]


def wrong_terms(term: Term, pool: Sequence[tuple[str, str]], rng: random.Random) -> list[str]:
    drawn = rng.sample(list(pool), len(pool))
    drawn.sort(key=lambda candidate: candidate[1] != term.kind)

    return [text for text, _ in drawn[:WRONG_COUNT]]


class Reply(ExerciseKind):
    name = Exercise.Kind.REPLY
    effort = Effort.READ
    prompt_version = PROMPT_VERSION
    system_prompt = SYSTEM_PROMPT
    item_serializer = ReplyItemSerializer

    def to_payload(self, item: Mapping[str, str]) -> ReplyPayload | None:
        mode = item["mode"]
        nina = clean_text(item["source_nina"])
        reply = clean_text(item["source_reply"])
        answer = clean_text(item["source_answer"])
        match = locate(answer, reply)
        if match is None or not nina_fits(mode, nina, answer):
            return None

        wrong: list[str] | None = []
        if mode == UNDERSTAND:
            wrong = wrong_phrases(item, answer)
        if wrong is None:
            return None

        return {
            "mode": mode,
            "segue": clean_text(item["source_segue"]),
            "nina": nina,
            "reply": reply,
            "start": match.start(),
            "end": match.end(),
            "nina_reply": clean_text(item["source_nina_reply"]),
            "translation": clean_text(item["target_translation"]),
            "extra": extra_of(item),
            "wrong": wrong,
        }

    def effort_of(self, payload: Payload | None) -> Effort:
        if payload is not None and payload.get("mode") == AUDIO:
            return Effort.LISTEN

        return self.effort

    def available(self, read_terms: int) -> bool:
        return read_terms >= OPTION_COUNT

    def fits(self, interval_days: float, retest: bool) -> bool:
        return not retest and interval_days >= settings.REVIEW_REPLY_MIN_INTERVAL_DAYS

    def serve(
        self, term: Term, payloads: Sequence[Payload], rng: random.Random
    ) -> Sequence[Payload]:
        pool = vocabulary_pool(term)
        served: list[Payload] = []
        for payload in payloads:
            stored = cast(ReplyPayload, payload)
            if stored["mode"] == UNDERSTAND:
                answer = stored["reply"][stored["start"] : stored["end"]]
                wrong = stored["wrong"]
            else:
                answer = term.text
                wrong = wrong_terms(term, pool, rng)
            options = [answer, *wrong]
            rng.shuffle(options)
            fields = {key: value for key, value in stored.items() if key != "wrong"}
            served.append({**fields, "answer": answer, "options": options})

        return served
