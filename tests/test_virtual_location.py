import sys, unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "run_page"))
from activity_privacy import clear_virtual_location


class VirtualLocationTest(unittest.TestCase):
    def test_virtual_location_removed_without_changing_training_data(self):
        row = SimpleNamespace(
            type="VirtualRide",
            summary_polyline="route",
            location_country="中国",
            distance=12000,
            average_heartrate=140,
        )
        clear_virtual_location(row)
        self.assertEqual(row.summary_polyline, "")
        self.assertIsNone(row.location_country)
        self.assertEqual(row.distance, 12000)
        self.assertEqual(row.average_heartrate, 140)

    def test_outdoor_locations_preserved(self):
        row = SimpleNamespace(
            type="Ride", summary_polyline="route", location_country="中国"
        )
        clear_virtual_location(row)
        self.assertEqual(row.summary_polyline, "route")
