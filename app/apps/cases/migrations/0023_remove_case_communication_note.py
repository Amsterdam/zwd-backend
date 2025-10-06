# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0022_casecommunicationnote"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="case",
            name="communication_note",
        ),
    ]
