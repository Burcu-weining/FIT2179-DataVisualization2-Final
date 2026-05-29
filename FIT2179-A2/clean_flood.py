import pandas as pd

df = pd.read_csv("data/disasters over the year.csv")

print("Columns in disaster file:")
print(df.columns)

# Clean column names
df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

print("Cleaned columns:")
print(df.columns)

# Try to find year and flood columns
year_col = None
flood_col = None

for col in df.columns:
    if "year" in col:
        year_col = col
    if "flood" in col:
        flood_col = col

print("Year column:", year_col)
print("Flood column:", flood_col)

# In this file, the first column is named "Category", but its values are years.
if year_col is None:
    first_col = df.columns[0]
    first_col_values = pd.to_numeric(df[first_col], errors="coerce")

    if first_col_values.notna().any():
        year_col = first_col
        print(f"Using '{year_col}' as year column because it contains year values.")

if year_col is None or flood_col is None:
    raise ValueError("Could not find year or flood column. Check printed column names above.")

clean = df[[year_col, flood_col]].copy()
clean.columns = ["year", "flood_count"]

clean["year"] = pd.to_numeric(clean["year"], errors="coerce")
clean["flood_count"] = pd.to_numeric(clean["flood_count"], errors="coerce").fillna(0)

clean = clean.dropna(subset=["year"])
clean = clean.sort_values("year")

clean.to_csv("data/flood_yearly_clean.csv", index=False)

print("Created data/flood_yearly_clean.csv")
print(clean.head())
