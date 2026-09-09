import unittest

import pandas as pd

from src.intake import (
    DataInputError,
    apply_mapping,
    read_csv_bytes,
    suggest_mapping,
    validate_mapping,
)
from src.schema import TABLE_SPECS


class CsvReadingTest(unittest.TestCase):
    def test_reads_utf8_and_gb18030_csv(self):
        text = "资源池编号,GPU数量\n池-1,8\n"
        for encoding in ("utf-8-sig", "gb18030"):
            with self.subTest(encoding=encoding):
                frame = read_csv_bytes(text.encode(encoding))
                self.assertEqual(frame.iloc[0, 1], 8)

    def test_rejects_empty_file(self):
        with self.assertRaisesRegex(DataInputError, "空文件"):
            read_csv_bytes(b"")


class MappingTest(unittest.TestCase):
    def setUp(self):
        self.spec = TABLE_SPECS["inventory"]

    def test_suggests_exact_names_and_known_chinese_aliases(self):
        columns = ["resource_pool_id", "团队编号", "GPU型号", "GPU数量", "区域", "采购方式", "有效小时费率"]
        mapping = suggest_mapping(columns, self.spec)
        self.assertEqual(mapping["resource_pool_id"], "resource_pool_id")
        self.assertEqual(mapping["team_id"], "团队编号")
        self.assertEqual(mapping["effective_hourly_rate_usd"], "有效小时费率")

    def test_reports_missing_required_and_reused_source_columns(self):
        mapping = {field: None for field in self.spec.required_fields + self.spec.optional_fields}
        mapping["resource_pool_id"] = "编号"
        mapping["team_id"] = "编号"
        errors = validate_mapping(mapping, self.spec)
        self.assertTrue(any("尚未映射" in error for error in errors))
        self.assertTrue(any("重复使用" in error for error in errors))

    def test_applies_mapping_without_changing_source_frame(self):
        source = pd.DataFrame({"资源池": ["GPU-1"], "数量": [4], "备注": ["保留"]})
        mapped = apply_mapping(source, {"resource_pool_id": "资源池", "gpu_count": "数量"})
        self.assertEqual(list(source.columns), ["资源池", "数量", "备注"])
        self.assertEqual(list(mapped.columns), ["resource_pool_id", "gpu_count"])
        self.assertEqual(mapped.iloc[0]["gpu_count"], 4)


if __name__ == "__main__":
    unittest.main()
