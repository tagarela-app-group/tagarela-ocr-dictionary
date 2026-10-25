from django.db import migrations


def fill(apps, schema_editor):
    Course = apps.get_model("courses", "Course")
    Group = apps.get_model("vocabulary", "Group")
    Term = apps.get_model("vocabulary", "Term")

    users = set(Group.objects.values_list("user_id", flat=True))
    users |= set(Term.objects.values_list("user_id", flat=True))
    for user_id in users:
        course, _ = Course.objects.get_or_create(
            user_id=user_id, learning="en", base="pt", defaults={"active": True}
        )
        Group.objects.filter(user_id=user_id).update(course=course)
        Term.objects.filter(user_id=user_id).update(course=course)


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0001_initial"),
        ("vocabulary", "0005_curso_nos_termos_e_grupos"),
    ]

    operations = [
        migrations.RunPython(fill, migrations.RunPython.noop),
    ]
