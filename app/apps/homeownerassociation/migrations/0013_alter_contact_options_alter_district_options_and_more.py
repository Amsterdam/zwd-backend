# Generated by Django 5.0.11 on 2025-03-20 11:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("homeownerassociation", "0012_priorityzipcode"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="contact",
            options={"ordering": ["email"]},
        ),
        migrations.AlterModelOptions(
            name="district",
            options={
                "ordering": ["name"],
                "verbose_name": "Stadsdeel",
                "verbose_name_plural": "Stadsdelen",
            },
        ),
        migrations.AlterModelOptions(
            name="neighborhood",
            options={
                "ordering": ["name"],
                "verbose_name": "Buurt",
                "verbose_name_plural": "Buurten",
            },
        ),
        migrations.AlterModelOptions(
            name="priorityzipcode",
            options={
                "ordering": ["zip_code"],
                "verbose_name": "Prioriteitsbuurt postcode",
                "verbose_name_plural": "Prioriteitsbuurt postcodes",
            },
        ),
        migrations.AlterModelOptions(
            name="wijk",
            options={
                "ordering": ["name"],
                "verbose_name": "Wijk",
                "verbose_name_plural": "Wijken",
            },
        ),
    ]
