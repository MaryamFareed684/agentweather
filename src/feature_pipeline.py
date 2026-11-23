"""AgentWeather feature pipeline (Week 2).

Steps: fetch_raw -> fuse -> impute -> add_features -> add_targets -> store
"""

import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

# Peshawar coordinates
LATITUDE = 34.01
LONGITUDE = 71.58

WEATHER_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

# Open-Meteo name -> our schema name (see docs/data_schema.md)
WEATHER_VARS = {
    "temperature_2m": "temperature_c",
    "relative_humidity_2m": "humidity_pct",
    "precipitation": "precipitation_mm",
    "wind_speed_10m": "wind_speed_ms",
    "wind_direction_10m": "wind_direction_deg",
    "pressure_msl": "pressure_hpa",
    "cloud_cover": "cloud_cover_pct",
}

# These already have the names we want
AIR_VARS = ["uv_index", "us_aqi", "pm2_5", "pm10"]


def month_chunks(start_date, end_date):
    """Split a date range into month-sized pieces.

    In: start_date, end_date as 'YYYY-MM-DD' strings.
    Out: list of (chunk_start, chunk_end) string pairs.
    """
    chunks = []
    current = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)

    while current <= end:
        chunk_end = min(current + pd.offsets.MonthEnd(0), end)
        chunks.append((current.date().isoformat(), chunk_end.date().isoformat()))
        current = chunk_end + pd.Timedelta(days=1)

    return chunks


def fetch_hourly(url, hourly_vars, start_date, end_date, extra_params=None):
    """Download hourly data for one date range from an Open-Meteo API.

    In: API url, list of variable names, start and end date strings.
    Out: DataFrame with a UTC 'time' column, or raises an error after 3 tries.
    """
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(hourly_vars),
        "timezone": "UTC",
    }
    if extra_params:
        params.update(extra_params)

    last_error = None
    for attempt in range(1, 4):
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            df = pd.DataFrame(data["hourly"])
            df["time"] = pd.to_datetime(df["time"], utc=True)
            return df

        except (requests.RequestException, ValueError, KeyError) as error:
            last_error = error
            print(f"  attempt {attempt} failed: {error}")
            time.sleep(2 * attempt)

    raise RuntimeError(f"Could not fetch {start_date} to {end_date}: {last_error}")


def fetch_backfill(start_date, end_date):
    """Download weather and air quality for a long range, month by month.

    In: start and end date strings.
    Out: (weather_df, air_df), each with a UTC 'time' column and schema names.
    """
    weather_parts = []
    air_parts = []

    for chunk_start, chunk_end in month_chunks(start_date, end_date):
        print(f"Fetching {chunk_start} to {chunk_end} ...")

        weather = fetch_hourly(
            WEATHER_ARCHIVE_URL,
            list(WEATHER_VARS.keys()),
            chunk_start,
            chunk_end,
            extra_params={"wind_speed_unit": "ms"},
        )
        weather_parts.append(weather)

        air = fetch_hourly(AIR_URL, AIR_VARS, chunk_start, chunk_end)
        air_parts.append(air)

    weather_df = pd.concat(weather_parts, ignore_index=True)
    air_df = pd.concat(air_parts, ignore_index=True)

    weather_df = weather_df.rename(columns=WEATHER_VARS)

    return weather_df, air_df


def fetch_raw(mode, start_date=None, end_date=None):
    """Get raw data for the chosen mode.

    In: mode ('backfill' or 'live'), and dates for backfill.
    Out: (weather_df, air_df).
    """
    if mode == "backfill":
        return fetch_backfill(start_date, end_date)

    if mode == "live":
        raise NotImplementedError("Live mode comes in a later step.")

    raise ValueError("mode must be 'backfill' or 'live'")


if __name__ == "__main__":
    # Quick test: about 45 days, so it crosses a month border (2 chunks).
    # The weather archive is a few days behind, so we stop 5 days ago.
    today = datetime.now(timezone.utc).date()
    end = (today - timedelta(days=5)).isoformat()
    start = (today - timedelta(days=45)).isoformat()

    weather_df, air_df = fetch_raw("backfill", start, end)

    print("\nWeather:", weather_df.shape)
    print(weather_df.head(3))
    print("\nAir quality:", air_df.shape)
    print(air_df.head(3))