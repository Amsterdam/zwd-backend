# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("homeownerassociation", "0018_convert_contact_to_foreignkey"),
    ]

    operations = [
        migrations.AddField(
            model_name="homeownerassociationcommunicationnote",
            name="is_imported",
            field=models.BooleanField(default=False),
        ),
    ]
