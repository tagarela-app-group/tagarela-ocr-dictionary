from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("vocabulary", "0010_prazo_pelo_nivel"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="term",
            name="level",
        ),
    ]
