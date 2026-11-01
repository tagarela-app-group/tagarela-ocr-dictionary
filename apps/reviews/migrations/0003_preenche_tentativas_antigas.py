from django.db import migrations
from django.db.models import F
from django.db.models.functions import TruncDate


def fill_attempts(apps, schema_editor):
    ReviewAttempt = apps.get_model("reviews", "ReviewAttempt")
    ReviewAttempt.objects.update(
        played_at=F("created_at"),
        local_date=TruncDate("created_at"),
    )


class Migration(migrations.Migration):
    dependencies = [
        ("reviews", "0002_sinais_da_tentativa"),
    ]

    operations = [
        migrations.RunPython(fill_attempts, migrations.RunPython.noop),
    ]
