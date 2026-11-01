from datetime import datetime

from rest_framework import serializers

from apps.common.text import term_key
from apps.courses.tests.helpers import make_course
from apps.vocabulary.models import Group, Term


def make_group(user, name: str = "Viagem", **fields) -> Group:
    fields.setdefault("course", make_course(user))
    return Group.objects.create(name=name, **{"icon": "travel", "accent": "sky", **fields})


def api_datetime(value: datetime) -> str:
    return serializers.DateTimeField().to_representation(value)


def make_term(user, text: str, group: Group | None = None, **fields) -> Term:
    kind = Term.Kind.EXPRESSION if " " in text else Term.Kind.WORD
    fields.setdefault("course", group.course if group else make_course(user))
    return Term.objects.create(
        user=user, group=group, text=text, key=term_key(text), **{"kind": kind, **fields}
    )
