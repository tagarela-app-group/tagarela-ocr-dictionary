from django.db import IntegrityError, transaction
from rest_framework import serializers

from apps.vocabulary.models import Group, Term

DUPLICATE_GROUP = "Você já tem um grupo com esse nome."


def clean_text(text: str) -> str:
    return " ".join(text.split())


def term_key(text: str) -> str:
    return clean_text(text).casefold()


class VocabularyService:
    def vocabulary(self, user) -> dict:
        return {
            "groups": Group.objects.filter(user=user).prefetch_related("terms"),
            "ungrouped": Term.objects.filter(user=user, group__isnull=True),
        }

    def create_group(self, user, data: dict) -> Group:
        if Group.objects.filter(user=user, name__iexact=data["name"]).exists():
            raise serializers.ValidationError({"name": [DUPLICATE_GROUP]})

        try:
            with transaction.atomic():
                return Group.objects.create(user=user, **data)
        except IntegrityError as exc:
            raise serializers.ValidationError({"name": [DUPLICATE_GROUP]}) from exc

    def move(self, user, term_ids: list, group_id) -> None:
        group = None
        if group_id is not None:
            group = Group.objects.filter(user=user, pk=group_id).first()
            if group is None:
                raise serializers.ValidationError({"group": ["Esse grupo não existe mais."]})

        terms = Term.objects.filter(user=user, pk__in=term_ids)
        if terms.count() != len(set(term_ids)):
            raise serializers.ValidationError({"terms": ["Algum termo não existe mais."]})

        terms.update(group=group)

    def add_terms(self, user, texts: list[str]) -> None:
        new = {}
        for text in texts:
            new.setdefault(term_key(text), clean_text(text))

        Term.objects.bulk_create(
            [
                Term(
                    user=user,
                    text=text,
                    key=key,
                    kind=Term.Kind.EXPRESSION if " " in text else Term.Kind.WORD,
                )
                for key, text in new.items()
            ],
            ignore_conflicts=True,
        )
