import fitz
import pandas as pd

def parse_pdf(filepath):
    doc = fitz.open(filepath)
    text = ""
    for page in doc:
        text += page.get_text()
    result = {}
    for field in [
        'trip_id','trip_date','vehicle_id','driver_id','planned_distance',
        'advance_given','origin','destination','vehicle_type','flags','total_freight'
    ]:
        result[field] = ""
        needle = field.replace("_"," ").lower()
        for line in text.splitlines():
            if needle in line.lower():
                try:
                    result[field] = line.split(':',1)[1].strip()
                except Exception:
                    result[field] = ""
                break
    try:
        result['total_freight'] = float(result.get('total_freight',0) or 0)
    except Exception:
        result['total_freight'] = 0.0
    return result

def load_excel_for_dashboard(file_path):
    df = pd.read_excel(file_path)
    df.columns = df.columns.str.strip()
    df['Trip Date'] = pd.to_datetime(df['Trip Date'], errors='coerce')
    df['Day'] = df['Trip Date'].dt.day
    return df
