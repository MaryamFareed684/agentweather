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

TIME_DTYPE = "datetime64[ns, UTC]"


def clean_hourly(df):
    """Put one source on the hourly grid.

    In: DataFrame with a 'time' column.
    Out: copy with UTC times rounded down to the hour, sorted, one row per hour.
    """
    df = df.copy()
    df["time"] = pd.to_datetime(df["time"], utc=True).dt.floor("h").astype(TIME_DTYPE)
    df = df.sort_values("time").drop_duplicates(subset="time", keep="last")
    return df


def fuse(weather_df, air_df, start_date=None, end_date=None):
    """Merge weather and air quality into exactly one row per hour.

    In: weather_df, air_df, and optionally start and end date strings.
    Out: DataFrame with a complete hourly 'time' column. Hours that no source
         gave us stay as visible NaN (they are not dropped).
    """
    weather = clean_hourly(weather_df)
    air = clean_hourly(air_df)

    if start_date and end_date:
        first = pd.Timestamp(start_date, tz="UTC")
        last = pd.Timestamp(end_date, tz="UTC") + pd.Timedelta(hours=23)
    else:
        first = min(weather["time"].min(), air["time"].min())
        last = max(weather["time"].max(), air["time"].max())

    grid = pd.DataFrame({"time": pd.date_range(first, last, freq="h")})
    grid["time"] = grid["time"].astype(TIME_DTYPE)

    df = grid.merge(weather, on="time", how="left")
    df = df.merge(air, on="time", how="left")
    df["source"] = "open-meteo"

    return df


def check_hourly_index(df):
    """Check that time is continuous, hourly and has no duplicates.

    In: DataFrame with a 'time' column.
    Out: True if all is fine, False otherwise (problems are printed).
    """
    ok = True

    duplicates = int(df["time"].duplicated().sum())
    if duplicates > 0:
        print(f"PROBLEM: {duplicates} duplicate timestamps")
        ok = False

    steps = df["time"].diff().dropna()
    bad_steps = int((steps != pd.Timedelta(hours=1)).sum())
    if bad_steps > 0:
        print(f"PROBLEM: {bad_steps} steps are not exactly 1 hour")
        ok = False

    if ok:
        print(f"OK: {len(df)} rows, continuous hourly index, no duplicates")

    return ok
# Rule for each column: (method, maximum hours we are willing to fill)
# "ffill" = repeat the last known value. "zero" = assume no rain.
IMPUTE_RULES = {
    "temperature_c": ("ffill", 3),
    "humidity_pct": ("ffill", 3),
    "precipitation_mm": ("zero", 3),
    "wind_speed_ms": ("ffill", 3),
    "wind_direction_deg": ("ffill", 3),
    "pressure_hpa": ("ffill", 3),
    "cloud_cover_pct": ("ffill", 3),
    "uv_index": ("ffill", 3),
    "us_aqi": ("ffill", 3),
    "pm2_5": ("ffill", 3),
    "pm10": ("ffill", 3),
}


def gap_position(series):
    """For each missing value, count how many hours into its gap it is.

    In: a Series with some NaN.
    Out: Series of numbers. 0 where the value exists, 1, 2, 3... inside a gap.
    """
    is_missing = series.isna()
    run_id = (~is_missing).cumsum()
    return is_missing.groupby(run_id).cumsum()


def impute(df):
    """Fill short gaps using only past values (no peeking into the future).

    In: fused DataFrame (one row per hour).
    Out: copy with short gaps filled, plus a '<column>_imputed' flag (1 or 0)
         for every column in IMPUTE_RULES. Gaps longer than the limit stay NaN.
    """
    df = df.sort_values("time").reset_index(drop=True).copy()

    for col, (method, limit) in IMPUTE_RULES.items():
        if col not in df.columns:
            continue

        # Same type every time, so Hopsworks never sees int one day, float the next
        df[col] = df[col].astype("float64")
        was_missing = df[col].isna()

        if method == "ffill":
            df[col] = df[col].ffill(limit=limit)
        elif method == "zero":
            position = gap_position(df[col])
            df.loc[was_missing & (position <= limit), col] = 0.0

        df[f"{col}_imputed"] = (was_missing & df[col].notna()).astype(int)

    return df


def imputation_report(before, after):
    """Make the table for docs/imputation.md.

    In: DataFrame before impute() and after impute().
    Out: DataFrame with column, % missing before, method, max gap, % missing after.
    """
    rows = []
    for col, (method, limit) in IMPUTE_RULES.items():
        if col not in before.columns:
            continue
        rows.append({
            "column": col,
            "missing_before_pct": round(100 * before[col].isna().mean(), 2),
            "method": "forward fill" if method == "ffill" else "fill with 0",
            "max_gap_filled_h": limit,
            "missing_after_pct": round(100 * after[col].isna().mean(), 2),
        })
    return pd.DataFrame(rows)

if __name__ == "__main__":
    # Quick test: about 45 days, so it crosses a month border (2 chunks).
    # The weather archive is a few days behind, so we stop 5 days ago.
    today = datetime.now(timezone.utc).date()
    end = (today - timedelta(days=5)).isoformat()
    start = (today - timedelta(days=45)).isoformat()

    weather_df, air_df = fetch_raw("backfill", start, end)
    df = fuse(weather_df, air_df, start, end)
    check_hourly_index(df)

    # 1) Real data
    clean = impute(df)
    print("\nREAL DATA imputation report:")
    print(imputation_report(df, clean).to_string(index=False))

    # 2) Practice data: we make holes on purpose to see the rules work
    test = df.copy()
    for col in ["temperature_c", "precipitation_mm", "wind_direction_deg", "us_aqi"]:
        test[col] = test[col].astype("float64")
        test.loc[100, col] = float("nan")             # 1 hour gap
        test.loc[200:202, col] = float("nan")         # 3 hour gap
        test.loc[300:305, col] = float("nan")         # 6 hour gap
    test_clean = impute(test)

    print("\nPRACTICE DATA (holes made on purpose):")
    print(imputation_report(test, test_clean).query(
        "column in ['temperature_c','precipitation_mm','wind_direction_deg','us_aqi']"
    ).to_string(index=False))
    print("\nThe 6 hour gap (rows 300 to 305), temperature_c and its flag:")
    print(test_clean.loc[298:307, ["time", "temperature_c", "temperature_c_imputed"]])