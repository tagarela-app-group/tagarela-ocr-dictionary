from django.db import migrations


def fill(apps, schema_editor):
    CaptureTerm = apps.get_model("captures", "CaptureTerm")
    Term = apps.get_model("vocabulary", "Term")

    new = {}
    analyzed = CaptureTerm.objects.filter(capture__analyzed_at__isnull=False).order_by(
        "capture__analyzed_at", "start", "-end"
    )
    for term in analyzed.values("capture__user_id", "text"):
        text = " ".join(term["text"].split())
        new.setdefault((term["capture__user_id"], text.casefold()), text)

    Term.objects.bulk_create(
        [
            Term(
                user_id=user_id,
                text=text,
                key=key,
                kind="expression" if " " in text else "word",
            )
            for (user_id, key), text in new.items()
        ],
        ignore_conflicts=True,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("captures", "0002_sem_processamento_no_servidor"),
        ("vocabulary", "0001_inicial"),
    ]

    operations = [
        migrations.RunPython(fill, migrations.RunPython.noop),
    ]
