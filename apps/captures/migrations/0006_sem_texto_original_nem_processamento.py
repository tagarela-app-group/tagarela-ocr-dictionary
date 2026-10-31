from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("captures", "0005_curso_obrigatorio"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="capture",
            name="original_text",
        ),
        migrations.RemoveField(
            model_name="capture",
            name="processed_at",
        ),
    ]
