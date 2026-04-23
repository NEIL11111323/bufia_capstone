from django.db import migrations


def add_missing_rental_payment_columns(apps, schema_editor):
    table_name = "machines_rental"

    with schema_editor.connection.cursor() as cursor:
        description = schema_editor.connection.introspection.get_table_description(
            cursor,
            table_name,
        )

    existing_columns = {
        column.name if hasattr(column, "name") else column[0]
        for column in description
    }

    quoted_table_name = schema_editor.quote_name(table_name)

    if "amount_paid" not in existing_columns:
        schema_editor.execute(
            f'ALTER TABLE {quoted_table_name} ADD COLUMN "amount_paid" decimal NULL'
        )

    if "or_number" not in existing_columns:
        schema_editor.execute(
            f'ALTER TABLE {quoted_table_name} ADD COLUMN "or_number" varchar(100) NOT NULL DEFAULT \'\''
        )

    if "payment_notes" not in existing_columns:
        schema_editor.execute(
            f'ALTER TABLE {quoted_table_name} ADD COLUMN "payment_notes" text NOT NULL DEFAULT \'\''
        )


class Migration(migrations.Migration):

    dependencies = [
        ("machines", "0019_add_payment_fields_manual"),
        ("machines", "0023_alter_ricemillappointment_status_dryerrental"),
    ]

    operations = [
        migrations.RunPython(add_missing_rental_payment_columns, migrations.RunPython.noop),
    ]
