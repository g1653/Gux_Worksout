import datetime as dt
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "run_page"))
from garmin_timelines import timeline_from_streams
from backfill_temperatures import parse_duration


class GarminTimelineTests(unittest.TestCase):
    def activity(self, kind="Run"):
        return SimpleNamespace(
            run_id=-123,
            name="Test",
            start_date_local="2026-11-04 12:00:00",
            distance=100,
            elapsed_time=dt.timedelta(seconds=25),
            moving_time=dt.timedelta(seconds=20),
            type=kind,
            elevation_gain=250,
        )

    def test_recorded_pace_heart_rate_and_uncovered_tail(self):
        streams = {
            "time": {"data": [0, 10, 20]},
            "velocity_smooth": {"data": [4, 0, 3]},
            "heartrate": {"data": [120, None, 150]},
            "altitude": {"data": [10, 20, 30]},
        }
        result = timeline_from_streams(self.activity(), streams)
        self.assertEqual(result["bins"][0][:3], [0, 10, 250])
        self.assertEqual(result["bins"][1][3], "paused")
        self.assertEqual(result["bins"][-1][3], "unknown")
        self.assertEqual(result["heartrate_bins"][0][2], 120)
        self.assertIsNone(result["heartrate_bins"][1][2])
        self.assertTrue(result["elevation_bins"])

    def test_empty_recording_does_not_invent_metrics(self):
        result = timeline_from_streams(self.activity(), {})
        self.assertEqual(result["bins"], [])
        self.assertEqual(result["heartrate_bins"], [])

    def test_fractional_garmin_duration(self):
        self.assertEqual(parse_duration("1:02:03.500000").total_seconds(), 3723.5)
        self.assertEqual(parse_duration("1 day, 1:00:00.25").total_seconds(), 90000.25)
