import unittest

from src.schema import TABLE_SPECS


class TableSchemaTest(unittest.TestCase):
    def test_supports_four_required_business_tables(self):
        self.assertEqual(
            set(TABLE_SPECS),
            {"inventory", "usage", "billing", "sla"},
        )

    def test_each_table_has_a_key_required_fields_and_chinese_labels(self):
        for role, spec in TABLE_SPECS.items():
            with self.subTest(role=role):
                self.assertTrue(spec.label_zh)
                self.assertIn(spec.key_field, spec.required_fields)
                self.assertGreater(len(spec.required_fields), 0)
                self.assertEqual(
                    set(spec.required_fields + spec.optional_fields),
                    set(spec.field_labels),
                )


if __name__ == "__main__":
    unittest.main()
