import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('courses', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DailyWord',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date', models.DateField()),
                ('text', models.CharField(max_length=255)),
                ('kind', models.CharField(choices=[('word', 'Palavra'), ('expression', 'Expressão')], max_length=20)),
                ('phonetic', models.CharField(blank=True, max_length=255, null=True)),
                ('example', models.TextField()),
                ('meaning', models.TextField()),
                ('prompt_version', models.CharField(max_length=20)),
                ('model', models.CharField(max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='daily_words', to='courses.course')),
            ],
            options={
                'ordering': ['-date'],
                'constraints': [models.UniqueConstraint(fields=('course', 'date'), name='unique_daily_word_per_day')],
            },
        ),
    ]
