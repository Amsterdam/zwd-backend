# Generated by Django 5.0.6 on 2024-07-26 10:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workflow', '0005_caseworkflow_case_state_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='caseworkflow',
            name='completed',
            field=models.BooleanField(default=False),
        ),
    ]
