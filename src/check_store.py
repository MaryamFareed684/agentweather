from feature_pipeline import FG_FEATURES_NAME, FG_RAW_NAME, TARGET_COLS, read_back

for name in (FG_RAW_NAME, FG_FEATURES_NAME):
    df = read_back(name)
    print(name, "rows:", len(df), "| duplicate times:", int(df["time"].duplicated().sum()))
    print("  first:", df["time"].min(), " last:", df["time"].max())
    if name == FG_FEATURES_NAME:
        print("  rows without a full target:", int(df[TARGET_COLS].isna().any(axis=1).sum()))