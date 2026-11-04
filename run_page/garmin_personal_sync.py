"""Read Garmin Personal API activities, preserving Strava records and locations."""

import argparse
import datetime as dt
import io
import json
import os
from pathlib import Path
import time
import zipfile

import fitdecode
import polyline
from garmin_personal_api import GarminPersonalApiClient, PersonalApiAuthenticator
from garmin_personal_api.errors import HttpError

from activity_matching import matching_activity
from backfill_locations import backfill_locations, rebuild_activities_json
from config import JSON_FILE, SQL_FILE
from generator.db import Activity, init_db, normalize_activity_type
from strava_auth import load_local_env
from garmin_timelines import needs_timeline, save_timeline
from backfill_temperatures import backfill_temperatures
from activity_privacy import clear_virtual_location

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache-garmin"
TYPE_MAP = {
    "lap_swimming": "Swim",
    "open_water_swimming": "Swim",
    "treadmill_running": "Run",
    "trail_running": "Trail Run",
    "soccer": "Workout",
    "other": "Workout",
    "yoga": "Workout",
    "driving_general": "RoadTrip",
    "indoor_cycling": "VirtualRide",
}


def activity_type(item):
    key = item["activityType"]["typeKey"]
    return TYPE_MAP.get(key, normalize_activity_type(key))


def route_from_zip(content):
    points = []
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        for name in archive.namelist():
            if not name.lower().endswith(".fit"):
                continue
            with fitdecode.FitReader(io.BytesIO(archive.read(name))) as reader:
                for frame in reader:
                    if (
                        not isinstance(frame, fitdecode.FitDataMessage)
                        or frame.name != "record"
                    ):
                        continue
                    lat = frame.get_value("position_lat", fallback=None)
                    lon = frame.get_value("position_long", fallback=None)
                    if lat is None or lon is None:
                        continue
                    lat, lon = lat * 180 / 2**31, lon * 180 / 2**31
                    if -90 <= lat <= 90 and -180 <= lon <= 180 and (lat or lon):
                        point = (lat, lon)
                        if not points or points[-1] != point:
                            points.append(point)
    return polyline.encode(points) if len(points) > 1 else ""


def merge_summary(session, item):
    aid = int(item["activityId"])
    kind = activity_type(item)
    invalid_date = False
    try:
        invalid_date = any(
            dt.datetime.fromisoformat(item[field]).year <= 1970
            for field in ("startTimeGMT", "startTimeLocal")
        )
    except (ValueError, TypeError, KeyError):
        invalid_date = True
    row = session.query(Activity).filter_by(garmin_id=aid).one_or_none()
    if row is None and not invalid_date:
        row = matching_activity(
            session.query(Activity)
            .filter_by(source="strava")
            .filter(Activity.garmin_id.is_(None))
            .all(),
            item["startTimeGMT"],
            kind,
            float(item.get("distance") or 0),
        )
    created = row is None
    if created:
        row = Activity(run_id=-aid, source="garmin", garmin_id=aid)
        session.add(row)
    row.garmin_id = aid
    if not invalid_date or row.source == "garmin":
        row.metrics_source = "garmin"
        row.garmin_invalid_date = invalid_date
        moving = item.get("movingDuration") or item.get("duration") or 0
        row.name = item.get("activityName") or kind
        row.type = kind
        row.distance = item.get("distance") or 0
        row.moving_time = dt.timedelta(seconds=moving)
        row.elapsed_time = dt.timedelta(
            seconds=item.get("elapsedDuration") or item.get("duration") or moving
        )
        row.start_date = item["startTimeGMT"]
        row.start_date_local = item["startTimeLocal"]
        row.average_heartrate = item.get("averageHR")
        row.average_speed = item.get("averageSpeed")
        row.elevation_gain = item.get("elevationGain")
    clear_virtual_location(row)
    return row, created


def sync(args):
    load_local_env()
    key = os.getenv("GARMIN_PERSONAL_API_KEY")
    if not key:
        raise RuntimeError("GARMIN_PERSONAL_API_KEY is required")
    region = os.getenv("GARMIN_REGION", "CN").upper()
    if region not in {"CN", "GLOBAL"}:
        raise ValueError("GARMIN_REGION must be CN or GLOBAL")
    os.environ["GARMIN_PERSONAL_API_BASE_URL"] = (
        "https://personal.connectapi.garmin." + ("cn" if region == "CN" else "com")
    )
    CACHE.mkdir(exist_ok=True)
    with PersonalApiAuthenticator(
        bearer_token_cache_file=CACHE / "token.json", timeout=45
    ) as auth:
        token = auth.obtain_token(key)
    session = init_db(SQL_FILE)
    total = created = linked = routes = failures = 0
    try:
        with GarminPersonalApiClient(token.access_token, timeout=60) as client:
            start = 0
            while True:
                # China endpoint accepts the official default page size (20).
                batch = client.search_activities(start=start, limit=20)
                if not isinstance(batch, list):
                    raise RuntimeError("Unexpected Garmin activity list")
                for item in batch:
                    total += 1
                    if item["activityType"]["typeKey"] == "incident_detected":
                        continue  # Safety event, not an independent workout.
                    row, added = merge_summary(session, item)
                    created += added
                    linked += row.source == "strava"
                    aid = int(item["activityId"])
                    cache_file = CACHE / f"{aid}.zip"
                    if (
                        not row.summary_polyline and not row.garmin_route_checked
                    ) or needs_timeline(row):
                        try:
                            if not cache_file.exists():
                                cache_file.write_bytes(client.download_activity(aid))
                                time.sleep(0.3)
                            route = route_from_zip(cache_file.read_bytes())
                            if route and row.type != "VirtualRide":
                                row.summary_polyline = route
                                routes += 1
                            row.garmin_route_checked = True
                            if needs_timeline(row):
                                save_timeline(row, cache_file.read_bytes())
                        except HttpError as error:
                            if error.status_code in (401, 403, 429):
                                raise
                            failures += 1
                            print(
                                f"Garmin {aid}: FIT deferred (HTTP {error.status_code})",
                                flush=True,
                            )
                        except (
                            ValueError,
                            zipfile.BadZipFile,
                            fitdecode.FitError,
                        ) as error:
                            failures += 1
                            print(
                                f"Garmin {aid}: FIT deferred ({type(error).__name__})",
                                flush=True,
                            )
                    session.commit()
                rebuild_activities_json(SQL_FILE, JSON_FILE)
                print(
                    f"Garmin checked={total}, new={created}, linked_strava={linked}, routes={routes}",
                    flush=True,
                )
                if len(batch) < 20:
                    break
                start += len(batch)
                time.sleep(0.5)
    finally:
        session.close()
        rebuild_activities_json(SQL_FILE, JSON_FILE)
    if not args.skip_locations:
        from types import SimpleNamespace

        backfill_locations(
            SimpleNamespace(
                db=SQL_FILE,
                json=JSON_FILE,
                limit=0,
                user_agent="g1653-workouts-garmin-location",
                timeout=15,
                cache_precision=4,
                sleep=1.2,
                language="zh-CN",
                dry_run=False,
                commit_every=10,
                no_json=False,
            )
        )
    backfill_temperatures(db_path=SQL_FILE, json_path=JSON_FILE, limit=100)
    print(
        json.dumps(
            dict(
                garmin_total=total,
                created=created,
                linked_strava=linked,
                routes_added=routes,
                deferred_files=failures,
            )
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-locations", action="store_true")
    args = parser.parse_args()
    try:
        sync(args)
    except Exception as error:
        # Never echo API response bodies or request headers containing credentials.
        print(
            f"Garmin sync failed: {type(error).__name__}, HTTP {getattr(error, 'status_code', 'n/a')}"
        )
        raise SystemExit(1) from None
