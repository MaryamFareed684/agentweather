
import requests
import pandas as pd

from datetime import datetime, timedelta, timezone
from pathlib import Path


import json



# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"

# Peshawar coordinates
LATITUDE = 34.01
LONGITUDE = 71.58


def get_date_range():

    # Use UTC dates
    today = datetime.now(timezone.utc).date()

    # Historical weather data has a delay.
    end_date = today - timedelta(days=5)

    # 90 calendar days including start and end
    start_date = end_date - timedelta(days=89)

    return start_date.isoformat(), end_date.isoformat()


def fetch_weather_history(start_date, end_date):

    url = "https://archive-api.open-meteo.com/v1/archive"

    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": start_date,
        "end_date": end_date,

        "hourly": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "precipitation,"
            "wind_speed_10m,"
            "wind_direction_10m"
        ),

        "timezone": "UTC",
        "wind_speed_unit": "kmh"
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        df = pd.DataFrame(data["hourly"])

        df["time"] = pd.to_datetime(df["time"], utc=True)

        return df

    except (requests.RequestException, ValueError, KeyError) as error:
        print("Weather history error:", error)
        return None


def fetch_air_quality_history(start_date, end_date):

    url = "https://air-quality-api.open-meteo.com/v1/air-quality"

    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": start_date,
        "end_date": end_date,

        "hourly": "uv_index,us_aqi",

        "timezone": "UTC"
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        df = pd.DataFrame(data["hourly"])

        df["time"] = pd.to_datetime(df["time"], utc=True)

        return df

    except (requests.RequestException, ValueError, KeyError) as error:
        print("Air quality history error:", error)
        return None


def main():

    print("===== AGENTWEATHER HISTORICAL DATA =====")

    start_date, end_date = get_date_range()

    print("Start date:", start_date)
    print("End date:", end_date)

    # Request 1: Weather history
    print("\nFetching historical weather...")

    weather_df = fetch_weather_history(start_date, end_date)

    if weather_df is None:
        print("Weather collection failed.")
        return

    print("Weather records:", len(weather_df))

    # Request 2: Air quality history
    print("\nFetching historical air quality...")

    air_df = fetch_air_quality_history(start_date, end_date)

    if air_df is None:
        print("Air quality collection failed.")
        return

    print("Air quality records:", len(air_df))

    # Join both datasets using UTC timestamps
    print("\nCombining datasets...")

    df = pd.merge(
        weather_df,
        air_df,
        on="time",
        how="inner",
        validate="one_to_one"
    )

    df = df.sort_values("time").reset_index(drop=True)

    # Save CSV
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    output_file = RAW_DIR / "history_90d.csv"

    df.to_csv(output_file, index=False)

    print("\n===== COLLECTION SUMMARY =====")

    print("Total records:", len(df))
    print("Total columns:", len(df.columns))

    print("\nColumns:")
    print(df.columns.tolist())

    print("\nFirst five records:")
    print(df.head())

    print("\nSaved file:", output_file)

    print("\nHistorical data collection completed!")


if __name__ == "__main__":
    main()
