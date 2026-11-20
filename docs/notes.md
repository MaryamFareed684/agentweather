
# AgentWeather - Data Source Notes

## 1. Data Sources

| Metric | Source | Field Name | Unit |
|---|---|---|---|
| Temperature | OpenWeather | main.temp | °C |
| Feels Like Temperature | OpenWeather | main.feels_like | °C |
| Humidity | OpenWeather | main.humidity | % |
| Pressure | OpenWeather | main.pressure | hPa |
| Wind Speed | OpenWeather | wind.speed | m/s |
| Air Quality Index | OpenWeather | list[0].main.aqi | 1-5 |
| PM2.5 | OpenWeather | list[0].components.pm2_5 | µg/m³ |
| Temperature | Open-Meteo | current.temperature_2m | °C |
| Humidity | Open-Meteo | current.relative_humidity_2m | % |
| Wind Speed | Open-Meteo | current.wind_speed_10m | km/h |
| Air Quality Index | AQICN | To verify from response | AQI scale |

## 2. Overlaps

- OpenWeather and Open-Meteo both provide temperature.
- OpenWeather and AQICN provide air-quality information.
- OpenWeather AQI uses a 1-5 scale.
- AQICN AQI uses a 0-500 scale.
- These AQI scales should not be mixed directly.

## 3. Data Gaps

- Rain probability needs to be checked.
- UV Index needs to be checked.
- Open-Meteo can provide these metrics through additional forecast parameters.

## 4. Data Storage

Raw API responses are stored in data/raw/.

All collection timestamps use UTC.
