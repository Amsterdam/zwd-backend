# Generated migration for moving Course from AdviceType to ApplicationType

from django.db import migrations, models
from enum import Enum


class ApplicationType(Enum):
    ADVICE = "Advies"
    ACTIVATIONTEAM = "Activatieteam"
    COURSE = "Cursus"

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]


class AdviceType(Enum):
    ENERGY_ADVICE = "Energieadvies"
    HBO = "Haalbaarheidsonderzoek"

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]


def migrate_course_cases_forward(apps, schema_editor):
    """Move cases with advice_type='Cursus' to application_type='Cursus'"""
    Case = apps.get_model("cases", "Case")

    # Find all cases with advice_type = "Cursus"
    cursus_cases = Case.objects.filter(advice_type="Cursus")
    count = cursus_cases.count()

    if count > 0:
        # Update them to have application_type = "Cursus" and advice_type = None
        cursus_cases.update(application_type="Cursus", advice_type=None)
        print(
            f"Migrated {count} case(s) from advice_type='Cursus' to application_type='Cursus'"
        )
    else:
        print("No cases with advice_type='Cursus' found to migrate")


def migrate_course_cases_backward(apps, schema_editor):
    """Revert: Move cases with application_type='Cursus' back to advice_type='Cursus'"""
    Case = apps.get_model("cases", "Case")

    # Find all cases with application_type = "Cursus"
    cursus_cases = Case.objects.filter(application_type="Cursus")
    count = cursus_cases.count()

    if count > 0:
        # Update them back - need to set application_type to a valid old value
        cursus_cases.update(application_type="Advies", advice_type="Cursus")
        print(f"Reverted {count} case(s) back to advice_type='Cursus'")
    else:
        print("No cases with application_type='Cursus' found to revert")


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0024_remove_casecommunicationnote"),
    ]

    operations = [
        # First, alter the application_type field to accept the new COURSE choice
        migrations.AlterField(
            model_name="case",
            name="application_type",
            field=models.CharField(
                choices=ApplicationType.choices(),
                default="Advies",
            ),
        ),
        # Then, alter the advice_type field to remove COURSE choice
        migrations.AlterField(
            model_name="case",
            name="advice_type",
            field=models.CharField(
                choices=AdviceType.choices(),
                blank=True,
                null=True,
            ),
        ),
        # Finally, migrate the data
        migrations.RunPython(
            migrate_course_cases_forward, migrate_course_cases_backward
        ),
    ]
