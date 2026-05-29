import pandas as pd
import json

# Load state monthly rainfall file
df = pd.read_csv("data/state_monthly_rainfall.csv")

# Clean column names
df.columns = [c.strip() for c in df.columns]

# Rename columns if needed
df = df.rename(columns={
    "State": "state",
    "Month": "month",
    "Avg_Rainfall_mm": "avg_rainfall_mm",
    "Average Rainfall": "avg_rainfall_mm"
})

# Remove empty rows
df = df.dropna(subset=["state"])
df["state"] = df["state"].astype(str).str.strip()

# Keep original state name
df["original_state_name"] = df["state"]

# Match your rainfall state names to the new GeoJSON names
state_name_map = {
    "Johor": "Johor",
    "Kedah": "Kedah",
    "Kelantan": "Kelantan",
    "Melaka": "Melaka",
    "NSembilan": "Negeri Sembilan",
    "Negeri Sembilan": "Negeri Sembilan",
    "Pahang": "Pahang",
    "Perak": "Perak",
    "Perlis": "Perlis",
    "Selangor": "Selangor",
    "Selangor-Wilayah": "Kuala Lumpur",
    "Kuala Lumpur": "Kuala Lumpur",
    "Terengganu": "Terengganu",
    "Pulau Pinang": "Pulau Pinang",
    "Penang": "Pulau Pinang"
}

df["state"] = df["state"].map(state_name_map)

# Month names
month_map = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec"
}

df["month"] = pd.to_numeric(df["month"], errors="coerce")
df["month_name"] = df["month"].map(month_map)
df["avg_rainfall_mm"] = pd.to_numeric(df["avg_rainfall_mm"], errors="coerce")

# Load new GeoJSON to check state names
with open("data/malaysia_states_simple.geojson", "r", encoding="utf-8") as f:
    geo = json.load(f)

geo_states = []

for feature in geo["features"]:
    props = feature["properties"]
    geo_states.append(props.get("name"))

geo_states = sorted(set(geo_states))

print("States in GeoJSON:")
print(geo_states)

print("\nStates in rainfall file after cleaning:")
print(sorted(df["state"].dropna().unique()))

# Check missing matches
missing = df[df["state"].isna()]

if len(missing) > 0:
    print("\nWARNING: These original state names did not map:")
    print(missing["original_state_name"].unique())

# Keep only rows where state, month, and rainfall exist
clean = df.dropna(subset=["state", "month", "avg_rainfall_mm"]).copy()

# Keep only states that exist in GeoJSON
clean = clean[clean["state"].isin(geo_states)].copy()

# Round rainfall
clean["avg_rainfall_mm"] = clean["avg_rainfall_mm"].round(2)

# Final columns
clean = clean[[
    "original_state_name",
    "state",
    "month",
    "month_name",
    "avg_rainfall_mm"
]]

# Save clean file
clean.to_csv("data/state_monthly_rainfall_clean.csv", index=False)

print("\nCreated data/state_monthly_rainfall_clean.csv")
print(clean.head(20))
print("\nRows created:", len(clean))