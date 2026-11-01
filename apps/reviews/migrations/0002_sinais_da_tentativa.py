import datetime

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("reviews", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="reviewattempt",
            name="role",
            field=models.CharField(
                choices=[
                    ("first_review", "Primeira revisão"),
                    ("session", "Sessão"),
                    ("retest", "Reteste"),
                    ("extra", "Sem efeito"),
                ],
                default="session",
                max_length=12,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="reviewattempt",
            name="played_at",
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="reviewattempt",
            name="local_date",
            field=models.DateField(default=datetime.date(2026, 1, 1)),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="reviewattempt",
            name="seen_sentence",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="reviewattempt",
            name="used_slow",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="reviewattempt",
            name="errors",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="reviewattempt",
            name="hints",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="reviewattempt",
            name="audio_replays",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="reviewattempt",
            name="response_ms",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="reviewattempt",
            name="points",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="reviewattempt",
            name="level_before",
            field=models.PositiveSmallIntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="reviewattempt",
            name="interval_before",
            field=models.FloatField(default=2.0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="reviewattempt",
            name="interval_days",
            field=models.FloatField(default=2.0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="reviewattempt",
            name="due_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
