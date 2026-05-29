import os
import pandas as pd

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# -------------------------------------------------
# Correct Malaysia state names based on your GeoJSON
# -------------------------------------------------

STATE_NAME_MAP = {
    "Johor": "Johor",
    "Kedah": "Kedah",
    "Kelantan": "Kelantan",
    "Melaka": "Melaka",
    "Malacca": "Melaka",
    "NSembilan": "Negeri Sembilan",
    "N Sembilan": "Negeri Sembilan",
    "Negeri Sembilan": "Negeri Sembilan",
    "Pahang": "Pahang",
    "Pulau Pinang": "Pulau Pinang",
    "Penang": "Pulau Pinang",
    "P.Pinang": "Pulau Pinang",
    "Perak": "Perak",
    "Perlis": "Perlis",
    "Sabah": "Sabah",
    "Sarawak": "Sarawak",
    "Selangor": "Selangor",
    "Selangor-Wilayah": "Kuala Lumpur",
    "Kuala Lumpur": "Kuala Lumpur",
    "KL": "Kuala Lumpur",
    "Putrajaya": "Putrajaya",
    "Labuan": "Labuan",
    "Terengganu": "Terengganu"
}

MONTH_MAP = {
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

MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# -------------------------------------------------
# Helper functions
# -------------------------------------------------

def clean_columns(df):
    df = df.copy()
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace("(", "", regex=False)
        .str.replace(")", "", regex=False)
        .str.replace("/", "_", regex=False)
    )
    return df


def find_file(possible_names):
    files = os.listdir(DATA_DIR)
    lower_files = {f.lower(): f for f in files}

    for name in possible_names:
        if name.lower() in lower_files:
            return os.path.join(DATA_DIR, lower_files[name.lower()])

    for f in files:
        f_lower = f.lower()
        for name in possible_names:
            base = name.lower().replace(".csv", "")
            if base in f_lower:
                return os.path.join(DATA_DIR, f)

    return None


def find_column(df, possible_keywords):
    for col in df.columns:
        col_lower = col.lower()
        for keyword in possible_keywords:
            if keyword.lower() in col_lower:
                return col
    return None


def standardise_state_name(x):
    if pd.isna(x):
        return None
    x = str(x).strip()
    return STATE_NAME_MAP.get(x, x)


# -------------------------------------------------
# 1. Clean state monthly rainfall
# -------------------------------------------------

rainfall_state_month_file = find_file([
    "state_monthly_rainfall.csv",
    "state_monthly_rainfall_clean.csv",
    "daily rainfall each state 2.csv",
    "daily rainfall each state.csv"
])

if rainfall_state_month_file:
    print("\nCleaning rainfall state-month file:", rainfall_state_month_file)

    rain = pd.read_csv(rainfall_state_month_file)
    rain = clean_columns(rain)

    print("Rainfall columns:", list(rain.columns))

    state_col = find_column(rain, ["state"])
    month_col = find_column(rain, ["month"])
    rainfall_col = find_column(rain, ["avg_rainfall", "rainfall", "precip"])

    if state_col and month_col and rainfall_col:
        rain_clean = rain[[state_col, month_col, rainfall_col]].copy()
        rain_clean.columns = ["original_state_name", "month", "avg_rainfall_mm"]

        rain_clean["state"] = rain_clean["original_state_name"].apply(standardise_state_name)
        rain_clean["month"] = pd.to_numeric(rain_clean["month"], errors="coerce")
        rain_clean["month_name"] = rain_clean["month"].map(MONTH_MAP)
        rain_clean["avg_rainfall_mm"] = pd.to_numeric(rain_clean["avg_rainfall_mm"], errors="coerce")

        rain_clean = rain_clean.dropna(subset=["state", "month", "month_name", "avg_rainfall_mm"])

        rain_clean = rain_clean[[
            "original_state_name",
            "state",
            "month",
            "month_name",
            "avg_rainfall_mm"
        ]]

        rain_clean["avg_rainfall_mm"] = rain_clean["avg_rainfall_mm"].round(2)

        rain_clean.to_csv("data/rainfall_state_month_clean.csv", index=False)
        print("Created data/rainfall_state_month_clean.csv")

        # Monthly rainfall overall
        monthly = (
            rain_clean
            .groupby(["month", "month_name"], as_index=False)
            .agg(avg_rainfall_mm=("avg_rainfall_mm", "mean"))
        )

        monthly["avg_rainfall_mm"] = monthly["avg_rainfall_mm"].round(2)
        monthly.to_csv("data/rainfall_monthly_clean.csv", index=False)
        print("Created data/rainfall_monthly_clean.csv")

        # State rainfall summary
        state_summary = (
            rain_clean
            .groupby("state", as_index=False)
            .agg(avg_rainfall_mm=("avg_rainfall_mm", "mean"))
        )

        state_summary["avg_rainfall_mm"] = state_summary["avg_rainfall_mm"].round(2)
        state_summary = state_summary.sort_values("avg_rainfall_mm", ascending=False)
        state_summary.to_csv("data/rainfall_state_summary_clean.csv", index=False)
        print("Created data/rainfall_state_summary_clean.csv")

    else:
        print("Could not detect state/month/rainfall columns.")
else:
    print("\nNo rainfall state-month file found.")


# -------------------------------------------------
# 2. Clean temperature data
# -------------------------------------------------

temp_file = find_file([
    "min av max air temp.csv",
    "precipitation min ave max temp.csv",
    "mean air temp.csv",
    "average air temp.csv"
])

if temp_file:
    print("\nCleaning temperature file:", temp_file)

    temp = pd.read_csv(temp_file)
    temp = clean_columns(temp)

    print("Temperature columns:", list(temp.columns))

    year_col = find_column(temp, ["year"])
    month_col = find_column(temp, ["month"])

    if year_col is None and month_col is None:
        first_col = temp.columns[0]
        first_values = temp[first_col].astype(str).str.strip()
        month_values = {v.lower(): k for k, v in MONTH_MAP.items()}

        if first_values.str.lower().isin(month_values).any():
            month_col = first_col
        elif pd.to_numeric(temp[first_col], errors="coerce").notna().any():
            year_col = first_col

    min_col = find_column(temp, ["minimum"])
    max_col = find_column(temp, ["maximum"])
    avg_col = find_column(temp, ["mean"])

    if avg_col is None:
        for col in temp.columns:
            if "average" in col and "minimum" not in col and "maximum" not in col:
                avg_col = col
                break

    # Avoid using min column as month by mistake
    if min_col == month_col:
        min_col = None

    if (year_col or month_col) and (avg_col or min_col or max_col):
        keep_cols = []
        rename_dict = {}

        if year_col:
            keep_cols.append(year_col)
            rename_dict[year_col] = "year"

        if month_col:
            keep_cols.append(month_col)
            rename_dict[month_col] = "month_raw"

        if min_col:
            keep_cols.append(min_col)
            rename_dict[min_col] = "min_temp"

        if avg_col:
            keep_cols.append(avg_col)
            rename_dict[avg_col] = "avg_temp"

        if max_col:
            keep_cols.append(max_col)
            rename_dict[max_col] = "max_temp"

        temp_clean = temp[keep_cols].copy()
        temp_clean = temp_clean.rename(columns=rename_dict)

        if "year" in temp_clean.columns:
            temp_clean["year"] = pd.to_numeric(temp_clean["year"], errors="coerce")

        if "month_raw" in temp_clean.columns:
            month_lookup = {v.lower(): k for k, v in MONTH_MAP.items()}
            numeric_month = pd.to_numeric(temp_clean["month_raw"], errors="coerce")
            named_month = temp_clean["month_raw"].astype(str).str.strip().str.lower().map(month_lookup)
            temp_clean["month"] = numeric_month.fillna(named_month)
            temp_clean["month_name"] = temp_clean["month"].map(MONTH_MAP)
            temp_clean = temp_clean.drop(columns=["month_raw"])

        for col in ["min_temp", "avg_temp", "max_temp"]:
            if col in temp_clean.columns:
                temp_clean[col] = pd.to_numeric(temp_clean[col], errors="coerce").round(2)

        if "year" in temp_clean.columns:
            temp_clean = temp_clean.dropna(subset=["year"])

        if "month" in temp_clean.columns:
            temp_clean = temp_clean.dropna(subset=["month"])
            temp_clean["month"] = temp_clean["month"].astype(int)
            temp_clean = temp_clean.sort_values("month")

        ordered_cols = []
        for col in ["year", "month", "month_name", "min_temp", "avg_temp", "max_temp"]:
            if col in temp_clean.columns:
                ordered_cols.append(col)
        temp_clean = temp_clean[ordered_cols]

        temp_clean.to_csv("data/temperature_clean.csv", index=False)
        print("Created data/temperature_clean.csv")

        if "month" in temp_clean.columns and "year" not in temp_clean.columns:
            temp_clean.to_csv("data/temperature_monthly_clean.csv", index=False)
            print("Created data/temperature_monthly_clean.csv")

        # Yearly version
        numeric_cols = [c for c in ["min_temp", "avg_temp", "max_temp"] if c in temp_clean.columns]

        if numeric_cols and "year" in temp_clean.columns:
            yearly_temp = (
                temp_clean
                .groupby("year", as_index=False)[numeric_cols]
                .mean()
            )

            for col in numeric_cols:
                yearly_temp[col] = yearly_temp[col].round(2)

            yearly_temp.to_csv("data/temperature_yearly_clean.csv", index=False)
            print("Created data/temperature_yearly_clean.csv")

    else:
        print("Could not detect year/temperature columns.")
else:
    print("\nNo temperature file found.")


# -------------------------------------------------
# 3. Clean disaster type summary
# -------------------------------------------------

disaster_type_file = find_file([
    "natural disasters count.csv",
    "disaster_type_summary.csv",
    "disaster_type_summary 2_compressed.csv"
])

if disaster_type_file:
    print("\nCleaning disaster type file:", disaster_type_file)

    dis = pd.read_csv(disaster_type_file)
    dis = clean_columns(dis)

    print("Disaster type columns:", list(dis.columns))

    # Usually first column = disaster type, second column = count
    type_col = dis.columns[0]
    count_col = None

    for col in dis.columns:
        if "count" in col or "total" in col or "number" in col:
            count_col = col
            break

    if count_col is None and len(dis.columns) >= 2:
        count_col = dis.columns[1]

    disaster_clean = dis[[type_col, count_col]].copy()
    disaster_clean.columns = ["disaster_type", "count"]

    disaster_clean["disaster_type"] = (
        disaster_clean["disaster_type"]
        .astype(str)
        .str.strip()
        .str.title()
    )

    disaster_clean["count"] = pd.to_numeric(disaster_clean["count"], errors="coerce")
    disaster_clean = disaster_clean.dropna(subset=["count"])
    disaster_clean = disaster_clean.sort_values("count", ascending=False)

    disaster_clean.to_csv("data/disaster_type_clean.csv", index=False)
    print("Created data/disaster_type_clean.csv")
else:
    print("\nNo disaster type file found.")


# -------------------------------------------------
# 4. Clean disasters over the year / flood yearly
# -------------------------------------------------

disaster_year_file = find_file([
    "disasters over the year.csv",
    "disasters over the year 2_compressed.csv"
])

if disaster_year_file:
    print("\nCleaning disaster year file:", disaster_year_file)

    dy = pd.read_csv(disaster_year_file)
    dy = clean_columns(dy)

    print("Disaster year columns:", list(dy.columns))

    year_col = find_column(dy, ["year"])
    flood_col = find_column(dy, ["flood"])

    if year_col is None:
        first_col = dy.columns[0]
        if pd.to_numeric(dy[first_col], errors="coerce").notna().any():
            year_col = first_col

    if year_col and flood_col:
        flood_clean = dy[[year_col, flood_col]].copy()
        flood_clean.columns = ["year", "flood_count"]

        flood_clean["year"] = pd.to_numeric(flood_clean["year"], errors="coerce")
        flood_clean["flood_count"] = pd.to_numeric(flood_clean["flood_count"], errors="coerce").fillna(0)

        flood_clean = flood_clean.dropna(subset=["year"])
        flood_clean = flood_clean.sort_values("year")

        flood_clean.to_csv("data/flood_yearly_clean.csv", index=False)
        print("Created data/flood_yearly_clean.csv")
    else:
        print("Could not detect year/flood columns.")
else:
    print("\nNo disaster year file found.")


# -------------------------------------------------
# 5. Optional: rainfall vs flood yearly combined file
# -------------------------------------------------

rainfall_monthly_path = "data/rainfall_monthly_clean.csv"
flood_yearly_path = "data/flood_yearly_clean.csv"

# This only creates a combined file if you have yearly rainfall later.
# For now, we skip because your rainfall_state_month_clean file is monthly/state-level.
print("\nCleaning complete.")
print("Use these clean files for non-map graphs:")
print("- data/rainfall_monthly_clean.csv")
print("- data/rainfall_state_summary_clean.csv")
print("- data/rainfall_state_month_clean.csv")
print("- data/temperature_clean.csv")
print("- data/temperature_monthly_clean.csv")
print("- data/disaster_type_clean.csv")
print("- data/flood_yearly_clean.csv")
