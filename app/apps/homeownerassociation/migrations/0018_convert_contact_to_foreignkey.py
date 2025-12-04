# Migration to convert Contact.homeowner_associations from ManyToMany to ForeignKey

from django.db import migrations, models
import django.db.models.deletion


def column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table."""
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = %s AND column_name = %s
        );
        """,
        [table_name, column_name],
    )
    return cursor.fetchone()[0]


def table_exists(cursor, table_name):
    """Check if a table exists."""
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_name = %s
        );
        """,
        [table_name],
    )
    return cursor.fetchone()[0]


def duplicate_contacts_with_multiple_hoas(apps, schema_editor):
    """
    For contacts that are linked to multiple HOAs, duplicate them so each HOA has its own contact.
    This preserves the relationship data before we convert to ForeignKey.
    """
    Contact = apps.get_model("homeownerassociation", "Contact")

    # Check if ManyToMany table still exists (if not, this step has already completed)
    with schema_editor.connection.cursor() as cursor:
        if not table_exists(
            cursor, "homeownerassociation_contact_homeowner_associations"
        ):
            # ManyToMany table doesn't exist, so this step has already been completed
            return

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


def add_homeowner_association_field_if_not_exists(apps, schema_editor):
    """
    Add the homeowner_association ForeignKey field only if it doesn't already exist.
    """
    with schema_editor.connection.cursor() as cursor:
        if not column_exists(
            cursor, "homeownerassociation_contact", "homeowner_association_id"
        ):
            # Column doesn't exist, add it using raw SQL
            cursor.execute(
                """
                ALTER TABLE homeownerassociation_contact
                ADD COLUMN homeowner_association_id BIGINT NULL
                REFERENCES homeownerassociation_homeownerassociation(id)
                ON DELETE CASCADE;
                """
            )
            # Create the index
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS homeownerassociation_contact_homeowner_association_id_idx
                ON homeownerassociation_contact(homeowner_association_id);
                """
            )


def populate_homeowner_association_foreignkey(apps, schema_editor):
    """
    Populate the new homeowner_association ForeignKey field from the ManyToMany relationship.
    Only populate if the field is NULL (hasn't been populated yet).
    """
    Contact = apps.get_model("homeownerassociation", "Contact")

    # Check if ManyToMany table still exists (if not, this step has already completed)
    with schema_editor.connection.cursor() as cursor:
        if not table_exists(
            cursor, "homeownerassociation_contact_homeowner_associations"
        ):
            # ManyToMany table doesn't exist, so this step has already been completed
            return

    for contact in Contact.objects.filter(homeowner_association__isnull=True):
        # Get the first (and now only) HOA from the ManyToMany relationship
        hoa = contact.homeowner_associations.first()
        if hoa:
            contact.homeowner_association = hoa
            contact.save()


def make_homeowner_association_non_nullable(apps, schema_editor):
    """
    Make the homeowner_association field non-nullable only if it's still nullable.
    """
    with schema_editor.connection.cursor() as cursor:
        # Check if column exists
        if not column_exists(
            cursor, "homeownerassociation_contact", "homeowner_association_id"
        ):
            return

        cursor.execute(
            """
            SELECT is_nullable
            FROM information_schema.columns
            WHERE table_name = 'homeownerassociation_contact'
            AND column_name = 'homeowner_association_id';
            """
        )
        result = cursor.fetchone()
        if result and result[0] == "YES":
            # Column is still nullable, make it non-nullable
            # First ensure all contacts have a homeowner_association
            # Only try to populate from ManyToMany if the table still exists
            if table_exists(
                cursor, "homeownerassociation_contact_homeowner_associations"
            ):
                cursor.execute(
                    """
                    UPDATE homeownerassociation_contact
                    SET homeowner_association_id = (
                        SELECT homeownerassociation_id
                        FROM homeownerassociation_contact_homeowner_associations
                        WHERE contact_id = homeownerassociation_contact.id
                        LIMIT 1
                    )
                    WHERE homeowner_association_id IS NULL;
                    """
                )
            # Now make it non-nullable (only if no NULL values remain)
            # Check if there are any NULL values first
            cursor.execute(
                """
                SELECT COUNT(*) FROM homeownerassociation_contact
                WHERE homeowner_association_id IS NULL;
                """
            )
            null_count = cursor.fetchone()[0]
            if null_count == 0:
                cursor.execute(
                    """
                    ALTER TABLE homeownerassociation_contact
                    ALTER COLUMN homeowner_association_id SET NOT NULL;
                    """
                )


def drop_manytomany_table(apps, schema_editor):
    """
    Drop the ManyToMany through table explicitly.
    This function ensures the operation happens outside of Django's transaction handling.
    """
    with schema_editor.connection.cursor() as cursor:
        if table_exists(cursor, "homeownerassociation_contact_homeowner_associations"):
            # Drop the table with CASCADE, this handles all constraints and triggers automatically
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
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    add_homeowner_association_field_if_not_exists,
                    migrations.RunPython.noop,
                ),
            ],
            state_operations=[
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
            ],
        ),
        # Step 3: Populate the new ForeignKey field from ManyToMany
        migrations.RunPython(
            populate_homeowner_association_foreignkey, migrations.RunPython.noop
        ),
        # Step 4: Make the ForeignKey non-nullable
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    make_homeowner_association_non_nullable, migrations.RunPython.noop
                ),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name="contact",
                    name="homeowner_association",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="contacts",
                        to="homeownerassociation.homeownerassociation",
                    ),
                ),
            ],
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
