"""User-selected sport corrections, keyed by stable provider identities."""

FOOTBALL_GARMIN_IDS = {492444762, 493748614, 494804319, 641611553, 641635199}
FOOTBALL_STRAVA_IDS = {20222185896, 20222185692, 20523819012, 20523818876}


def apply_activity_overrides(activity):
    if (
        activity.garmin_id in FOOTBALL_GARMIN_IDS
        or activity.run_id in FOOTBALL_STRAVA_IDS
    ):
        activity.type = "Soccer"
