from django.db import migrations


def repair_core_schema(apps, schema_editor):
    connection = schema_editor.connection
    introspection = connection.introspection

    def get_columns(cursor, table_name):
        return {
            col.name
            for col in introspection.get_table_description(cursor, table_name)
        }

    def add_column_if_missing(cursor, table_name, column_name, column_sql):
        columns = get_columns(cursor, table_name)
        if column_name in columns:
            return

        quoted_table = schema_editor.quote_name(table_name)
        quoted_column = schema_editor.quote_name(column_name)
        schema_editor.execute(
            f"ALTER TABLE {quoted_table} "
            f"ADD COLUMN {quoted_column} {column_sql}"
        )

    with connection.cursor() as cursor:
        tables = set(introspection.table_names(cursor))

        if "core_patientprofile" in tables:
            add_column_if_missing(cursor, "core_patientprofile", "risk_score", "REAL NULL")
            add_column_if_missing(
                cursor,
                "core_patientprofile",
                "prescription_image",
                "varchar(100) NULL",
            )
            add_column_if_missing(
                cursor,
                "core_patientprofile",
                "prescription_text",
                "TEXT NULL",
            )
            add_column_if_missing(cursor, "core_patientprofile", "qr_code", "varchar(100) NULL")
            add_column_if_missing(
                cursor,
                "core_patientprofile",
                "created_at",
                "datetime NULL",
            )

        if "core_doctorprofile" in tables:
            add_column_if_missing(
                cursor,
                "core_doctorprofile",
                "created_at",
                "datetime NULL",
            )

        if "core_doctorpatient" not in tables:
            doctor_patient_model = apps.get_model("core", "DoctorPatient")
            schema_editor.create_model(doctor_patient_model)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_delete_doctorpatient"),
    ]

    operations = [
        migrations.RunPython(repair_core_schema, reverse_code=migrations.RunPython.noop),
    ]
