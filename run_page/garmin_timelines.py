"""Convert recorded Garmin FIT samples to the dashboard's elapsed-time strips."""

import datetime as dt
import io
import zipfile
import fitdecode
from activity_matching import utc_date
from strava_pace_preview import sample_bins, activity_bins, finite_number
from strava_timeline_sync import (
    STORE,
    atomic_json,
    read_json,
    normalize_streams,
    heartrate_bins,
    route_points,
    record_summary,
)

VERSION = 1


def fit_streams(content, start):
    records = []
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        for name in archive.namelist():
            if not name.lower().endswith(".fit"):
                continue
            with fitdecode.FitReader(io.BytesIO(archive.read(name))) as reader:
                for frame in reader:
                    if (
                        isinstance(frame, fitdecode.FitDataMessage)
                        and frame.name == "record"
                    ):
                        records.append(
                            {
                                f: frame.get_value(f, fallback=None)
                                for f in (
                                    "timestamp",
                                    "enhanced_speed",
                                    "speed",
                                    "heart_rate",
                                    "power",
                                    "enhanced_altitude",
                                    "altitude",
                                    "position_lat",
                                    "position_long",
                                    "distance",
                                )
                            }
                        )
    records = [r for r in records if isinstance(r["timestamp"], dt.datetime)]
    if not records:
        return {}
    origin = min(utc_date(start), utc_date(records[0]["timestamp"]))
    streams = {
        k: {"data": []}
        for k in ("time", "velocity_smooth", "heartrate", "watts", "altitude", "latlng")
    }
    previous = None
    for row in records:
        t = (utc_date(row["timestamp"]) - origin).total_seconds()
        speed = (
            row["enhanced_speed"] if row["enhanced_speed"] is not None else row["speed"]
        )
        if (
            speed is None
            and previous
            and row["distance"] is not None
            and previous["distance"] is not None
        ):
            gap = (
                utc_date(row["timestamp"]) - utc_date(previous["timestamp"])
            ).total_seconds()
            delta = row["distance"] - previous["distance"]
            if 0 < gap <= 30 and delta >= 0:
                speed = delta / gap
        lat, lon = row["position_lat"], row["position_long"]
        point = (
            [lat * 180 / 2**31, lon * 180 / 2**31]
            if lat is not None and lon is not None
            else None
        )
        if point and (
            not (-90 <= point[0] <= 90 and -180 <= point[1] <= 180) or point == [0, 0]
        ):
            point = None
        values = [
            t,
            speed,
            row["heart_rate"],
            row["power"],
            (
                row["enhanced_altitude"]
                if row["enhanced_altitude"] is not None
                else row["altitude"]
            ),
            point,
        ]
        for key, value in zip(streams, values):
            streams[key]["data"].append(value)
        previous = row
    return normalize_streams(streams)


def timeline_from_streams(activity, streams):
    stamp = dt.datetime.now(dt.timezone.utc).isoformat()
    duration = activity.elapsed_time.total_seconds() if activity.elapsed_time else 0
    times = streams.get("time", {}).get("data", [])
    elapsed = max(duration, times[-1] if times else 0)
    group = (
        "run"
        if activity.type in {"Run", "Trail Run"}
        else (
            "ride"
            if activity.type in {"Ride", "VirtualRide", "Indoor Ride"}
            else "hike" if activity.type == "Hike" else None
        )
    )
    metric, bins = (
        activity_bins(streams, elapsed, prefer_power=group == "ride")
        if times
        else ("pace", [])
    )
    if group not in {"run", "ride"}:
        bins = []
    item = dict(
        id=activity.run_id,
        name=activity.name,
        start_date_local=activity.start_date_local,
        distance=activity.distance,
        elapsed_time=elapsed,
        moving_time=activity.moving_time.total_seconds() if activity.moving_time else 0,
        metric=metric,
        bins=bins,
        sport_group=group,
        source="garmin",
        garmin_fit_version=VERSION,
        fetched_at=stamp,
        timeline_checked_at=stamp,
        route_checked_at=stamp,
        heartrate_checked_at=stamp,
        speed_checked_at=stamp,
        elevation_checked_at=stamp,
        climbs_checked_at=stamp,
        climbs=[],
        route_points=route_points(streams),
        heartrate_bins=heartrate_bins(streams, elapsed) if times else [],
        elevation_bins=[],
    )
    if times and (activity.elevation_gain or 0) > 200 and group:
        values = streams.get("altitude", {}).get("data", [])
        if any(finite_number(v) for v in values):
            item["elevation_bins"] = sample_bins(
                times, values, elapsed=elapsed, metric="elevation"
            )
    if metric == "power":
        item["speed_bins"] = activity_bins(streams, elapsed)[1]
    return item


def needs_timeline(activity):
    if not activity.garmin_id or activity.garmin_invalid_date:
        return False
    item = read_json(STORE / f"{activity.run_id}.json", {})
    return item.get("garmin_fit_version") != VERSION


def fill_missing_channels(item, previous):
    # Garmin owns recorded channels; Strava can fill a channel absent from FIT.
    for key in ("bins", "heartrate_bins", "elevation_bins", "speed_bins"):
        recorded = any(b[2] is not None for b in item.get(key, []))
        if not recorded and previous.get(key):
            item[key] = previous[key]
            item["elapsed_time"] = max(
                item["elapsed_time"], previous.get("elapsed_time", 0)
            )
            if key == "bins":
                item["metric"] = previous.get("metric", "pace")
    if not item["route_points"] and previous.get("route_points"):
        item["route_points"] = previous["route_points"]
    if previous.get("climbs"):
        item["climbs"] = previous["climbs"]
        item["climbs_source"] = previous.get("climbs_source", "strava_segments")
    return item


def save_timeline(activity, content):
    item = timeline_from_streams(activity, fit_streams(content, activity.start_date))
    previous = read_json(STORE / f"{activity.run_id}.json", {})
    fill_missing_channels(item, previous)
    if activity.type == "VirtualRide":
        item.update(route_points=[], elevation_bins=[], climbs=[])
    atomic_json(STORE / f"{activity.run_id}.json", item)
    manifest = read_json(STORE / "index.json", {"version": 1, "activities": {}})
    manifest["activities"][str(activity.run_id)] = record_summary(
        item, activity.to_dict(), item["fetched_at"]
    )
    manifest["generated_at"] = item["fetched_at"]
    atomic_json(STORE / "index.json", manifest)
    return item
