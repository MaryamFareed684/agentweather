from feature_pipeline import fetch_live

weather, air = fetch_live()
print("weather rows:", len(weather), "| first:", weather["time"].min(), "| last:", weather["time"].max())
print("air rows:", len(air), "| first:", air["time"].min(), "| last:", air["time"].max())
print(weather.tail(3).to_string())
print(air.tail(3).to_string())