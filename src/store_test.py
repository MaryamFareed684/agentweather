"""Store a small test range in Hopsworks twice and check nothing is duplicated."""

from datetime import datetime, timedelta, timezone

from feature_pipeline import (
    FG_FEATURES_NAME,
    FG_RAW_NAME,
    RAW_COLS,
    build_features,
    fetch_raw,
    fuse,
    read_back,
    store,
)

today = datetime.now(timezone.utc).date()
end = (today - timedelta(days=5)).isoformat()
start = (today - timedelta(days=45)).isoformat()

weather_df, air_df = fetch_raw("backfill", start, end)
fused = fuse(weather_df, air_df, start, end)
features, feature_cols = build_features(fused)
observations = fused[RAW_COLS]

for run in (1, 2):
    print(f"\n=== Store run {run} (same data both times) ===")
    n_obs, n_feat = store(observations, features, feature_cols)
    print(f"Sent {n_obs} observation rows and {n_feat} feature rows")

print("\n=== Read back from Hopsworks ===")
for name in (FG_RAW_NAME, FG_FEATURES_NAME):
    df = read_back(name)
    print(name, "rows:", len(df), "| duplicate times:", int(df["time"].duplicated().sum()))
    print("  first:", df["time"].min(), " last:", df["time"].max())