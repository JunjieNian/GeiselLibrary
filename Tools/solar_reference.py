"""NOAA-style approximate solar geometry; standard library only.

Target site: Geisel Library, UC San Diego. Times are 2026-09-30 PDT (UTC-7).
Azimuth is degrees clockwise from true north. Directional-light rotations
are outgoing light-ray directions, not the direction from observer to sun.
Reference equations: https://gml.noaa.gov/grad/solcalc/calcdetails.html
"""
import datetime as dt
import json
import math
from pathlib import Path

LATITUDE = 32.88116
LONGITUDE = -117.23765
PDT = dt.timezone(dt.timedelta(hours=-7), "PDT")


def solar_position(local_time, latitude=LATITUDE, longitude=LONGITUDE):
    if local_time.tzinfo is None:
        raise ValueError("Use a timezone-aware datetime")
    utc = local_time.astimezone(dt.timezone.utc)
    jd = utc.timestamp() / 86400.0 + 2440587.5
    t = (jd - 2451545.0) / 36525.0
    radians = math.radians
    sin, cos, tan = math.sin, math.cos, math.tan
    longitude_mean = (280.46646 + t * (36000.76983 + 0.0003032 * t)) % 360
    anomaly_mean = 357.52911 + t * (35999.05029 - 0.0001537 * t)
    eccentricity = 0.016708634 - t * (0.000042037 + 0.0000001267 * t)
    equation_center = (
        sin(radians(anomaly_mean)) * (1.914602 - t * (0.004817 + 0.000014 * t))
        + sin(radians(2 * anomaly_mean)) * (0.019993 - 0.000101 * t)
        + sin(radians(3 * anomaly_mean)) * 0.000289
    )
    sun_true_longitude = longitude_mean + equation_center
    omega = 125.04 - 1934.136 * t
    apparent_longitude = sun_true_longitude - 0.00569 - 0.00478 * sin(radians(omega))
    obliquity_mean = 23 + (26 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60) / 60
    obliquity = obliquity_mean + 0.00256 * cos(radians(omega))
    declination = math.asin(sin(radians(obliquity)) * sin(radians(apparent_longitude)))
    y = tan(radians(obliquity / 2)) ** 2
    equation_time = 4 * math.degrees(
        y * sin(2 * radians(longitude_mean))
        - 2 * eccentricity * sin(radians(anomaly_mean))
        + 4 * eccentricity * y * sin(radians(anomaly_mean)) * cos(2 * radians(longitude_mean))
        - 0.5 * y * y * sin(4 * radians(longitude_mean))
        - 1.25 * eccentricity * eccentricity * sin(2 * radians(anomaly_mean))
    )
    offset_minutes = local_time.utcoffset().total_seconds() / 60
    local_minutes = local_time.hour * 60 + local_time.minute + local_time.second / 60
    true_solar_minutes = (local_minutes + equation_time + 4 * longitude - offset_minutes) % 1440
    hour_angle = radians(true_solar_minutes / 4 - 180)
    lat = radians(latitude)
    elevation = math.degrees(math.asin(
        sin(lat) * sin(declination) + cos(lat) * cos(declination) * cos(hour_angle)
    ))
    azimuth = (math.degrees(math.atan2(
        sin(hour_angle), cos(hour_angle) * sin(lat) - tan(declination) * cos(lat)
    )) + 180) % 360
    elev, az = radians(elevation), radians(azimuth)
    # Observer-to-sun direction in Blender's scene axes: East, North, Up.
    east, north, up = cos(elev) * sin(az), cos(elev) * cos(az), sin(elev)
    # UE scene axes East, South, Up. UE forward axis is outgoing light rays.
    # Outgoing light ray: (-east, +north, -up), pitch=-alt; yaw=az+90.
    yaw = (azimuth + 90 + 180) % 360 - 180
    return {
        "local_datetime": local_time.isoformat(),
        "utc_datetime": utc.isoformat(),
        "azimuth_deg_clockwise_from_north": round(azimuth, 6),
        "geometric_elevation_deg": round(elevation, 6),
        "equation_of_time_minutes": round(equation_time, 6),
        "sun_direction_east_north_up": [round(x, 9) for x in (east, north, up)],
        "ue_outgoing_direction_east_south_up": [round(x, 9) for x in (-east, north, -up)],
        "ue_directional_light_rotation": {"pitch": round(-elevation, 6), "yaw": round(yaw, 6), "roll": 0.0},
        "direct_sun_enabled": elevation > 0,
    }


def presets():
    return {
        name: solar_position(dt.datetime(2026, 9, 30, hour, minute, tzinfo=PDT))
        for name, hour, minute in (
            ("Morning Daylight", 9, 0),
            ("Golden Hour", 17, 15),
            ("Blue Hour", 19, 5),
        )
    }


if __name__ == "__main__":
    values = presets()
    # Geometric consistency and physically meaningful preset checks.
    for value in values.values():
        assert abs(sum(v * v for v in value["sun_direction_east_north_up"]) - 1) < 1e-7
    assert values["Morning Daylight"]["sun_direction_east_north_up"][0] > 0
    assert values["Golden Hour"]["sun_direction_east_north_up"][0] < 0
    assert values["Blue Hour"]["geometric_elevation_deg"] < 0
    print(json.dumps(values, indent=2))
