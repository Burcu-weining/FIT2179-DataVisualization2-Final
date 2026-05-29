import pandas as pd

df = pd.read_csv("data/min av max air temp.csv")

print("Columns in temperature file:")
print(df.columns)

# Clean column names
df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

print("Cleaned columns:")
print(df.columns)

MONTH_MAP = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def find_column(include_words, exclude_words=None):
    exclude_words = exclude_words or []

    for col in df.columns:
        if all(word in col for word in include_words) and not any(word in col for word in exclude_words):
            return col

    return None


# Try to detect columns
year_col = None
month_col = None
min_col = None
avg_col = None
max_col = None

for col in df.columns:
    if "year" in col:
        year_col = col

if year_col is None:
    first_col = df.columns[0]
    first_col_values = df[first_col].astype(str).str.strip().str.lower()

    if first_col_values.isin(MONTH_MAP).any():
        month_col = first_col
        print(f"Using '{month_col}' as month column because it contains month names.")
    elif pd.to_numeric(df[first_col], errors="coerce").notna().any():
        year_col = first_col
        print(f"Using '{year_col}' as year column because it contains numeric year values.")

min_col = find_column(["minimum", "temperature"]) or find_column(["min", "temperature"])
avg_col = find_column(["mean", "temperature"]) or find_column(["average", "temperature"], ["minimum", "maximum"])
max_col = find_column(["maximum", "temperature"]) or find_column(["max", "temperature"])

print("Year:", year_col)
print("Month:", month_col)
print("Min temp:", min_col)
print("Avg temp:", avg_col)
print("Max temp:", max_col)

if year_col is None and month_col is None:
    raise ValueError("Could not find year or month column.")

clean = df.copy()

rename_cols = {}

if year_col:
    rename_cols[year_col] = "year"
if month_col:
    rename_cols[month_col] = "month_name"

if min_col:
    rename_cols[min_col] = "min_temp"
if avg_col:
    rename_cols[avg_col] = "avg_temp"
if max_col:
    rename_cols[max_col] = "max_temp"

clean = clean.rename(columns=rename_cols)

keep_cols = []
if "year" in clean.columns:
    keep_cols.append("year")
if "month_name" in clean.columns:
    keep_cols.append("month_name")

for col in ["min_temp", "avg_temp", "max_temp"]:
    if col in clean.columns:
        keep_cols.append(col)

clean = clean[keep_cols].copy()

if "year" in clean.columns:
    clean["year"] = pd.to_numeric(clean["year"], errors="coerce")

if "month_name" in clean.columns:
    clean["month_name"] = clean["month_name"].astype(str).str.strip()
    clean["month"] = clean["month_name"].str.lower().map(MONTH_MAP)

for col in ["min_temp", "avg_temp", "max_temp"]:
    if col in clean.columns:
        clean[col] = pd.to_numeric(clean[col], errors="coerce")

if "year" in clean.columns:
    clean = clean.dropna(subset=["year"])

if "month" in clean.columns:
    clean = clean.dropna(subset=["month"])
    clean["month"] = clean["month"].astype(int)

for col in ["min_temp", "avg_temp", "max_temp"]:
    if col in clean.columns:
        clean[col] = clean[col].round(2)

if "year" in clean.columns:
    # If there are repeated years, average them
    clean = clean.groupby("year", as_index=False).mean(numeric_only=True)

    for col in ["min_temp", "avg_temp", "max_temp"]:
        if col in clean.columns:
            clean[col] = clean[col].round(2)

    clean.to_csv("data/temperature_yearly_clean.csv", index=False)
    print("Created data/temperature_yearly_clean.csv")
else:
    clean = clean.sort_values("month")
    clean = clean[["month", "month_name"] + [c for c in ["min_temp", "avg_temp", "max_temp"] if c in clean.columns]]
    clean.to_csv("data/temperature_monthly_clean.csv", index=False)
    clean.to_csv("data/temperature_clean.csv", index=False)
    print("Created data/temperature_monthly_clean.csv")
    print("Created data/temperature_clean.csv")

print(clean.head())
