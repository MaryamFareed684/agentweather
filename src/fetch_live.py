
import os
import json
from pathlib import Path
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

# Load API keys from the .env file
load_dotenv()

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"

# Peshawar coordinates
LATITUDE = 34.01
LONGITUDE = 71.58


# Save original API response as a JSON file
def save_raw(source, data):
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H-%M-%SZ"
    )

    filename = f"{source}_{timestamp}.json"
    filepath = RAW_DIR / filename

    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

    print(f"Saved raw data: {filename}")


# Common function for making API requests
def fetch_json(source, url, params):
    try:
        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        response.raise_for_status()
        data = response.json()

        save_raw(source, data)

        return data

    except (requests.RequestException, ValueError) as error:
        print(f"{source} API error: {error}")
        return None


# 1. OpenWeather current weather
def get_openweather_weather():

    api_key = os.getenv("OPENWEATHER_API_KEY")

    if not api_key:
        print("OpenWeather API key is missing!")
        return None

    url = "https://api.openweathermap.org/data/2.5/weather"

    params = {
        "lat": LATITUDE,
        "lon": LONGITUDE,
        "appid": api_key,
        "units": "metric"
    }

    return fetch_json("openweather_weather", url, params)


# 2. OpenWeather air pollution
def get_openweather_air_pollution():

    api_key = os.getenv("OPENWEATHER_API_KEY")

    if not api_key:
        print("OpenWeather API key is missing!")
        return None

    url = "https://api.openweathermap.org/data/2.5/air_pollution"

    params = {
        "lat": LATITUDE,
        "lon": LONGITUDE,
        "appid": api_key
    }

    return fetch_json("openweather_pollution", url, params)


# 3. AQICN Peshawar station
def get_aqicn_data():

    token = os.getenv("AQICN_TOKEN")

    if not token:
        print("AQICN token is missing!")
        return None

    url = "https://api.waqi.info/feed/@541759/"

    params = {
        "token": token
    }

    data = fetch_json("aqicn", url, params)

    if data is None:
        return None

    # Honest check: the real AQI value must be inside the reply
    inner = data.get("data")

    if not isinstance(inner, dict) or "aqi" not in inner:
        print("AQICN failed:", inner)
        return None

    return data


# 4. Open-Meteo current weather
def get_openmeteo_weather():

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "apparent_temperature,"
            "precipitation,"
            "rain,"
            "weather_code,"
            "cloud_cover,"
            "pressure_msl,"
            "wind_speed_10m,"
            "wind_direction_10m"
        ),
        "timezone": "GMT"
    }

    return fetch_json("openmeteo_weather", url, params)
# 5. Open-Meteo current air quality
def get_openmeteo_air_quality():

    url = "https://air-quality-api.open-meteo.com/v1/air-quality"

    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "current": "us_aqi,pm2_5,pm10",
        "timezone": "GMT"
    }

    data = fetch_json("openmeteo_airquality", url, params)

    # Honest check: the real AQI value must be inside the reply
    if data is None:
        return None

    if "us_aqi" not in data.get("current", {}):
        print("Open-Meteo air quality: AQI value is missing.")
        return None

    return data


# Run all four functions
if __name__ == "__main__":

    print("\n===== AGENTWEATHER LIVE DATA =====\n")

    print("1. Fetching OpenWeather weather...")
    weather = get_openweather_weather()

    print("\n2. Fetching OpenWeather pollution...")
    pollution = get_openweather_air_pollution()

    print("\n3. Fetching AQICN station data...")
    aqi = get_aqicn_data()

    print("\n4. Fetching Open-Meteo weather...")
    meteo = get_openmeteo_weather()
    
    print("\n5. Fetching Open-Meteo air quality...")
    air = get_openmeteo_air_quality()

    print("\n===== FETCH SUMMARY =====")

    print("OpenWeather weather:", "Success" if weather else "Failed")
    print("OpenWeather pollution:", "Success" if pollution else "Failed")
    print("AQICN:", "Success" if aqi else "Failed")
    print("Open-Meteo:", "Success" if meteo else "Failed")
    print("Open-Meteo air quality:", "Success" if air else "Failed")

    print("\nData collection completed.")
