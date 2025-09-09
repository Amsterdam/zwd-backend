from django.db import migrations


def compute_prefixed_dossier_id(case, hoa):
    # Values must match the Enum values defined in the model
    APPLICATION_ACTIVATIONTEAM = "Activatieteam"
    ADVICE_COURSE = "Cursus"
    ADVICE_HBO = "Haalbaarheidsonderzoek"
    ADVICE_ENERGY = "Energieadvies"

    if case.application_type == APPLICATION_ACTIVATIONTEAM:
        return f"{case.id}ACT"

    if case.advice_type == ADVICE_COURSE:
        return f"{case.id}CUR"
    if case.advice_type == ADVICE_HBO:
        return f"{case.id}HBO"
    if case.advice_type == ADVICE_ENERGY:
        # When HOA unknown, default to EAG (large)
        is_small = False
        if hoa is not None and getattr(hoa, "number_of_apartments", None) is not None:
            is_small = hoa.number_of_apartments <= 12
        return f"{case.id}{'EAK' if is_small else 'EAG'}"

    return str(case.id)


def forwards(apps, schema_editor):
    Case = apps.get_model("cases", "Case")
    HomeownerAssociation = apps.get_model(
        "homeownerassociation", "HomeownerAssociation"
    )

    for case in Case.objects.all().iterator():
        hoa = None
        if case.homeowner_association_id:
            try:
                hoa = HomeownerAssociation.objects.get(id=case.homeowner_association_id)
            except HomeownerAssociation.DoesNotExist:
                hoa = None
        case.prefixed_dossier_id = compute_prefixed_dossier_id(case, hoa)
        case.save(update_fields=["prefixed_dossier_id"])


def backwards(apps, schema_editor):
    Case = apps.get_model("cases", "Case")
    # Revert to None (field is nullable)
    Case.objects.all().update(prefixed_dossier_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0018_case_prefixed_dossier_id"),
        (
            "homeownerassociation",
            "0015_rename_number_of_appartments_homeownerassociation_number_of_apartments_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
