# Generated by Django 5.0.6 on 2024-07-24 08:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0003_genericcompletedtask"),
    ]

    operations = [
        migrations.AddField(
            model_name="genericcompletedtask",
            name="case_user_task_id",
            field=models.CharField(default="-1", max_length=255),
        ),
    ]
