# Generated by Django 5.0.11 on 2025-03-20 11:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0009_workflowoption_enabled_on_case_closed"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="caseworkflow",
            name="case_state_type",
        ),
    ]
