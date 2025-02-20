# Generated by Django 5.0.8 on 2025-02-20 13:56

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Advisor",
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
                ("enabled", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("advice_type_energieadvies", models.BooleanField(default=False)),
                ("advice_type_hbo", models.BooleanField(default=False)),
                ("small_hoa", models.BooleanField(default=False)),
            ],
        ),
    ]
