# Week 1 Notes

## City
Peshawar (lat 34.01, lon 71.58). Times are in UTC everywhere.

## Source to metric table

| Metric | Source | Field | Unit |
|---|---|---|---|
| Temperature | OpenWeather weather | main.temp | °C (units=metric) |
| Temperature | Open-Meteo current | current.temperature_2m | °C |
| Humidity | OpenWeather weather | main.humidity | % |
| Humidity | Open-Meteo current | current.relative_humidity_2m | % |
| Precipitation | OpenWeather weather | rain.1h (only present when raining) | mm |
| Precipitation | Open-Meteo current | current.precipitation | mm |
| Wind speed | OpenWeather weather | wind.speed | m/s |
| Wind speed | Open-Meteo current | current.wind_speed_10m | km/h |
| Wind direction | OpenWeather weather | wind.deg | degrees |
| Wind direction | Open-Meteo current | current.wind_direction_10m | degrees |
| UV index | Open-Meteo history (air quality API) | hourly.uv_index | index |
| AQI | Open-Meteo air quality |



## Free tier limits (checked 2026-11-21)
- OpenWeather (free): 60 calls/minute, 1,000,000 calls/month. Current weather
  and air pollution are included.
- AQICN: default 1,000 requests/second, free for non-commercial use.
  Rules: no caching or redistribution of data, attribution required.
- Open-Meteo (free): non-commercial only, under 10,000 calls/day,
  5,000/hour, 600/minute. Attribution required (CC-BY 4.0).
- Hopsworks (free): 1 project, capped capacity, no credit card.
  Exact storage: check my dashboard (sources disagree).
- Groq (free): no credit card, limits depend on the model. Check the
  Limits page in the Groq console.
- Our usage: about 5 API calls per hour (about 120 per day), far below
  every limit.