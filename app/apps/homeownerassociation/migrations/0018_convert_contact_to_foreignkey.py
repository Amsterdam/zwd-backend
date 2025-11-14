# Migration to convert Contact.homeowner_associations from ManyToMany to ForeignKey

from django.db import migrations, models
import django.db.models.deletion


def duplicate_contacts_with_multiple_hoas(apps, schema_editor):
    """
    For contacts that are linked to multiple HOAs, duplicate them so each HOA has its own contact.
    This preserves the relationship data before we convert to ForeignKey.
    """
    Contact = apps.get_model("homeownerassociation", "Contact")

    # Find all contacts and their associated HOAs
    contacts_to_process = []

    for contact in Contact.objects.prefetch_related("homeowner_associations").all():
        hoas = list(contact.homeowner_associations.all())
        if len(hoas) > 1:
            contacts_to_process.append((contact, hoas))

    # Duplicate contacts for additional HOAs
    for original_contact, hoas in contacts_to_process:
        # Keep the first HOA for the original contact
        first_hoa = hoas[0]
        additional_hoas = hoas[1:]

        # Create duplicates for each additional HOA
        for hoa in additional_hoas:
            duplicate_contact = Contact.objects.create(
                email=original_contact.email,
                phone=original_contact.phone,
                fullname=original_contact.fullname,
                role=original_contact.role,
            )
            duplicate_contact.homeowner_associations.add(hoa)

        # Remove additional HOAs from original contact, keeping only the first one
        original_contact.homeowner_associations.set([first_hoa])


def populate_homeowner_association_foreignkey(apps, schema_editor):
    """
    Populate the new homeowner_association ForeignKey field from the ManyToMany relationship.
    """
    Contact = apps.get_model("homeownerassociation", "Contact")

    for contact in Contact.objects.all():
        # Get the first (and now only) HOA from the ManyToMany relationship
        hoa = contact.homeowner_associations.first()
        if hoa:
            contact.homeowner_association = hoa
            contact.save()


def drop_manytomany_table(apps, schema_editor):
    """
    Drop the ManyToMany through table explicitly.
    This function ensures the operation happens outside of Django's transaction handling.
    """
    with schema_editor.connection.cursor() as cursor:
        # Disable all triggers on the table
        cursor.execute(
            "ALTER TABLE IF EXISTS homeownerassociation_contact_homeowner_associations DISABLE TRIGGER ALL;"
        )
        # Drop the table with CASCADE
        cursor.execute(
            "DROP TABLE IF EXISTS homeownerassociation_contact_homeowner_associations CASCADE;"
        )


class Migration(migrations.Migration):

    # Mark as non-atomic to allow operations to commit separately
    # This helps avoid PostgreSQL "pending trigger events" errors
    atomic = False

    dependencies = [
        ("homeownerassociation", "0017_add_hoa_communication_note"),
    ]

    operations = [
        # Step 1: Duplicate contacts that are linked to multiple HOAs
        migrations.RunPython(
            duplicate_contacts_with_multiple_hoas, migrations.RunPython.noop
        ),
        # Step 2: Add the new ForeignKey field (nullable initially)
        migrations.AddField(
            model_name="contact",
            name="homeowner_association",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="contacts",
                to="homeownerassociation.homeownerassociation",
            ),
        ),
        # Step 3: Populate the new ForeignKey field from ManyToMany
        migrations.RunPython(
            populate_homeowner_association_foreignkey, migrations.RunPython.noop
        ),
        # Step 4: Make the ForeignKey non-nullable
        migrations.AlterField(
            model_name="contact",
            name="homeowner_association",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="contacts",
                to="homeownerassociation.homeownerassociation",
            ),
        ),
        # Step 5: Remove the ManyToMany field using SeparateDatabaseAndState
        # This separates the database operation from the state change to avoid PostgreSQL trigger event issues
        migrations.SeparateDatabaseAndState(
            database_operations=[
                # Use RunPython to drop the table with explicit cursor handling
                migrations.RunPython(drop_manytomany_table, migrations.RunPython.noop),
            ],
            state_operations=[
                # Remove the field from Django's model state
                migrations.RemoveField(
                    model_name="contact",
                    name="homeowner_associations",
                ),
            ],
        ),
    ]
