from contextlib import contextmanager
import importlib
from types import SimpleNamespace
from unittest.mock import MagicMock

from django.test import SimpleTestCase

add_missing_rental_payment_columns = importlib.import_module(
    "machines.migrations.0024_repair_rental_payment_columns"
).add_missing_rental_payment_columns


class RepairRentalPaymentColumnsMigrationTests(SimpleTestCase):
    def test_uses_backend_introspection_and_only_adds_missing_columns(self):
        cursor = MagicMock()

        @contextmanager
        def cursor_context():
            yield cursor

        introspection = MagicMock()
        introspection.get_table_description.return_value = [
            SimpleNamespace(name="id"),
            SimpleNamespace(name="amount_paid"),
        ]

        connection = MagicMock()
        connection.cursor.side_effect = cursor_context
        connection.introspection = introspection

        schema_editor = MagicMock()
        schema_editor.connection = connection
        schema_editor.quote_name.side_effect = lambda value: f'"{value}"'

        add_missing_rental_payment_columns(None, schema_editor)

        introspection.get_table_description.assert_called_once_with(
            cursor,
            "machines_rental",
        )
        cursor.execute.assert_not_called()
        schema_editor.execute.assert_any_call(
            'ALTER TABLE "machines_rental" ADD COLUMN "or_number" varchar(100) NOT NULL DEFAULT \'\''
        )
        schema_editor.execute.assert_any_call(
            'ALTER TABLE "machines_rental" ADD COLUMN "payment_notes" text NOT NULL DEFAULT \'\''
        )
        self.assertEqual(schema_editor.execute.call_count, 2)
