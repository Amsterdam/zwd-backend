# Generated by Django 5.0.11 on 2025-07-28 14:44

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0016_caseclosereason_caseclose"),
    ]

    operations = [
        migrations.AlterField(
            model_name="case",
            name="created",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
