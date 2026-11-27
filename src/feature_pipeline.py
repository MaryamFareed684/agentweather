"""AgentWeather feature pipeline (Week 2).

Steps: fetch_raw -> fuse -> impute -> add_features -> add_targets -> store
"""

import time
import argparse
import sys
from datetime import datetime, timedelta, timezone
import numpy as np

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

# Columns we build history features from (lags, rolling means, changes)
HISTORY_COLS = [
    "temperature_c", "humidity_pct", "precipitation_mm", "wind_speed_ms",
    "uv_index", "us_aqi", "pm2_5", "pressure_hpa",
]
LAGS = [1, 3, 6, 24]          # hours back
ROLL_WINDOWS = [3, 6, 24]     # hours

# target column -> the column it looks 24 hours ahead at
TARGETS = {
    "target_us_aqi_24h": "us_aqi",
    "target_temperature_c_24h": "temperature_c",
    "target_humidity_pct_24h": "humidity_pct",
    "target_uv_index_24h": "uv_index",
    "target_precipitation_mm_24h": "precipitation_mm",
    "target_wind_speed_ms_24h": "wind_speed_ms",
}
TARGET_COLS = list(TARGETS) + [
    "target_rain_24h", "target_wind_sin_24h", "target_wind_cos_24h",
]


def require_hourly_grid(df):
    """Stop with an error if the table is not one row per hour.

    shift() counts rows, so it only means 'hours' when every hour is present.
    """
    steps = df["time"].diff().dropna()
    if not (steps == pd.Timedelta(hours=1)).all():
        raise ValueError("Table is not a continuous hourly grid. Run fuse() first.")


def add_time_features(df):
    """Add hour, day, month, day of week and their sine/cosine versions.

    In: DataFrame with a UTC 'time' column.
    Out: copy with 8 new columns. They come from the timestamp only.
    """
    t = df["time"]
    new = pd.DataFrame({
        "hour": t.dt.hour,
        "day": t.dt.day,
        "month": t.dt.month,
                "day_of_week": t.dt.day_of_week,
        "hour_sin": np.sin(2 * np.pi * t.dt.hour / 24),
        "hour_cos": np.cos(2 * np.pi * t.dt.hour / 24),
        "month_sin": np.sin(2 * np.pi * t.dt.month / 12),
        "month_cos": np.cos(2 * np.pi * t.dt.month / 12),
    })
    return pd.concat([df, new], axis=1)


def add_wind_features(df):
    """Turn wind direction (a circle) into sine and cosine.

    In: DataFrame with 'wind_direction_deg'.
    Out: copy with 'wind_dir_sin' and 'wind_dir_cos'. 359 and 1 degrees now
         become almost the same numbers.
    """
    rad = np.deg2rad(df["wind_direction_deg"])
    new = pd.DataFrame({"wind_dir_sin": np.sin(rad), "wind_dir_cos": np.cos(rad)})
    return pd.concat([df, new], axis=1)


def add_history_features(df):
    """Add lag, rolling mean and rate-of-change features. Past values only.

    In: imputed DataFrame (one row per hour).
    Out: copy with lag (1, 3, 6, 24 h), rolling mean (3, 6, 24 h) and change
         (1 h, 3 h) columns for each column in HISTORY_COLS, plus the rain sum
         of the last 24 hours. A rolling window needs all its hours, so the
         first 23 rows are NaN.
    """
    new = {}
    for col in HISTORY_COLS:
        s = df[col]
        for k in LAGS:
            new[f"{col}_lag{k}h"] = s.shift(k)
        for w in ROLL_WINDOWS:
            new[f"{col}_mean{w}h"] = s.rolling(w, min_periods=w).mean()
        for k in (1, 3):
            new[f"{col}_diff{k}h"] = s.diff(k)

    new["precip_sum_24h"] = df["precipitation_mm"].rolling(24, min_periods=24).sum()
    return pd.concat([df, pd.DataFrame(new)], axis=1)


def add_features(df):
    """Build all input features (time, wind, history).

    In: imputed DataFrame (one row per hour).
    Out: copy with the extra feature columns.
    """
    require_hourly_grid(df)
    df = add_time_features(df)
    df = add_wind_features(df)
    df = add_history_features(df)
    return df


def add_targets(df):
    """Add the 'what happens 24 hours later' columns.

    In: imputed DataFrame (one row per hour).
    Out: copy with 9 target columns. The last 24 rows have NaN targets
         (the future has not happened yet). Keep them for forecasting only.
    """
    require_hourly_grid(df)

    new = {}
    for target, source in TARGETS.items():
        new[target] = df[source].shift(-24)

    rain_amount = new["target_precipitation_mm_24h"]
    new["target_rain_24h"] = (rain_amount > 0.1).astype("float64").where(rain_amount.notna())

    future_dir = np.deg2rad(df["wind_direction_deg"].shift(-24))
    new["target_wind_sin_24h"] = np.sin(future_dir)
    new["target_wind_cos_24h"] = np.cos(future_dir)

    return pd.concat([df, pd.DataFrame(new)], axis=1)


def leakage_check(df, n=500):
    """Prove that features do not use the future.

    We build features twice: once on the full table, once on a table cut off
    after row n. If a feature at row n-1 changes, it was peeking at the future.

    In: imputed DataFrame. Out: True if no leakage was found.
    """
    n = min(n, len(df) - 24)
    full = add_features(df)
    part = add_features(df.iloc[:n].copy())

    new_cols = [c for c in full.columns if c not in df.columns]
    a = full.loc[n - 1, new_cols].astype("float64").to_numpy()
    b = part.loc[n - 1, new_cols].astype("float64").to_numpy()

    same = np.isclose(a, b, equal_nan=True)
    if same.all():
        print(f"OK: no leakage found ({len(new_cols)} features checked)")
        return True

    bad = [c for c, ok in zip(new_cols, same) if not ok]
    print("LEAKAGE in:", bad)
    return False


# Hopsworks feature groups
FG_RAW_NAME = "weather_observations"
FG_FEATURES_NAME = "weather_features"
FG_VERSION = 1
TIME_TRAVEL_FORMAT = "HUDI"   # Delta needs a library that is not installed on Windows

# Columns of the raw observation table (after fuse, before imputation)
RAW_COLS = ["time"] + list(WEATHER_VARS.values()) + AIR_VARS + ["source"]


def build_features(fused):
    """Run imputation, features and targets in one go.

    In: fused DataFrame (one row per hour).
    Out: (features_df, feature_cols). features_df has the imputed columns,
         flags, features and targets. feature_cols lists the new feature columns.
    """
    clean = impute(fused)
    features = add_targets(add_features(clean))
    feature_cols = [c for c in features.columns
                    if c not in clean.columns and c not in TARGET_COLS]
    return features, feature_cols


def get_feature_store():
    """Log in to Hopsworks with the key from .env and return the feature store."""
    # Imported here, so the rest of the pipeline also works without Hopsworks
    import os

    import hopsworks
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("HOPSWORKS_API_KEY")
    if not api_key:
        raise RuntimeError("HOPSWORKS_API_KEY is missing in .env")

    project = hopsworks.login(
        api_key_value=api_key,
        project=os.getenv("HOPSWORKS_PROJECT"),
    )
    return project.get_feature_store()


def to_float(df):
    """Make every number column float64, so the table has the same types every run.

    In: DataFrame. Out: copy where all columns except 'time' and 'source' are float64.
    """
    df = df.copy()
    for col in df.columns:
        if col not in ("time", "source"):
            df[col] = df[col].astype("float64")
    return df


def store(observations_df, features_df, feature_cols, wait=False):
    """Save the data in two Hopsworks feature groups. Safe to run twice.

    Both groups use 'time' as primary key and event time. If a row with the
    same time already exists, Hopsworks updates it instead of adding a copy.

    In: observations_df (RAW_COLS), features_df and feature_cols from build_features().
    Out: (rows sent to the observation group, rows sent to the feature group).
    """
    fs = get_feature_store()

    obs_fg = fs.get_or_create_feature_group(
        name=FG_RAW_NAME,
        version=FG_VERSION,
        description="Hourly weather and air quality for Peshawar (UTC). "
                    "Cleaned and fused, but not imputed or processed.",
        primary_key=["time"],
        event_time="time",
        time_travel_format=TIME_TRAVEL_FORMAT,
    )
    feat_fg = fs.get_or_create_feature_group(
        name=FG_FEATURES_NAME,
        version=FG_VERSION,
        description="Hourly features and 24-hour-ahead targets for Peshawar. "
                    "The newest 24 rows have no target (forecasting only).",
        primary_key=["time"],
        event_time="time",
        time_travel_format=TIME_TRAVEL_FORMAT,
    )

    obs = to_float(observations_df)

    # Rows whose features are incomplete (the first 24 hours) are not stored.
    feats = features_df.drop(columns=["source"]).dropna(subset=feature_cols)
    feats = to_float(feats)

    obs_fg.insert(obs, write_options={"wait_for_job": wait})
    feat_fg.insert(feats, write_options={"wait_for_job": wait})

    return len(obs), len(feats)


def read_back(name):
    """Read a whole feature group back from Hopsworks.

    In: feature group name. Out: pandas DataFrame.
    """
    fs = get_feature_store()
    return fs.get_feature_group(name, version=FG_VERSION).read()

def run_backfill(start_date, end_date, dry_run=False, wait=False):
    """Build and store features for a past date range (training data).

    In: start and end date strings ('YYYY-MM-DD'), dry_run (do not store),
        wait (wait for the Hopsworks jobs).
    Out: nothing. Prints a summary.
    """
    # The weather archive is a few days behind, so we cannot go past that
    latest = datetime.now(timezone.utc).date() - timedelta(days=5)
    if pd.Timestamp(end_date).date() > latest:
        print(f"Note: weather history only goes up to {latest}. Using it as the end date.")
        end_date = latest.isoformat()

    if pd.Timestamp(start_date) > pd.Timestamp(end_date):
        sys.exit("The start date must be before the end date.")

    # One extra day before the start, so the first rows have 24 hours of history.
    # One extra day after the end (if it exists), so the last rows get their
    # 24-hour-ahead target. Otherwise a small re-run would erase old targets.
    first_day = (pd.Timestamp(start_date) - pd.Timedelta(days=1)).date().isoformat()
    last_day = min((pd.Timestamp(end_date) + pd.Timedelta(days=1)).date(), latest)

    weather_df, air_df = fetch_backfill(first_day, last_day.isoformat())
    fused = fuse(weather_df, air_df, first_day, last_day.isoformat())
    check_hourly_index(fused)
    features, feature_cols = build_features(fused)

    # Keep only the days that were asked for (drop the extra days)
    start_ts = pd.Timestamp(start_date, tz="UTC")
    stop_ts = pd.Timestamp(end_date, tz="UTC") + pd.Timedelta(days=1)
    keep = (fused["time"] >= start_ts) & (fused["time"] < stop_ts)
    observations = fused.loc[keep, RAW_COLS]
    features = features.loc[keep]

    complete = features.dropna(subset=feature_cols)
    with_target = complete.dropna(subset=TARGET_COLS)
    print(f"\nRange: {start_date} to {end_date}")
    print(f"Observation rows: {len(observations)}")
    print(f"Feature rows (complete): {len(complete)}")
    print(f"  of which have a target: {len(with_target)} "
          "(only the newest 24 hours of the history have none)")

    if dry_run:
        print("\nDry run: nothing was stored in Hopsworks.")
        return

    store(observations, features, feature_cols, wait=wait)
    print("\nData sent to Hopsworks.")
    if not wait:
        print("Hopsworks now processes it in background jobs (about 10 minutes each).")
        print("Check the Jobs page, then run: python src/check_store.py")


def parse_args():
    """Read the command line options."""
    parser = argparse.ArgumentParser(description="AgentWeather feature pipeline")
    parser.add_argument("--mode", choices=["backfill", "live"], required=True)
    parser.add_argument("--start", help="backfill start date, YYYY-MM-DD")
    parser.add_argument("--end", help="backfill end date, YYYY-MM-DD")
    parser.add_argument("--dry-run", action="store_true",
                        help="do everything except storing in Hopsworks")
    parser.add_argument("--wait", action="store_true",
                        help="wait until the Hopsworks jobs have finished")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()

    if args.mode == "backfill":
        if not (args.start and args.end):
            sys.exit("Backfill needs --start and --end, for example: "
                     "--mode backfill --start 2026-01-01 --end 2026-06-30")
        run_backfill(args.start, args.end, dry_run=args.dry_run, wait=args.wait)
    else:
        print("Live mode comes in a later step.")