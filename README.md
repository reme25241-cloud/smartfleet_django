# SmartFleet (Django + SQLite)

A Django port of your Flask Smart Fleet app using the same UI and SQLite.

## Quickstart

```bash
# 1) Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2) Install deps
pip install -r requirements.txt

# 3) Migrate DB
python manage.py migrate

# 4) Run
python manage.py runserver
```

### Optional
Create a superuser to access /admin:
```
python manage.py createsuperuser
```

### Notes
- Uploads will be saved under `uploads/`.
- Dashboard expects an Excel with columns like in your sample: `Trip ID, Trip Date, Vehicle ID, Route, Freight Amount, Total Trip Expense, Net Profit, Actual Distance (KM), Trip Status, POD Status`.
- `Trip Generator` saves trips to DB. `Trip Closure` can bulk import closures from an Excel sheet or save manually.
