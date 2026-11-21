# AgentWeather

An automated system that forecasts 6 weather and air-quality metrics for
Peshawar, Pakistan, for the next 24 hours:

- Air Quality Index (AQI)
- Temperature (°C)
- Precipitation (mm and rain probability)
- Humidity (%)
- UV index
- Wind (speed and direction)

Built for the 10Pearls SHINE Internship, Cohort 10. The full system will have
a feature pipeline, model training, four LangGraph agents (forecast, alert,
weather report, drift), GitHub Actions automation and a Streamlit dashboard.

## City
Peshawar (latitude 34.01, longitude 71.58). All timestamps use UTC.

## Data sources
| Source | Used for |
|---|---|
| OpenWeather | Current weather and air pollution |
| Open-Meteo | 90 days of hourly history, live weather, live air quality (AQI, PM2.5, PM10) |
| AQICN | Optional extra. The Peshawar station is not available through the API, so it fails safely |

## Setup
1. Clone the repo and open the folder.
2. Create and activate a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate
   ```
3. Install the libraries:
   ```
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and add your own keys:
   ```
   OPENWEATHER_API_KEY=your_key_here
   AQICN_TOKEN=your_token_here
   ```

## How to run
- Fetch live data (saves raw JSON files in `data/raw/`):
  ```
  python src/fetch_live.py
  ```
- Download 90 days of hourly history (saves `data/raw/history_90d.csv`):
  ```
  python src/fetch_history.py
  ```
- First look at the data: open `notebooks/01_first_look.ipynb`

## Project structure
```
src/         Python scripts
notebooks/   Exploration notebooks
data/raw/    Raw downloads
docs/        Notes and answers
```

## Status
- Week 1: done (setup, live fetch, 90-day history, first look at the data)
- Week 2: feature pipeline, backfill, EDA (next)