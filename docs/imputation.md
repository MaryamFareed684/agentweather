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
(paste the REAL DATA table here)

The history comes from a model (reanalysis), so it has no gaps (0% missing).
Gaps are expected in live data (API downtime, sensor gaps).

## Test with deliberate gaps
We removed 1-hour, 3-hour and 6-hour gaps from 4 columns. The 1-hour and
3-hour gaps were fully filled. In the 6-hour gap only the first 3 hours were
filled and the rest stayed missing, as intended.