# Generated by Django 5.0.11 on 2025-02-28 09:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("homeownerassociation", "0011_alter_wijk_options"),
    ]

    operations = [
        migrations.CreateModel(
            name="PriorityZipCode",
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
                ("zip_code", models.CharField(max_length=6, unique=True)),
            ],
        ),
    ]
