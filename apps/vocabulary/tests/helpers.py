from apps.vocabulary.models import Group, Term
from apps.vocabulary.services import term_key


def make_group(user, name: str = "Viagem", **fields) -> Group:
    return Group.objects.create(
        user=user, name=name, **{"icon": "travel", "accent": "sky", **fields}
    )


def make_term(user, text: str, group: Group | None = None, **fields) -> Term:
    kind = Term.Kind.EXPRESSION if " " in text else Term.Kind.WORD
    return Term.objects.create(
        user=user, group=group, text=text, key=term_key(text), **{"kind": kind, **fields}
    )
