from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import HttpResponse, FileResponse, HttpResponseNotFound
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.views.decorators.http import require_http_methods
from django.conf import settings
import os, io, json
import pandas as pd
from .models import Trip, TripClosure
from .utils import parse_pdf, load_excel_for_dashboard

# ---------- Auth + Landing ----------
def redirect_to_signup(request):
    return redirect('signup')

def signup_view(request):
    if request.method == 'POST':
        fullname = request.POST.get('fullname')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        confirm = request.POST.get('confirm_password')
        if password != confirm:
            messages.error(request, "Passwords do not match.")
        else:
            username = email
            if User.objects.filter(username=username).exists():
                messages.error(request, "User already exists. Please log in.")
            else:
                user = User.objects.create_user(username=username, email=email, password=password,
                                                first_name=fullname)
                messages.success(request, "Registration successful. Please log in.")
                return redirect('login')
    return render(request, 'signup.html')

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            return redirect('welcome_dashboard')
        messages.error(request, "Invalid credentials.")
    return render(request, 'login.html')

def change_password_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        old = request.POST.get('old_password')
        new = request.POST.get('new_password')
        confirm = request.POST.get('confirm_password')
        if new != confirm:
            messages.error(request, "New passwords do not match.")
        else:
            try:
                user = User.objects.get(username=email)
            except User.DoesNotExist:
                user = None
            if not user or not user.check_password(old):
                messages.error(request, "Incorrect email or old password.")
            else:
                user.set_password(new)
                user.save()
                messages.success(request, "Password updated. Please log in again.")
                return redirect('login')
    return render(request, 'change_password.html')

def logout_view(request):
    logout(request)
    return redirect('login')

# ---------- Welcome ----------
def welcome_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'welcome_dashboard.html', {'name': request.user.first_name or request.user.username})

# ---------- Dashboard (Excel-driven like Flask) ----------
DEFAULT_FILE = 'fleet_50_entries.xlsx'
_uploaded_file_path = None

def _load_excel(path):
    df = pd.read_excel(path)
    df.columns = df.columns.str.strip()
    df['Trip Date'] = pd.to_datetime(df['Trip Date'], errors='coerce')
    df['Day'] = df['Trip Date'].dt.day
    return df

def _generate_ai_report(filtered_df):
    if filtered_df.empty:
        return "No data available for AI report."
    most_profitable_vehicle = filtered_df.groupby('Vehicle ID')['Net Profit'].sum().idxmax()
    top_routes = ", ".join(filtered_df['Route'].value_counts().head(2).index) if 'Route' in filtered_df.columns else "N/A"
    avg_profit_per_trip = round(filtered_df['Net Profit'].sum() / len(filtered_df), 2)
    rev = filtered_df['Freight Amount'].sum()
    exp = filtered_df['Total Trip Expense'].sum()
    profit = filtered_df['Net Profit'].sum()
    kms = filtered_df['Actual Distance (KM)'].sum()
    profit_pct = round((profit / rev * 100), 1) if rev else 0
    per_km = round(profit / kms, 2) if kms else 0
    return f"""
Total Trips: {len(filtered_df)}
On-going Trips: {filtered_df[filtered_df['Trip Status'] == 'Pending Closure'].shape[0]}
Completed Trips: {filtered_df[filtered_df['Trip Status'] == 'Completed'].shape[0]}
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


def dashboard(request):
    global _uploaded_file_path
    if not request.user.is_authenticated:
        return redirect('login')

    if request.method == 'POST' and request.FILES.get('excel'):
        f = request.FILES['excel']
        dest = (settings.MEDIA_ROOT / f.name) if hasattr(settings, 'MEDIA_ROOT') else None
        dest = dest or os.path.join('uploads', f.name)
        os.makedirs(os.path.dirname(str(dest)), exist_ok=True)
        with open(dest, 'wb+') as out:
            for chunk in f.chunks():
                out.write(chunk)
        _uploaded_file_path = str(dest)

    file_to_use = _uploaded_file_path or DEFAULT_FILE
    try:
        df = _load_excel(file_to_use)
    except Exception:
        df = pd.DataFrame()

    vehicle = request.GET.get('vehicle') or ''
    route = request.GET.get('route') or ''
    start = request.GET.get('start') or ''
    end = request.GET.get('end') or ''

    filtered = df.copy()
    if not filtered.empty:
        if vehicle:
            filtered = filtered[filtered['Vehicle ID'] == vehicle]
        if route:
            filtered = filtered[filtered['Route'] == route]
        if start and end:
            start_date = pd.to_datetime(start)
            end_date = pd.to_datetime(end)
            filtered = filtered[(filtered['Trip Date'] >= start_date) & (filtered['Trip Date'] <= end_date)]

    vehicles = sorted(filtered['Vehicle ID'].dropna().unique().tolist()) if not filtered.empty else []
    routes = sorted(filtered['Route'].dropna().unique().tolist()) if (not filtered.empty and 'Route' in filtered.columns) else []
    available_dates = sorted(filtered['Trip Date'].dropna().dt.strftime('%Y-%m-%d').unique().tolist()) if not filtered.empty else []

    total_trips = len(filtered)
    ongoing = filtered[filtered['Trip Status'] == 'Pending Closure'].shape[0] if not filtered.empty else 0
    closed = filtered[filtered['Trip Status'] == 'Completed'].shape[0] if not filtered.empty else 0
    flags = filtered[filtered['Trip Status'] == 'Under Audit'].shape[0] if not filtered.empty else 0
    resolved = filtered[(filtered['Trip Status'] == 'Under Audit') & (filtered['POD Status'] == 'Yes')].shape[0] if not filtered.empty else 0

    rev = filtered['Freight Amount'].sum() if not filtered.empty else 0
    exp = filtered['Total Trip Expense'].sum() if not filtered.empty else 0
    profit = filtered['Net Profit'].sum() if not filtered.empty else 0
    kms = filtered['Actual Distance (KM)'].sum() if not filtered.empty else 0

    rev_m = round(rev / 1e6, 2) if rev else 0
    exp_m = round(exp / 1e6, 2) if exp else 0
    profit_m = round(profit / 1e6, 2) if profit else 0
    kms_k = round(kms / 1e3, 1) if kms else 0
    per_km = round(profit / kms, 2) if kms else 0
    profit_pct = round((profit / rev) * 100, 1) if rev else 0

    if not filtered.empty:
        daily = filtered.groupby('Day')['Trip ID'].count().reindex(range(1,32), fill_value=0).tolist()
        audited = filtered[filtered['Trip Status'] == 'Under Audit'].groupby('Day')['Trip ID'].count().reindex(range(1,32), fill_value=0).tolist()
    else:
        daily = [0]*31
        audited = [0]*31
    audit_pct = [round(a / b * 100, 1) if b else 0 for a, b in zip(audited, daily)]
    bar_labels = ['Revenue', 'Expense', 'Profit']
    bar_values = [float(rev_m), float(exp_m), float(profit_m)]
    ai_report = _generate_ai_report(filtered) if not filtered.empty else "Upload an Excel to see insights."

    return render(request, 'dashboard.html', {
        'vehicles': vehicles, 'routes': routes, 'available_dates': available_dates,
        'total_trips': total_trips, 'ongoing': ongoing, 'closed': closed, 'flags': flags, 'resolved': resolved,
        'rev_m': rev_m, 'exp_m': exp_m, 'profit_m': profit_m, 'kms_k': kms_k, 'per_km': per_km, 'profit_pct': profit_pct,
        'daily': json.dumps(daily), 'audited': json.dumps(audited), 'audit_pct': json.dumps(audit_pct),
        'bar_labels': json.dumps(bar_labels), 'bar_values': json.dumps(bar_values),
        'ai_report': ai_report,
    })

def download_summary(request):
    content = "AI Report Summary\n\nPlease generate from the dashboard after filtering."
    buf = io.BytesIO(content.encode('utf-8'))
    return FileResponse(buf, as_attachment=True, filename='AI_Report_Summary.txt')

# ---------- Trip Generator ----------
def trip_generator(request):
    parsed = {}
    if request.method == 'POST':
        if request.FILES.get('pdf_file'):
            pdf = request.FILES['pdf_file']
            path = settings.MEDIA_ROOT / pdf.name
            os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
            with open(path, 'wb+') as out:
                for ch in pdf.chunks():
                    out.write(ch)
            parsed = parse_pdf(str(path))
        elif request.FILES.get('excel_file'):
            excel = request.FILES['excel_file']
            path = settings.MEDIA_ROOT / excel.name
            with open(path, 'wb+') as out:
                for ch in excel.chunks():
                    out.write(ch)
            df = pd.read_excel(path)
            row = df.iloc[0]
            parsed = {
                'trip_id': str(row.get('trip_id', '')),
                'trip_date': str(row.get('trip_date', '')),
                'vehicle_id': str(row.get('vehicle_id', '')),
                'driver_id': str(row.get('driver_id', '')),
                'planned_distance': row.get('planned_distance', None),
                'advance_given': row.get('advance_given', None),
                'origin': str(row.get('origin', '')),
                'destination': str(row.get('destination', '')),
                'vehicle_type': str(row.get('vehicle_type', '')),
                'flags': str(row.get('flags', '')),
                'total_freight': float(row.get('total_freight', 0) or 0),
            }
        else:
            # Manual save
            fields = ['trip_id','trip_date','vehicle_id','driver_id','planned_distance','advance_given',
                      'origin','destination','vehicle_type','flags','total_freight']
            data = {f: request.POST.get(f) for f in fields}
            if not data['trip_id']:
                messages.error(request, "Trip ID is required.")
            else:
                trip, _ = Trip.objects.update_or_create(
                    trip_id=data['trip_id'],
                    defaults={
                        'trip_date': data['trip_date'],
                        'vehicle_id': data['vehicle_id'],
                        'driver_id': data['driver_id'],
                        'planned_distance': float(data['planned_distance'] or 0),
                        'advance_given': float(data['advance_given'] or 0),
                        'origin': data['origin'],
                        'destination': data['destination'],
                        'vehicle_type': data['vehicle_type'],
                        'flags': data['flags'],
                        'total_freight': float(data['total_freight'] or 0),
                    }
                )
                messages.success(request, f"Trip {trip.trip_id} saved.")
                return redirect('trip_generator')

    trips = Trip.objects.order_by('-id').values_list('trip_id','trip_date','vehicle_id','driver_id','planned_distance','advance_given','origin','destination','vehicle_type','flags','total_freight')
    return render(request, 'trip_generator.html', {'parsed_data': parsed, 'all_trips': trips})

# ---------- Trip Closure ----------
def trip_closure(request):
    fields = [
        ('actual_distance', 'Actual Distance (KM)', 'number'),
        ('actual_delivery_date', 'Actual Delivery Date', 'date'),
        ('trip_delay_reason', 'Trip Delay Reason', 'text'),
        ('fuel_quantity', 'Fuel Quantity (L)', 'number'),
        ('fuel_rate', 'Fuel Rate', 'number'),
        ('fuel_cost', 'Fuel Cost', 'number'),
        ('toll_charges', 'Toll Charges', 'number'),
        ('food_expense', 'Food Expense', 'number'),
        ('lodging_expense', 'Lodging Expense', 'number'),
        ('miscellaneous_expense', 'Miscellaneous Expense', 'number'),
        ('maintenance_cost', 'Maintenance Cost', 'number'),
        ('loading_charges', 'Loading Charges', 'number'),
        ('unloading_charges', 'Unloading Charges', 'number'),
        ('penalty_fine', 'Penalty/Fine', 'number'),
        ('total_trip_expense', 'Total Trip Expense', 'number'),
        ('freight_amount', 'Freight Amount', 'number'),
        ('incentives', 'Incentives', 'number'),
        ('net_profit', 'Net Profit', 'number'),
        ('payment_mode', 'Payment Mode', 'text'),
        ('pod_status', 'POD Status', 'text'),
        ('trip_status', 'Trip Status', 'text'),
        ('remarks', 'Remarks', 'text')
    ]
    start_date = request.GET.get('start_date','')
    end_date = request.GET.get('end_date','')
    search_trip_id = request.GET.get('search_trip_id','').strip()
    trip_data = {}

    if request.method == 'POST':
        if request.FILES.get('excel_file'):
            excel = request.FILES['excel_file']
            path = settings.MEDIA_ROOT / excel.name
            os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
            with open(path, 'wb+') as out:
                for ch in excel.chunks():
                    out.write(ch)
            df = pd.read_excel(path, dtype=str)
            df.columns = df.columns.str.strip()
            for _, row in df.iterrows():
                tid = str(row.get('Trip ID','')).strip()
                if not tid:
                    continue
                trip, _ = Trip.objects.get_or_create(trip_id=tid)
                defaults = {}
                for f, label, _type in fields:
                    val = row.get(label,'')
                    if pd.isna(val): val = ''
                    defaults[f] = val
                TripClosure.objects.update_or_create(trip=trip, defaults=defaults)
            messages.success(request, "Excel uploaded and closures saved.")
            return redirect('trip_closure')
        else:
            tid = request.POST.get('trip_id','').strip()
            if not tid:
                return HttpResponse("Trip ID is required", status=400)
            trip, _ = Trip.objects.get_or_create(trip_id=tid)
            defaults = {}
            for f, label, ftype in fields:
                val = request.POST.get(f,'')
                defaults[f] = float(val) if ftype=='number' and val!='' else val
            TripClosure.objects.update_or_create(trip=trip, defaults=defaults)
            messages.success(request, f"Trip {tid} closure saved.")
            return redirect('trip_closure')

    qs = TripClosure.objects.select_related('trip').all().order_by('-trip__trip_id')
    closures = list(qs.values_list('trip__trip_id', *[f[0] for f in fields]))
    if search_trip_id:
        try:
            tc = TripClosure.objects.select_related('trip').get(trip__trip_id=search_trip_id)
            trip_data = {'trip_id': tc.trip.trip_id}
            for f, _label, _type in fields:
                trip_data[f] = getattr(tc, f) or ''
        except TripClosure.DoesNotExist:
            pass

    return render(request, 'trip_closure.html', {
        'fields': fields,
        'closures': closures,
        'trip_data': trip_data,
        'start_date': start_date, 'end_date': end_date
    })

# ---------- Trip Audit (simplified to DB) ----------
def trip_audit_dashboard(request):
    # Use TripClosure data to compute stats
    df = pd.DataFrame(list(TripClosure.objects.select_related('trip').values(
        'trip__trip_id','trip_status','pod_status','freight_amount','total_trip_expense','net_profit'
    )))
    if df.empty:
        days = [0]*31
        closed_data = [0]*31
        audited_data = [0]*31
        audit_pct = [0]*31
        totals = dict(total_trips=0, opened=0, closed=0, audited=0, audit_closed=0, flags=0)
        trips = []
    else:
        df['day'] = pd.Series([1]*len(df))  # placeholder since trips table doesn't have date here
        total_trips = len(df)
        opened = (df['trip_status'].str.lower()=='pending closure').sum()
        closed = (df['trip_status'].str.lower()=='completed').sum()
        audited = (df['pod_status'].str.lower()=='yes').sum()
        audit_closed = ((df['trip_status'].str.lower()=='completed') & (df['pod_status'].str.lower()=='yes')).sum()
        flags = (df['trip_status'].str.lower()=='under audit').sum()
        days = list(range(1,32))
        closed_data = [0]*31
        audited_data = [0]*31
        audit_pct = [round((a/c)*100,1) if c else 0 for a,c in zip(audited_data, closed_data)]
        totals = dict(total_trips=total_trips, opened=opened, closed=closed, audited=audited, audit_closed=audit_closed, flags=flags)
        trips = [{'trip id': t} for t in df['trip__trip_id'].tolist()]
    return render(request, 'trip_audit.html', {
        'closed_data': json.dumps(closed_data),
        'audited_data': json.dumps(audited_data),
        'audit_pct': json.dumps(audit_pct),
        **totals, 'trips': trips, 'filter_option': 'all'
    })

def audit_trip(request, trip_id):
    try:
        tc = TripClosure.objects.select_related('trip').get(trip__trip_id=trip_id)
    except TripClosure.DoesNotExist:
        return HttpResponseNotFound("Trip not found")
    if request.method == 'POST':
        for field in [f.name for f in TripClosure._meta.fields if f.name not in ['id','trip']]:
            if field in request.POST:
                setattr(tc, field, request.POST.get(field))
        tc.save()
        # build a text response for download
        content = "Trip Audit Details\\n\\n"
        for field in [f.name for f in TripClosure._meta.fields if f.name not in ['id','trip']]:
            content += f"{field}: {getattr(tc, field)}\\n"
        return HttpResponse(content, content_type='text/plain',
                            headers={'Content-Disposition': f'attachment; filename=trip_{trip_id}_audit.txt'})
    # Render simple edit form
    fields = [f.name for f in TripClosure._meta.fields if f.name not in ['id','trip']]
    return render(request, 'audit_trip.html', {'trip_id': trip_id, 'data': tc, 'fields': fields})

# ---------- Financial Dashboard (placeholder) ----------
def financial_dashboard(request):
    return HttpResponse("Financial Dashboard coming soon.")

# ---------- User Settings (static demo) ----------
def user_settings(request):
    users = [
        {'name': 'Anna Smith', 'email': 'anna.smith@example.com', 'role': 'Admin',
         'rights': {'view': True, 'edit': True, 'delete': True, 'add_fields': False}},
        {'name': 'John Doe', 'email': 'john.doe@example.com', 'role': 'Manager',
         'rights': {'view': True, 'edit': False, 'delete': False, 'add_fields': False}},
    ]
    return render(request, 'user_settings.html', {'users': users})
