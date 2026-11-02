from collections.abc import Mapping
from typing import TypedDict

from rest_framework import serializers

from apps.common.text import clean_text
from apps.exercises.kinds.base import SHARED_RULES, Effort, ExerciseKind, Extra, extra_of, locate
from apps.exercises.models import Exercise

PROMPT_VERSION = "1.0"

SYSTEM_PROMPT = f"""You write listen-and-write exercises for language learners. The learner hears a sentence in the
source language, sees it with a gap, and types the missing part. The input gives the focus (the word or expression the
learner is studying), its kind, the source language, the learner's target language, the meaning the learner studied when
known, and how many items to write.
For each item, write source_sentence: one short, natural sentence of 8 to 18 words, in the source language, set in an
everyday situation, that uses the focus with the studied meaning. Every item uses a different situation.
In source_answer, copy from source_sentence, character by character, the part the learner must type: the focus as it
appears in the sentence, inflected when the sentence needs it. When the focus is a long saying that natives often cut
short, the sentence may use only the part people say, and source_answer is that part.
In source_syllables, repeat source_answer with a | between the syllables of every word, like Pro|cras|ti|na|tion or
on the fence. Removing every | must give source_answer exactly.
In target_translation, translate source_sentence naturally into the target language.
{SHARED_RULES}"""


class ListenWritePayload(TypedDict):
    sentence: str
    start: int
    end: int
    syllables: str
    translation: str
    extra: Extra


class ListenWriteItemSerializer(serializers.Serializer):
    source_sentence = serializers.CharField(max_length=300)
    source_answer = serializers.CharField(max_length=100)
    source_syllables = serializers.CharField(max_length=200)
    target_translation = serializers.CharField(max_length=300)
    target_extra_note = serializers.CharField(max_length=300)
    source_extra_say = serializers.CharField(max_length=150)


def syllables(answer: str, marked: str) -> str:
    plain = marked.replace("|", "")
    if len(plain) != len(answer) or plain.lower() != answer.lower():
        return answer

    parts: list[str] = []
    index = 0
    for char in marked:
        if char != "|":
            parts.append(answer[index])
            index += 1
        elif 0 < index < len(answer) and answer[index - 1].isalpha() and answer[index].isalpha():
            if parts[-1] != "|":
                parts.append("|")

    return "".join(parts)


class ListenWrite(ExerciseKind):
    name = Exercise.Kind.LISTEN_WRITE
    effort = Effort.LISTEN
    prompt_version = PROMPT_VERSION
    system_prompt = SYSTEM_PROMPT
    item_serializer = ListenWriteItemSerializer

    def to_payload(self, item: Mapping[str, str]) -> ListenWritePayload | None:
        sentence = clean_text(item["source_sentence"])
        match = locate(clean_text(item["source_answer"]), sentence)
        if match is None:
            return None

        return {
            "sentence": sentence,
            "start": match.start(),
            "end": match.end(),
            "syllables": syllables(match.group(), clean_text(item["source_syllables"])),
            "translation": clean_text(item["target_translation"]),
            "extra": extra_of(item),
        }
