from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("captures", "0006_sem_texto_original_nem_processamento"),
    ]

    operations = [
        migrations.AddField(
            model_name="captureterm",
            name="key",
            field=models.CharField(default="", max_length=255),
            preserve_default=False,
        ),
    ]
