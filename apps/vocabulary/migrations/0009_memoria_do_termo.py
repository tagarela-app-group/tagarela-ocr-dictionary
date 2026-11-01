from django.db import migrations, models

import apps.vocabulary.models


class Migration(migrations.Migration):
    dependencies = [
        ("vocabulary", "0008_grupo_sem_usuario"),
    ]

    operations = [
        migrations.AddField(
            model_name="term",
            name="interval_days",
            field=models.FloatField(default=apps.vocabulary.models.start_interval_days),
        ),
        migrations.AddField(
            model_name="term",
            name="scheduled_days",
            field=models.FloatField(default=apps.vocabulary.models.first_review_days),
        ),
        migrations.AddField(
            model_name="term",
            name="due_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="term",
            name="last_session_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="term",
            name="ease",
            field=models.FloatField(default=1.0),
        ),
        migrations.AddField(
            model_name="term",
            name="first_read_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="term",
            name="audio_heard_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="term",
            name="study_points",
            field=models.FloatField(default=0.0),
        ),
    ]
