import json
import sqlite3
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "run_page"))
from activity_locations import structured_location, needs_location
from backfill_locations import load_empty_location_rows


class LocationTests(unittest.TestCase):
    def test_iso_province_code_when_state_is_omitted(self):
        for code, province in [("CN-BJ", "北京市"), ("CN-HK", "香港特别行政区")]:
            data = json.loads(
                structured_location(
                    SimpleNamespace(
                        raw={
                            "address": {
                                "country_code": "cn",
                                "country": "中国",
                                "city": "昌平区",
                                "ISO3166-2-lvl4": code,
                            }
                        }
                    )
                )
            )
            self.assertEqual(data["province"], province)
            self.assertEqual(data["province_code"], code)

    def test_address_fields_ignore_street_names(self):
        location = SimpleNamespace(
            raw={
                "address": {
                    "country_code": "cn",
                    "country": "中国",
                    "state": "北京市",
                    "road": "河北省路",
                    "city": "北京市",
                }
            }
        )
        data = json.loads(structured_location(location))
        self.assertEqual(data["province"], "北京市")
        self.assertNotIn("road", data)
        self.assertFalse(needs_location(json.dumps(data)))

    def test_hong_kong_and_municipality(self):
        for code, state in [
            ("hk", "香港特别行政区"),
            ("mo", "澳门特别行政区"),
            ("cn", "北京市"),
        ]:
            data = json.loads(
                structured_location(
                    SimpleNamespace(
                        raw={
                            "address": {
                                "country_code": code,
                                "country": "中国",
                                "city": "北京市",
                            }
                        }
                    )
                )
            )
            self.assertEqual(data["province"], state)

    def test_failed_lookup_is_empty_and_unknown_remains_pending(self):
        self.assertEqual(structured_location(None), "")
        self.assertEqual(structured_location(SimpleNamespace(raw={})), "")
        for value in [None, "None", "China", "北京市, 中国", '{"country":"中国"}']:
            self.assertTrue(needs_location(value))

    def test_only_pending_routes_selected_before_limit(self):
        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)
        conn.execute(
            "CREATE TABLE activities (run_id, name, start_date_local, summary_polyline, location_country)"
        )
        good = '{"version":1,"country":"中国","province":"北京市"}'
        conn.executemany(
            "INSERT INTO activities VALUES (?, '', ?, ?, ?)",
            [
                (1, "2026-03", "abc", good),
                (2, "2026-02", "abc", "None"),
                (3, "2026-01", "", None),
                (4, "2025-01", "abc", "China"),
            ],
        )
        self.assertEqual([row[0] for row in load_empty_location_rows(conn, 1)], [2])
        self.assertEqual([row[0] for row in load_empty_location_rows(conn, 0)], [2, 4])
