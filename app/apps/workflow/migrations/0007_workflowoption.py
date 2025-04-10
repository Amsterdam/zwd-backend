# Generated by Django 5.0.8 on 2024-11-20 09:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0006_caseworkflow_completed"),
    ]

    operations = [
        migrations.CreateModel(
            name="WorkflowOption",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("message_name", models.CharField(max_length=255)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
    ]
