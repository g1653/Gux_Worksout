import datetime as dt
import io
import zipfile
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
import polyline

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "run_page"))
from activity_matching import matching_activity
from garmin_personal_sync import merge_summary, activity_type, route_from_zip
from generator.db import Activity, init_db, update_or_create_activity


class GarminTests(unittest.TestCase):
    def test_invalid_epoch_date_is_preserved_but_excluded_from_dashboard(self):
        from generator import Generator

        self.item.update(
            startTimeGMT="1970-01-01 00:00:00", startTimeLocal="1970-01-01 08:00:00"
        )
        row, _ = merge_summary(self.session, self.item)
        self.session.commit()
        self.assertTrue(row.garmin_invalid_date)
        generator = Generator.__new__(Generator)
        generator.session = self.session
        self.assertEqual(generator.loadForMapping(), [])
        self.assertEqual(self.session.query(Activity).count(), 1)

    def test_fit_coordinates_are_converted_without_inventing_indoor_routes(self):
        class Record:
            name = "record"

            def __init__(self, lat, lon):
                self.values = {"position_lat": lat, "position_long": lon}

            def get_value(self, name, fallback=None):
                return self.values.get(name, fallback)

        payload = io.BytesIO()
        with zipfile.ZipFile(payload, "w") as archive:
            archive.writestr("activity.fit", b"fixture")
        reader = MagicMock()
        reader.__enter__.return_value = [
            Record(None, None),
            Record(2**29, 2**30),
            Record(2**29 + 10000, 2**30 + 10000),
        ]
        with (
            patch("garmin_personal_sync.fitdecode.FitDataMessage", Record),
            patch("garmin_personal_sync.fitdecode.FitReader", return_value=reader),
        ):
            points = polyline.decode(route_from_zip(payload.getvalue()))
            self.assertEqual(points[0], (45, 90))
            self.assertEqual(len(points), 2)
            reader.__enter__.return_value = [Record(None, None)]
            self.assertEqual(route_from_zip(payload.getvalue()), "")

    def setUp(self):
        self.session = init_db(":memory:")
        self.addCleanup(self.session.close)
        self.item = dict(
            activityId=42,
            activityName="Run",
            activityType={"typeKey": "running"},
            startTimeGMT="2026-11-04 06:04:14",
            startTimeLocal="2026-11-04 14:04:14",
            distance=11000,
            duration=3600,
            movingDuration=3500,
            elapsedDuration=3700,
        )

    def test_merge_preserves_strava_metrics_route_and_location(self):
        row = Activity(
            run_id=123,
            source="strava",
            type="Run",
            distance=11100,
            start_date="2026-11-04 06:04:14+00:00",
            summary_polyline="existing",
            location_country="北京市, 中国",
            name="existing",
        )
        self.session.add(row)
        self.session.commit()
        result, created = merge_summary(self.session, self.item)
        self.assertFalse(created)
        self.assertEqual(
            (result.run_id, result.garmin_id, result.distance), (123, 42, 11100)
        )
        self.assertEqual(
            (result.summary_polyline, result.location_country),
            ("existing", "北京市, 中国"),
        )
        self.session.commit()
        merge_summary(self.session, self.item)
        self.assertEqual(self.session.query(Activity).count(), 1)

    def test_new_garmin_then_strava_becomes_one_record(self):
        row, created = merge_summary(self.session, self.item)
        self.session.commit()
        self.assertTrue(created)
        self.assertEqual(row.run_id, -42)
        row.summary_polyline = "preserved"
        incoming = SimpleNamespace(
            id=456,
            source="strava",
            name="Strava Run",
            type="Run",
            start_date="2026-11-04 06:04:14+00:00",
            start_date_local="2026-11-04 14:04:14",
            distance=11100,
            moving_time=dt.timedelta(seconds=3500),
            elapsed_time=dt.timedelta(seconds=3700),
            average_heartrate=150,
            average_speed=3,
            elevation_gain=10,
            map=None,
        )
        update_or_create_activity(self.session, incoming)
        self.session.commit()
        self.assertEqual(self.session.query(Activity).count(), 1)
        result = self.session.get(Activity, 456)
        self.assertEqual(result.garmin_id, 42)
        self.assertEqual(result.summary_polyline, "preserved")

    def test_ambiguous_or_different_workout_is_not_merged(self):
        row = SimpleNamespace(
            type="Run", distance=11000, start_date=self.item["startTimeGMT"]
        )
        self.assertIsNone(
            matching_activity([row, row], self.item["startTimeGMT"], "Run", 11000)
        )
        self.assertIsNone(
            matching_activity([row], self.item["startTimeGMT"], "Ride", 11000)
        )
        self.assertIsNone(
            matching_activity([row], self.item["startTimeGMT"], "Run", 20000)
        )
        self.assertIsNone(matching_activity([row], "2026-11-04 06:10:00", "Run", 11000))

    def test_swimming_and_transport_types(self):
        self.assertEqual(
            activity_type({"activityType": {"typeKey": "lap_swimming"}}), "Swim"
        )
        self.assertEqual(
            activity_type({"activityType": {"typeKey": "driving_general"}}), "RoadTrip"
        )
