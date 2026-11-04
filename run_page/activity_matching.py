"""Conservative cross-provider matching; ambiguous matches stay separate."""

from datetime import datetime, timezone


def utc_date(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def sport_family(kind):
    return {
        "Soccer": "Workout",
        "Trail Run": "Run",
        "TrailRun": "Run",
        "VirtualRun": "Run",
        "Indoor Ride": "Ride",
        "VirtualRide": "Ride",
    }.get(kind, kind)


def matching_activity(rows, start, kind, distance):
    matches = []
    start = utc_date(start)
    for row in rows:
        if sport_family(row.type) != sport_family(kind):
            continue
        if (
            not row.start_date
            or abs((utc_date(row.start_date) - start).total_seconds()) > 90
        ):
            continue
        old_distance = float(row.distance or 0)
        if abs(old_distance - distance) > max(100, max(old_distance, distance) * 0.05):
            continue
        matches.append(row)
    return matches[0] if len(matches) == 1 else None
