import argparse
import json
import os
import logging
from types import SimpleNamespace
from backfill_locations import backfill_locations
from strava_auth import load_local_env

from backfill_temperatures import backfill_temperatures
from config import JSON_FILE, SQL_FILE
from generator import Generator
from strava_best_efforts import sync_best_efforts
from strava_power_efforts import sync_power_efforts
from strava_timeline_sync import backfill_timelines


# for only run type, we use the same logic as garmin_sync
def run_strava_sync(
    client_id,
    client_secret,
    refresh_token,
    sync_types: list = [],
    only_run=False,
    force=False,
    skip_temperature_backfill=False,
    temperature_limit=25,
    timeline_limit=20,
):
    logging.getLogger("stravalib.model").setLevel(logging.ERROR)
    logging.getLogger("stravalib.attributes").setLevel(logging.ERROR)
    generator = Generator(SQL_FILE)
    generator.set_strava_config(client_id, client_secret, refresh_token)
    # judge sync types is only running or not
    if not only_run and len(sync_types) == 1 and sync_types[0] == "running":
        only_run = True
    # if you want to refresh data change False to True
    generator.only_run = only_run
    generator.sync(force)
    # Keep known locations on network failure and retry missing ones every sync.
    backfill_locations(
        SimpleNamespace(
            db=SQL_FILE,
            json=JSON_FILE,
            limit=100,
            user_agent="g1653-workouts-location-sync",
            timeout=15,
            cache_precision=4,
            sleep=1.2,
            language="zh-CN",
            dry_run=False,
            commit_every=10,
            no_json=True,
        )
    )
    generator.session.expire_all()
    sync_best_efforts(generator.client, generator.session, limit=20, refresh=force)
    sync_power_efforts(generator.client, generator.session, limit=20, refresh=force)

    activities_list = generator.loadForMapping()
    with open(JSON_FILE, "w") as f:
        json.dump(activities_list, f, indent=0)

    if timeline_limit > 0:
        try:
            backfill_timelines(
                activities=activities_list,
                token=generator.access_token,
                limit=timeline_limit,
            )
        except Exception as error:
            print(f"Timeline backfill deferred after error: {error}")

    if skip_temperature_backfill:
        print("Skip temperature backfill")
        return

    try:
        backfill_temperatures(
            db_path=SQL_FILE,
            json_path=JSON_FILE,
            limit=temperature_limit,
            all_missing=False,
            sleep_seconds=0.2,
        )
    except Exception as error:
        print(f"Temperature backfill skipped after error: {error}")


if __name__ == "__main__":
    load_local_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("client_id", nargs="?", default=os.getenv("STRAVA_CLIENT_ID"))
    parser.add_argument(
        "client_secret", nargs="?", default=os.getenv("STRAVA_CLIENT_SECRET")
    )
    parser.add_argument(
        "refresh_token", nargs="?", default=os.getenv("STRAVA_CLIENT_REFRESH_TOKEN")
    )
    parser.add_argument(
        "--only-run",
        dest="only_run",
        action="store_true",
        help="if is only for running",
    )
    parser.add_argument(
        "--force",
        dest="force",
        action="store_true",
        help="sync all activities from strava instead of only recent activities",
    )
    parser.add_argument(
        "--skip-temperature-backfill",
        dest="skip_temperature_backfill",
        action="store_true",
        help="skip automatic Open-Meteo temperature backfill after sync",
    )
    parser.add_argument(
        "--temperature-limit",
        dest="temperature_limit",
        type=int,
        default=25,
        help="maximum number of recent missing activities to backfill temperature",
    )
    parser.add_argument(
        "--timeline-limit",
        type=int,
        default=20,
        help="maximum pending run/ride/hike timelines per sync; 0 skips backfill",
    )
    options = parser.parse_args()
    if not all((options.client_id, options.client_secret, options.refresh_token)):
        parser.error("Set Strava credentials in .env or environment variables.")
    run_strava_sync(
        options.client_id,
        options.client_secret,
        options.refresh_token,
        only_run=options.only_run,
        force=options.force,
        skip_temperature_backfill=options.skip_temperature_backfill,
        temperature_limit=options.temperature_limit,
        timeline_limit=options.timeline_limit,
    )
