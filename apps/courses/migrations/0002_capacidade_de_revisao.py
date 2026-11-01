from django.db import migrations, models

import apps.courses.models


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0001_initial"),
        ("vocabulary", "0008_grupo_sem_usuario"),
    ]

    operations = [
        migrations.AddField(
            model_name="course",
            name="review_capacity",
            field=models.PositiveSmallIntegerField(default=apps.courses.models.start_capacity),
        ),
        migrations.AddField(
            model_name="course",
            name="daily_limit",
            field=models.PositiveSmallIntegerField(default=apps.courses.models.start_capacity),
        ),
        migrations.AddField(
            model_name="course",
            name="last_active_on",
            field=models.DateField(blank=True, null=True),
        ),
    ]
