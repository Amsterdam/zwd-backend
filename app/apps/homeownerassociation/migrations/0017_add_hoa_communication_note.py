# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("homeownerassociation", "0016_add_annotation"),
    ]

    operations = [
        migrations.CreateModel(
            name="HomeownerAssociationCommunicationNote",
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
                ("note", models.TextField()),
                ("author_name", models.CharField(blank=True, max_length=255)),
                ("date", models.DateTimeField(blank=True, null=True)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now=True)),
                (
                    "author",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="homeownerassociation_communication_note_author",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "homeowner_association",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="communication_notes",
                        to="homeownerassociation.homeownerassociation",
                    ),
                ),
            ],
            options={
                "db_table": "homeownerassociation_communicationnote",
                "verbose_name": "Communication note",
                "verbose_name_plural": "Communication notes",
                "ordering": ["-date"],
            },
        ),
    ]
