# SmartFleet Django 

A ready-to-run Django project that ports your Flask `app.py` features with the same UI (Tailwind/Chart.js), mobile responsiveness, SQLite, and `base.html` template inheritance.

## Quickstart

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Now open http://127.0.0.1:8000/

- Login with: **travels123@gmail.com / travel1**
- Upload/analytics use the included sample Excel files in `data/`

## Features
- Signup/Login using allowed users list
- Fleet Dashboard with file upload (Excel), filters, AI text report, charts
- Trip Generator (manual form + PDF/Excel parsing helpers)
- Trip Closure (insert/update from Excel or manual; stored in SQLite)
- Trip Audit (edit a row and download audit text)
- Financial Dashboard (10-day aggregates)
- User Settings (demo in-memory users like original)

## Notes
- Database: SQLite (`db.sqlite3`)
- Media uploads: `media/uploads/`
- Tailwind via CDN; Chart.js via CDN
