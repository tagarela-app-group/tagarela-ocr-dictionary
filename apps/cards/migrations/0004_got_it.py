from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cards", "0003_formality_revealed"),
    ]

    operations = [
        migrations.AddField(
            model_name="termcard",
            name="got_it",
            field=models.BooleanField(blank=True, null=True),
        ),
    ]
