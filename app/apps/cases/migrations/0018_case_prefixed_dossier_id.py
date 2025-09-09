from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0017_alter_case_created"),
    ]

    operations = [
        migrations.AddField(
            model_name="case",
            name="prefixed_dossier_id",
            field=models.CharField(max_length=255, unique=True, null=True, blank=True),
        ),
    ]
