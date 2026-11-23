# Imputation

## Rules
- Only past values are used (forward fill), because in the live pipeline we
  cannot see the future. Training data uses the same rule, so both match.
- Maximum gap filled: 3 hours. Longer gaps stay missing and the rows are
  dropped from training. We do not invent days of data.
- Wind direction is never interpolated: halfway between 350 and 10 degrees
  would be 180, the opposite direction.
- Precipitation is filled with 0 (not the last value), because rain is spiky
  and repeating a rain amount would invent a storm. This assumes "no rain" for
  short gaps and can be wrong during a storm.
- Every filled column gets a flag column (<column>_imputed, 1 = filled).

## Results on the history data (41 days checked)

REAL DATA imputation report:
            column  missing_before_pct       method  max_gap_filled_h  missing_after_pct
     temperature_c                 0.0 forward fill                 3                0.0
      humidity_pct                 0.0 forward fill                 3                0.0
  precipitation_mm                 0.0  fill with 0                 3                0.0
     wind_speed_ms                 0.0 forward fill                 3                0.0
wind_direction_deg                 0.0 forward fill                 3                0.0
      pressure_hpa                 0.0 forward fill                 3                0.0
   cloud_cover_pct                 0.0 forward fill                 3                0.0
          uv_index                 0.0 forward fill                 3                0.0
            us_aqi                 0.0 forward fill                 3                0.0
             pm2_5                 0.0 forward fill                 3                0.0
              pm10                 0.0 forward fill                 3                0.0

PRACTICE DATA (holes made on purpose):
            column  missing_before_pct       method  max_gap_filled_h  missing_after_pct
     temperature_c                1.02 forward fill                 3                0.3
  precipitation_mm                1.02  fill with 0                 3                0.3
wind_direction_deg                1.02 forward fill                 3                0.3
            us_aqi                1.02 forward fill                 3                0.3

The 6 hour gap (rows 300 to 305), temperature_c and its flag:
                         time  temperature_c  temperature_c_imputed
298 2026-10-21 10:00:00+00:00           28.4                      0
299 2026-10-21 11:00:00+00:00           27.8                      0
300 2026-10-21 12:00:00+00:00           27.8                      1
301 2026-10-21 13:00:00+00:00           27.8                      1
302 2026-10-21 14:00:00+00:00           27.8                      1
303 2026-10-21 15:00:00+00:00            NaN                      0
304 2026-10-21 16:00:00+00:00            NaN                      0
305 2026-10-21 17:00:00+00:00            NaN                      0
306 2026-10-21 18:00:00+00:00           20.9                      0
307 2026-10-21 19:00:00+00:00           20.4                      0

The history comes from a model (reanalysis), so it has no gaps (0% missing).
Gaps are expected in live data (API downtime, sensor gaps).

## Test with deliberate gaps
We removed 1-hour, 3-hour and 6-hour gaps from 4 columns. The 1-hour and
3-hour gaps were fully filled. In the 6-hour gap only the first 3 hours were
filled and the rest stayed missing, as intended.