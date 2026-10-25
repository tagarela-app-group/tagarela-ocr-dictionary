from django.db import migrations


def fill(apps, schema_editor):
    Course = apps.get_model("courses", "Course")
    Capture = apps.get_model("captures", "Capture")

    for user_id in set(Capture.objects.values_list("user_id", flat=True)):
        course, _ = Course.objects.get_or_create(
            user_id=user_id, learning="en", base="pt", defaults={"active": True}
        )
        Capture.objects.filter(user_id=user_id).update(course=course)


class Migration(migrations.Migration):
    dependencies = [
        ("captures", "0003_curso_nas_capturas"),
        ("courses", "0001_initial"),
        ("vocabulary", "0006_preenche_curso"),
    ]

    operations = [
        migrations.RunPython(fill, migrations.RunPython.noop),
    ]
