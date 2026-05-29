import os
import json
import math
import pandas as pd

DATA_DIR = "data"
JS_DIR = "js"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(JS_DIR, exist_ok=True)


# =========================
# HELPER FUNCTIONS
# =========================

def save_json(filename, spec):
    with open(os.path.join(JS_DIR, filename), "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2)
    print(f"Created js/{filename}")


def clean_columns(df):
    df = df.copy()
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("/", "_", regex=False)
        .str.replace("(", "", regex=False)
        .str.replace(")", "", regex=False)
        .str.replace("%", "pct", regex=False)
    )
    return df


# =========================
# 1. PREPARE STATE RAINFALL DATA
# =========================

state_rain = pd.read_csv("data/state_rainfall_map.csv")
state_rain = clean_columns(state_rain)

# Fix column name if needed
if "shapeiso" in state_rain.columns:
    state_rain = state_rain.rename(columns={"shapeiso": "shapeISO"})
elif "shape_iso" in state_rain.columns:
    state_rain = state_rain.rename(columns={"shape_iso": "shapeISO"})

# If your CSV has MY-01 style already, keep it.
# If it accidentally became MY01, convert it.
state_rain["shapeISO"] = state_rain["shapeISO"].astype(str)
state_rain["shapeISO"] = state_rain["shapeISO"].str.replace("MY", "MY-", regex=False)
state_rain["shapeISO"] = state_rain["shapeISO"].str.replace("MY--", "MY-", regex=False)

# Create state labels using codes for now
state_rain["state"] = state_rain["shapeISO"]

# Create extra columns
state_rain["rainfall_ratio"] = state_rain["avg_rainfall_mm"] / state_rain["avg_normal_rainfall_mm"]

state_rain["rainfall_status"] = state_rain["difference_from_normal"].apply(
    lambda x: "Above normal" if x >= 0 else "Below normal"
)

q1 = state_rain["avg_rainfall_mm"].quantile(0.33)
q2 = state_rain["avg_rainfall_mm"].quantile(0.66)

def category(x):
    if x <= q1:
        return "Lower rainfall"
    elif x <= q2:
        return "Moderate rainfall"
    else:
        return "Higher rainfall"

state_rain["rainfall_category"] = state_rain["avg_rainfall_mm"].apply(category)

state_rain.to_csv("data/state_rainfall_summary.csv", index=False)
print("Created data/state_rainfall_summary.csv")


# =========================
# 2. PREPARE MONTHLY RAINFALL DATA
# =========================

daily_file = "data/daily rainfall each state.csv"

if os.path.exists(daily_file):
    daily = pd.read_csv(daily_file)
    daily = clean_columns(daily)

    print("Daily rainfall columns:", list(daily.columns))

    # Try to detect columns
    state_col = None
    month_col = None
    rain_col = None

    for col in daily.columns:
        if "state" in col:
            state_col = col
        if "month" in col:
            month_col = col
        if "rain" in col:
            rain_col = col

    if state_col and month_col and rain_col:
        daily[rain_col] = pd.to_numeric(daily[rain_col], errors="coerce")
        daily = daily.dropna(subset=[rain_col])

        monthly = (
            daily.groupby(month_col, as_index=False)[rain_col]
            .mean()
            .rename(columns={month_col: "month", rain_col: "avg_rainfall_mm"})
        )
        monthly["avg_rainfall_mm"] = monthly["avg_rainfall_mm"].round(2)
        monthly.to_csv("data/monthly_rainfall.csv", index=False)

        state_monthly = (
            daily.groupby([state_col, month_col], as_index=False)[rain_col]
            .mean()
            .rename(columns={
                state_col: "state",
                month_col: "month",
                rain_col: "avg_rainfall_mm"
            })
        )
        state_monthly["avg_rainfall_mm"] = state_monthly["avg_rainfall_mm"].round(2)
        state_monthly.to_csv("data/state_monthly_rainfall.csv", index=False)

        print("Created monthly rainfall files")
    else:
        print("Could not detect state/month/rainfall columns in daily rainfall file")


# =========================
# 3. PREPARE DISASTER DATA
# =========================

disaster_count_file = "data/natural disasters count.csv"

if os.path.exists(disaster_count_file):
    disaster_count = pd.read_csv(disaster_count_file)
    disaster_count = clean_columns(disaster_count)

    print("Natural disaster count columns:", list(disaster_count.columns))

    first_col = disaster_count.columns[0]
    second_col = disaster_count.columns[1]

    disaster_summary = disaster_count[[first_col, second_col]].copy()
    disaster_summary.columns = ["disaster_type", "count"]
    disaster_summary["count"] = pd.to_numeric(disaster_summary["count"], errors="coerce")
    disaster_summary = disaster_summary.dropna(subset=["count"])
    disaster_summary.to_csv("data/disaster_type_summary.csv", index=False)

    print("Created data/disaster_type_summary.csv")

    disaster_pareto = disaster_summary[
        ~disaster_summary["disaster_type"].str.lower().str.contains("mass movement", na=False)
    ].copy()
    disaster_pareto = disaster_pareto.sort_values("count", ascending=False).reset_index(drop=True)
    disaster_pareto["cumulative_count"] = disaster_pareto["count"].cumsum()
    disaster_pareto["cumulative_pct"] = (
        disaster_pareto["cumulative_count"] / disaster_pareto["count"].sum() * 100
    ).round(2)
    disaster_pareto["count"] = disaster_pareto["count"].round(0)
    disaster_pareto.to_csv("data/disaster_type_pareto.csv", index=False)
    print("Created data/disaster_type_pareto.csv")


disaster_year_file = "data/disasters over the year.csv"

if os.path.exists(disaster_year_file):
    disaster_year = pd.read_csv(disaster_year_file)
    disaster_year = clean_columns(disaster_year)

    print("Disasters over year columns:", list(disaster_year.columns))

    year_col = None
    flood_col = None

    for col in disaster_year.columns:
        if "year" in col:
            year_col = col
        if "flood" in col:
            flood_col = col

    if year_col is None:
        first_col = disaster_year.columns[0]
        if pd.to_numeric(disaster_year[first_col], errors="coerce").notna().any():
            year_col = first_col

    if year_col and flood_col:
        flood_yearly = disaster_year[[year_col, flood_col]].copy()
        flood_yearly.columns = ["year", "flood_count"]
        flood_yearly["year"] = pd.to_numeric(flood_yearly["year"], errors="coerce")
        flood_yearly["flood_count"] = pd.to_numeric(flood_yearly["flood_count"], errors="coerce").fillna(0)
        flood_yearly = flood_yearly.dropna(subset=["year"])
        flood_yearly = flood_yearly.sort_values("year")
        flood_yearly.to_csv("data/flood_yearly.csv", index=False)

        print("Created data/flood_yearly.csv")

        disaster_long = disaster_year.rename(columns={year_col: "year"}).copy()
        disaster_long["year"] = pd.to_numeric(disaster_long["year"], errors="coerce")
        value_cols = [c for c in disaster_long.columns if c != "year"]
        disaster_long = disaster_long.melt(
            id_vars="year",
            value_vars=value_cols,
            var_name="disaster_type",
            value_name="count"
        )
        disaster_long["count"] = pd.to_numeric(disaster_long["count"], errors="coerce").fillna(0)
        disaster_long["disaster_type"] = (
            disaster_long["disaster_type"]
            .str.replace("_", " ")
            .str.title()
            .str.replace("Dry", "(Dry)", regex=False)
            .str.replace("Wet", "(Wet)", regex=False)
        )
        disaster_long = disaster_long.dropna(subset=["year"])
        disaster_long["year"] = disaster_long["year"].astype(int)
        disaster_long.to_csv("data/disaster_year_type_long.csv", index=False)
        print("Created data/disaster_year_type_long.csv")
    else:
        print("Could not detect year/flood columns")

rainfall_history_file = "data/full rainfall data.csv"
if os.path.exists(rainfall_history_file) and os.path.exists("data/flood_yearly.csv"):
    rain_history = pd.read_csv(rainfall_history_file)
    rain_history = clean_columns(rain_history)

    if {"dt", "rfh", "rfh_avg"}.issubset(rain_history.columns):
        rain_history["year"] = pd.to_numeric(
            rain_history["dt"].astype(str).str.slice(0, 4),
            errors="coerce"
        )
        rain_history["rfh"] = pd.to_numeric(rain_history["rfh"], errors="coerce")
        rain_history["rfh_avg"] = pd.to_numeric(rain_history["rfh_avg"], errors="coerce")

        annual_rain = (
            rain_history
            .dropna(subset=["year", "rfh", "rfh_avg"])
            .groupby("year", as_index=False)
            .agg(actual_rainfall=("rfh", "sum"), normal_rainfall=("rfh_avg", "sum"))
        )
        annual_rain["rainfall_ratio"] = annual_rain["actual_rainfall"] / annual_rain["normal_rainfall"]
        annual_rain["rainfall_anomaly_pct"] = (annual_rain["rainfall_ratio"] - 1) * 100

        flood_yearly = pd.read_csv("data/flood_yearly.csv")
        flood_yearly["year"] = pd.to_numeric(flood_yearly["year"], errors="coerce")
        flood_yearly["flood_count"] = pd.to_numeric(flood_yearly["flood_count"], errors="coerce").fillna(0)

        flood_rainfall = annual_rain.merge(flood_yearly, on="year", how="inner")
        flood_rainfall["flood_risk_level"] = pd.cut(
            flood_rainfall["flood_count"],
            bins=[-0.1, 1, 4, float("inf")],
            labels=["0-1 flood", "2-4 floods", "5+ floods"]
        )
        flood_rainfall["year"] = flood_rainfall["year"].astype(int)
        flood_rainfall = flood_rainfall.round({
            "actual_rainfall": 2,
            "normal_rainfall": 2,
            "rainfall_ratio": 3,
            "rainfall_anomaly_pct": 2,
            "flood_count": 0
        })
        flood_rainfall.to_csv("data/flood_rainfall_yearly_relationship.csv", index=False)
        print("Created data/flood_rainfall_yearly_relationship.csv")

# =========================
# 4. PREPARE NEW FLOOD DATASETS
# =========================

STATE_NUMERIC_TO_NAME = {
    101: "Johor",
    102: "Kedah",
    103: "Kelantan",
    104: "Melaka",
    105: "Negeri Sembilan",
    106: "Pahang",
    107: "Pulau Pinang",
    108: "Perak",
    109: "Perlis",
    110: "Selangor",
    111: "Terengganu",
    112: "Sabah",
    113: "Sarawak",
    114: "Kuala Lumpur",
    115: "Labuan",
    116: "Putrajaya"
}

CITY_TO_STATE = {
    "Johor Bahru": "Johor",
    "Kota Bharu": "Kelantan",
    "Kota Kinabalu": "Sabah",
    "Kuala Lumpur": "Kuala Lumpur",
    "Kuantan": "Pahang",
    "Kuching": "Sarawak",
    "Melaka": "Melaka",
    "Shah Alam": "Selangor"
}

CITY_COORDS = {
    "Johor Bahru": (103.7414, 1.4927),
    "Kota Bharu": (102.2386, 6.1254),
    "Kota Kinabalu": (116.0735, 5.9804),
    "Kuala Lumpur": (101.6869, 3.1390),
    "Kuantan": (103.3256, 3.8077),
    "Kuching": (110.3592, 1.5533),
    "Melaka": (102.2501, 2.1896),
    "Shah Alam": (101.5183, 3.0738)
}

MONTH_NAME_MAP = {
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

master_flood_file = "data/malaysia_flood_master.csv"
if os.path.exists(master_flood_file):
    master_flood = pd.read_csv(master_flood_file)
    master_flood = clean_columns(master_flood)
    master_flood = master_flood.rename(columns={
        "date": "date",
        "temperature_c": "temperature_c",
        "humidity_pct": "humidity_pct",
        "wind_speed_ms": "wind_speed_ms",
        "rainfall_3day": "rainfall_3day_mm",
        "rainfall_7day": "rainfall_7day_mm",
        "rainfall_14day": "rainfall_14day_mm",
        "rainfall_cumsum7": "rainfall_cumsum7_mm",
        "is_monsoon": "is_monsoon",
        "flash_flood": "flash_flood"
    })
    master_flood["date"] = pd.to_datetime(master_flood["date"], errors="coerce")
    master_flood["year"] = master_flood["date"].dt.year
    master_flood["month"] = pd.to_numeric(master_flood["month"], errors="coerce")
    master_flood["month_name"] = master_flood["month"].map(MONTH_NAME_MAP)
    master_flood["state_name"] = master_flood["city"].map(CITY_TO_STATE)
    master_flood["longitude"] = master_flood["city"].map(lambda city: CITY_COORDS.get(city, (None, None))[0])
    master_flood["latitude"] = master_flood["city"].map(lambda city: CITY_COORDS.get(city, (None, None))[1])

    numeric_cols = [
        "temperature_c",
        "humidity_pct",
        "wind_speed_ms",
        "rainfall_3day_mm",
        "rainfall_7day_mm",
        "rainfall_14day_mm",
        "rainfall_cumsum7_mm",
        "is_monsoon",
        "flood",
        "flash_flood"
    ]
    for col in numeric_cols:
        if col in master_flood.columns:
            master_flood[col] = pd.to_numeric(master_flood[col], errors="coerce")

    master_flood = master_flood.dropna(subset=["date", "city", "state_name"])
    master_flood.to_csv("data/malaysia_flood_master_clean.csv", index=False)
    print("Created data/malaysia_flood_master_clean.csv")

    city_flood_summary = (
        master_flood
        .groupby(["city", "state_name", "longitude", "latitude"], as_index=False)
        .agg(
            total_days=("date", "count"),
            flood_days=("flood", "sum"),
            flash_flood_days=("flash_flood", "sum"),
            avg_rainfall_7day_mm=("rainfall_7day_mm", "mean"),
            avg_humidity_pct=("humidity_pct", "mean")
        )
    )
    city_flood_summary["flood_day_rate_pct"] = (
        city_flood_summary["flood_days"] / city_flood_summary["total_days"] * 100
    )
    city_flood_summary["flash_flood_share_pct"] = (
        city_flood_summary["flash_flood_days"] / city_flood_summary["flood_days"].replace(0, pd.NA) * 100
    ).fillna(0)
    city_flood_summary = city_flood_summary.round({
        "avg_rainfall_7day_mm": 2,
        "avg_humidity_pct": 2,
        "flood_day_rate_pct": 2,
        "flash_flood_share_pct": 2
    })
    city_flood_summary.to_csv("data/malaysia_city_flood_summary.csv", index=False)
    print("Created data/malaysia_city_flood_summary.csv")

    city_month_flood = (
        master_flood
        .groupby(["city", "month", "month_name"], as_index=False)
        .agg(
            total_days=("date", "count"),
            flood_days=("flood", "sum"),
            avg_rainfall_7day_mm=("rainfall_7day_mm", "mean"),
            avg_humidity_pct=("humidity_pct", "mean")
        )
    )
    city_month_flood["flood_rate_pct"] = city_month_flood["flood_days"] / city_month_flood["total_days"] * 100
    city_month_flood = city_month_flood.round({
        "avg_rainfall_7day_mm": 2,
        "avg_humidity_pct": 2,
        "flood_rate_pct": 2
    })
    city_month_flood.to_csv("data/malaysia_city_month_flood_summary.csv", index=False)
    print("Created data/malaysia_city_month_flood_summary.csv")

district_flood_file = "data/malaysiaflooddataset.csv"
if os.path.exists(district_flood_file):
    district_flood = pd.read_csv(district_flood_file)
    district_flood = clean_columns(district_flood)
    district_flood = district_flood.rename(columns={
        "state": "state_code",
        "district": "district_code",
        "0v": "nov",
        "annual_rainfall": "annual_rainfall_mm"
    })
    district_flood["state_name"] = district_flood["state_code"].map(STATE_NUMERIC_TO_NAME)
    month_cols = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    for col in ["state_code", "district_code", "year", "annual_rainfall_mm", "flood"] + month_cols:
        if col in district_flood.columns:
            district_flood[col] = pd.to_numeric(district_flood[col], errors="coerce")
    district_flood = district_flood.dropna(subset=["state_name", "district_code", "year"])
    district_flood["year"] = district_flood["year"].astype(int)
    district_flood.to_csv("data/malaysia_flood_district_clean.csv", index=False)
    print("Created data/malaysia_flood_district_clean.csv")

    flood_state_summary = (
        district_flood
        .groupby(["state_code", "state_name"], as_index=False)
        .agg(
            district_year_records=("flood", "count"),
            flood_records=("flood", "sum"),
            districts=("district_code", "nunique"),
            avg_annual_rainfall_mm=("annual_rainfall_mm", "mean")
        )
    )
    flood_state_summary["flood_rate_pct"] = (
        flood_state_summary["flood_records"] / flood_state_summary["district_year_records"] * 100
    )
    flood_state_summary = flood_state_summary.round({
        "avg_annual_rainfall_mm": 2,
        "flood_rate_pct": 2
    })
    flood_state_summary.to_csv("data/malaysia_flood_state_summary.csv", index=False)
    print("Created data/malaysia_flood_state_summary.csv")

    geojson_file = "data/malaysia_states_simple.geojson"
    if os.path.exists(geojson_file):
        with open(geojson_file, "r", encoding="utf-8") as f:
            state_geo = json.load(f)

        def collect_points(coords):
            points = []
            if (
                isinstance(coords, list)
                and len(coords) >= 2
                and isinstance(coords[0], (int, float))
                and isinstance(coords[1], (int, float))
            ):
                return [(coords[0], coords[1])]

            if isinstance(coords, list):
                for item in coords:
                    points.extend(collect_points(item))

            return points

        centroid_rows = []
        for feature in state_geo.get("features", []):
            state_name = feature.get("properties", {}).get("name")
            points = collect_points(feature.get("geometry", {}).get("coordinates", []))
            if state_name and points:
                centroid_rows.append({
                    "state_name": state_name,
                    "longitude": sum(point[0] for point in points) / len(points),
                    "latitude": sum(point[1] for point in points) / len(points)
                })

        state_centroids = pd.DataFrame(centroid_rows)
        flood_symbol_map = flood_state_summary.merge(state_centroids, on="state_name", how="left")
        flood_symbol_map = flood_symbol_map.dropna(subset=["longitude", "latitude"])
        flood_symbol_map.to_csv("data/malaysia_flood_state_symbol_map.csv", index=False)
        print("Created data/malaysia_flood_state_symbol_map.csv")

state_monthly_file = "data/state_monthly_rainfall_clean.csv"
if os.path.exists(state_monthly_file):
    state_monthly = pd.read_csv(state_monthly_file)
    state_monthly = clean_columns(state_monthly)
    state_monthly["avg_rainfall_mm"] = pd.to_numeric(state_monthly["avg_rainfall_mm"], errors="coerce")
    state_monthly["month"] = pd.to_numeric(state_monthly["month"], errors="coerce")
    state_monthly = state_monthly.dropna(subset=["state", "month", "avg_rainfall_mm"])

    seasonality_rows = []
    for state, group in state_monthly.groupby("state"):
        wettest = group.loc[group["avg_rainfall_mm"].idxmax()]
        driest = group.loc[group["avg_rainfall_mm"].idxmin()]
        avg_monthly = group["avg_rainfall_mm"].mean()
        seasonality_index = group["avg_rainfall_mm"].std(ddof=0) / avg_monthly if avg_monthly else 0
        peak_to_dry_ratio = (
            wettest["avg_rainfall_mm"] / driest["avg_rainfall_mm"]
            if driest["avg_rainfall_mm"] else 0
        )

        wettest_month = int(wettest["month"])
        if wettest_month in [11, 12, 1]:
            wettest_period = "Northeast monsoon peak"
        elif wettest_month in [9, 10]:
            wettest_period = "Late-year transition peak"
        elif wettest_month in [3, 4, 5]:
            wettest_period = "Inter-monsoon peak"
        else:
            wettest_period = "Southwest monsoon peak"

        seasonality_rows.append({
            "state": state,
            "avg_monthly_rainfall": round(avg_monthly, 2),
            "seasonality_index": round(seasonality_index, 3),
            "wettest_month": wettest["month_name"],
            "wettest_month_rainfall": round(wettest["avg_rainfall_mm"], 2),
            "driest_month": driest["month_name"],
            "driest_month_rainfall": round(driest["avg_rainfall_mm"], 2),
            "peak_to_dry_ratio": round(peak_to_dry_ratio, 2),
            "wettest_period": wettest_period
        })

    seasonality = pd.DataFrame(seasonality_rows).sort_values("seasonality_index", ascending=False)
    seasonality.to_csv("data/rainfall_seasonality_by_state.csv", index=False)
    print("Created data/rainfall_seasonality_by_state.csv")

    radar_source = (
        seasonality
        .sort_values("seasonality_index", ascending=False)
        .head(5)
        .copy()
    )
    radar_metrics = [
        ("Average monthly rainfall", "avg_monthly_rainfall"),
        ("Wettest month rainfall", "wettest_month_rainfall"),
        ("Seasonality strength", "seasonality_index"),
        ("Wet/dry contrast", "peak_to_dry_ratio")
    ]
    radar_rows = []
    metric_count = len(radar_metrics)

    for metric_order, (metric_label, metric_col) in enumerate(radar_metrics):
        min_value = radar_source[metric_col].min()
        max_value = radar_source[metric_col].max()
        value_range = max_value - min_value
        angle = (2 * math.pi * metric_order / metric_count) - (math.pi / 2)

        for _, row in radar_source.iterrows():
            raw_value = row[metric_col]
            normalised = 0.25 + (0.75 * (raw_value - min_value) / value_range if value_range else 0)
            radar_rows.append({
                "state": row["state"],
                "metric": metric_label,
                "metric_order": metric_order,
                "point_order": metric_order,
                "raw_value": round(raw_value, 3),
                "normalised_value": round(normalised, 4),
                "x": round(normalised * math.cos(angle), 4),
                "y": round(normalised * math.sin(angle), 4)
            })

    # Repeat the first metric to close each state's radar polygon.
    for state in radar_source["state"]:
        first_point = next(row for row in radar_rows if row["state"] == state and row["metric_order"] == 0)
        closing_point = first_point.copy()
        closing_point["point_order"] = metric_count
        radar_rows.append(closing_point)

    pd.DataFrame(radar_rows).to_csv("data/rainfall_state_radar.csv", index=False)
    pd.DataFrame([
        {
            "metric": metric_label,
            "metric_order": metric_order,
            "x": round(1.08 * math.cos((2 * math.pi * metric_order / metric_count) - (math.pi / 2)), 4),
            "y": round(1.08 * math.sin((2 * math.pi * metric_order / metric_count) - (math.pi / 2)), 4)
        }
        for metric_order, (metric_label, _) in enumerate(radar_metrics)
    ]).to_csv("data/rainfall_state_radar_axes.csv", index=False)
    print("Created data/rainfall_state_radar.csv")


# =========================
# VEGA-LITE CHARTS
# =========================

STATE_CODE_TO_NAME_EXPR = "datum.shapeISO == 'MY-01' ? 'Johor' : datum.shapeISO == 'MY-02' ? 'Kedah' : datum.shapeISO == 'MY-03' ? 'Kelantan' : datum.shapeISO == 'MY-04' ? 'Melaka' : datum.shapeISO == 'MY-05' ? 'Negeri Sembilan' : datum.shapeISO == 'MY-06' ? 'Pahang' : datum.shapeISO == 'MY-07' ? 'Pulau Pinang' : datum.shapeISO == 'MY-08' ? 'Perak' : datum.shapeISO == 'MY-09' ? 'Perlis' : datum.shapeISO == 'MY-10' ? 'Selangor' : datum.shapeISO == 'MY-11' ? 'Terengganu' : datum.shapeISO == 'MY-12' ? 'Sabah' : datum.shapeISO == 'MY-13' ? 'Sarawak' : datum.shapeISO == 'MY-14' ? 'Kuala Lumpur' : datum.shapeISO == 'MY-15' ? 'Labuan' : datum.shapeISO == 'MY-16' ? 'Putrajaya' : datum.shapeISO == 'MY-17' ? 'Putrajaya' : datum.shapeISO"

def map_chart(filename, title, subtitle, field, legend_title, scheme, scale_extra=None):
    scale = {"scheme": scheme}
    if scale_extra:
        scale.update(scale_extra)

    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "title": {
            "text": title,
            "subtitle": subtitle,
            "font": "Georgia, Times New Roman, serif",
            "fontSize": 18,
            "color": "#1f5f99",
            "subtitleFont": "Arial, sans-serif",
            "subtitleFontSize": 12,
            "subtitleColor": "#222222",
            "anchor": "start"
        },
        "width": 420,
        "height": 360,
        "data": {"url": "data/state_rainfall_summary.csv"},
        "transform": [
            {"calculate": STATE_CODE_TO_NAME_EXPR, "as": "state_name"},
            {
                "lookup": "state_name",
                "from": {
                    "data": {
                        "url": "data/malaysia_states_simple.geojson",
                        "format": {"type": "json", "property": "features"}
                    },
                    "key": "properties.name"
                },
                "as": "geo"
            }
        ],
        "projection": {"type": "mercator"},
        "mark": {
            "type": "geoshape",
            "stroke": "white",
            "strokeWidth": 0.7
        },
        "encoding": {
            "shape": {"field": "geo", "type": "geojson"},
            "color": {
                "field": field,
                "type": "quantitative",
                "title": legend_title,
                "scale": scale
            },
            "tooltip": [
                {"field": "state_name", "type": "nominal", "title": "State"},
                {"field": "avg_rainfall_mm", "type": "quantitative", "title": "Average rainfall", "format": ".2f"},
                {"field": "avg_normal_rainfall_mm", "type": "quantitative", "title": "Normal rainfall", "format": ".2f"},
                {"field": "difference_from_normal", "type": "quantitative", "title": "Difference", "format": ".2f"},
                {"field": "rainfall_ratio", "type": "quantitative", "title": "Rainfall ratio", "format": ".2f"}
            ]
        },
        "config": {
            "view": {"stroke": None}
        }
    }

    save_json(filename, spec)


save_json("interactive_rainfall_condition_map.json", {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "title": {
        "text": "Interactive Rainfall Condition Map Across Malaysia",
        "subtitle": [
            "Use the dropdown to switch between normal rainfall, rainfall above normal, and actual / normal rainfall ratio."
        ],
        "font": "Georgia, Times New Roman, serif",
        "fontSize": 18,
        "color": "#1f5f99",
        "subtitleFont": "Arial, sans-serif",
        "subtitleFontSize": 12,
        "subtitleColor": "#222222",
        "anchor": "start"
    },
    "width": 820,
    "height": 520,
    "params": [
        {
            "name": "SelectedRainfallMetric",
            "value": "difference_from_normal",
            "bind": {
                "input": "select",
                "name": "Show: ",
                "options": [
                    "avg_normal_rainfall_mm",
                    "difference_from_normal",
                    "rainfall_ratio"
                ],
                "labels": [
                    "Normal rainfall",
                    "Rainfall above normal",
                    "Actual / normal rainfall ratio"
                ]
            }
        }
    ],
    "data": {"url": "data/state_rainfall_summary.csv"},
    "transform": [
        {"calculate": STATE_CODE_TO_NAME_EXPR, "as": "state_name"},
        {
            "calculate": "SelectedRainfallMetric == 'avg_normal_rainfall_mm' ? datum.avg_normal_rainfall_mm : SelectedRainfallMetric == 'difference_from_normal' ? datum.difference_from_normal : datum.rainfall_ratio",
            "as": "selected_value"
        },
        {
            "calculate": "SelectedRainfallMetric == 'avg_normal_rainfall_mm' ? 'Normal rainfall' : SelectedRainfallMetric == 'difference_from_normal' ? 'Rainfall above normal' : 'Actual / normal rainfall ratio'",
            "as": "selected_metric_label"
        },
        {
            "lookup": "state_name",
            "from": {
                "data": {
                    "url": "data/malaysia_states_simple.geojson",
                    "format": {"type": "json", "property": "features"}
                },
                "key": "properties.name"
            },
            "as": "geo"
        }
    ],
    "projection": {"type": "mercator"},
    "mark": {
        "type": "geoshape",
        "stroke": "white",
        "strokeWidth": 0.7
    },
    "encoding": {
        "shape": {"field": "geo", "type": "geojson"},
        "color": {
            "field": "selected_value",
            "type": "quantitative",
            "title": "Selected value",
            "scale": {"scheme": "cividis", "domainMin": 0}
        },
        "tooltip": [
            {"field": "state_name", "type": "nominal", "title": "State"},
            {"field": "selected_metric_label", "type": "nominal", "title": "Selected metric"},
            {"field": "selected_value", "type": "quantitative", "title": "Selected value", "format": ".2f"},
            {"field": "avg_rainfall_mm", "type": "quantitative", "title": "Recent rainfall", "format": ".2f"},
            {"field": "avg_normal_rainfall_mm", "type": "quantitative", "title": "Normal rainfall", "format": ".2f"},
            {"field": "difference_from_normal", "type": "quantitative", "title": "Rainfall above normal", "format": ".2f"},
            {"field": "rainfall_ratio", "type": "quantitative", "title": "Actual / normal ratio", "format": ".2f"}
        ]
    },
    "config": {
        "view": {"stroke": None}
    }
})


save_json("rainfall_bar.json", {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "title": {
        "text": "Average Rainfall in Each State in Malaysia",
        "subtitle": "Average rainfall in each state in Malaysia.",
        "font": "Georgia, Times New Roman, serif",
        "fontSize": 18,
        "color": "#1f5f99",
        "subtitleFont": "Arial, sans-serif",
        "subtitleFontSize": 12,
        "subtitleColor": "#222222",
        "anchor": "start"
    },
    "width": 440,
    "height": 360,
    "projection": {"type": "mercator"},
    "data": {"url": "data/state_rainfall_map.csv"},
    "transform": [
        {"calculate": STATE_CODE_TO_NAME_EXPR, "as": "state"},
        {
            "lookup": "state",
            "from": {
                "data": {
                    "url": "data/malaysia_states_simple.geojson",
                    "format": {"type": "json", "property": "features"}
                },
                "key": "properties.name"
            },
            "as": "geo"
        }
    ],
    "mark": {"type": "geoshape", "stroke": "white", "strokeWidth": 0.8},
    "encoding": {
        "shape": {"field": "geo", "type": "geojson"},
        "color": {
            "field": "avg_rainfall_mm",
            "type": "quantitative",
            "title": "Average rainfall (mm)",
            "scale": {"scheme": "cividis", "domainMin": 0},
            "legend": {"orient": "bottom", "titleLimit": 220, "labelLimit": 80}
        },
        "tooltip": [
            {"field": "state", "type": "nominal", "title": "State"},
            {"field": "shapeISO", "type": "nominal", "title": "State code"},
            {"field": "avg_rainfall_mm", "type": "quantitative", "title": "Average rainfall (mm)", "format": ".2f"},
            {"field": "avg_normal_rainfall_mm", "type": "quantitative", "title": "Normal rainfall (mm)", "format": ".2f"},
            {"field": "difference_from_normal", "type": "quantitative", "title": "Difference from normal", "format": ".2f"}
        ]
    },
    "config": {"view": {"stroke": None}}
})


# 6 WETTEST STATES MAP
save_json("bar_wettest_states.json", {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "title": {
        "text": "Most Humid State due to Rainfall in West Malaysia",
        "subtitle": [
            "These are the states with the most rainfall hence the most humid.",
            "This map focuses on West Malaysia because the map on the left shows it has",
            "higher average rainfall than East Malaysia."
        ],
        "font": "Georgia, Times New Roman, serif",
        "fontSize": 18,
        "color": "#1f5f99",
        "subtitleFont": "Arial, sans-serif",
        "subtitleFontSize": 12,
        "subtitleColor": "#222222",
        "anchor": "start"
    },
    "width": 300,
    "height": 360,
    "projection": {"type": "mercator"},
    "layer": [
        {
            "data": {
                "url": "data/malaysia_states_simple.geojson",
                "format": {
                    "type": "json",
                    "property": "features"
                }
            },
            "transform": [
                {
                    "filter": "indexof(['Sabah', 'Sarawak', 'Labuan'], datum.properties.name) < 0"
                }
            ],
            "mark": {
                "type": "geoshape",
                "fill": "#e6e6e6",
                "stroke": "white",
                "strokeWidth": 0.8
            },
            "encoding": {
                "tooltip": [
                    {"field": "properties.name", "type": "nominal", "title": "State"},
                    {"value": "No rainfall value in this dataset", "title": "Average rainfall"}
                ]
            }
        },
        {
            "data": {"url": "data/rainfall_state_summary_clean.csv"},
            "transform": [
                {
                    "lookup": "state",
                    "from": {
                        "data": {
                            "url": "data/malaysia_states_simple.geojson",
                            "format": {
                                "type": "json",
                                "property": "features"
                            }
                        },
                        "key": "properties.name"
                    },
                    "as": "geo"
                }
            ],
            "mark": {
                "type": "geoshape",
                "stroke": "white",
                "strokeWidth": 0.8
            },
            "encoding": {
                "shape": {
                    "field": "geo",
                    "type": "geojson"
                },
                "color": {
                    "field": "avg_rainfall_mm",
                    "type": "quantitative",
                    "title": "Average rainfall",
                    "scale": {"scheme": "viridis", "domainMin": 0},
                    "legend": {"orient": "bottom", "titleLimit": 220, "labelLimit": 80}
                },
                "tooltip": [
                    {"field": "state", "type": "nominal", "title": "State"},
                    {"field": "avg_rainfall_mm", "type": "quantitative", "title": "Average rainfall", "format": ".2f"}
                ]
            }
        }
    ],
    "config": {"view": {"stroke": None}}
})

save_json("precipitation_monthly.json", {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "title": {
        "text": "Monthly Precipitation",
        "subtitle": [
            "Monthly precipitation shows when rainfall is higher or lower across the year."
        ],
        "font": "Georgia, Times New Roman, serif",
        "fontSize": 18,
        "color": "#1f5f99",
        "subtitleFont": "Arial, sans-serif",
        "subtitleFontSize": 14,
        "subtitleColor": "#222222",
        "anchor": "start"
    },
    "width": 720,
    "height": 380,
    "data": {"url": "data/precipitation min ave max temp.csv"},
    "mark": {"type": "bar", "color": "#8ecae6", "tooltip": True},
    "encoding": {
        "x": {
            "field": "Category",
            "type": "ordinal",
            "title": "Month",
            "sort": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
            "axis": {"labelAngle": 0}
        },
        "y": {
            "field": "Precipitation (mm)",
            "type": "quantitative",
            "title": "Precipitation (mm)"
        },
        "tooltip": [
            {"field": "Category", "type": "ordinal", "title": "Month"},
            {"field": "Precipitation (mm)", "type": "quantitative", "format": ".2f"}
        ]
    },
    "config": {"view": {"stroke": None}}
})


save_json("rainfall_temperature_relationship.json", {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "title": {
        "text": "Relationship Between Rainfall and Temperature",
        "subtitle": [
            "Each point is a month: x = average temperature, y = precipitation, and color identifies the month.",
            "The downward trend suggests warmer months are generally drier, while the wettest months are slightly cooler."
        ],
        "font": "Georgia, Times New Roman, serif",
        "fontSize": 18,
        "color": "#1f5f99",
        "subtitleFont": "Arial, sans-serif",
        "subtitleFontSize": 12,
        "subtitleColor": "#222222",
        "anchor": "start"
    },
    "width": 820,
    "height": 420,
    "data": {"url": "data/precipitation min ave max temp.csv"},
    "layer": [
        {
            "transform": [
                {
                    "regression": "Precipitation (mm)",
                    "on": "Average Mean Surface Air Temperature (°C)"
                }
            ],
            "mark": {
                "type": "line",
                "color": "#1f5f99",
                "strokeWidth": 3,
                "strokeDash": [6, 4]
            },
            "encoding": {
                "x": {
                    "field": "Average Mean Surface Air Temperature (°C)",
                    "type": "quantitative",
                    "title": "Average temperature (°C)",
                    "axis": {"format": ".2~f"},
                    "scale": {"zero": False}
                },
                "y": {
                    "field": "Precipitation (mm)",
                    "type": "quantitative",
                    "title": "Precipitation (mm)"
                }
            }
        },
        {
            "mark": {
                "type": "circle",
                "size": 260,
                "opacity": 0.85,
                "stroke": "white",
                "strokeWidth": 1.2,
                "tooltip": True
            },
            "encoding": {
                "x": {
                    "field": "Average Mean Surface Air Temperature (°C)",
                    "type": "quantitative",
                    "title": "Average temperature (°C)",
                    "axis": {"format": ".2~f"},
                    "scale": {"zero": False}
                },
                "y": {
                    "field": "Precipitation (mm)",
                    "type": "quantitative",
                    "title": "Precipitation (mm)"
                },
                "color": {
                    "field": "Category",
                    "type": "ordinal",
                    "title": "Month",
                    "sort": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                    "scale": {
                        "domain": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                        "range": ["#0072B2", "#56B4E9", "#E69F00", "#CC79A7", "#6A3D9A", "#999999", "#332288", "#88CCEE", "#44AA99", "#AA4499", "#DDCC77", "#000000"]
                    },
                    "legend": {
                        "labelExpr": "datum.label == 'Jan' ? 'January' : datum.label == 'Feb' ? 'February' : datum.label == 'Mar' ? 'March' : datum.label == 'Apr' ? 'April' : datum.label == 'May' ? 'May' : datum.label == 'Jun' ? 'June' : datum.label == 'Jul' ? 'July' : datum.label == 'Aug' ? 'August' : datum.label == 'Sep' ? 'September' : datum.label == 'Oct' ? 'October' : datum.label == 'Nov' ? 'November' : 'December'"
                    }
                },
                "tooltip": [
                    {"field": "Category", "type": "ordinal", "title": "Month"},
                    {"field": "Precipitation (mm)", "type": "quantitative", "format": ".2f"},
                    {"field": "Average Mean Surface Air Temperature (°C)", "type": "quantitative", "title": "Average temperature (°C)", "format": ".2f"},
                    {"field": "Precipitation amount during wettest days (mm)", "type": "quantitative", "title": "Wettest-day rainfall", "format": ".2f"}
                ]
            }
        }
    ],
    "config": {"view": {"stroke": None}}
})

save_json("line_monthly_rainfall.json", {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "title": {
        "text": "Average Rainfall by Month",
        "subtitle": [
            "Malaysia receives rainfall throughout the year, but the intensity differs by month and by state.",
            "These charts show when rainfall increases and which states record higher average rainfall."
        ],
        "font": "Georgia, Times New Roman, serif",
        "fontSize": 18,
        "color": "#1f5f99",
        "subtitleFont": "Arial, sans-serif",
        "subtitleFontSize": 14,
        "subtitleColor": "#222222",
        "anchor": "start"
    },
    "width": 820,
    "height": 380,
    "data": {"url": "data/monthly_rainfall.csv"},
    "mark": {"type": "line", "point": True, "tooltip": True},
    "encoding": {
        "x": {
            "field": "month",
            "type": "quantitative",
            "title": "Month",
            "scale": {"domain": [1, 12]},
            "axis": {
                "values": list(range(1, 13)),
                "labelAngle": 0,
                "tickMinStep": 1,
                "labelExpr": "datum.value == 1 ? 'January' : datum.value == 2 ? 'February' : datum.value == 3 ? 'March' : datum.value == 4 ? 'April' : datum.value == 5 ? 'May' : datum.value == 6 ? 'June' : datum.value == 7 ? 'July' : datum.value == 8 ? 'August' : datum.value == 9 ? 'September' : datum.value == 10 ? 'October' : datum.value == 11 ? 'November' : 'December'"
            }
        },
        "y": {
            "field": "avg_rainfall_mm",
            "type": "quantitative",
            "title": "Average rainfall"
        },
        "tooltip": [
            {"field": "month", "type": "quantitative", "format": "d"},
            {"field": "avg_rainfall_mm", "type": "quantitative", "format": ".2f"}
        ]
    },
    "config": {"view": {"stroke": None}}
})


# 10 HEATMAP
save_json("heatmap_state_month.json", {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "title": {
        "text": "Rainfall Heatmap by State and Month in West Malaysia",
        "subtitle": "Select a month to compare average rainfall across West Malaysian states.",
        "font": "Georgia, Times New Roman, serif",
        "fontSize": 18,
        "color": "#1f5f99",
        "subtitleFont": "Arial, sans-serif",
        "subtitleFontSize": 12,
        "subtitleColor": "#222222",
        "anchor": "start"
    },
    "width": 820,
    "height": 520,
    "params": [
        {
            "name": "SelectedMonth",
            "value": 1,
            "bind": {
                "input": "select",
                "name": "Select month: ",
                "options": list(range(1, 13)),
                "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            }
        }
    ],
    "data": {"url": "data/state_monthly_rainfall_clean.csv"},
    "transform": [
        {"filter": "datum.month == SelectedMonth"},
        {
            "lookup": "state",
            "from": {
                "data": {
                    "url": "data/malaysia_states_simple.geojson",
                    "format": {"type": "json", "property": "features"}
                },
                "key": "properties.name"
            },
            "as": "geo"
        }
    ],
    "projection": {"type": "mercator"},
    "mark": {
        "type": "geoshape",
        "stroke": "white",
        "strokeWidth": 0.8,
        "tooltip": True
    },
    "encoding": {
        "shape": {"field": "geo", "type": "geojson"},
        "color": {
            "field": "avg_rainfall_mm",
            "type": "quantitative",
            "title": "Average rainfall",
            "scale": {"scheme": "plasma", "domainMin": 0}
        },
        "tooltip": [
            {"field": "state", "type": "nominal", "title": "State"},
            {"field": "month_name", "type": "ordinal", "title": "Month"},
            {"field": "avg_rainfall_mm", "type": "quantitative", "title": "Average rainfall", "format": ".2f"}
        ]
    },
    "config": {"view": {"stroke": None}}
})


save_json("rainfall_seasonality_scatter.json", {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "title": {
        "text": "Rainfall Seasonality by State in West Malaysia",
        "subtitle": [
            "Rainfall does not arrive in the same rhythm across West Malaysia.",
            "Darker states have rain concentrated into fewer wet months, while lighter states receive it more evenly through the year.",
            "Hover over a state to compare its wettest month, driest month, and main wet period."
        ],
        "font": "Georgia, Times New Roman, serif",
        "fontSize": 18,
        "color": "#1f5f99",
        "subtitleFont": "Arial, sans-serif",
        "subtitleFontSize": 12,
        "subtitleColor": "#222222",
        "anchor": "start"
    },
    "width": 820,
    "height": 520,
    "projection": {"type": "mercator"},
    "data": {"url": "data/rainfall_seasonality_by_state.csv"},
    "transform": [
        {
            "lookup": "state",
            "from": {
                "data": {
                    "url": "data/malaysia_states_simple.geojson",
                    "format": {"type": "json", "property": "features"}
                },
                "key": "properties.name"
            },
            "as": "geo"
        }
    ],
    "mark": {
        "type": "geoshape",
        "stroke": "white",
        "strokeWidth": 0.8,
        "tooltip": True
    },
    "encoding": {
        "shape": {"field": "geo", "type": "geojson"},
        "color": {
            "field": "seasonality_index",
            "type": "quantitative",
            "title": "Seasonality index",
            "scale": {
                "scheme": "plasma",
                "domain": [0, 0.8]
            }
        },
        "tooltip": [
            {"field": "state", "type": "nominal", "title": "State"},
            {"field": "seasonality_index", "type": "quantitative", "title": "Seasonality index", "format": ".3f"},
            {"field": "wettest_month", "type": "nominal", "title": "Wettest month"},
            {"field": "wettest_month_rainfall", "type": "quantitative", "title": "Wettest month rainfall", "format": ".2f"},
            {"field": "driest_month", "type": "nominal", "title": "Driest month"},
            {"field": "driest_month_rainfall", "type": "quantitative", "title": "Driest month rainfall", "format": ".2f"},
            {"field": "peak_to_dry_ratio", "type": "quantitative", "title": "Wettest / driest month", "format": ".2f"},
            {"field": "avg_monthly_rainfall", "type": "quantitative", "title": "Average monthly rainfall", "format": ".2f"},
            {"field": "wettest_period", "type": "nominal", "title": "Wettest period"}
        ]
    },
    "config": {"view": {"stroke": None}}
})

save_json("rainfall_state_radar.json", {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "title": {
        "text": "Radar Profile of Most Seasonal Rainfall States",
        "subtitle": [
            "Each line compares a highly seasonal rainfall state across four normalised rainfall profile metrics.",
            "Wider shapes indicate stronger monthly rainfall totals, sharper wet-season peaks, or higher wet/dry contrast."
        ],
        "font": "Georgia, Times New Roman, serif",
        "fontSize": 18,
        "color": "#1f5f99",
        "subtitleFont": "Arial, sans-serif",
        "subtitleFontSize": 12,
        "subtitleColor": "#222222",
        "anchor": "start"
    },
    "width": 720,
    "height": 560,
    "layer": [
        {
            "data": {"url": "data/rainfall_state_radar_axes.csv"},
            "mark": {"type": "rule", "stroke": "#c9d4df", "strokeWidth": 1},
            "encoding": {
                "x": {"datum": 0, "type": "quantitative"},
                "y": {"datum": 0, "type": "quantitative"},
                "x2": {"field": "x"},
                "y2": {"field": "y"}
            }
        },
        {
            "data": {"url": "data/rainfall_state_radar_axes.csv"},
            "mark": {
                "type": "text",
                "fontSize": 11,
                "fontWeight": "bold",
                "color": "#222222"
            },
            "encoding": {
                "x": {"field": "x", "type": "quantitative"},
                "y": {"field": "y", "type": "quantitative"},
                "text": {"field": "metric"},
                "tooltip": [{"field": "metric", "type": "nominal"}]
            }
        },
        {
            "data": {"url": "data/rainfall_state_radar.csv"},
            "mark": {
                "type": "line",
                "point": True,
                "strokeWidth": 2,
                "opacity": 0.78,
                "tooltip": True
            },
            "encoding": {
                "x": {"field": "x", "type": "quantitative", "axis": None, "scale": {"domain": [-1.18, 1.18]}},
                "y": {"field": "y", "type": "quantitative", "axis": None, "scale": {"domain": [-1.18, 1.18]}},
                "detail": {"field": "state"},
                "order": {"field": "point_order", "type": "quantitative"},
                "color": {
                    "field": "state",
                    "type": "nominal",
                    "title": "State",
                    "scale": {"scheme": "tableau10"}
                },
                "tooltip": [
                    {"field": "state", "type": "nominal", "title": "State"},
                    {"field": "metric", "type": "nominal", "title": "Metric"},
                    {"field": "raw_value", "type": "quantitative", "title": "Original value", "format": ".2f"},
                    {"field": "normalised_value", "type": "quantitative", "title": "Normalised score", "format": ".2f"}
                ]
            }
        }
    ],
    "config": {"view": {"stroke": None}}
})


# 11 DISASTER TYPE PIE CHART
DISASTER_TYPE_DOMAIN = ["Flood", "Storm", "Epidemic", "Drought", "Wildfire", "Earthquake"]
DISASTER_TYPE_RANGE = ["#0072B2", "#56B4E9", "#E69F00", "#6A3D9A", "#D55E00", "#999999"]
NO_MASS_MOVEMENT_FILTER = "indexof(lower(datum.disaster_type), 'mass movement') < 0"

save_json("bar_disaster_types.json", {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "title": {
        "text": "Natural Disaster Types Recorded in Malaysia",
        "subtitle": "Floods dominate the disaster record.",
        "font": "Georgia, Times New Roman, serif",
        "fontSize": 18,
        "color": "#1f5f99",
        "subtitleFont": "Arial, sans-serif",
        "subtitleFontSize": 12,
        "subtitleColor": "#222222",
        "anchor": "start"
    },
    "width": 620,
    "height": 360,
    "data": {"url": "data/disaster_type_summary.csv"},
    "transform": [
        {"filter": NO_MASS_MOVEMENT_FILTER}
    ],
    "mark": {
        "type": "arc",
        "innerRadius": 45,
        "outerRadius": 145,
        "tooltip": True
    },
    "encoding": {
        "theta": {
            "field": "count",
            "type": "quantitative",
            "title": "Count"
        },
        "color": {
            "field": "disaster_type",
            "type": "nominal",
            "title": "Disaster type",
            "legend": {"orient": "right"},
            "scale": {
                "domain": DISASTER_TYPE_DOMAIN,
                "range": DISASTER_TYPE_RANGE
            }
        },
        "tooltip": [
            {"field": "disaster_type", "type": "nominal"},
            {"field": "count", "type": "quantitative"}
        ]
    },
    "config": {"view": {"stroke": None}}
})

save_json("pareto_disaster_types.json", {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "title": {
        "text": "Natural Disaster Types",
        "subtitle": [
            "Bars show the number of recorded disasters; the black line shows the cumulative percentage as each type is added.",
            "Floods alone make up most records, and floods plus epidemics already account for over 80% of the disaster total."
        ],
        "font": "Georgia, Times New Roman, serif",
        "fontSize": 18,
        "color": "#1f5f99",
        "subtitleFont": "Arial, sans-serif",
        "subtitleFontSize": 12,
        "subtitleColor": "#222222",
        "anchor": "start"
    },
    "width": 820,
    "height": 420,
    "data": {"url": "data/disaster_type_pareto.csv"},
    "resolve": {"scale": {"y": "independent"}},
    "layer": [
        {
            "mark": {"type": "bar", "tooltip": True, "opacity": 0.86},
            "encoding": {
                "x": {
                    "field": "disaster_type",
                    "type": "nominal",
                    "title": "Disaster type",
                    "sort": "-y",
                    "axis": {"labelAngle": -25, "labelLimit": 120}
                },
                "y": {
                    "field": "count",
                    "type": "quantitative",
                    "title": "Recorded disasters"
                },
                "color": {
                    "field": "disaster_type",
                    "type": "nominal",
                    "legend": None,
                    "scale": {
                        "domain": DISASTER_TYPE_DOMAIN,
                        "range": DISASTER_TYPE_RANGE
                    }
                },
                "tooltip": [
                    {"field": "disaster_type", "type": "nominal", "title": "Disaster type"},
                    {"field": "count", "type": "quantitative", "title": "Count", "format": ".0f"},
                    {"field": "cumulative_pct", "type": "quantitative", "title": "Cumulative share (%)", "format": ".2f"}
                ]
            }
        },
        {
            "mark": {
                "type": "line",
                "color": "#111111",
                "strokeWidth": 3,
                "point": {"filled": True, "size": 70},
                "tooltip": True
            },
            "encoding": {
                "x": {
                    "field": "disaster_type",
                    "type": "nominal",
                    "sort": "-y"
                },
                "y": {
                    "field": "cumulative_pct",
                    "type": "quantitative",
                    "title": "Cumulative share (%)",
                    "scale": {"domain": [0, 100]},
                    "axis": {"orient": "right"}
                },
                "tooltip": [
                    {"field": "disaster_type", "type": "nominal", "title": "Disaster type"},
                    {"field": "cumulative_pct", "type": "quantitative", "title": "Cumulative share (%)", "format": ".2f"}
                ]
            }
        },
        {
            "mark": {
                "type": "rule",
                "color": "#777777",
                "strokeDash": [5, 4],
                "opacity": 0.65
            },
            "encoding": {
                "y": {"datum": 80, "type": "quantitative"}
            }
        }
    ],
    "config": {"view": {"stroke": None}}
})

save_json("disaster_timeline_heatmap.json", {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "title": {
        "text": "Disaster Timeline by Type in Malaysia",
        "font": "Georgia, Times New Roman, serif",
        "fontSize": 18,
        "color": "#1f5f99",
        "subtitleFont": "Arial, sans-serif",
        "subtitleFontSize": 12,
        "subtitleColor": "#222222",
        "anchor": "start"
    },
    "width": 820,
    "height": 360,
    "data": {"url": "data/disaster_year_type_long.csv"},
    "transform": [
        {"filter": f"datum.count > 0 && toNumber(datum.year) >= 2004 && {NO_MASS_MOVEMENT_FILTER}"}
    ],
    "mark": {
        "type": "circle",
        "opacity": 0.85,
        "stroke": "white",
        "strokeWidth": 1,
        "tooltip": True
    },
    "encoding": {
        "x": {
            "field": "year",
            "type": "ordinal",
            "title": "Year",
            "axis": {"labelAngle": -45, "labelOverlap": True, "labelFontSize": 10}
        },
        "y": {
            "field": "disaster_type",
            "type": "nominal",
            "title": "Disaster type",
            "sort": DISASTER_TYPE_DOMAIN,
            "axis": {"labelLimit": 170}
        },
        "size": {
            "field": "count",
            "type": "quantitative",
            "title": "Count",
            "scale": {"range": [35, 650]},
            "legend": None
        },
        "color": {
            "field": "disaster_type",
            "type": "nominal",
            "title": "Disaster type",
            "legend": None,
            "scale": {
                "domain": DISASTER_TYPE_DOMAIN,
                "range": DISASTER_TYPE_RANGE
            }
        },
        "tooltip": [
            {"field": "year", "type": "ordinal", "title": "Year"},
            {"field": "disaster_type", "type": "nominal", "title": "Disaster type"},
            {"field": "count", "type": "quantitative", "title": "Count"}
        ]
    },
    "config": {"view": {"stroke": None}}
})

save_json("map_flood_rate_state.json", {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "title": {
        "text": "Proportional Symbol Map of State Flood Occurrence",
        "subtitle": [
            "State outlines provide geographic context, while circle size shows the share of district-year records marked as flood events.",
            "This changes the flood-risk view from a filled-area map into a symbol map."
        ],
        "font": "Georgia, Times New Roman, serif",
        "fontSize": 18,
        "color": "#1f5f99",
        "subtitleFont": "Arial, sans-serif",
        "subtitleFontSize": 12,
        "subtitleColor": "#222222",
        "anchor": "start"
    },
    "width": 820,
    "height": 430,
    "projection": {"type": "mercator"},
    "layer": [
        {
            "data": {
                "url": "data/malaysia_states_simple.geojson",
                "format": {"type": "json", "property": "features"}
            },
            "mark": {
                "type": "geoshape",
                "fill": "#eaf0f4",
                "stroke": "white",
                "strokeWidth": 0.8
            }
        },
        {
            "data": {"url": "data/malaysia_flood_state_symbol_map.csv"},
            "mark": {
                "type": "circle",
                "stroke": "#123b5d",
                "strokeWidth": 1,
                "opacity": 0.82,
                "tooltip": True
            },
            "encoding": {
                "longitude": {"field": "longitude", "type": "quantitative"},
                "latitude": {"field": "latitude", "type": "quantitative"},
                "size": {
                    "field": "flood_rate_pct",
                    "type": "quantitative",
                    "title": "Flood occurrence (%)",
                    "scale": {"domainMin": 0, "range": [180, 2800]},
                    "legend": {"orient": "right", "titleLimit": 180}
                },
                "color": {
                    "field": "flood_rate_pct",
                    "type": "quantitative",
                    "title": "Flood occurrence (%)",
                    "scale": {"scheme": "cividis", "domainMin": 0},
                    "legend": {"orient": "right", "titleLimit": 180}
                },
                "tooltip": [
                    {"field": "state_name", "type": "nominal", "title": "State"},
                    {"field": "flood_rate_pct", "type": "quantitative", "title": "Flood occurrence (%)", "format": ".2f"},
                    {"field": "flood_records", "type": "quantitative", "title": "Flood records"},
                    {"field": "district_year_records", "type": "quantitative", "title": "District-year records"},
                    {"field": "avg_annual_rainfall_mm", "type": "quantitative", "title": "Average annual rainfall (mm)", "format": ".2f"}
                ]
            }
        }
    ],
    "config": {"view": {"stroke": None}}
})

save_json("map_city_flood_days_symbols.json", {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "title": {
        "text": "City Flood Days on State Flood-Risk Background",
        "subtitle": [
            "This map brings the state-level flood background together with the cities measured in the daily flood dataset.",
            "Larger circles mark cities with more flood days, while the shaded states show where flood records are more common."
        ],
        "font": "Georgia, Times New Roman, serif",
        "fontSize": 18,
        "color": "#1f5f99",
        "subtitleFont": "Arial, sans-serif",
        "subtitleFontSize": 12,
        "subtitleColor": "#222222",
        "anchor": "start"
    },
    "width": 820,
    "height": 430,
    "projection": {"type": "mercator"},
    "layer": [
        {
            "data": {
                "url": "data/malaysia_states_simple.geojson",
                "format": {"type": "json", "property": "features"}
            },
            "mark": {
                "type": "geoshape",
                "fill": "#edf2f4",
                "stroke": "#ffffff",
                "strokeWidth": 0.8
            }
        },
        {
            "data": {"url": "data/malaysia_flood_state_summary.csv"},
            "transform": [
                {
                    "lookup": "state_name",
                    "from": {
                        "data": {
                            "url": "data/malaysia_states_simple.geojson",
                            "format": {"type": "json", "property": "features"}
                        },
                        "key": "properties.name"
                    },
                    "as": "geo"
                }
            ],
            "mark": {
                "type": "geoshape",
                "stroke": "white",
                "strokeWidth": 0.8,
                "opacity": 0.55,
                "tooltip": True
            },
            "encoding": {
                "shape": {"field": "geo", "type": "geojson"},
                "color": {
                    "field": "flood_rate_pct",
                    "type": "quantitative",
                    "title": "State flood occurrence (%)",
                    "scale": {"scheme": "cividis", "domainMin": 0},
                    "legend": {"orient": "right", "titleLimit": 220}
                },
                "tooltip": [
                    {"field": "state_name", "type": "nominal", "title": "State"},
                    {"field": "flood_rate_pct", "type": "quantitative", "title": "State flood occurrence (%)", "format": ".2f"},
                    {"field": "flood_records", "type": "quantitative", "title": "Flood records"},
                    {"field": "district_year_records", "type": "quantitative", "title": "District-year records"}
                ]
            }
        },
        {
            "data": {"url": "data/malaysia_city_flood_summary.csv"},
            "transform": [
                {
                    "calculate": "toNumber(datum.longitude)",
                    "as": "display_longitude"
                },
                {
                    "calculate": "toNumber(datum.latitude)",
                    "as": "display_latitude"
                }
            ],
            "mark": {
                "type": "circle",
                "stroke": "#111111",
                "strokeWidth": 1.1,
                "opacity": 0.95,
                "tooltip": True
            },
            "encoding": {
                "longitude": {"field": "display_longitude", "type": "quantitative"},
                "latitude": {"field": "display_latitude", "type": "quantitative"},
                "size": {
                    "field": "flood_days",
                    "type": "quantitative",
                    "title": "City flood days",
                    "scale": {"range": [180, 3600]},
                    "legend": {"orient": "right", "titleLimit": 180}
                },
                "color": {
                    "field": "city",
                    "type": "nominal",
                    "title": "Measured city",
                    "scale": {
                        "domain": ["Johor Bahru", "Kota Bharu", "Kota Kinabalu", "Kuala Lumpur", "Kuantan", "Kuching", "Melaka", "Shah Alam"],
                        "range": ["#D55E00", "#0072B2", "#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#000000", "#F0E442"]
                    },
                    "legend": {"orient": "right", "titleLimit": 180, "labelLimit": 180}
                },
                "tooltip": [
                    {"field": "city", "type": "nominal", "title": "City"},
                    {"field": "state_name", "type": "nominal", "title": "State"},
                    {"field": "flood_days", "type": "quantitative", "title": "Flood days"},
                    {"field": "flash_flood_days", "type": "quantitative", "title": "Flash flood days"},
                    {"field": "flash_flood_share_pct", "type": "quantitative", "title": "Flash flood share (%)", "format": ".2f"},
                    {"field": "avg_rainfall_7day_mm", "type": "quantitative", "title": "Average 7-day rainfall (mm)", "format": ".2f"},
                    {"field": "avg_humidity_pct", "type": "quantitative", "title": "Average humidity (%)", "format": ".2f"}
                ]
            }
        },
        {
            "data": {"url": "data/malaysia_city_flood_summary.csv"},
            "transform": [
                {
                    "calculate": "toNumber(datum.longitude)",
                    "as": "display_longitude"
                },
                {
                    "calculate": "toNumber(datum.latitude)",
                    "as": "display_latitude"
                }
            ],
            "mark": {
                "type": "text",
                "font": "Arial",
                "fontSize": 11,
                "fontWeight": "bold",
                "dx": 8,
                "dy": -8,
                "color": "#222222"
            },
            "encoding": {
                "longitude": {"field": "display_longitude", "type": "quantitative"},
                "latitude": {"field": "display_latitude", "type": "quantitative"},
                "text": {"field": "city", "type": "nominal"}
            }
        }
    ],
    "resolve": {"scale": {"color": "independent"}},
    "config": {"view": {"stroke": None}}
})

save_json("heatmap_city_month_flood_rate.json", {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "title": {
        "text": "Monthly Flood Pattern by City",
        "subtitle": [
            "This heatmap shows when each city records more flood days in the new city-day dataset.",
            "Darker cells mean a higher percentage of days in that month were marked as flood days."
        ],
        "font": "Georgia, Times New Roman, serif",
        "fontSize": 18,
        "color": "#1f5f99",
        "subtitleFont": "Arial, sans-serif",
        "subtitleFontSize": 12,
        "subtitleColor": "#222222",
        "anchor": "start"
    },
    "width": 820,
    "height": 300,
    "data": {"url": "data/malaysia_city_month_flood_summary.csv"},
    "mark": {"type": "rect", "tooltip": True},
    "encoding": {
        "x": {
            "field": "month_name",
            "type": "ordinal",
            "title": "Month",
            "sort": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
            "axis": {"labelAngle": 0}
        },
        "y": {
            "field": "city",
            "type": "nominal",
            "title": "City"
        },
        "color": {
            "field": "flood_rate_pct",
            "type": "quantitative",
            "title": "Flood days (%)",
            "scale": {"scheme": "viridis"}
        },
        "tooltip": [
            {"field": "city", "type": "nominal", "title": "City"},
            {"field": "month_name", "type": "ordinal", "title": "Month"},
            {"field": "flood_rate_pct", "type": "quantitative", "title": "Flood days (%)", "format": ".2f"},
            {"field": "flood_days", "type": "quantitative", "title": "Flood days"},
            {"field": "avg_rainfall_7day_mm", "type": "quantitative", "title": "Average 7-day rainfall (mm)", "format": ".2f"},
            {"field": "avg_humidity_pct", "type": "quantitative", "title": "Average humidity (%)", "format": ".2f"}
        ]
    },
    "config": {"view": {"stroke": None}}
})

save_json("flood_rainfall_relationship.json", {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "title": {
        "text": "Rainfall Anomaly and Flood Disasters Over Time",
        "subtitle": [
            "From 2013 to 2023, blue bars show flood disasters and the orange line shows rainfall anomaly from normal.",
            "Flood counts peak in 2021, while 2022 has the highest above-normal rainfall, showing rainfall is one part of flood risk."
        ],
        "font": "Georgia, Times New Roman, serif",
        "fontSize": 18,
        "color": "#1f5f99",
        "subtitleFont": "Arial, sans-serif",
        "subtitleFontSize": 12,
        "subtitleColor": "#222222",
        "anchor": "start"
    },
    "width": 820,
    "height": 420,
    "data": {"url": "data/flood_rainfall_yearly_relationship.csv"},
    "transform": [
        {"filter": "toNumber(datum.year) > 2011"}
    ],
    "resolve": {"scale": {"y": "independent"}},
    "layer": [
        {
            "mark": {
                "type": "bar",
                "color": "#0072B2",
                "opacity": 0.82,
                "tooltip": True
            },
            "encoding": {
                "x": {
                    "field": "year",
                    "type": "ordinal",
                    "title": "Year",
                    "axis": {"labelAngle": 0, "labelOverlap": True}
                },
                "y": {
                    "field": "flood_count",
                    "type": "quantitative",
                    "title": "Flood disasters"
                },
                "tooltip": [
                    {"field": "year", "type": "ordinal", "title": "Year"},
                    {"field": "flood_count", "type": "quantitative", "title": "Flood disasters"}
                ]
            }
        },
        {
            "mark": {
                "type": "line",
                "color": "#E69F00",
                "strokeWidth": 3,
                "point": {"filled": True, "size": 55},
                "tooltip": True
            },
            "encoding": {
                "x": {
                    "field": "year",
                    "type": "ordinal",
                    "title": "Year",
                    "axis": {"labelAngle": 0, "labelOverlap": True}
                },
                "y": {
                    "field": "rainfall_anomaly_pct",
                    "type": "quantitative",
                    "title": "Rainfall anomaly from normal (%)"
                },
                "tooltip": [
                    {"field": "year", "type": "ordinal", "title": "Year"},
                    {"field": "rainfall_anomaly_pct", "type": "quantitative", "title": "Rainfall anomaly (%)", "format": ".2f"},
                    {"field": "rainfall_ratio", "type": "quantitative", "title": "Actual / normal rainfall", "format": ".2f"}
                ]
            }
        }
    ],
    "config": {"view": {"stroke": None}}
})


# 12 FLOOD LINE CHART
save_json("line_floods_over_time.json", {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "title": {
        "text": "Flood Disasters Over Time",
        "subtitle": "From 2013 to 2023, flood records rise after 2018 and peak in 2021 before easing in 2022 and 2023.",
        "font": "Georgia, Times New Roman, serif",
        "fontSize": 18,
        "color": "#1f5f99",
        "subtitleFont": "Arial, sans-serif",
        "subtitleFontSize": 12,
        "subtitleColor": "#222222",
        "anchor": "start"
    },
    "width": 820,
    "height": 360,
    "data": {"url": "data/flood_yearly.csv"},
    "transform": [
        {"filter": "toNumber(datum.year) > 2011"}
    ],
    "mark": {"type": "line", "point": True, "tooltip": True, "color": "#0072B2"},
    "encoding": {
        "x": {
            "field": "year",
            "type": "ordinal",
            "title": "Year",
            "axis": {"labelAngle": 0}
        },
        "y": {
            "field": "flood_count",
            "type": "quantitative",
            "title": "Flood count"
        },
        "tooltip": [
            {"field": "year", "type": "ordinal"},
            {"field": "flood_count", "type": "quantitative"}
        ]
    },
    "config": {"view": {"stroke": None}}
})


# =========================
# CREATE INDEX.HTML
# =========================

html = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Rainfall Patterns and Natural Disasters in Each State in Malaysia</title>

  <script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>

  <style>
    body {
      font-family: Arial, sans-serif;
      background:
        linear-gradient(180deg, #edf4f8 0, #f6f8fb 260px, #eef3f7 100%);
      margin: 0;
      color: #222;
      scroll-behavior: smooth;
    }

    .page {
      box-sizing: border-box;
      width: min(1150px, calc(100vw - 296px));
      margin-left: calc(240px + (100vw - 240px - min(1150px, calc(100vw - 296px))) / 2);
      margin-right: auto;
      padding: 42px 28px;
    }

    .intro-panel {
      position: relative;
      overflow: hidden;
      background:
        linear-gradient(90deg, rgba(31,95,153,0.10), rgba(68,170,153,0.10), rgba(230,159,0,0.10)),
        #ffffff;
      border: 1px solid rgba(31,95,153,0.14);
      border-radius: 18px;
      padding: 28px 30px;
      margin-bottom: 32px;
      box-shadow: 0 8px 26px rgba(24, 49, 83, 0.08);
    }

    .intro-panel > :not(.malaysia-flag) {
      position: relative;
      z-index: 1;
    }

    .meta-line {
      font-family: "Trebuchet MS", Arial, sans-serif;
      font-size: 18px;
      color: #6a3d9a;
      margin: 4px 0 18px;
      letter-spacing: 0;
    }

    .malaysia-flag {
      position: absolute;
      top: 0;
      right: 0;
      z-index: 0;
      width: min(480px, 62%);
      height: 230px;
      margin: 0;
      overflow: hidden;
      pointer-events: none;
      opacity: 0.72;
      background:
        radial-gradient(ellipse at 100% 0%, rgba(48,79,138,0.76) 0 28%, transparent 29%),
        linear-gradient(125deg, rgba(255,255,255,0.10), rgba(255,255,255,0) 45%),
        repeating-linear-gradient(
          168deg,
          rgba(199,91,91,0.64) 0,
          rgba(199,91,91,0.64) 10px,
          rgba(248,245,236,0.74) 10px,
          rgba(248,245,236,0.74) 20px
        );
      mask-image:
        linear-gradient(225deg, #000 0 54%, transparent 84%),
        radial-gradient(ellipse at 100% 0%, #000 0 42%, transparent 72%);
      mask-composite: intersect;
    }

    .malaysia-flag::before {
      content: "";
      position: absolute;
      inset: 0;
      background:
        linear-gradient(120deg, rgba(255,255,255,0.18) 0 18%, transparent 18% 36%, rgba(0,0,0,0.05) 36% 54%, transparent 54% 72%, rgba(255,255,255,0.16) 72% 90%, transparent 90%);
      mix-blend-mode: soft-light;
    }

    .flag-canton {
      position: absolute;
      right: 0;
      top: 0;
      width: 45%;
      height: 48%;
      background: rgba(48,79,138,0.76);
    }

    .flag-moon {
      position: absolute;
      right: 82px;
      top: 32px;
      width: 42px;
      height: 42px;
      border-radius: 50%;
      background: rgba(236,211,108,0.86);
    }

    .flag-moon::after {
      content: "";
      position: absolute;
      left: 12px;
      top: 0;
      width: 42px;
      height: 42px;
      border-radius: 50%;
      background: rgba(48,79,138,0.86);
    }

    .flag-star {
      position: absolute;
      right: 36px;
      top: 38px;
      width: 30px;
      height: 30px;
      background: rgba(236,211,108,0.86);
      clip-path: polygon(50% 0%, 61% 34%, 98% 35%, 68% 56%, 79% 91%, 50% 70%, 21% 91%, 32% 56%, 2% 35%, 39% 34%);
    }

    .side-nav {
      position: fixed;
      left: 0;
      top: 0;
      bottom: 0;
      width: 220px;
      z-index: 20;
      display: flex;
      flex-direction: column;
      gap: 12px;
      background: linear-gradient(180deg, #123b5d 0%, #1f5f99 58%, #44aa99 100%);
      padding: 34px 16px;
      box-shadow: 8px 0 24px rgba(24, 49, 83, 0.18);
      overflow: hidden;
    }

    .side-nav-title {
      position: relative;
      z-index: 1;
      font-family: "Trebuchet MS", Arial, sans-serif;
      font-size: 15px;
      line-height: 1.3;
      font-weight: 800;
      color: #fff4cf;
      margin: 0 4px 8px;
      letter-spacing: 0;
    }

    .side-nav a {
      position: relative;
      z-index: 1;
      min-height: 44px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 12px;
      text-decoration: none;
      font-family: "Trebuchet MS", Arial, sans-serif;
      font-size: 14px;
      line-height: 1.2;
      font-weight: 700;
      color: #f8fbff;
      background: rgba(255,255,255,0.10);
      border: 1px solid rgba(255,255,255,0.18);
      letter-spacing: 0;
    }

    .side-nav a:hover {
      color: #123b5d;
      background: #fff4cf;
      border-color: rgba(255,255,255,0.70);
    }

    .nav-number {
      flex: 0 0 26px;
      width: 26px;
      height: 26px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      font-family: Georgia, "Times New Roman", serif;
      font-weight: bold;
      color: #123b5d;
      background: #ffffff;
    }

    .nav-label {
      overflow-wrap: anywhere;
    }

    .sidebar-flood {
      position: absolute;
      left: -18px;
      right: -18px;
      bottom: -8px;
      height: 116px;
      z-index: 0;
      pointer-events: none;
      background:
        linear-gradient(180deg, rgba(136, 204, 238, 0.12) 0%, rgba(86, 180, 233, 0.42) 38%, rgba(0, 114, 178, 0.72) 100%);
    }

    .sidebar-flood::before,
    .sidebar-flood::after {
      content: "";
      position: absolute;
      left: -12%;
      width: 124%;
      height: 54px;
      border-radius: 50%;
      background: rgba(237, 244, 248, 0.34);
    }

    .sidebar-flood::before {
      top: -19px;
      transform: rotate(-3deg);
    }

    .sidebar-flood::after {
      top: 9px;
      background: rgba(255, 255, 255, 0.18);
      transform: rotate(4deg);
    }

    .flood-wave {
      position: absolute;
      left: 18px;
      right: 18px;
      height: 18px;
      border-radius: 999px;
      background:
        radial-gradient(circle at 12px 9px, rgba(255,255,255,0.44) 0 7px, transparent 8px) 0 0 / 36px 18px repeat-x;
    }

    .flood-wave.wave-1 {
      top: 31px;
      opacity: 0.55;
    }

    .flood-wave.wave-2 {
      top: 62px;
      opacity: 0.32;
      transform: translateX(14px);
    }

    h1 {
      font-family: Georgia, "Times New Roman", serif;
      font-size: 46px;
      color: #1f5f99;
      margin-bottom: 8px;
      letter-spacing: -1px;
    }

    h2 {
      font-size: 26px;
      margin-top: 44px;
      margin-bottom: 12px;
      padding-left: 14px;
      border-left: 6px solid #44aa99;
    }

    .chapter-title {
      font-family: Georgia, "Times New Roman", serif;
      font-size: 34px;
      color: #8a4b08;
      margin: 28px 0 18px;
      letter-spacing: 0;
      scroll-margin-top: 28px;
    }

    .subtitle {
      font-size: 18px;
      color: #555;
      max-width: 900px;
      line-height: 1.6;
      margin-bottom: 30px;
    }

    .section-text {
      font-size: 16px;
      color: #555;
      max-width: 900px;
      line-height: 1.6;
      margin-bottom: 20px;
    }

    .chart-card {
      background: white;
      border-radius: 18px;
      padding: 26px;
      margin-bottom: 30px;
      box-shadow: 0 8px 28px rgba(24, 49, 83, 0.08);
      border: 1px solid rgba(31,95,153,0.10);
      border-top: 6px solid #1f5f99;
      overflow-x: hidden;
    }

    .chart-card:nth-of-type(3n + 1) {
      border-top-color: #44aa99;
    }

    .chart-card:nth-of-type(3n + 2) {
      border-top-color: #e69f00;
    }

    .vega-embed {
      max-width: 100%;
    }

    .grid-two {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
    }

    footer {
      border-top: 1px solid #ddd;
      margin-top: 52px;
      padding-top: 18px;
      color: #666;
      font-size: 13px;
      line-height: 1.6;
    }

    .references {
      margin-top: 12px;
    }

    .references strong,
    .references a {
      display: block;
    }

    .references a {
      color: #1f5f99;
      overflow-wrap: anywhere;
    }

    @media (max-width: 900px) {
      .page {
        width: auto;
        margin: auto;
      }

      .side-nav {
        position: static;
        top: 0;
        bottom: auto;
        width: auto;
        flex-direction: column;
        margin: 0;
        padding: 14px;
        box-shadow: 0 8px 22px rgba(24, 49, 83, 0.12);
      }

      .sidebar-flood {
        display: none;
      }

      .side-nav a {
        min-height: 36px;
      }

      .grid-two {
        grid-template-columns: 1fr;
      }

      h1 {
        font-size: 36px;
      }

      .intro-panel {
        padding: 22px;
      }
    }
  </style>
</head>

<body>
  <nav class="side-nav" aria-label="Section navigation">
    <p class="side-nav-title">Click to access directly</p>
    <a href="#section-1"><span class="nav-number">1</span><span class="nav-label">Temperature in Malaysia</span></a>
    <a href="#section-2"><span class="nav-number">2</span><span class="nav-label">Rainfall in Malaysia</span></a>
    <a href="#section-3"><span class="nav-number">3</span><span class="nav-label">Rainfall Data Breakdown</span></a>
    <a href="#section-4"><span class="nav-number">4</span><span class="nav-label">Normal Rainfall Condition</span></a>
    <a href="#section-5"><span class="nav-number">5</span><span class="nav-label">Natural Disaster Risks</span></a>
    <div class="sidebar-flood" aria-hidden="true">
      <span class="flood-wave wave-1"></span>
      <span class="flood-wave wave-2"></span>
    </div>
  </nav>

  <div class="page">

    <header class="intro-panel">
      <div class="malaysia-flag" aria-label="Stylised wavy Malaysia flag">
        <span class="flag-canton"></span>
        <span class="flag-moon"></span>
        <span class="flag-star"></span>
      </div>

      <h1>Rainfall Patterns and Natural Disasters in Each State in Malaysia</h1>

      <p class="meta-line">Author: Tu Wei Ning&nbsp;&nbsp;&nbsp;&nbsp; Created for FIT2179</p>

      <p class="subtitle">
        This visualization explores the rainfall patterns and temperature in different states in Malaysia,
        followed by the different types of natural disasters. The story moves from climate patterns to
        floods, showing why rainfall plays a huge part in natural disasters in Malaysia.
      </p>
    </header>

    <h2 id="section-1" class="chapter-title">1. Temperature in Malaysia</h2>

    <div class="chart-card"><div id="line_temperature_min_avg_max"></div></div>
    <div class="chart-card"><div id="area_temperature_range"></div></div>

    <h2 id="section-2" class="chapter-title">2. Rainfall in Malaysia</h2>

    <div class="chart-card"><div id="precipitation_monthly"></div></div>
    <div class="chart-card"><div id="line_monthly_rainfall"></div></div>
    <div class="chart-card"><div id="rainfall_temperature_relationship"></div></div>

    <h2 id="section-3" class="chapter-title">3. Rainfall Data Breakdown in Each State</h2>

    <div class="grid-two">
      <div class="chart-card"><div id="rainfall_bar"></div></div>
      <div class="chart-card"><div id="bar_wettest_states"></div></div>
    </div>

    <p class="section-text">
      We can also break down this information into different months. The heatmaps below show the average rainfall
      according to the month you select.
    </p>

    <div class="chart-card"><div id="heatmap_state_month"></div></div>
    <div class="chart-card"><div id="rainfall_seasonality_scatter"></div></div>

    <h2 id="section-4" class="chapter-title">4. Rainfall Compared with Normal Condition</h2>

    <p class="section-text">
      Comparing actual rainfall with normal rainfall helps show which states are above or below the expected conditions.
      In this context, normal condition means the usual rainfall baseline for each state, based on the historical
      average in the dataset. Comparing recent rainfall against that baseline adds more context than just showing
      raw rainfall totals.
    </p>

    <div class="chart-card"><div id="interactive_rainfall_condition_map"></div></div>

    <h2 id="section-5" class="chapter-title">5. Natural Disasters and Flood Risks</h2>

    <p class="section-text">
      The charts below compare disaster patterns over time and test whether wetter-than-normal years tend to coincide
      with more flood disasters.
    </p>

    <div class="chart-card"><div id="bar_disaster_types"></div></div>
    <div class="chart-card"><div id="pareto_disaster_types"></div></div>
    <div class="chart-card"><div id="disaster_timeline_heatmap"></div></div>

    <div class="chart-card"><div id="map_flood_rate_state"></div></div>
    <div class="chart-card"><div id="map_city_flood_days_symbols"></div></div>
    <div class="chart-card"><div id="heatmap_city_month_flood_rate"></div></div>

    <div class="chart-card"><div id="line_floods_over_time"></div></div>
    <div class="chart-card"><div id="flood_rainfall_relationship"></div></div>

    <footer>
      Visualisations created using Vega-Lite. Data sources include rainfall, temperature,
      natural disaster, and Malaysia boundary datasets.
      <p>
        Generative AI is used in assisting manners for integrating graphs and cleaning data.
        It is also used for giving guidance of creating the best storyline flow.
      </p>
      <div class="references">
        <strong>Reference Datasets:</strong>
        <a href="https://www.kaggle.com/datasets/wenjiun/malaysia-states-geojson?resource=download" target="_blank" rel="noopener noreferrer">Malaysia States GeoJSON</a>
        <a href="https://data.humdata.org/dataset/mys-rainfall-subnational" target="_blank" rel="noopener noreferrer">Malaysia Subnational Rainfall</a>
        <a href="https://climateknowledgeportal.worldbank.org/country/malaysia/climate-data-historical" target="_blank" rel="noopener noreferrer">World Bank Malaysia Historical Climate Data</a>
      </div>
    </footer>

  </div>

  <script>
    const charts = [
      ["#line_temperature_min_avg_max", "js/line_temperature_min_avg_max.json"],
      ["#area_temperature_range", "js/area_temperature_range.json"],
      ["#precipitation_monthly", "js/precipitation_monthly.json"],
      ["#line_monthly_rainfall", "js/line_monthly_rainfall.json"],
      ["#bar_wettest_states", "js/bar_wettest_states.json"],
      ["#rainfall_bar", "js/rainfall_bar.json"],
      ["#heatmap_state_month", "js/heatmap_state_month.json"],
      ["#rainfall_seasonality_scatter", "js/rainfall_seasonality_scatter.json"],
      ["#rainfall_temperature_relationship", "js/rainfall_temperature_relationship.json"],
      ["#interactive_rainfall_condition_map", "js/interactive_rainfall_condition_map.json"],
      ["#map_flood_rate_state", "js/map_flood_rate_state.json"],
      ["#map_city_flood_days_symbols", "js/map_city_flood_days_symbols.json"],
      ["#heatmap_city_month_flood_rate", "js/heatmap_city_month_flood_rate.json"],
      ["#bar_disaster_types", "js/bar_disaster_types.json"],
      ["#pareto_disaster_types", "js/pareto_disaster_types.json"],
      ["#disaster_timeline_heatmap", "js/disaster_timeline_heatmap.json"],
      ["#line_floods_over_time", "js/line_floods_over_time.json"],
      ["#flood_rainfall_relationship", "js/flood_rainfall_relationship.json"]
    ];

    charts.forEach(([div, file]) => {
      vegaEmbed(div, file, {"actions": false}).catch(error => {
        console.error("Error loading", file, error);
      });
    });
  </script>

</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Created index.html")
print("DONE. Now open index.html with Live Server.")
