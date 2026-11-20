
import requests

url = "https://api.open-meteo.com/v1/forecast"

params = {
    "latitude": 34.01,
    "longitude": 71.58,
    "current": "temperature_2m"
}

response = requests.get(url, params=params, timeout=10)

print("Status Code:", response.status_code)

data = response.json()

print("Weather Data:")
print(data)

print("Current Temperature:", data["current"]["temperature_2m"], "°C")
