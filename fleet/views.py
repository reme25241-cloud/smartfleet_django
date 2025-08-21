from django.conf import settings
from django.shortcuts import render, redirect
from django.http import HttpResponse, FileResponse, HttpResponseBadRequest
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from .models import Trip, TripClosure
from django.db.models import Sum
from .utils import load_excel, generate_ai_report, parse_pdf, parse_excel
import pandas as pd
import os
import json
from io import BytesIO

DATA_FLEET = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'fleet_50_entries.xlsx')
DATA_CLOSURE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'Trip_Closure_Sheet_Oct2024_Mar2025.xlsx')

def index(request):
    return redirect('signup')

def signup(request):
    if request.method == 'POST':
        fullname = request.POST.get('fullname')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if email not in settings.ALLOWED_USERS:
            return render(request, 'fleet/simple_message.html', {'message': '❌ This email is not allowed to register.'})

        if password != confirm_password:
            return render(request, 'fleet/simple_message.html', {'message': '❌ Passwords do not match!'})

        # store to a text file just like original app
        with open(os.path.join(settings.BASE_DIR, 'users.txt'), 'w') as f:
            f.write(f"{email},{password},{fullname},{phone}\n")
        return render(request, 'fleet/simple_message.html', {'message': '✅ Registration successful! <a href="/login">Click here to login</a>'})
    return render(request, 'fleet/signup.html')

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        allowed = settings.ALLOWED_USERS.get(email)
        if allowed and allowed['password'] == password:
            request.session['user_email'] = email
            request.session['user_name'] = allowed['fullname']
            return redirect('welcome_dashboard')
        return render(request, 'fleet/simple_message.html', {'message':'❌ Invalid credentials or access not allowed. <a href="/login">Try again</a>'})
    return render(request, 'fleet/login.html')

def logout_view(request):
    request.session.flush()
    return redirect('login')

def welcome_dashboard(request):
    if 'user_name' in request.session:
        return render(request, 'fleet/welcome_dashboard.html', {'name': request.session['user_name']})
    return redirect('login')

def fleet_dashboard_redirect(request):
    return redirect('dashboard')

# --- Dashboard (Fleet) ---@ensure_csrf_cookie
def dashboard(request):
    # default excel from data folder; allow uploads via POST
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(upload_dir, exist_ok=True)

    if request.method == 'POST' and 'excel' in request.FILES:
        f = request.FILES['excel']
        path = os.path.join(upload_dir, f.name)
        with open(path, 'wb+') as dest:
            for chunk in f.chunks():
                dest.write(chunk)
        df = load_excel(path)
    else:
        path = DATA_FLEET if os.path.exists(DATA_FLEET) else None
        df = load_excel(path) if path else pd.DataFrame()

    # Filters
    vehicle = request.GET.get('vehicle') or ''
    route = request.GET.get('route') or ''
    start = request.GET.get('start') or ''
    end = request.GET.get('end') or ''

    filtered = df.copy()
    if not df.empty:
        if vehicle:
            filtered = filtered[filtered['Vehicle ID'] == vehicle]
        if route and 'Route' in filtered.columns:
            filtered = filtered[filtered['Route'] == route]
        if start and end and 'Trip Date' in filtered.columns:
            start_date = pd.to_datetime(start)
            end_date = pd.to_datetime(end)
            filtered = filtered[(filtered['Trip Date'] >= start_date) & (filtered['Trip Date'] <= end_date)]

        vehicles = sorted(filtered['Vehicle ID'].dropna().unique()) if 'Vehicle ID' in df.columns else []
        routes = sorted(filtered['Route'].dropna().unique()) if 'Route' in df.columns else []
        available_dates = sorted(filtered['Trip Date'].dropna().dt.strftime('%Y-%m-%d').unique()) if 'Trip Date' in df.columns else []
    else:
        vehicles, routes, available_dates = [], [], []

    def g(col): return filtered[col].sum() if col in filtered.columns else 0
    total_trips = len(filtered)
    ongoing = len(filtered[filtered.get('Trip Status','') == 'Pending Closure']) if 'Trip Status' in filtered.columns else 0
    closed = len(filtered[filtered.get('Trip Status','') == 'Completed']) if 'Trip Status' in filtered.columns else 0
    flags = len(filtered[filtered.get('Trip Status','') == 'Under Audit']) if 'Trip Status' in filtered.columns else 0
    resolved = len(filtered[(filtered.get('Trip Status','') == 'Under Audit') & (filtered.get('POD Status','') == 'Yes')]) if 'Trip Status' in filtered.columns and 'POD Status' in filtered.columns else 0

    rev = g('Freight Amount'); exp = g('Total Trip Expense'); profit = g('Net Profit'); kms = g('Actual Distance (KM)')
    rev_m, exp_m, profit_m = round(rev/1e6,2), round(exp/1e6,2), round(profit/1e6,2)
    kms_k = round(kms/1e3,1) if kms else 0
    per_km = round(profit/kms,2) if kms else 0
    profit_pct = round((profit/rev)*100,1) if rev else 0

    if not filtered.empty and 'Day' not in filtered.columns and 'Trip Date' in filtered.columns:
        filtered['Day'] = filtered['Trip Date'].dt.day
    daily = filtered.groupby('Day')['Trip ID'].count().reindex(range(1,32), fill_value=0).tolist() if 'Trip ID' in filtered.columns and 'Day' in filtered.columns else [0]*31
    audited = filtered[filtered.get('Trip Status','') == 'Under Audit'].groupby('Day')['Trip ID'].count().reindex(range(1,32), fill_value=0).tolist() if 'Trip ID' in filtered.columns and 'Day' in filtered.columns else [0]*31
    audit_pct = [round(a/b*100,1) if b else 0 for a,b in zip(audited, daily)]

    bar_labels = ['Revenue','Expense','Profit']
    columns = list(filtered.columns) if not filtered.empty else []
    rows = filtered.fillna('').to_dict('records') if not filtered.empty else []
    bar_values = [float(rev_m), float(exp_m), float(profit_m)]
    ai_report = generate_ai_report(filtered) if not filtered.empty else "Upload an Excel to see the report."

    context = dict(total_trips=total_trips, ongoing=ongoing, closed=closed, flags=flags,
                   columns=columns, rows=rows,
                   resolved=resolved, rev_m=rev_m, exp_m=exp_m, profit_m=profit_m, kms_k=kms_k,
                   per_km=per_km, profit_pct=profit_pct, ai_report=ai_report,
                   vehicles=vehicles, routes=routes, request=request, filtered=filtered.fillna(''),
                   daily=daily, audited=audited, audit_pct=audit_pct,
                   bar_labels=bar_labels, bar_values=bar_values, available_dates=available_dates)
    return render(request, 'fleet/dashboard.html', context)

# --- Simple in-memory users table like Flask demo ---
from werkzeug.security import generate_password_hash
USERS = [
    {'name': 'Anna Smith', 'email': 'anna.smith@example.com', 'role': 'Admin', 'password': generate_password_hash("password1"),
     'rights': {'view': True, 'edit': True, 'delete': True, 'add_fields': False}},
    {'name': 'John Doe', 'email': 'john.doe@example.com', 'role': 'Manager', 'password': generate_password_hash("password2"),
     'rights': {'view': True, 'edit': False, 'delete': False, 'add_fields': False}},
    {'name': 'Emily Johnson', 'email': 'emily.johnson@example.com', 'role': 'Viewer', 'password': generate_password_hash("password3"),
     'rights': {'view': True, 'edit': False, 'delete': False, 'add_fields': False}},
    {'name': 'Michael Brown', 'email': 'michael.brown@example.com', 'role': 'Trip Closer', 'password': generate_password_hash("password4"),
     'rights': {'view': True, 'edit': True, 'delete': True, 'add_fields': False}},
]

def user_settings(request):
    return render(request, 'fleet/user_settings.html', {'users': USERS})

def add_user(request):
    if request.method != 'POST':
        return redirect('user_settings')
    rights = {
        'view': 'view' in request.POST,
        'edit': 'edit' in request.POST,
        'delete': 'delete' in request.POST,
        'add_fields': 'add_fields' in request.POST
    }
    USERS.append({
        'name': request.POST.get('name'),
        'email': request.POST.get('email'),
        'password': generate_password_hash(request.POST.get('password')),
        'role': request.POST.get('role'),
        'rights': rights
    })
    return redirect('user_settings')

def update_rights(request):
    if request.method != 'POST':
        return redirect('user_settings')
    email = request.POST.get('email')
    for u in USERS:
        if u['email'] == email:
            u['rights'] = {
                'view': 'view' in request.POST,
                'edit': 'edit' in request.POST,
                'delete': 'delete' in request.POST,
                'add_fields': 'add_fields' in request.POST
            }
            break
    return redirect('user_settings')

# --- Trip Generator ---
def trip_generator(request):
    parsed_data = {}
    if request.method == 'POST':
        if request.FILES.get('pdf_file') and request.FILES['pdf_file'].name.endswith('.pdf'):
            upload_path = os.path.join(settings.MEDIA_ROOT, 'uploads', request.FILES['pdf_file'].name)
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)
            with open(upload_path, 'wb+') as dest:
                for chunk in request.FILES['pdf_file'].chunks():
                    dest.write(chunk)
            parsed_data = parse_pdf(upload_path)

        elif request.FILES.get('excel_file') and request.FILES['excel_file'].name.endswith('.xlsx'):
            upload_path = os.path.join(settings.MEDIA_ROOT, 'uploads', request.FILES['excel_file'].name)
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)
            with open(upload_path, 'wb+') as dest:
                for chunk in request.FILES['excel_file'].chunks():
                    dest.write(chunk)
            parsed_data = parse_excel(upload_path)
        else:
            fields = [
                'trip_id', 'trip_date', 'vehicle_id', 'driver_id', 'planned_distance',
                'advance_given', 'origin', 'destination', 'vehicle_type', 'flags', 'total_freight'
            ]
            data = {f: request.POST.get(f, '') for f in fields}
            try:
                data['total_freight'] = float(data.get('total_freight') or 0)
            except: data['total_freight'] = 0.0
            Trip.objects.create(**data)
            return redirect('trip_generator')

    generator_fields = [
        {'name':'trip_id','label':'Trip ID','type':'text','required':True},
        {'name':'trip_date','label':'Trip Date','type':'text','required':True},
        {'name':'vehicle_id','label':'Vehicle ID','type':'text','required':True},
        {'name':'driver_id','label':'Driver ID','type':'text','required':True},
        {'name':'planned_distance','label':'Planned Distance','type':'number','required':False},
        {'name':'advance_given','label':'Advance Given','type':'number','required':False},
        {'name':'origin','label':'Origin','type':'text','required':True},
        {'name':'destination','label':'Destination','type':'text','required':True},
        {'name':'vehicle_type','label':'Vehicle Type','type':'text','required':False},
        {'name':'flags','label':'Flags','type':'text','required':False},
        {'name':'total_freight','label':'Total Freight','type':'number','required':False},
    ]

    trip_count = Trip.objects.count()
    total_flags = Trip.objects.exclude(flags='').count()
    total_freight = Trip.objects.aggregate(s=Sum('total_freight'))['s'] or 0.0
    generator_headers = ['Trip ID','Date','Vehicle ID','Driver ID','Distance','Advance','Origin','Destination','Type','Flags','Freight']
    all_trips = Trip.objects.all().order_by('-id').values_list(
        'trip_id','trip_date','vehicle_id','driver_id','planned_distance','advance_given',
        'origin','destination','vehicle_type','flags','total_freight'
    )
    trip_columns = ['Trip ID','Date','Vehicle ID','Driver ID','Distance','Advance','Origin','Destination','Type','Flags','Freight']
    return render(request, 'fleet/trip_generator.html', { 'trip_columns': trip_columns,
        'generator_fields': generator_fields,
        'trip_count': trip_count, 'total_flags': total_flags, 'total_freight': total_freight,
        'parsed_data': parsed_data, 'all_trips': all_trips, 'generator_headers': generator_headers
    })

# --- Trip Closure ---
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
    trip_data = {}
    start_date = request.GET.get('start_date','')
    end_date = request.GET.get('end_date','')
    search_trip_id = (request.GET.get('search_trip_id') or '').strip()

    if request.method == 'POST':
        if request.FILES.get('excel_file'):
            f = request.FILES['excel_file']
            path = os.path.join(settings.MEDIA_ROOT, 'uploads', f.name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'wb+') as dest:
                for chunk in f.chunks():
                    dest.write(chunk)
            df = pd.read_excel(path, dtype=str)
            df.columns = df.columns.str.strip()
            conn = TripClosure.objects
            for _, row in df.iterrows():
                values = {'trip_id': row.get('Trip ID','')}
                for fld, label, _ in fields:
                    val = row.get(label, '')
                    if pd.isna(val) or val is None:
                        val = ''
                    values[fld] = val
                TripClosure.objects.update_or_create(trip_id=values['trip_id'], defaults=values)
            return redirect('trip_closure')
        else:
            trip_id = (request.POST.get('trip_id') or '').strip()
            if not trip_id:
                return HttpResponseBadRequest('Trip ID is required')
            values = {'trip_id': trip_id}
            for f, _, _ in fields:
                v = request.POST.get(f,'')
                try:
                    if f.endswith(('distance','quantity','rate','cost','charges','expense','amount','profit','fine')):
                        v = float(v) if v != '' else 0.0
                except: pass
                values[f] = v
            TripClosure.objects.update_or_create(trip_id=trip_id, defaults=values)
            return redirect('trip_closure')

    qs = TripClosure.objects.all()
    if start_date and end_date:
        qs = qs.filter(actual_delivery_date__gte=start_date, actual_delivery_date__lte=end_date)
    elif start_date:
        qs = qs.filter(actual_delivery_date__gte=start_date)
    elif end_date:
        qs = qs.filter(actual_delivery_date__lte=end_date)
    closure_field_names = [f[0] for f in fields]
    closures_qs = qs.values('trip_id', *closure_field_names)
    closures_rows = list(closures_qs)
    closures_columns = ['Trip ID'] + [label for _, label, _ in fields]
    if search_trip_id:
        try:
            obj = TripClosure.objects.get(trip_id=search_trip_id)
            trip_data = obj.__dict__
        except TripClosure.DoesNotExist:
            trip_data = {}

    total_closures = TripClosure.objects.count()
    sums = TripClosure.objects.aggregate(total_exp=Sum('total_trip_expense'), total_profit=Sum('net_profit'))
    total_expense = sums.get('total_exp') or 0.0
    total_profit = sums.get('total_profit') or 0.0

    return render(request, 'fleet/trip_closure.html', {
        'fields': fields, 'closures_columns': closures_columns, 'closures_rows': closures_rows, 'uploaded_range': '', 'trip_data': trip_data,
        'total_closures': total_closures, 'total_expense': total_expense, 'total_profit': total_profit,
        'start_date': start_date, 'end_date': end_date, 'closures_colspan': len(fields) + 1
    })

# --- Trip Audit ---
def load_data_for_audit():
    path = DATA_CLOSURE if os.path.exists(DATA_CLOSURE) else DATA_FLEET
    df = pd.read_excel(path)
    df.columns = df.columns.str.strip().str.lower()
    if 'trip date' in df.columns:
        df['trip date'] = pd.to_datetime(df['trip date'], errors='coerce')
        df['day'] = df['trip date'].dt.day
    return df

def trip_audit_dashboard(request):
    df = load_data_for_audit()
    filter_option = (request.GET.get('filter','all') or 'all').lower()
    filtered_df = df
    if 'trip status' in df.columns and 'pod status' in df.columns:
        if filter_option == 'open':
            filtered_df = df[df['trip status'].str.lower() == 'pending closure']
        elif filter_option == 'closed':
            filtered_df = df[df['trip status'].str.lower() == 'completed']
        elif filter_option == 'flag':
            filtered_df = df[df['trip status'].str.lower() == 'under audit']
    total_trips = len(df)
    opened = len(df[df.get('trip status','').str.lower() == 'pending closure']) if 'trip status' in df.columns else 0
    closed = len(df[df.get('trip status','').str.lower() == 'completed']) if 'trip status' in df.columns else 0
    audited = len(df[df.get('pod status','').str.lower() == 'yes']) if 'pod status' in df.columns else 0
    audit_closed = len(df[(df.get('trip status','').str.lower() == 'completed') & (df.get('pod status','').str.lower() == 'yes')]) if 'trip status' in df.columns and 'pod status' in df.columns else 0
    flags = len(df[df.get('trip status','').str.lower() == 'under audit']) if 'trip status' in df.columns else 0
    trip_data = filtered_df[['trip id']].dropna().to_dict('records') if 'trip id' in filtered_df.columns else []

    days = list(range(1,32))
    if 'trip id' in df.columns and 'day' in df.columns:
        closed_data = df[df.get('trip status','').str.lower() == 'completed'].groupby('day')['trip id'].count().reindex(days, fill_value=0).tolist()
        audited_data = df[df.get('pod status','').str.lower() == 'yes'].groupby('day')['trip id'].count().reindex(days, fill_value=0).tolist()
        audit_pct = [round((a/c)*100,1) if c else 0 for a,c in zip(audited_data, closed_data)]
    else:
        closed_data = [0]*31; audited_data=[0]*31; audit_pct=[0]*31

    return render(request, 'fleet/trip_audit_dashboard.html', {
        'total_trips': total_trips, 'opened': opened, 'closed': closed,
        'audited': audited, 'audit_closed': audit_closed, 'flags': flags,
        'trips': trip_data, 'filter_option': filter_option,
        'closed_data': json.dumps(closed_data), 'audited_data': json.dumps(audited_data),
        'audit_pct': json.dumps(audit_pct)
    })

def audit_trip(request, trip_id):
    df = load_data_for_audit()
    if 'trip id' not in df.columns:
        return HttpResponse('Trip not found', status=404)
    trip_row = df[df['trip id'].astype(str) == str(trip_id)]
    if trip_row.empty:
        return HttpResponse('Trip not found', status=404)
    trip_data = trip_row.iloc[0].to_dict()
    if request.method == 'POST':
        for k in list(trip_data.keys()):
            if k in request.POST:
                trip_data[k] = request.POST[k]
        df.loc[df['trip id'].astype(str) == str(trip_id), list(trip_data.keys())] = list(trip_data.values())
        df.to_excel(DATA_CLOSURE if os.path.exists(DATA_CLOSURE) else DATA_FLEET, index=False)
        content = "Trip Audit Details\n\n" + "\n".join([f"{k.title()}: {v}" for k,v in trip_data.items()])
        resp = HttpResponse(content, content_type='text/plain')
        resp['Content-Disposition'] = f'attachment; filename=trip_{trip_id}_audit.txt'
        return resp
    return render(request, 'fleet/audit_trip.html', {'trip_id': trip_id, 'trip_data': trip_data})

# Download AI summary
def download_summary(request):
    path = DATA_FLEET if os.path.exists(DATA_FLEET) else None
    df = load_excel(path) if path else pd.DataFrame()
    report = generate_ai_report(df) if not df.empty else "No data"
    resp = HttpResponse(report, content_type='text/plain')
    resp['Content-Disposition'] = 'attachment; filename=AI_Report_Summary.txt'
    return resp

# Financial dashboard
@ensure_csrf_cookie
def financial_dashboard(request):
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(upload_dir, exist_ok=True)
    if request.method == 'POST' and request.FILES.get('file'):
        f = request.FILES['file']
        path = os.path.join(upload_dir, f.name)
        with open(path, 'wb+') as dest:
            for chunk in f.chunks(): dest.write(chunk)
        file_to_use = path
    else:
        file_to_use = DATA_CLOSURE if os.path.exists(DATA_CLOSURE) else DATA_FLEET
    df = load_excel(file_to_use)
    if df.empty:
        days = []; revenue=[]; expense=[]; profit=[]; total_revenue=0; total_profit=0; total_km=0
    else:
        recent_days = sorted(df['Day'].dropna().unique())[-10:] if 'Day' in df.columns else []
        day_labels = [f"Day {{int(d)}}" for d in recent_days]
        daily = df[df['Day'].isin(recent_days)] if recent_days else df
        revenue = daily.groupby('Day')['Freight Amount'].sum().reindex(recent_days, fill_value=0).astype(int).tolist() if 'Freight Amount' in df.columns and recent_days else []
        expense = daily.groupby('Day')['Total Trip Expense'].sum().reindex(recent_days, fill_value=0).astype(int).tolist() if 'Total Trip Expense' in df.columns and recent_days else []
        profit = [r-e for r,e in zip(revenue, expense)] if revenue and expense else []
        total_revenue = round(df.get('Freight Amount', pd.Series(0)).sum()/1e6,2)
        total_profit = round(df.get('Net Profit', pd.Series(0)).sum()/1e6,2)
        total_km = round(df.get('Actual Distance (KM)', pd.Series(0)).sum()/1e3,1)
        days = [f"Day {{int(d)}}" for d in recent_days]
    context = dict(days=json.dumps(days), revenue=json.dumps(revenue), expense=json.dumps(expense),
                   profit=json.dumps(profit), total_revenue=total_revenue, total_profit=total_profit, total_km=total_km)
    return render(request, 'fleet/financial_dashboard.html', context)
