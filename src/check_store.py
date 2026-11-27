from feature_pipeline import FG_FEATURES_NAME, FG_RAW_NAME, read_back

for name in (FG_RAW_NAME, FG_FEATURES_NAME):
    df = read_back(name)
    print(name, "rows:", len(df), "| duplicate times:", int(df["time"].duplicated().sum()))
    print("  first:", df["time"].min(), " last:", df["time"].max())