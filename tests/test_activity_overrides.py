import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "run_page"))
from activity_overrides import apply_activity_overrides, FOOTBALL_GARMIN_IDS
from config import MAPPING_TYPE
from generator.db import normalize_activity_type


class ActivityOverrideTests(unittest.TestCase):
    def test_all_selected_activities_survive_provider_type_refresh(self):
        for aid in FOOTBALL_GARMIN_IDS:
            row = SimpleNamespace(run_id=-aid, garmin_id=aid, type="Workout")
            apply_activity_overrides(row)
            self.assertEqual(row.type, "Soccer")
            row.type = "Workout"
            apply_activity_overrides(row)
            self.assertEqual(row.type, "Soccer")

    def test_unselected_workout_is_unchanged(self):
        row = SimpleNamespace(run_id=1, garmin_id=None, type="Workout")
        apply_activity_overrides(row)
        self.assertEqual(row.type, "Workout")

    def test_soccer_is_normalized_and_exportable(self):
        self.assertEqual(normalize_activity_type("soccer"), "Soccer")
        self.assertIn("Soccer", MAPPING_TYPE)
