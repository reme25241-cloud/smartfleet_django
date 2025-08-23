import pandas as pd
import fitz
import os

import pandas as pd

def load_excel(file_path):
    df = pd.read_excel(file_path)
    df.columns = df.columns.str.strip().str.lower()

    rename_map = {
        "trip date": "trip_date",
        "date": "trip_date",
        "vehicle": "vehicle",
        "vehicle id": "vehicle",
        "route": "route",
        "freight amount": "revenue",
        "revenue (inr)": "revenue",
        "total trip expense": "expense",
        "expense": "expense",
        "cost": "expense",
        "net profit": "profit",
        "actual distance (km)": "km",
        "distance": "km",
        "km": "km",
        "trip status": "trip_status",
    }
    df = df.rename(columns={c: rename_map.get(c, c) for c in df.columns})

    if "trip_date" in df.columns:
        df["trip_date"] = pd.to_datetime(df["trip_date"], errors="coerce")
        df["day"] = df["trip_date"].dt.day

    return df



def generate_ai_report(filtered_df):
    if filtered_df.empty:
        return "No data available for AI report."
    import numpy as np
    most_profitable_vehicle = filtered_df.groupby('Vehicle ID')['Net Profit'].sum().idxmax() if 'Vehicle ID' in filtered_df.columns else "N/A"
    top_routes = ", ".join(filtered_df['Route'].value_counts().head(2).index) if 'Route' in filtered_df.columns else "N/A"
    avg_profit_per_trip = round(filtered_df['Net Profit'].sum() / max(len(filtered_df),1), 2) if 'Net Profit' in filtered_df.columns else 0
    rev = filtered_df.get('Freight Amount', pd.Series(0)).sum()
    exp = filtered_df.get('Total Trip Expense', pd.Series(0)).sum()
    profit = filtered_df.get('Net Profit', pd.Series(0)).sum()
    kms = filtered_df.get('Actual Distance (KM)', pd.Series(0)).sum()
    profit_pct = round((profit / rev * 100), 1) if rev else 0
    per_km = round(profit / kms, 2) if kms else 0
    return f"""
📊 AI Report Highlights:

Total Trips: {len(filtered_df)}
On-going Trips: {filtered_df[filtered_df.get('Trip Status','') == 'Pending Closure'].shape[0] if 'Trip Status' in filtered_df.columns else 0}
Completed Trips: {filtered_df[filtered_df.get('Trip Status','') == 'Completed'].shape[0] if 'Trip Status' in filtered_df.columns else 0}
Profit Percentage: {profit_pct}%

Financials:
- Revenue: ₹{round(rev / 1e6, 2)}M
- Expense: ₹{round(exp / 1e6, 2)}M
- Profit: ₹{round(profit / 1e6, 2)}M
- KMs Travelled: {round(kms / 1e3, 1)}K
- Cost per KM: ₹{per_km}

AI Insights:
- Top Vehicle: {most_profitable_vehicle}
- Average Profit per Trip: ₹{avg_profit_per_trip}
- Top Routes: {top_routes}
"""

def parse_pdf(filepath):
    doc = fitz.open(filepath)
    text = ""
    for page in doc:
        text += page.get_text()
    result = {{}}
    for field in [
        'trip_id', 'trip_date', 'vehicle_id', 'driver_id', 'planned_distance',
        'advance_given', 'origin', 'destination', 'vehicle_type', 'flags', 'total_freight'
    ]:
        for line in text.splitlines():
            if field.replace("_", " ").lower() in line.lower():
                try: value = line.split(":")[1].strip()
                except: value = ""
                result[field] = value
                break
        else:
            result[field] = ""
    try:
        result['total_freight'] = float(result.get('total_freight', 0) or 0)
    except: result['total_freight'] = 0.0
    return result

def parse_excel(filepath):
    try:
        df = pd.read_excel(filepath)
        row = df.iloc[0]
        return {{
            'trip_id': str(row.get('trip_id', '')),
            'trip_date': str(row.get('trip_date', '')),
            'vehicle_id': str(row.get('vehicle_id', '')),
            'driver_id': str(row.get('driver_id', '')),
            'planned_distance': str(row.get('planned_distance', '')),
            'advance_given': str(row.get('advance_given', '')),
            'origin': str(row.get('origin', '')),
            'destination': str(row.get('destination', '')),
            'vehicle_type': str(row.get('vehicle_type', '')),
            'flags': str(row.get('flags', '')),
            'total_freight': float(row.get('total_freight', 0) or 0),
        }}
    except Exception:
        return {{}}
