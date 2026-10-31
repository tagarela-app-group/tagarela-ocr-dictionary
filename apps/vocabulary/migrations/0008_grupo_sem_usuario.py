from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("vocabulary", "0007_curso_obrigatorio"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="group",
            name="user",
        ),
    ]
