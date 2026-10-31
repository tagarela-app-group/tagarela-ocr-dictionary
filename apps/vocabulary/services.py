from django.db import IntegrityError, transaction
from django.db.models import Prefetch
from django.http import Http404
from django.utils import timezone
from rest_framework import serializers

from apps.courses.models import Course
from apps.vocabulary.models import Group, Term

DUPLICATE_GROUP = "Você já tem um grupo com esse nome."
MISSING_TERM = "Algum termo não existe mais."


def clean_text(text: str) -> str:
    return " ".join(text.split())


def term_key(text: str) -> str:
    return clean_text(text).casefold()


class VocabularyService:
    def vocabulary(self, course: Course) -> dict:
        return {
            "groups": self._groups(course),
            "ungrouped": self._terms(course).filter(group__isnull=True),
        }

    def group(self, course: Course, group_id) -> Group:
        group = self._groups(course).filter(pk=group_id).first()
        if group is None:
            raise Http404

        return group

    def create_group(self, course: Course, data: dict) -> Group:
        return self._save_group(Group(course=course), data)

    def update_group(self, group: Group, data: dict) -> Group:
        self._save_group(group, data)

        return self.group(group.course, group.pk)

    def delete_group(self, group: Group) -> None:
        group.delete()

    def move(self, course: Course, term_ids: list, group_id) -> None:
        group = None
        if group_id is not None:
            group = Group.objects.filter(course=course, pk=group_id).first()
            if group is None:
                raise serializers.ValidationError({"group": ["Esse grupo não existe mais."]})

        self._owned(self._terms(course), term_ids, MISSING_TERM).update(group=group)

    @transaction.atomic
    def delete_terms(self, course: Course, term_ids: list) -> None:
        terms = self._owned(self._terms(course), term_ids, MISSING_TERM)
        Term.objects.filter(course=course, deleted_at__isnull=False).delete()

        terms.update(deleted_at=timezone.now())

    def restore_terms(self, course: Course, term_ids: list) -> None:
        deleted = Term.objects.filter(course=course, deleted_at__isnull=False)

        self._owned(deleted, term_ids, "Não dá mais pra desfazer.").update(deleted_at=None)

    def add_terms(self, course: Course, texts: list[str]) -> None:
        new = {}
        for text in texts:
            new.setdefault(term_key(text), clean_text(text))

        Term.objects.filter(course=course, key__in=new, deleted_at__isnull=False).delete()
        Term.objects.bulk_create(
            [
                Term(
                    user_id=course.user_id,
                    course=course,
                    text=text,
                    key=key,
                    kind=Term.Kind.EXPRESSION if " " in text else Term.Kind.WORD,
                )
                for key, text in new.items()
            ],
            ignore_conflicts=True,
        )

    def _terms(self, course: Course):
        return Term.objects.filter(course=course, deleted_at__isnull=True)

    def _groups(self, course: Course):
        return Group.objects.filter(course=course).prefetch_related(
            Prefetch("terms", queryset=self._terms(course))
        )

    def _owned(self, terms, term_ids: list, message: str):
        owned = terms.filter(pk__in=term_ids)
        if owned.count() != len(set(term_ids)):
            raise serializers.ValidationError({"terms": [message]})

        return owned

    def _save_group(self, group: Group, data: dict) -> Group:
        name = data.get("name")
        others = Group.objects.filter(course=group.course).exclude(pk=group.pk)
        if name is not None and others.filter(name__iexact=name).exists():
            raise serializers.ValidationError({"name": [DUPLICATE_GROUP]})

        for field, value in data.items():
            setattr(group, field, value)

        try:
            with transaction.atomic():
                group.save()
        except IntegrityError as exc:
            raise serializers.ValidationError({"name": [DUPLICATE_GROUP]}) from exc

        return group
