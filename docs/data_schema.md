# Data Schema (Week 2)

All timestamps are UTC, one row per hour. Column names are lowercase.

## Observation columns (raw layer)

| Column | Unit | Source | Description |
|---|---|---|---|
| time | UTC datetime | all | Start of the hour. Primary key and event time. |
| temperature_c | °C | Open-Meteo (fallback OpenWeather) | Air temperature at 2 m |
| humidity_pct | % | Open-Meteo (fallback OpenWeather) | Relative humidity at 2 m |
| precipitation_mm | mm | Open-Meteo (fallback OpenWeather) | Rain in the last hour |
| wind_speed_ms | m/s | Open-Meteo (km/h divided by 3.6) | Wind speed at 10 m |
| wind_direction_deg | degrees 0-360 | Open-Meteo | Direction the wind comes from |
| pressure_hpa | hPa | Open-Meteo | Pressure at sea level |
| cloud_cover_pct | % | Open-Meteo | Cloud cover |
| uv_index | index | Open-Meteo air quality API | UV index |
| us_aqi | US AQI 0-500 | Open-Meteo air quality API | Air quality index (model estimate) |
| pm2_5 | µg/m³ | Open-Meteo air quality API | Fine particles |
| pm10 | µg/m³ | Open-Meteo air quality API | Coarse particles |
| source | text | pipeline | Which source filled the weather columns |
| ow_aqi_level | level 1-5 | OpenWeather (live only) | Extra check only, not a model input |
Open-Meteo (requested in m/s)

## Fusion strategy

- Weather metrics: source priority. Open-Meteo first, OpenWeather only as a
  fallback. Reason: training history exists only from Open-Meteo, so using the
  same source live avoids a mismatch between training and live data (the two
  sources differed by 1 °C and 15 % humidity in our test). The `source`
  column records any switch.
- AQI: Open-Meteo us_aqi only. Reason: OpenWeather uses a 1-5 scale, so
  averaging would give a meaningless number, and AQICN has no working API
  station for Peshawar.
- Known limit: Open-Meteo AQI is a model estimate and can differ from a real
  station (AQICN website showed 175 while the model gave 133 on 2026-11-20).

## Targets (24 hours ahead)

| Target column | Definition |
|---|---|
| target_us_aqi_24h | us_aqi 24 hours later |
| target_temperature_c_24h | temperature_c 24 hours later |
| target_humidity_pct_24h | humidity_pct 24 hours later |
| target_uv_index_24h | uv_index 24 hours later |
| target_precipitation_mm_24h | precipitation_mm 24 hours later |
| target_rain_24h | 1 if precipitation_mm 24 hours later is above 0.1, else 0 |
| target_wind_speed_ms_24h | wind_speed_ms 24 hours later |
| target_wind_sin_24h, target_wind_cos_24h | sine and cosine of wind direction 24 hours later |

The last 24 rows have no target. They are used for forecasting only.