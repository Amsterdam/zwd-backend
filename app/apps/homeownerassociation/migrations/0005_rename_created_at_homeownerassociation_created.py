# Generated by Django 5.0.8 on 2024-10-31 08:20

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("homeownerassociation", "0004_alter_owner_name"),
    ]

    operations = [
        migrations.RenameField(
            model_name="homeownerassociation",
            old_name="created_at",
            new_name="created",
        ),
    ]