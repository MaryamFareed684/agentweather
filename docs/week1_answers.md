# Week 1 Answers

## Q1. Explain the project to a friend
AgentWeather is like a small weather newsroom run by robots. Every hour it
collects weather and air-quality numbers for Peshawar and saves them. It
learns patterns from the past and predicts the next 24 hours of AQI,
temperature, rain, humidity, UV and wind. Four helper programs (agents) make
the forecast, write warnings, write a news-style report, and check that the
data and models are still good. A website shows everything, and GitHub
Actions runs the whole thing automatically.

## Q2. What is a target?
A target is the answer we want the model to predict. For the row at 10:00
today, the temperature target is the temperature at 10:00 tomorrow. We make
targets by shifting the data 24 hours, so each row gets "tomorrow's answer"
next to today's values. The newest 24 hours have no target yet, so they are
only used for forecasting.

## Q3. Why are API keys dangerous in GitHub code?
My repo is public, and bots scan GitHub all day looking for keys. Anyone who
finds my key can use my account, use up my free limits, or act in my name.
So I keep keys in the .env file, which is listed in .gitignore. The repo only
has .env.example with fake values.

## Q4. Why two sources for one metric, and what problem appears?
Two sources can fill each other's gaps when one API is down, and I can
compare them to catch mistakes. The problem is that they can use different
units and scales (OpenWeather AQI is 1 to 5, Open-Meteo AQI is 0 to 500, wind
is m/s in one and km/h in the other), and they can give different values for
the same hour (19.1 vs 18.1 C, 55 vs 70 % humidity). So I must convert them
to the same units first, then decide to average them, use one as the main
source, or keep both as separate features.

## Q5. Which column has the most missing values?
No column has missing values. All 8 columns have 2160 non-null values. This
is because Open-Meteo history comes from a computer model that fills every
hour, not from a sensor that can fail. Missing values will appear in the live
data when an API is down or a station stops sending (for example AQICN
returned "Unknown ID" for my station), so I still need an imputation plan in
Week 2.

## Q6. Clearest daily pattern, hardest metric, and was my guess right?
UV index and temperature have the clearest daily pattern. UV is zero at night
and has one peak at midday, and temperature rises in the afternoon and falls
at night. Humidity is also clear and moves opposite to temperature.
Precipitation is the hardest because it is zero most of the time with a few
sudden spikes (only about 5 mm in one hour on the biggest day). Wind speed and
wind direction also look hard because they have no daily pattern, and the
direction jumps between 0 and 360 degrees.

My Day 1 guess was that AQI, temperature and UV would be easy, and that
rain, humidity and wind would be harder. Temperature, UV, rain and wind were
right. Humidity was easier than I guessed because it has a clear daily
pattern. AQI was medium, not easy: it moves in slow waves over several days
instead of a clean daily cycle.