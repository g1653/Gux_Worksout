def clear_virtual_location(activity):
    if activity.type != "VirtualRide":
        return
    activity.summary_polyline = ""
    activity.location_country = None
    for field in (
        "temperature_min",
        "temperature_max",
        "temperature_source",
        "weather_code",
        "weather_source",
    ):
        setattr(activity, field, None)
