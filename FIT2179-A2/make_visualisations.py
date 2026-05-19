import os
import json
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
        .str.replace("(", "", regex=False)
        .str.replace(")", "", regex=False)
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

    if year_col and flood_col:
        flood_yearly = disaster_year[[year_col, flood_col]].copy()
        flood_yearly.columns = ["year", "flood_count"]
        flood_yearly["flood_count"] = pd.to_numeric(flood_yearly["flood_count"], errors="coerce").fillna(0)
        flood_yearly.to_csv("data/flood_yearly.csv", index=False)

        print("Created data/flood_yearly.csv")
    else:
        print("Could not detect year/flood columns")


# =========================
# VEGA-LITE CHARTS
# =========================

def map_chart(filename, title, field, legend_title, scheme):
    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "title": {
            "text": title,
            "fontSize": 18,
            "anchor": "start"
        },
        "width": 720,
        "height": 430,
        "data": {
            "url": "data/malaysia_states.geojson",
            "format": {
                "type": "json",
                "property": "features"
            }
        },
        "transform": [
            {
                "lookup": "properties.shapeISO",
                "from": {
                    "data": {
                        "url": "data/state_rainfall_summary.csv"
                    },
                    "key": "shapeISO",
                    "fields": [
                        "avg_rainfall_mm",
                        "avg_normal_rainfall_mm",
                        "difference_from_normal",
                        "rainfall_ratio",
                        "rainfall_status",
                        "rainfall_category"
                    ]
                }
            }
        ],
        "projection": {
            "type": "mercator",
            "center": [109, 4],
            "scale": 1100
        },
        "mark": {
            "type": "geoshape",
            "stroke": "white",
            "strokeWidth": 0.7
        },
        "encoding": {
            "color": {
                "field": field,
                "type": "quantitative",
                "title": legend_title,
                "scale": {
                    "scheme": scheme
                }
            },
            "tooltip": [
                {"field": "properties.shapeName", "type": "nominal", "title": "State"},
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


# 5 MAPS
map_chart(
    "map_avg_rainfall.json",
    "Map 1: Average Recent Rainfall Across Malaysia",
    "avg_rainfall_mm",
    "Average rainfall",
    "blues"
)

map_chart(
    "map_normal_rainfall.json",
    "Map 2: Normal Rainfall Across Malaysia",
    "avg_normal_rainfall_mm",
    "Normal rainfall",
    "tealblues"
)

map_chart(
    "map_difference_rainfall.json",
    "Map 3: Difference from Normal Rainfall",
    "difference_from_normal",
    "Difference from normal",
    "redblue"
)

map_chart(
    "map_rainfall_ratio.json",
    "Map 4: Actual Rainfall Compared with Normal",
    "rainfall_ratio",
    "Actual / normal rainfall",
    "purples"
)

# Map 5 categorical
save_json("map_rainfall_category.json", {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "title": {
        "text": "Map 5: Rainfall Category Across Malaysia",
        "fontSize": 18,
        "anchor": "start"
    },
    "width": 720,
    "height": 430,
    "data": {
        "url": "data/malaysia_states.geojson",
        "format": {
            "type": "json",
            "property": "features"
        }
    },
    "transform": [
        {
            "lookup": "properties.shapeISO",
            "from": {
                "data": {"url": "data/state_rainfall_summary.csv"},
                "key": "shapeISO",
                "fields": [
                    "avg_rainfall_mm",
                    "rainfall_category"
                ]
            }
        }
    ],
    "projection": {
        "type": "mercator",
        "center": [109, 4],
        "scale": 1100
    },
    "mark": {
        "type": "geoshape",
        "stroke": "white",
        "strokeWidth": 0.7
    },
    "encoding": {
        "color": {
            "field": "rainfall_category",
            "type": "nominal",
            "title": "Rainfall category",
            "scale": {
                "domain": ["Lower rainfall", "Moderate rainfall", "Higher rainfall"],
                "range": ["#d6e9f8", "#74a9cf", "#08306b"]
            }
        },
        "tooltip": [
            {"field": "properties.shapeName", "type": "nominal", "title": "State"},
            {"field": "avg_rainfall_mm", "type": "quantitative", "title": "Average rainfall", "format": ".2f"},
            {"field": "rainfall_category", "type": "nominal", "title": "Category"}
        ]
    },
    "config": {
        "view": {"stroke": None}
    }
})


# 6 BAR CHART
save_json("bar_wettest_states.json", {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "title": {
        "text": "Wettest States by Average Rainfall",
        "fontSize": 18,
        "anchor": "start"
    },
    "width": 720,
    "height": 420,
    "data": {"url": "data/state_rainfall_summary.csv"},
    "mark": {"type": "bar", "tooltip": True},
    "encoding": {
        "x": {
            "field": "avg_rainfall_mm",
            "type": "quantitative",
            "title": "Average rainfall"
        },
        "y": {
            "field": "shapeISO",
            "type": "nominal",
            "sort": "-x",
            "title": "State code"
        },
        "color": {
            "field": "avg_rainfall_mm",
            "type": "quantitative",
            "scale": {"scheme": "blues"},
            "legend": None
        },
        "tooltip": [
            {"field": "shapeISO", "type": "nominal", "title": "State code"},
            {"field": "avg_rainfall_mm", "type": "quantitative", "format": ".2f"},
            {"field": "difference_from_normal", "type": "quantitative", "format": ".2f"}
        ]
    },
    "config": {"view": {"stroke": None}}
})


# 7 LOLLIPOP CHART
save_json("lollipop_difference.json", {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "title": {
        "text": "Rainfall Difference from Normal by State",
        "fontSize": 18,
        "anchor": "start"
    },
    "width": 720,
    "height": 420,
    "data": {"url": "data/state_rainfall_summary.csv"},
    "layer": [
        {
            "mark": {"type": "rule", "strokeWidth": 2},
            "encoding": {
                "x": {"datum": 0},
                "x2": {"field": "difference_from_normal"},
                "y": {
                    "field": "shapeISO",
                    "type": "nominal",
                    "sort": "-x",
                    "title": "State code"
                },
                "color": {
                    "condition": {
                        "test": "datum.difference_from_normal >= 0",
                        "value": "#2b6cb0"
                    },
                    "value": "#c53030"
                }
            }
        },
        {
            "mark": {"type": "circle", "size": 130, "tooltip": True},
            "encoding": {
                "x": {
                    "field": "difference_from_normal",
                    "type": "quantitative",
                    "title": "Difference from normal rainfall"
                },
                "y": {
                    "field": "shapeISO",
                    "type": "nominal",
                    "sort": "-x"
                },
                "color": {
                    "condition": {
                        "test": "datum.difference_from_normal >= 0",
                        "value": "#2b6cb0"
                    },
                    "value": "#c53030"
                },
                "tooltip": [
                    {"field": "shapeISO", "type": "nominal"},
                    {"field": "difference_from_normal", "type": "quantitative", "format": ".2f"}
                ]
            }
        }
    ],
    "config": {"view": {"stroke": None}}
})


# 8 SCATTERPLOT
save_json("scatter_actual_normal.json", {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "title": {
        "text": "Actual Rainfall vs Normal Rainfall",
        "fontSize": 18,
        "anchor": "start"
    },
    "width": 700,
    "height": 420,
    "data": {"url": "data/state_rainfall_summary.csv"},
    "mark": {"type": "circle", "size": 130, "opacity": 0.8, "tooltip": True},
    "encoding": {
        "x": {
            "field": "avg_normal_rainfall_mm",
            "type": "quantitative",
            "title": "Normal rainfall"
        },
        "y": {
            "field": "avg_rainfall_mm",
            "type": "quantitative",
            "title": "Actual rainfall"
        },
        "color": {
            "field": "difference_from_normal",
            "type": "quantitative",
            "scale": {"scheme": "redblue"},
            "title": "Difference"
        },
        "tooltip": [
            {"field": "shapeISO", "type": "nominal"},
            {"field": "avg_rainfall_mm", "type": "quantitative", "format": ".2f"},
            {"field": "avg_normal_rainfall_mm", "type": "quantitative", "format": ".2f"},
            {"field": "difference_from_normal", "type": "quantitative", "format": ".2f"}
        ]
    },
    "config": {"view": {"stroke": None}}
})


# 9 MONTHLY LINE CHART
save_json("line_monthly_rainfall.json", {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "title": {
        "text": "Average Rainfall by Month",
        "fontSize": 18,
        "anchor": "start"
    },
    "width": 720,
    "height": 380,
    "data": {"url": "data/monthly_rainfall.csv"},
    "mark": {"type": "line", "point": True, "tooltip": True},
    "encoding": {
        "x": {
            "field": "month",
            "type": "ordinal",
            "title": "Month"
        },
        "y": {
            "field": "avg_rainfall_mm",
            "type": "quantitative",
            "title": "Average rainfall"
        },
        "tooltip": [
            {"field": "month", "type": "ordinal"},
            {"field": "avg_rainfall_mm", "type": "quantitative", "format": ".2f"}
        ]
    },
    "config": {"view": {"stroke": None}}
})


# 10 HEATMAP
save_json("heatmap_state_month.json", {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "title": {
        "text": "Rainfall Heatmap by State and Month",
        "fontSize": 18,
        "anchor": "start"
    },
    "width": 720,
    "height": 420,
    "data": {"url": "data/state_monthly_rainfall.csv"},
    "mark": {"type": "rect", "tooltip": True},
    "encoding": {
        "x": {
            "field": "month",
            "type": "ordinal",
            "title": "Month"
        },
        "y": {
            "field": "state",
            "type": "nominal",
            "title": "State"
        },
        "color": {
            "field": "avg_rainfall_mm",
            "type": "quantitative",
            "scale": {"scheme": "blues"},
            "title": "Average rainfall"
        },
        "tooltip": [
            {"field": "state", "type": "nominal"},
            {"field": "month", "type": "ordinal"},
            {"field": "avg_rainfall_mm", "type": "quantitative", "format": ".2f"}
        ]
    },
    "config": {"view": {"stroke": None}}
})


# 11 DISASTER TYPE BAR CHART
save_json("bar_disaster_types.json", {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "title": {
        "text": "Natural Disaster Types Recorded in Malaysia",
        "fontSize": 18,
        "anchor": "start"
    },
    "width": 720,
    "height": 380,
    "data": {"url": "data/disaster_type_summary.csv"},
    "mark": {"type": "bar", "tooltip": True},
    "encoding": {
        "x": {
            "field": "count",
            "type": "quantitative",
            "title": "Count"
        },
        "y": {
            "field": "disaster_type",
            "type": "nominal",
            "sort": "-x",
            "title": "Disaster type"
        },
        "color": {
            "field": "count",
            "type": "quantitative",
            "scale": {"scheme": "orangered"},
            "legend": None
        },
        "tooltip": [
            {"field": "disaster_type", "type": "nominal"},
            {"field": "count", "type": "quantitative"}
        ]
    },
    "config": {"view": {"stroke": None}}
})


# 12 FLOOD LINE CHART
save_json("line_floods_over_time.json", {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "title": {
        "text": "Flood Disasters Over Time",
        "fontSize": 18,
        "anchor": "start"
    },
    "width": 720,
    "height": 380,
    "data": {"url": "data/flood_yearly.csv"},
    "mark": {"type": "line", "point": True, "tooltip": True},
    "encoding": {
        "x": {
            "field": "year",
            "type": "ordinal",
            "title": "Year"
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
  <title>When Rain Becomes Risk</title>

  <script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>

  <style>
    body {
      font-family: Arial, sans-serif;
      background: #f4f7fb;
      margin: 0;
      color: #222;
    }

    .page {
      max-width: 1150px;
      margin: auto;
      padding: 42px 28px;
    }

    h1 {
      font-size: 46px;
      margin-bottom: 8px;
      letter-spacing: -1px;
    }

    h2 {
      font-size: 26px;
      margin-top: 44px;
      margin-bottom: 12px;
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
      box-shadow: 0 6px 22px rgba(0,0,0,0.07);
      overflow-x: auto;
    }

    .grid-two {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
    }

    .note-box {
      background: #fff6df;
      border-left: 5px solid #f0b429;
      padding: 14px 18px;
      border-radius: 8px;
      max-width: 900px;
      color: #5c4300;
      font-size: 15px;
      margin-bottom: 28px;
      line-height: 1.6;
    }

    footer {
      border-top: 1px solid #ddd;
      margin-top: 52px;
      padding-top: 18px;
      color: #666;
      font-size: 13px;
      line-height: 1.6;
    }

    @media (max-width: 900px) {
      .grid-two {
        grid-template-columns: 1fr;
      }

      h1 {
        font-size: 36px;
      }
    }
  </style>
</head>

<body>
  <div class="page">

    <h1>When Rain Becomes Risk</h1>

    <p class="subtitle">
      This visualisation explores Malaysia’s precipitation patterns and how heavier rainfall
      connects to flood-related disaster risk. It focuses on where rainfall is highest,
      when rainfall is most intense, and how flood disasters appear across time.
    </p>

    <div class="note-box">
      This project explores a relationship, not direct causation. Flood impacts are also affected
      by drainage, land use, urbanisation, river systems, and population exposure.
    </div>

    <h2>1. Rainfall is not evenly distributed across Malaysia</h2>

    <p class="section-text">
      These maps show different ways of understanding rainfall across Malaysian states.
    </p>

    <div class="chart-card"><div id="map_avg_rainfall"></div></div>
    <div class="chart-card"><div id="map_normal_rainfall"></div></div>
    <div class="chart-card"><div id="map_difference_rainfall"></div></div>
    <div class="chart-card"><div id="map_rainfall_ratio"></div></div>
    <div class="chart-card"><div id="map_rainfall_category"></div></div>

    <h2>2. Which states are wetter?</h2>

    <p class="section-text">
      These charts compare rainfall levels directly between Malaysian state codes.
    </p>

    <div class="grid-two">
      <div class="chart-card"><div id="bar_wettest_states"></div></div>
      <div class="chart-card"><div id="lollipop_difference"></div></div>
    </div>

    <div class="chart-card"><div id="scatter_actual_normal"></div></div>

    <h2>3. Rainfall changes by month</h2>

    <p class="section-text">
      Monthly rainfall patterns show when rainfall tends to be stronger.
    </p>

    <div class="chart-card"><div id="line_monthly_rainfall"></div></div>
    <div class="chart-card"><div id="heatmap_state_month"></div></div>

    <h2>4. Rainfall matters because floods dominate the disaster story</h2>

    <p class="section-text">
      The disaster charts show why rainfall is important for understanding risk in Malaysia.
    </p>

    <div class="grid-two">
      <div class="chart-card"><div id="bar_disaster_types"></div></div>
      <div class="chart-card"><div id="line_floods_over_time"></div></div>
    </div>

    <footer>
      Author: Faraz Rasool. Created for FIT2179 Data Visualisation 2, 2026.
      Visualisations created using Vega-Lite. Data sources: rainfall and natural disaster datasets.
    </footer>

  </div>

  <script>
    const charts = [
      ["#map_avg_rainfall", "js/map_avg_rainfall.json"],
      ["#map_normal_rainfall", "js/map_normal_rainfall.json"],
      ["#map_difference_rainfall", "js/map_difference_rainfall.json"],
      ["#map_rainfall_ratio", "js/map_rainfall_ratio.json"],
      ["#map_rainfall_category", "js/map_rainfall_category.json"],
      ["#bar_wettest_states", "js/bar_wettest_states.json"],
      ["#lollipop_difference", "js/lollipop_difference.json"],
      ["#scatter_actual_normal", "js/scatter_actual_normal.json"],
      ["#line_monthly_rainfall", "js/line_monthly_rainfall.json"],
      ["#heatmap_state_month", "js/heatmap_state_month.json"],
      ["#bar_disaster_types", "js/bar_disaster_types.json"],
      ["#line_floods_over_time", "js/line_floods_over_time.json"]
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