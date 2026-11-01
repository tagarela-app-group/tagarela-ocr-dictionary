from datetime import timedelta

from django.db import migrations
from django.utils import timezone

INTERVAL_BY_LEVEL = {1: 4, 2: 8, 3: 16, 4: 24, 5: 32}


def fill_intervals(apps, schema_editor):
    Term = apps.get_model("vocabulary", "Term")
    now = timezone.now()
    for level, interval in INTERVAL_BY_LEVEL.items():
        Term.objects.filter(level=level).update(
            interval_days=interval,
            scheduled_days=interval,
            due_at=now,
            first_read_at=now,
            last_session_at=now - timedelta(days=interval),
        )


class Migration(migrations.Migration):
    dependencies = [
        ("vocabulary", "0009_memoria_do_termo"),
    ]

    operations = [
        migrations.RunPython(fill_intervals, migrations.RunPython.noop),
    ]
