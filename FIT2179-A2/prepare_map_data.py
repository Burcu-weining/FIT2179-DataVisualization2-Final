import pandas as pd

# Load your rainfall dataset
df = pd.read_csv("data/rainfall_recent.csv")

# Keep only state-level rows
# adm_level = 1 means state/admin level 1
df = df[df["adm_level"] == 1].copy()

# Convert PCODE format from MY01 to MY-01
df["shapeISO"] = df["PCODE"].str.replace(r"MY(\d+)", r"MY-\1", regex=True)

# Keep only the columns we need
df = df[["date", "PCODE", "shapeISO", "rfh", "rfh_avg"]]

# Remove missing rainfall values
df = df.dropna(subset=["rfh"])

# Calculate average rainfall by state
state_rainfall = (
    df.groupby(["shapeISO"], as_index=False)
      .agg(
          avg_rainfall_mm=("rfh", "mean"),
          avg_normal_rainfall_mm=("rfh_avg", "mean")
      )
)

# Add difference from normal rainfall
state_rainfall["difference_from_normal"] = (
    state_rainfall["avg_rainfall_mm"] - state_rainfall["avg_normal_rainfall_mm"]
)

# Round values
state_rainfall["avg_rainfall_mm"] = state_rainfall["avg_rainfall_mm"].round(2)
state_rainfall["avg_normal_rainfall_mm"] = state_rainfall["avg_normal_rainfall_mm"].round(2)
state_rainfall["difference_from_normal"] = state_rainfall["difference_from_normal"].round(2)

# Save cleaned file for Vega-Lite
state_rainfall.to_csv("data/state_rainfall_map.csv", index=False)

print("Created data/state_rainfall_map.csv")
print(state_rainfall.head())