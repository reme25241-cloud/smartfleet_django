from flask import Flask, request, render_template_string, send_file, redirect, url_for

from werkzeug.security import generate_password_hash
from flask import Flask, request, render_template_string, redirect, url_for
from flask import Flask, render_template_string, request, redirect, url_for, Response
import sqlite3
import fitz  # PyMuPDF
import os
import pandas as pd
import json
from flask import Flask, render_template_string, request, redirect, url_for, session, send_file
import os
import sqlite3
import fitz  # PyMuPDF
import pandas as pd
import time
import pandas as pd
from datetime import date
from flask import Flask, request, jsonify
from markupsafe import Markup
import sqlite3



# ✅ Create trip_closure table
def init_db():
    conn = sqlite3.connect('trips.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS trips (
            trip_id TEXT,
            trip_date TEXT,
            vehicle_id TEXT,
            driver_id TEXT,
            planned_distance REAL,
            advance_given REAL,
            origin TEXT,
            destination TEXT,
            vehicle_type TEXT,
            flags TEXT,
            total_freight REAL
        )
    ''')
    c.execute('DROP TABLE IF EXISTS trip_closure')
    c.execute('''
            CREATE TABLE IF NOT EXISTS trip_closure (
            trip_id TEXT PRIMARY KEY,
            actual_distance REAL,
            actual_delivery_date TEXT,
            trip_delay_reason TEXT,
            fuel_quantity REAL,
            fuel_rate REAL,
            fuel_cost REAL,
            toll_charges REAL,
            food_expense REAL,
            lodging_expense REAL,
            miscellaneous_expense REAL,
            maintenance_cost REAL,
            loading_charges REAL,
            unloading_charges REAL,
            penalty_fine REAL,
            total_trip_expense REAL,
            freight_amount REAL,
            incentives REAL,
            net_profit REAL,
            payment_mode TEXT,
            pod_status TEXT,
            trip_status TEXT,
            remarks TEXT
        )''')
    conn.commit()
    conn.close()


app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)



UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}


# Global file trackers
uploaded_file = None
uploaded_trip_stats_file = None   # ✅ separate tracker if needed
DEFAULT_FILE = os.path.join(app.config['UPLOAD_FOLDER'], "Trip_Closure_Sheet_Oct2024_Mar2025.xlsx")


# ✅ Allowed users
ALLOWED_USERS = {
    "travels123@gmail.com": {
        "password": "travel1",
        "fullname": "travel",
        "phone": "1234567890"
    }
}

# ================== HTML FORMS ==================
HTML_SIGNUP_FORM = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Smart Fleet Ai - Sign Up</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-[#0B132B] flex flex-col items-center justify-center h-screen text-white font-sans">
  <div class="text-center mb-4">
    <h1 class="text-4xl font-bold">Smart Fleet Ai</h1>
    <p class="text-gray-400 mt-2">Powered by Ai Data Portal</p>
  </div>
  <form method="POST" action="/signup" class="bg-[#0E1A36] p-8 rounded-xl w-full max-w-sm shadow-md space-y-4">
    <input type="text" name="fullname" placeholder="Full Name" required class="w-full bg-[#1C2541] text-white placeholder-gray-400 p-3 rounded-md outline-none" />
    <input type="email" name="email" placeholder="Email" required class="w-full bg-[#1C2541] text-white placeholder-gray-400 p-3 rounded-md outline-none" />
    <input type="text" name="phone" placeholder="Phone Number" required class="w-full bg-[#1C2541] text-white placeholder-gray-400 p-3 rounded-md outline-none" />
    <input type="password" name="password" placeholder="Password" required class="w-full bg-[#1C2541] text-white placeholder-gray-400 p-3 rounded-md outline-none" />
    <input type="password" name="confirm_password" placeholder="Confirm Password" required class="w-full bg-[#1C2541] text-white placeholder-gray-400 p-3 rounded-md outline-none" />
    <button type="submit" class="w-full bg-white text-[#0B132B] font-semibold py-2 rounded-md hover:bg-gray-200 transition duration-200">
      Sign Up
    </button>
    <p class="text-gray-400 text-sm text-center">Already registered? <a href="/login" class="text-blue-400">Login</a></p>
  </form>
</body>
</html>
"""

HTML_LOGIN_FORM = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Smart Fleet Ai - Login</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-[#0B132B] flex flex-col items-center justify-center h-screen text-white font-sans">
  <div class="text-center mb-4">
    <h1 class="text-4xl font-bold">Smart Fleet Ai</h1>
    <p class="text-gray-400 mt-2">Login to your account</p>
  </div>
  <form method="POST" action="/login" class="bg-[#0E1A36] p-8 rounded-xl w-full max-w-sm shadow-md space-y-4">
    <input type="email" name="email" placeholder="Email" required class="w-full bg-[#1C2541] text-white placeholder-gray-400 p-3 rounded-md outline-none" />
    <input type="password" name="password" placeholder="Password" required class="w-full bg-[#1C2541] text-white placeholder-gray-400 p-3 rounded-md outline-none" />
    <button type="submit" class="w-full bg-white text-[#0B132B] font-semibold py-2 rounded-md hover:bg-gray-200 transition duration-200">
      Login
    </button>
    <p class="text-gray-400 text-sm text-center mt-3">
      <a href="/change-password" class="text-blue-400">Forgot / Change Password?</a>
    </p>
  </form>
</body>
</html>
"""

# ================== ROUTES ==================
@app.route('/')
def index():
    return redirect(url_for('signup'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        fullname = request.form.get("fullname")
        email = request.form.get("email")
        phone = request.form.get("phone")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if email not in ALLOWED_USERS:
            return "❌ This email is not allowed to register."

        if password != confirm_password:
            return "❌ Passwords do not match!"

        with open("users.txt", "w") as f:
            f.write(f"{email},{password},{fullname},{phone}\n")

        return "✅ Registration successful! <a href='/login'>Click here to login</a>"

    return render_template_string(HTML_SIGNUP_FORM)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get("email")
        password = request.form.get("password")

        allowed = ALLOWED_USERS.get(email)
        if allowed and allowed['password'] == password:
            session['user_email'] = email
            session['user_name'] = allowed['fullname']
            return redirect('/welcome-dashboard')

        return "<h3>❌ Invalid credentials or access not allowed. <a href='/login'>Try again</a></h3>"

    return render_template_string(HTML_LOGIN_FORM)

@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    if request.method == 'POST':
        email = request.form.get("email")
        old_password = request.form.get("old_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        user = ALLOWED_USERS.get(email)
        if not user or user['password'] != old_password:
            return "<h3>❌ Incorrect email or old password. <a href='/change-password'>Try again</a></h3>"

        if new_password != confirm_password:
            return "<h3>❌ New passwords do not match. <a href='/change-password'>Try again</a></h3>"

        # Update password and log user in
        user['password'] = new_password
        session['user_email'] = email
        session['user_name'] = user['fullname']
        return redirect('/welcome-dashboard')

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
      <title>Change Password</title>
      <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-[#0B132B] flex flex-col items-center justify-center h-screen text-white font-sans">
      <div class="text-center mb-4">
        <h1 class="text-3xl font-bold">Change Password</h1>
      </div>
      <form method="POST" action="/change-password" class="bg-[#0E1A36] p-8 rounded-xl w-full max-w-sm shadow-md space-y-4">
        <input type="email" name="email" placeholder="Email" required class="w-full bg-[#1C2541] p-3 rounded-md outline-none text-white" />
        <input type="password" name="old_password" placeholder="Old Password" required class="w-full bg-[#1C2541] p-3 rounded-md outline-none text-white" />
        <input type="password" name="new_password" placeholder="New Password" required class="w-full bg-[#1C2541] p-3 rounded-md outline-none text-white" />
        <input type="password" name="confirm_password" placeholder="Confirm New Password" required class="w-full bg-[#1C2541] p-3 rounded-md outline-none text-white" />
        <button type="submit" class="w-full bg-white text-[#0B132B] font-semibold py-2 rounded-md hover:bg-gray-200">
          Update Password
        </button>
      </form>
    </body>
    </html>
    """)

@app.route('/welcome-dashboard')
def welcome_dashboard():
    if 'user_name' in session:
        name = session['user_name']
        return render_template_string(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Welcome Dashboard</title>
            <script src="https://cdn.tailwindcss.com"></script>
            <style>
                body {{ background-color: #0B132B; color: white; font-family: sans-serif; padding: 2em; }}
                .greeting {{ font-size: 2em; font-weight: bold; color: #00FFC6; }}
                ul {{ line-height: 1.8em; }}
            </style>
        </head>
        <body>
            <div class="greeting">👋 Hello, {name}!</div>
            <p class="mt-4 text-lg">Welcome to your <strong>Smart Fleet Ai Dashboard</strong> 🚛</p>

            <ul class="mt-6">
                <li>📊 <strong>View Trip Reports</strong></li>
                <li>📁 <strong>Upload Files</strong></li>
                <li>🧮 <strong>Financial Analytics</strong></li>
                <li>🚀 <strong>Trip Statistics</strong></li>
                <li>🛠️ <strong>Trip Generator</strong></li>
                <li>✅ <strong>Trip Closure</strong></li>
                <li>🔍 <strong>Trip Audit</strong></li>
            </ul>

            <!-- New button to go to Fleet Dashboard -->
            <div class="mt-8">
                <a href="/fleet-dashboard" 
                   class="bg-[#00FFC6] text-[#0B132B] px-6 py-3 rounded-lg font-semibold hover:bg-[#02d9aa] transition">
                   🚚 Go to Fleet Dashboard
                </a>
            </div>

            <div class="mt-6">
                <a href="/logout" class="text-red-400 hover:underline">🔒 Logout</a>
            </div>
        </body>
        </html>
        """)
    return redirect('/login')
# ✅ Fleet Dashboard route alias
@app.route('/fleet-dashboard')
def fleet_dashboard():
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

DEFAULT_FILE = 'fleet_50_entries.xlsx'
uploaded_file_path = None
uploaded_trip_stats_file = None

def load_excel(file_path):
    df = pd.read_excel(file_path)
    df.columns = df.columns.str.strip()
    df['Trip Date'] = pd.to_datetime(df['Trip Date'], errors='coerce')
    df['Day'] = df['Trip Date'].dt.day
    return df

df = load_excel(DEFAULT_FILE)

def generate_ai_report(filtered_df):
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
📊 AI Report Highlights:

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

@app.route('/dashboard',  methods=["GET", "POST"])

def dashboard():
    global df

    # Upload Excel
    if request.method == 'POST':
        if 'excel' in request.files:
            f = request.files['excel']
            path = os.path.join(app.config['UPLOAD_FOLDER'], f.filename)
            f.save(path)
            df = load_excel(path)

    vehicle = request.args.get('vehicle')
    route = request.args.get('route')
    start = request.args.get('start')
    end = request.args.get('end')

    filtered = df.copy()
    if vehicle:
        filtered = filtered[filtered['Vehicle ID'] == vehicle]
    if route:
        filtered = filtered[filtered['Route'] == route]
    if start and end:
        start_date = pd.to_datetime(start)
        end_date = pd.to_datetime(end)
        filtered = filtered[(filtered['Trip Date'] >= start_date) & (filtered['Trip Date'] <= end_date)]

    vehicles = sorted(df['Vehicle ID'].dropna().unique())
    routes = sorted(df['Route'].dropna().unique()) if 'Route' in df.columns else []
    available_dates = sorted(df['Trip Date'].dropna().dt.strftime('%Y-%m-%d').unique())

    total_trips = len(filtered)
    ongoing = filtered[filtered['Trip Status'] == 'Pending Closure'].shape[0]
    closed = filtered[filtered['Trip Status'] == 'Completed'].shape[0]
    flags = filtered[filtered['Trip Status'] == 'Under Audit'].shape[0]
    resolved = filtered[(filtered['Trip Status'] == 'Under Audit') & (filtered['POD Status'] == 'Yes')].shape[0]

    rev = filtered['Freight Amount'].sum()
    exp = filtered['Total Trip Expense'].sum()
    profit = filtered['Net Profit'].sum()
    kms = filtered['Actual Distance (KM)'].sum()

    rev_m = round(rev / 1e6, 2)
    exp_m = round(exp / 1e6, 2)
    profit_m = round(profit / 1e6, 2)
    kms_k = round(kms / 1e3, 1)
    per_km = round(profit / kms, 2) if kms else 0
    profit_pct = round((profit / rev) * 100, 1) if rev else 0

    daily = filtered.groupby('Day')['Trip ID'].count().reindex(range(1, 32), fill_value=0).tolist()
    audited = filtered[filtered['Trip Status'] == 'Under Audit'].groupby('Day')['Trip ID'].count().reindex(range(1, 32), fill_value=0).tolist()
    audit_pct = [round(a / b * 100, 1) if b else 0 for a, b in zip(audited, daily)]

    bar_labels = ['Revenue', 'Expense', 'Profit']
    bar_values = [float(rev_m), float(exp_m), float(profit_m)]

    ai_report = generate_ai_report(filtered)

    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Fleet Dashboard</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body class="bg-[#0B132B] text-white p-6 font-sans">

  <!-- ✅ Navigation Bar -->
  <nav class="bg-[#1C2541] p-4 rounded flex justify-between items-center mb-6">
    <div class="flex gap-4 text-sm sm:text-base">
      <a href="/user-settings" class="text-white hover:underline">User Settings</a>
      <a href="/trip-generator" class="text-white hover:underline">Trip Generator</a>
      <a href="/trip-closure" class="text-white hover:underline">Trip Closure</a>
      <a href="/trip-audit" class="text-white hover:underline">Trip Audit</a>
      <a href="/trip-statistics" class="text-white hover:underline">Trip Statistics</a>
      <a href="/financial-dashboard" class="text-white hover:underline">Financial Dashboard</a>
    </div>
    <div>
      <a href="/logout" class="bg-red-600 px-3 py-1 rounded hover:bg-red-700">Logout</a>
    </div>
  </nav>

  <h1 class="text-3xl font-bold mb-6">Fleet Dashboard</h1>

  <div class="mb-6">
  <h2 class="text-lg font-semibold mb-2">Upload Excel File</h2>

  <form id="upload-form" method="post" enctype="multipart/form-data">
    <div id="drop-area" class="border-2 border-dashed border-gray-400 p-6 rounded bg-white text-black text-center cursor-pointer hover:bg-gray-100">
      <p class="text-gray-700">Drag & Drop your Excel file here or click to upload</p>
      <input type="file" id="fileElem" name="excel" class="hidden" accept=".xlsx,.xls">
    </div>
  </form>

  <div id="upload-status" class="mt-2 text-sm text-green-400"></div>
</div>

<script>
  const dropArea = document.getElementById('drop-area');
  const fileElem = document.getElementById('fileElem');
  const uploadForm = document.getElementById('upload-form');
  const statusDiv = document.getElementById('upload-status');

  dropArea.addEventListener('click', () => fileElem.click());

  ['dragenter', 'dragover'].forEach(eventName => {
    dropArea.addEventListener(eventName, e => {
      e.preventDefault();
      dropArea.classList.add('bg-gray-200');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, e => {
      e.preventDefault();
      dropArea.classList.remove('bg-gray-200');
    });
  });

  dropArea.addEventListener('drop', e => {
    const file = e.dataTransfer.files[0];
    uploadFile(file);
  });

  fileElem.addEventListener('change', () => {
    const file = fileElem.files[0];
    uploadFile(file);
  });

  function uploadFile(file) {
    if (!file) return;
    const formData = new FormData();
    formData.append('excel', file);
    

    fetch('/dashboard', {
      method: 'POST',
      body: formData
    })
    .then(response => {
      if (response.ok) {
        statusDiv.textContent = '✅ File uploaded successfully! Refreshing...';
        setTimeout(() => window.location.reload(), 1500);
      } else {
        statusDiv.textContent = '❌ Upload failed!';
      }
    })
    .catch(err => {
      statusDiv.textContent = '❌ Upload error!';
      console.error(err);
    });
  }
</script>

  <form method="get" class="flex flex-wrap gap-4 mb-6">
    <select name="vehicle" class="text-black p-2 rounded">
      <option value="">All Vehicles</option>
      {% for v in vehicles %}
        <option value="{{v}}" {% if v == request.args.get('vehicle') %}selected{% endif %}>{{v}}</option>
      {% endfor %}
    </select>
    <select name="route" class="text-black p-2 rounded">
      <option value="">All Routes</option>
      {% for r in routes %}
        <option value="{{r}}" {% if r == request.args.get('route') %}selected{% endif %}>{{r}}</option>
      {% endfor %}
    </select>
    <input type="date" name="start" class="text-black p-2 rounded" value="{{ request.args.get('start') }}">
    <input type="date" name="end" class="text-black p-2 rounded" value="{{ request.args.get('end') }}">
    <button class="bg-green-600 px-4 py-2 rounded">Apply Filters</button>
  </form>

  <div class="grid grid-cols-3 gap-4 mb-6">
    <div class="bg-[#1C2541] p-4 rounded">
      <p>Total Trips: <b>{{ total_trips }}</b></p>
      <p>Ongoing: <b>{{ ongoing }}</b></p>
      <p>Closed: <b>{{ closed }}</b></p>
      <p>Flags: <b>{{ flags }}</b></p>
      <p>Resolved: <b>{{ resolved }}</b></p>
    </div>
    <div class="bg-[#1C2541] p-4 rounded">
      <p class="font-bold mb-2 text-lg">Financial Summary</p>
      <p>Revenue: ₹{{ rev_m }}M</p>
      <p>Expense: ₹{{ exp_m }}M</p>
      <p>Profit: ₹{{ profit_m }}M</p>
      <p>KMs: {{ kms_k }}K</p>
      <p>Per KM: ₹{{ per_km }}</p>
      <p>Profit %: {{ profit_pct }}%</p>
    </div>
    <div class="bg-[#1C2541] p-4 rounded">
      <p class="font-bold mb-2">AI Report</p>
      <pre class="text-sm text-gray-300">{{ ai_report }}</pre>
      <a href="/download-summary" class="mt-2 inline-block bg-green-600 px-3 py-1 rounded hover:bg-green-700">Download Summary</a>
    </div>
  </div>

  <div class="grid grid-cols-2 gap-4 mb-8">
    <div class="bg-[#1C2541] p-4 rounded">
      <h2 class="mb-2 font-semibold text-lg">Daily Trips vs Audits</h2>
      <canvas id="auditChart" height="120"></canvas>
    </div>
    <div class="bg-[#1C2541] p-4 rounded">
      <h2 class="mb-2 font-semibold text-lg">Finance Chart</h2>
      <canvas id="financeChart" height="120"></canvas>
    </div>
  </div>

  <div class="bg-[#1C2541] p-4 rounded mb-6 overflow-auto max-h-[400px]">
    <h2 class="font-semibold text-lg mb-2">Trip Records (Filtered)</h2>
    <table class="w-full text-sm text-left">
      <tr class="text-yellow-300 font-semibold">
        {% for col in filtered.columns %}
        <th class="px-2 py-1 border-b border-gray-500">{{ col }}</th>
        {% endfor %}
      </tr>
      {% for row in filtered.itertuples() %}
      <tr class="hover:bg-gray-700">
        {% for val in row[1:] %}
        <td class="px-2 py-1 border-b border-gray-600">{{ val }}</td>
        {% endfor %}
      </tr>
      {% endfor %}
    </table>
  </div>

  <script>
    new Chart(document.getElementById('auditChart').getContext('2d'), {
      data: {
        labels: Array.from({length: 31}, (_, i) => i + 1),
        datasets: [
          {type: 'bar', label: 'Closed', data: {{ daily | safe }}, backgroundColor: '#4CAF50'},
          {type: 'bar', label: 'Audited', data: {{ audited | safe }}, backgroundColor: '#2196F3'},
          {type: 'line', label: 'Audit %', data: {{ audit_pct | safe }}, yAxisID: 'y1', borderColor: 'yellow', fill: false}
        ]
      },
      options: {
        responsive: true,
        scales: {
          y: {beginAtZero: true, ticks: {color: 'white'}, grid: {color: '#444'}},
          y1: {beginAtZero: true, position: 'right', ticks: {color: 'white'}, grid: {drawOnChartArea: false}},
          x: {ticks: {color: 'white'}, grid: {color: '#444'}}
        },
        plugins: {legend: {labels: {color: 'white'}}}
      }
    });

    new Chart(document.getElementById('financeChart').getContext('2d'), {
      type: 'bar',
      data: {
        labels: {{ bar_labels | safe }},
        datasets: [{
          label: '₹ in Millions',
          data: {{ bar_values | safe }},
          backgroundColor: ['#FFA500', '#FF4444', '#44FF44']
        }]
      },
      options: {
        plugins: {legend: {labels: {color: 'white'}}},
        scales: {
          y: {beginAtZero: true, ticks: {color: 'white'}},
          x: {ticks: {color: 'white'}}
        }
      }
    });
  </script>

</body>
</html>
''', total_trips=total_trips, ongoing=ongoing, closed=closed, flags=flags,
    resolved=resolved, rev_m=rev_m, exp_m=exp_m, profit_m=profit_m, kms_k=kms_k,
    per_km=per_km, profit_pct=profit_pct, ai_report=ai_report,
    vehicles=vehicles, routes=routes, request=request, filtered=filtered,
    daily=daily, audited=audited, audit_pct=audit_pct,
    bar_labels=bar_labels, bar_values=bar_values, available_dates=available_dates)

@app.route('/download-summary')
def download_summary():
    report = generate_ai_report(df)
    with open("AI_Report_Summary.txt", 'w', encoding='utf-8') as f:
        f.write(report)
    return send_file("AI_Report_Summary.txt", as_attachment=True)



    





users = [
    {'name': 'Anna Smith', 'email': 'anna.smith@example.com', 'role': 'Admin', 'password': generate_password_hash("password1"),
     'rights': {'view': True, 'edit': True, 'delete': True, 'add_fields': False}},
    {'name': 'John Doe', 'email': 'john.doe@example.com', 'role': 'Manager', 'password': generate_password_hash("password2"),
     'rights': {'view': True, 'edit': False, 'delete': False, 'add_fields': False}},
    {'name': 'Emily Johnson', 'email': 'emily.johnson@example.com', 'role': 'Viewer', 'password': generate_password_hash("password3"),
     'rights': {'view': True, 'edit': False, 'delete': False, 'add_fields': False}},
    {'name': 'Michael Brown', 'email': 'michael.brown@example.com', 'role': 'Trip Closer', 'password': generate_password_hash("password4"),
     'rights': {'view': True, 'edit': True, 'delete': True, 'add_fields': False}},
]

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Fleet Owner User Settings</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-[#0B132B] text-white font-sans p-6">
  <h1 class="text-2xl font-bold mb-4">Fleet Owner User Settings</h1>

  <!-- Navigation -->
  <div class="flex space-x-6 border-b border-gray-600 pb-2 mb-6 text-sm">
    <button class="text-gray-300 hover:text-white">Dashboard</button>
    <button class="text-gray-300 hover:text-white">Trip Generator</button>
    <button class="text-gray-300 hover:text-white">Trip Closer</button>
    <button class="text-gray-300 hover:text-white">Trip Auditor</button>
    <button class="text-white border-b-2 border-white pb-1">AI Module</button>
  </div>

  <!-- User Table -->
  <div class="grid grid-cols-3 gap-6 mb-8">
    <div class="col-span-2">
      <h2 class="text-lg font-semibold mb-2">User Credentials Table</h2>
      <div class="bg-[#1C2541] p-4 rounded-lg overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="text-left text-gray-400 border-b border-gray-600">
            <tr>
              <th class="pb-2">Name</th>
              <th class="pb-2">Email</th>
              <th class="pb-2">Role</th>
              <th class="pb-2">Rights</th>
            </tr>
          </thead>
          <tbody class="text-white">
            {% for user in users %}
            <tr class="border-b border-gray-700">
              <td class="py-2">{{ user.name }}</td>
              <td>{{ user.email }}</td>
              <td>{{ user.role }}</td>
              <td>
                <form action="/update_rights" method="POST" class="flex flex-wrap items-center gap-2">
                  <input type="hidden" name="email" value="{{ user.email }}">
                  <label><input type="checkbox" name="view" {% if user.rights.view %}checked{% endif %}> View</label>
                  <label><input type="checkbox" name="edit" {% if user.rights.edit %}checked{% endif %}> Edit</label>
                  <label><input type="checkbox" name="delete" {% if user.rights.delete %}checked{% endif %}> Delete</label>
                  <label><input type="checkbox" name="add_fields" {% if user.rights.add_fields %}checked{% endif %}> Add Fields</label>
                  <button type="submit" class="bg-gray-600 px-2 py-1 rounded hover:bg-gray-500 text-sm">Save</button>
                </form>
              </td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>

    <!-- Add New User -->
    <div>
      <h2 class="text-lg font-semibold mb-2">User Credentials</h2>
      <div class="bg-[#1C2541] p-4 rounded-lg">
        <form action="/add_user" method="POST">
          <input type="text" name="name" placeholder="Name" class="w-full bg-[#0E1A36] p-2 rounded text-white placeholder-gray-400 outline-none mb-2" required>
          <input type="email" name="email" placeholder="Email" class="w-full bg-[#0E1A36] p-2 rounded text-white placeholder-gray-400 outline-none mb-2" required>
          <input type="password" name="password" placeholder="Password" class="w-full bg-[#0E1A36] p-2 rounded text-white placeholder-gray-400 outline-none mb-2" required>
          <input type="text" name="role" placeholder="Role" class="w-full bg-[#0E1A36] p-2 rounded text-white placeholder-gray-400 outline-none mb-2" required>

          <div class="space-y-2 text-sm mb-4">
            <div><input type="checkbox" name="view" class="mr-2">View</div>
            <div><input type="checkbox" name="edit" class="mr-2">Edit</div>
            <div><input type="checkbox" name="delete" class="mr-2">Delete</div>
            <div><input type="checkbox" name="add_fields" class="mr-2">Add Fields</div>
          </div>

          <button type="submit" class="bg-blue-600 px-4 py-2 rounded hover:bg-blue-500">Save Credentials</button>
        </form>
      </div>
    </div>
  </div>
</body>
</html>
'''

@app.route('/user-settings')
def user_settings():

    return render_template_string(HTML_TEMPLATE, users=users)

@app.route('/add_user', methods=['POST'])
def add_user():
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role')
    rights = {
        'view': 'view' in request.form,
        'edit': 'edit' in request.form,
        'delete': 'delete' in request.form,
        'add_fields': 'add_fields' in request.form
    }
    hashed_password = generate_password_hash(password)
    users.append({'name': name, 'email': email, 'role': role, 'password': hashed_password, 'rights': rights})
    return redirect(url_for('user_settings'))

@app.route('/update_rights', methods=['POST'])
def update_rights():
    email = request.form.get('email')
    for user in users:
        if user['email'] == email:
            user['rights'] = {
                'view': 'view' in request.form,
                'edit': 'edit' in request.form,
                'delete': 'delete' in request.form,
                'add_fields': 'add_fields' in request.form
            }
            break
    return redirect(url_for('user_settings'))  # ✅ Correct route name here

    
# === PDF Parser ===
def parse_pdf(filepath):
    doc = fitz.open(filepath)
    text = ""
    for page in doc:
        text += page.get_text()

    result = {}
    for field in [
        'trip_id', 'trip_date', 'vehicle_id', 'driver_id', 'planned_distance',
        'advance_given', 'origin', 'destination', 'vehicle_type', 'flags', 'total_freight'
    ]:
        for line in text.splitlines():
            if field.replace("_", " ").lower() in line.lower():
                try:
                    value = line.split(":")[1].strip()
                except:
                    value = ""
                result[field] = value
                break
        else:
            result[field] = ""
    try:
        result['total_freight'] = float(result.get('total_freight', 0) or 0)
    except:
        result['total_freight'] = 0.0
    return result

# === Excel Parser ===
def parse_excel(filepath):
    try:
        df = pd.read_excel(filepath)
        row = df.iloc[0]
        return {
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
        }
    except Exception as e:
        print("Excel parsing error:", e)
        return {}

# === Trip Generator Page ===
@app.route('/trip-generator', methods=['GET', 'POST'])
def trip_generator():
    parsed_data = {}
    if request.method == 'POST':
        if 'pdf_file' in request.files and request.files['pdf_file'].filename.endswith('.pdf'):
            pdf_file = request.files['pdf_file']
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], pdf_file.filename)
            pdf_file.save(filepath)
            parsed_data = parse_pdf(filepath)

        elif 'excel_file' in request.files and request.files['excel_file'].filename.endswith('.xlsx'):
            excel_file = request.files['excel_file']
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], excel_file.filename)
            excel_file.save(filepath)
            parsed_data = parse_excel(filepath)

        else:
            fields = [
                'trip_id', 'trip_date', 'vehicle_id', 'driver_id', 'planned_distance',
                'advance_given', 'origin', 'destination', 'vehicle_type', 'flags', 'total_freight'
            ]
            data = []
            for f in fields:
                val = request.form.get(f, '')
                if f == 'total_freight':
                    try:
                        val = float(val)
                    except:
                        val = 0.0
                data.append(val)
            conn = sqlite3.connect('trips.db')
            c = conn.cursor()
            c.execute(f"INSERT INTO trips ({','.join(fields)}) VALUES (?,?,?,?,?,?,?,?,?,?,?)", data)
            conn.commit()
            conn.close()
            return redirect(url_for('trip_generator'))

    # Dashboard data
    conn = sqlite3.connect('trips.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM trips")
    trip_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM trips WHERE flags IS NOT NULL AND flags != ''")
    total_flags = c.fetchone()[0]
    c.execute("SELECT SUM(total_freight) FROM trips")
    total_freight = c.fetchone()[0] or 0.0
    c.execute("SELECT * FROM trips ORDER BY rowid DESC")
    all_trips = c.fetchall()
    conn.close()

    html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8"/>
      <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
      <title>Trip Generator</title>
      <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 text-white font-sans p-6">
      <div class="max-w-7xl mx-auto bg-[#0B132B] p-6 rounded-lg shadow-lg">
        <h1 class="text-2xl font-semibold mb-6">Trip Generator</h1>

        <div class="grid grid-cols-3 gap-6 mb-6 text-center">
          <div class="bg-[#1C2541] p-4 rounded-lg">
            <p class="text-3xl font-bold">{{ trip_count }}</p>
            <p class="text-gray-400">Total Trips Generated</p>
          </div>
          <div class="bg-[#1C2541] p-4 rounded-lg">
            <p class="text-3xl font-bold">{{ total_flags }}</p>
            <p class="text-gray-400">Flags</p>
          </div>
          <div class="bg-[#1C2541] p-4 rounded-lg">
            <p class="text-3xl font-bold">₹{{ '{:,.2f}'.format(total_freight) }}</p>
            <p class="text-gray-400">Total Freight</p>
          </div>
        </div>


        <form method="POST" class="bg-[#3A506B] p-6 rounded-lg grid grid-cols-2 gap-4">
          {% for field in [
            'trip_id', 'trip_date', 'vehicle_id', 'driver_id', 'planned_distance',
            'advance_given', 'origin', 'destination', 'vehicle_type', 'flags', 'total_freight'
          ] %}
            <div>
              <label class="block text-sm text-gray-200 capitalize">{{ field.replace('_', ' ') }}</label>
              <input name="{{ field }}" value="{{ parsed_data.get(field, '') }}" class="w-full px-3 py-2 rounded bg-gray-200 text-black" {% if field != 'total_freight' %}required{% endif %} type="{{ 'number' if field=='total_freight' else 'text' }}">
            </div>
          {% endfor %}
          <button type="submit" class="mt-6 bg-[#1C2541] hover:bg-[#3A506B] px-4 py-2 rounded text-white col-span-2">Submit</button>
        </form>

        <h2 class="text-xl font-semibold mt-10 mb-4">Trip Generated Details</h2>
        <div class="overflow-x-auto">
          <table class="min-w-full bg-white text-black rounded shadow overflow-hidden">
            <thead class="bg-[#3A506B] text-white">
              <tr>
                <th class="px-2 py-2">Trip ID</th>
                <th class="px-2 py-2">Date</th>
                <th class="px-2 py-2">Vehicle ID</th>
                <th class="px-2 py-2">Driver ID</th>
                <th class="px-2 py-2">Distance</th>
                <th class="px-2 py-2">Advance</th>
                <th class="px-2 py-2">Origin</th>
                <th class="px-2 py-2">Destination</th>
                <th class="px-2 py-2">Type</th>
                <th class="px-2 py-2">Flags</th>
                <th class="px-2 py-2">Freight</th>
              </tr>
            </thead>
            <tbody>
              {% for trip in all_trips %}
              <tr class="border-t">
                {% for item in trip %}
                <td class="px-2 py-1">{{ item }}</td>
                {% endfor %}
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </body>
    </html>
    '''

    return render_template_string(html, trip_count=trip_count, total_flags=total_flags,
                                  total_freight=total_freight, parsed_data=parsed_data,
                        
                                  all_trips=all_trips)



@app.route('/')
def home():
    return redirect(url_for('trip_closure'))


@app.route('/trip-closure', methods=['GET', 'POST'])
def trip_closure():
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

    uploaded_range = ""
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    search_trip_id = request.args.get('search_trip_id', '').strip()
    trip_data = {}
    
    filter_status = request.args.get('filter_status', 'all').lower()
    
    # Load trip data for editing
    if filter_status:
        conn = sqlite3.connect('trips.db')
        c = conn.cursor()
        c.execute("SELECT * FROM trip_closure WHERE trip_status LIKE ?", (filter_status,))
        result = c.fetchone()
        conn.close()
        if result:
            # Zip trip_id + fields to match SELECT * order
            trip_data = dict(zip(['trip_id'] + [f for f, _, _ in fields], result))
        

    # Load trip data for editing
    if search_trip_id:
        conn = sqlite3.connect('trips.db')
        c = conn.cursor()
        c.execute("SELECT * FROM trip_closure WHERE trip_id = ?", (search_trip_id,))
        result = c.fetchone()
        conn.close()
        if result:
            # Zip trip_id + fields to match SELECT * order
            trip_data = dict(zip(['trip_id'] + [f for f, _, _ in fields], result))

    if request.method == 'POST':
        if 'excel_file' in request.files:
            file = request.files['excel_file']
            if file.filename.endswith(('.xlsx', '.xls')):
                path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(path)

                # Robust Excel reading
                df = pd.read_excel(path, dtype=str)
                df.columns = df.columns.str.strip()
                # if 'Trip Status' in df.columns:
                #     df = df[df['Trip Status'].str.lower() == 'closed']
                # if 'Actual Delivery Date' in df.columns:
                #     df['Actual Delivery Date'] = pd.to_datetime(df['Actual Delivery Date'], errors='coerce')

                try:
                    uploaded_range = f"From {df['Actual Delivery Date'].min().strftime('%Y-%m-%d')} to {df['Actual Delivery Date'].max().strftime('%Y-%m-%d')}"
                except Exception:
                    uploaded_range = "No valid dates"

                conn = sqlite3.connect('trips.db')
                c = conn.cursor()
                for _, row in df.iterrows():
                    values = [row.get('Trip ID', '')]
                    for f, label, _ in fields:
                        val = row.get(label, '')
                        if pd.isna(val) or val is None:
                            val = ''
                        elif isinstance(val, pd.Timestamp):
                            val = val.strftime('%Y-%m-%d')
                        else:
                            try:
                                val = float(val) if f.endswith(('distance', 'quantity', 'rate', 'cost', 'charges', 'expense', 'amount', 'profit', 'fine')) else str(val)
                            except:
                                val = str(val)
                        values.append(val)
                    placeholders = ','.join('?' * len(values))
                    c.execute(f'''
                        INSERT OR REPLACE INTO trip_closure (
                            trip_id, {','.join(f for f, _, _ in fields)}
                        ) VALUES ({placeholders})
                    ''', values)
                conn.commit()
                conn.close()
                return redirect(url_for('trip_closure'))

        else:
            # Manual edit form save
            trip_id = request.form.get('trip_id', '').strip()
            if not trip_id:
                return "Trip ID is required", 400
            data = [trip_id]
            for f, label, ftype in fields:
                val = request.form.get(f, '')
                if ftype == 'number':
                    try:
                        val = float(val) if val != '' else 0.0
                    except:
                        val = 0.0
                data.append(val)
            conn = sqlite3.connect('trips.db')
            c = conn.cursor()
            placeholders = ','.join('?' * len(data))
            columns = ','.join(['trip_id'] + [f for f, _, _ in fields])
            c.execute(f'''
                INSERT OR REPLACE INTO trip_closure ({columns})
                VALUES ({placeholders})
            ''', data)
            conn.commit()
            conn.close()
            return redirect(url_for('trip_closure'))

    query = "SELECT * FROM trip_closure"
    params = []
    if start_date and end_date:
        query += " WHERE actual_delivery_date BETWEEN ? AND ?"
        params.extend([start_date, end_date])
    elif start_date:
        query += " WHERE actual_delivery_date >= ?"
        params.append(start_date)
    elif end_date:
        query += " WHERE actual_delivery_date <= ?"
        params.append(end_date)
    query += " ORDER BY trip_id DESC"

    conn = sqlite3.connect('trips.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM trip_closure")
    total_closures = c.fetchone()[0]
    c.execute("SELECT SUM(total_trip_expense), SUM(net_profit) FROM trip_closure")
    sums = c.fetchone()
    total_expense = sums or 0.0
    total_profit = sums or 0.0
    c.execute(query, params)
    closures = c.fetchall()
    conn.close()


    html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8"/>
      <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
      <title>Trip Closure Dashboard</title>
      <script src="https://cdn.tailwindcss.com"></script>
      <script>
        window.addEventListener('DOMContentLoaded', function() {
          const params = new URLSearchParams(window.location.search);
          if (params.has('search_trip_id')) {
            document.getElementById('edit-form').scrollIntoView({behavior: 'smooth'});
          }
        });
      </script>
    </head>
    <body class="bg-gray-100 text-white font-sans p-6">
      <div class="max-w-6xl mx-auto bg-[#0B132B] p-6 rounded-lg shadow-lg">
        <h1 class="text-3xl font-semibold mb-6">Trip Closure Dashboard</h1>

        <!-- Search -->
        <form method="get" class="mb-4">
          <label class="block text-sm mb-1 text-gray-300">Search by Trip ID</label>
          <div class="flex gap-4">
            <input type="text" name="search_trip_id" value="{{ request.args.get('search_trip_id', '') }}" class="text-black px-4 py-2 rounded" placeholder="Enter Trip ID">
            <button type="submit" class="bg-yellow-500 px-4 py-2 rounded hover:bg-yellow-600">Search</button>
          </div>
        </form>

        <!-- Date Filter -->
        <form method="get" class="mb-6 flex gap-4">
          <label>Start Date:
            <input type="date" name="start_date" value="{{ request.args.get('start_date', '') }}" class="text-black rounded px-2 py-1">
          </label>
          <label>End Date:
            <input type="date" name="end_date" value="{{ request.args.get('end_date', '') }}" class="text-black rounded px-2 py-1">
          </label>
          <button type="submit" class="bg-green-600 px-4 py-2 rounded hover:bg-green-700">Filter</button>
        </form>
        
        <!-- Upload Excel -->
        <form method="POST" enctype="multipart/form-data" class="mb-6">
          <div class="flex justify-between items-center">
            <label class="block text-sm text-gray-300 mb-2">Upload Trip Excel Sheet</label>
            <span class="text-sm text-gray-400 italic">{{ uploaded_range }}</span>
          </div>
          <input type="file" name="excel_file" accept=".xlsx,.xls" class="mb-4 px-3 py-2 rounded bg-white text-black">
          <button type="submit" class="bg-blue-600 px-4 py-2 rounded hover:bg-blue-700">Upload & Insert</button>
        </form>

        <!-- Edit Form (Always on Top) -->
        <form id="edit-form" method="POST" class="bg-[#3A506B] p-6 rounded-lg grid grid-cols-2 gap-4 mb-8">
          <div>
            <label class="block text-sm text-gray-200 font-bold mb-2">Trip ID</label>
            <input name="trip_id" value="{{ trip_data.get('trip_id', '') }}" required class="w-full px-3 py-2 rounded bg-gray-200 text-black" type="text" placeholder="Enter Trip ID to close">
          </div>
          {% for f, label, ftype in fields %}
            <div>
              <label class="block text-sm text-gray-200 capitalize mb-2">{{ label }}</label>
              <input name="{{ f }}" value="{{ trip_data.get(f, '') }}" class="w-full px-3 py-2 rounded bg-gray-200 text-black" type="{{ ftype }}">
            </div>
          {% endfor %}
          <button type="submit" class="mt-6 bg-[#1C2541] hover:bg-[#3A506B] px-4 py-2 rounded text-white col-span-2">Submit Trip Closure</button>
        </form>

        <!-- Table -->
        <h2 class="text-xl font-semibold mb-4">Recent Trip Closures</h2>
        <div class="overflow-x-auto">
          <table class="min-w-full bg-[#1C2541] rounded-lg overflow-hidden">
            <thead class="bg-[#3A506B] text-white">
              <tr>
                <th class="text-left px-4 py-2">Trip ID</th>
                {% for _, label, _ in fields %}
                <th class="text-left px-4 py-2">{{ label }}</th>
                {% endfor %}
              </tr>
            </thead>
            <tbody>
              {% for row in closures %}
              <tr class="border-b border-gray-600">
                <td class="px-4 py-2">
                  <a href="?search_trip_id={{ row[0] }}{% if start_date %}&start_date={{ start_date }}{% endif %}{% if end_date %}&end_date={{ end_date }}{% endif %}" class="text-blue-400 hover:underline">{{ row[0] }}</a>
                </td>
                {% for i in range(1, fields|length + 1) %}
                <td class="px-4 py-2">{{ row[i] }}</td>
                {% endfor %}
              </tr>
              {% endfor %}
              {% if closures|length == 0 %}
              <tr>
                <td colspan="{{ fields|length + 1 }}" class="px-4 py-2 text-center text-gray-400">No trip closures recorded yet.</td>
              </tr>
              {% endif %}
            </tbody>
          </table>
        </div>

        {% if trip_data %}
        <!-- Second Edit Form (Below Table) -->
        <h2 class="text-xl font-semibold mt-8 mb-4">Edit Trip: {{ trip_data['trip_id'] }}</h2>
        <form method="POST" class="bg-[#3A506B] p-6 rounded-lg grid grid-cols-2 gap-4 mb-8">
          <div>
            <label class="block text-sm text-gray-200 font-bold mb-2">Trip ID</label>
            <input name="trip_id" value="{{ trip_data.get('trip_id', '') }}" required class="w-full px-3 py-2 rounded bg-gray-200 text-black" type="text" readonly>
          </div>
          {% for f, label, ftype in fields %}
            <div>
              <label class="block text-sm text-gray-200 capitalize mb-2">{{ label }}</label>
              <input name="{{ f }}" value="{{ trip_data.get(f, '') }}" class="w-full px-3 py-2 rounded bg-gray-200 text-black" type="{{ ftype }}">
            </div>
          {% endfor %}
          <button type="submit" class="mt-6 bg-[#1C2541] hover:bg-[#3A506B] px-4 py-2 rounded text-white col-span-2">Update Trip</button>
        </form>
        {% endif %}

      </div>
    </body>
    </html>
    '''



    return render_template_string(html,
                                  total_closures=total_closures,
                                  total_expense=total_expense,
                                  total_profit=total_profit,
                                  fields=fields,
                                  closures=closures,
                                  uploaded_range=uploaded_range,
                                  trip_data=trip_data,
                                  start_date=start_date,
                                  end_date=end_date)




@app.route('/trip-audit')
def trip_audit_dashboard():

    df = load_data()
    filter_option = request.args.get('filter', 'all').lower()

    if filter_option == 'open':
        filtered_df = df[df['trip status'].str.lower() == 'pending closure']
    elif filter_option == 'closed':
        filtered_df = df[df['trip status'].str.lower() == 'completed']
    elif filter_option == 'flag':
        filtered_df = df[df['trip status'].str.lower() == 'under audit']
    else:
        filtered_df = df

    total_trips = len(df)
    opened = len(df[df['trip status'].str.lower() == 'pending closure'])
    closed = len(df[df['trip status'].str.lower() == 'completed'])
    audited = len(df[df['pod status'].str.lower() == 'yes'])
    audit_closed = len(df[(df['trip status'].str.lower() == 'completed') & (df['pod status'].str.lower() == 'yes')])
    flags = len(df[df['trip status'].str.lower() == 'under audit'])

    trip_data = filtered_df[['trip id']].dropna().to_dict('records')

    days = list(range(1, 32))
    closed_data = df[df['trip status'].str.lower() == 'completed'].groupby('day')['trip id'].count().reindex(days, fill_value=0).tolist()
    audited_data = df[df['pod status'].str.lower() == 'yes'].groupby('day')['trip id'].count().reindex(days, fill_value=0).tolist()
    audit_pct = [round((a / c) * 100, 1) if c else 0 for a, c in zip(audited_data, closed_data)]

    return render_template_string(template, total_trips=total_trips, opened=opened, closed=closed,
                                  audited=audited, audit_closed=audit_closed, flags=flags,
                                  trips=trip_data, filter_option=filter_option,
                                  closed_data=json.dumps(closed_data),
                                  audited_data=json.dumps(audited_data),
                                  audit_pct=json.dumps(audit_pct))

                 


                                 

                                   

                                   


EXCEL_FILE = 'Trip_Closure_Sheet_Oct2024_Mar2025.xlsx'

def load_data():
    df = pd.read_excel(EXCEL_FILE)
    df.columns = df.columns.str.strip().str.lower()
    df['trip date'] = pd.to_datetime(df['trip date'], errors='coerce')
    df['day'] = df['trip date'].dt.day
    return df


@app.route('/audit/<trip_id>', methods=['GET', 'POST'])
def audit_trip(trip_id):
    df = load_data()
    trip_row = df[df['trip id'].astype(str) == str(trip_id)]
    
    if trip_row.empty:
        return "Trip not found", 404

    trip_data = trip_row.iloc[0].to_dict()

    if request.method == 'POST':
        for key in trip_data.keys():
            if key in request.form:
                trip_data[key] = request.form[key]
        
        df.loc[df['trip id'].astype(str) == str(trip_id), list(trip_data.keys())] = list(trip_data.values())
        df.to_excel(EXCEL_FILE, index=False)

        # Prepare the trip data text for download
        text_content = "Trip Audit Details\n\n"
        for k, v in trip_data.items():
            text_content += f"{k.title()}: {v}\n"

        return Response(
            text_content,
            mimetype='text/plain',
            headers={"Content-Disposition": f"attachment;filename=trip_{trip_id}_audit.txt"}
        )

    # Always return this in GET or fallback
    form_html = f"""
    <!DOCTYPE html><html><head><title>Audit Trip</title>
    <style>body{{background:#0D1117;color:white;font-family:Arial;padding:20px}}input,textarea{{width:100%;margin-bottom:10px}}label{{font-weight:bold}}.btn{{background:#2563EB;color:white;padding:8px 12px;border:none;border-radius:5px}}</style>
    </head><body>
    <h1>Edit Trip: {trip_id}</h1><form method="POST">
    """
    for k, v in trip_data.items():
        form_html += f"<label>{k.title()}</label><input name='{k}' value='{v}' /><br>"
    form_html += "<button type='submit' class='btn'>Save & Download Audit</button>"
    form_html += "</form></body></html>"

    return form_html  # ✅ Always ensure a return at the end

template = """
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\">
  <title>Trip Auditor Dashboard</title>
  <script src=\"https://cdn.jsdelivr.net/npm/chart.js\"></script>
  <style>
    body { background: #0D1117; color: white; font-family: Arial; padding: 20px; }
    h1 { font-size: 24px; margin-bottom: 20px; }
    .dashboard-cards { display: flex; gap: 20px; margin-bottom: 30px; }
    .card { background: #161B22; padding: 20px; border-radius: 10px; flex: 1; text-align: center; }
    .card h2 { font-size: 16px; color: #9CA3AF; margin: 0; }
    .card p { font-size: 26px; margin-top: 5px; }
    select {
      background: #0D1117; color: white; padding: 6px 10px;
      border: 1px solid #555; border-radius: 5px; margin-bottom: 20px;
    }
    .chart-container { background: #161B22; border-radius: 10px; padding: 20px; margin-bottom: 30px; }
    .trip-table { background: #161B22; padding: 20px; border-radius: 10px; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    th, td { padding: 10px; }
    th { background: #1F2937; color: #9CA3AF; }
    tr:nth-child(even) { background-color: #1E293B; }
    a.btn { background: #2563EB; padding: 5px 10px; color: white; border-radius: 5px; text-decoration: none; }
  </style>
</head>
<body>
  <h1>Trip Auditor Dashboard</h1>
  <div class=\"dashboard-cards\">
    <div class=\"card\"><h2>Total Trips Generated</h2><p>{{ total_trips }}</p></div>
    <div class=\"card\"><h2>Trips Opened vs Audited</h2><p>{{ opened }} / {{ audited }}</p></div>
    <div class=\"card\"><h2>Trips Closed vs Audited</h2><p>{{ closed }} / {{ audit_closed }}</p></div>
    <div class=\"card\"><h2>Flags</h2><p>{{ flags }}</p></div>
  </div>
  <form method=\"get\">
    <label>Filter:
      <select name=\"filter\" onchange=\"this.form.submit()\">
        <option value=\"all\" {{ 'selected' if filter_option == 'all' else '' }}>All</option>
        <option value=\"open\" {{ 'selected' if filter_option == 'open' else '' }}>Open</option>
        <option value=\"closed\" {{ 'selected' if filter_option == 'closed' else '' }}>Closed</option>
        <option value=\"flag\" {{ 'selected' if filter_option == 'flag' else '' }}>Flag</option>
      </select>
    </label>
  </form>
  <div class=\"chart-container\">
    <canvas id=\"tripChart\"></canvas>
  </div>
  <script>
    const ctx = document.getElementById('tripChart').getContext('2d');
    const chart = new Chart(ctx, {
      data: {
        labels: Array.from({length: 31}, (_, i) => `Day ${i + 1}`),
        datasets: [
          {
            type: 'bar', label: 'Closed Trips', data: {{ closed_data|safe }}, backgroundColor: '#4DB8FF'
          },
          {
            type: 'bar', label: 'Audited Trips', data: {{ audited_data|safe }}, backgroundColor: '#FFA500'
          },
          {
            type: 'line', label: 'Audit %', data: {{ audit_pct|safe }}, yAxisID: 'y1', borderColor: 'lime', borderWidth: 2, fill: false, tension: 0.3
          }
        ]
      },
      options: {
        responsive: true,
        scales: {
          y: { beginAtZero: true, ticks: { color: 'white' }, title: { display: true, text: 'Trip Count', color: 'white' } },
          y1: { beginAtZero: true, position: 'right', title: { display: true, text: 'Audit %', color: 'white' }, ticks: { color: 'white' }, grid: { drawOnChartArea: false } },
          x: { ticks: { color: 'white' }, grid: { color: '#1F2A40' } }
        },
        plugins: {
          legend: { labels: { color: 'white' } },
          title: { display: true, text: 'Trips Closed vs Audited + Audit %', color: 'white', font: { size: 18 } }
        }
      }
    });
  </script>
  <div class=\"trip-table\">
    <h2>Trips (Filter: {{ filter_option.capitalize() }})</h2>
    <table>
      <thead><tr><th>Trip ID</th><th>Actions</th></tr></thead>
      <tbody>
        {% for trip in trips %}
          <tr>
            <td>{{ trip['trip id'] }}</td>
            <td><a class=\"btn\" href=\"/audit/{{ trip['trip id'] }}\">Audit</a></td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</body>
</html>
"""

def load_financial_data(filepath):
    df = pd.read_excel(filepath)
    df.columns = df.columns.str.strip()
    df['Trip Date'] = pd.to_datetime(df['Trip Date'], errors='coerce')
    df['Day'] = df['Trip Date'].dt.day
    return df

@app.route('/financial-dashboard', methods=['GET', 'POST'])
def financial_dashboard():
    ...

    global uploaded_file_path

    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename.endswith('.xlsx'):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            uploaded_file_path = filepath
            return redirect(url_for('financial_dashboard'))

    file_to_use = uploaded_file_path if uploaded_file_path else DEFAULT_FILE
    df = load_financial_data(file_to_use)

    recent_days = sorted(df['Day'].dropna().unique())[-10:]
    day_labels = [f"Day {int(d)}" for d in recent_days]
    daily = df[df['Day'].isin(recent_days)]

    revenue_data = daily.groupby('Day')['Freight Amount'].sum().reindex(recent_days, fill_value=0).astype(int).tolist()
    expense_data = daily.groupby('Day')['Total Trip Expense'].sum().reindex(recent_days, fill_value=0).astype(int).tolist()
    profit_data = [r - e for r, e in zip(revenue_data, expense_data)]

    total_revenue = round(df['Freight Amount'].sum() / 1e6, 2)
    total_profit = round(df['Net Profit'].sum() / 1e6, 2)
    total_km = round(df['Actual Distance (KM)'].sum() / 1e3, 1)

    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Revenue Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body {
      background-color: #0d1b2a;
      font-family: Arial, sans-serif;
      color: white;
      padding: 20px;
    }
    h2 {
      font-size: 32px;
      color: #f5c518;
      margin-bottom: 10px;
    }
    form {
      margin-bottom: 30px;
    }
    input[type="file"] {
      margin-right: 10px;
    }
    button {
      padding: 6px 12px;
      background-color: #2563EB;
      color: white;
      border: none;
      border-radius: 5px;
      cursor: pointer;
    }
    .stats {
      display: flex;
      justify-content: space-around;
      margin-bottom: 20px;
      text-align: center;
    }
    .stat-block h1 {
      font-size: 36px;
      margin: 0;
      color: #f5c518;
    }
    .legend {
      display: flex;
      justify-content: center;
      gap: 30px;
      margin-bottom: 20px;
    }
    .legend label {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 16px;
    }
    input[type="checkbox"] {
      transform: scale(1.2);
    }
    canvas {
      background-color: #0d1b2a;
    }
  </style>
</head>
<body>
  <h2>Revenue Dashboard</h2>
  <form method="POST" enctype="multipart/form-data">
    <input type="file" name="file" accept=".xlsx" required>
    <button type="submit">Upload Excel</button>
  </form>

  <div class="stats">
    <div class="stat-block">
      <h1>₹{{ total_revenue }} M</h1>
      <div>Total Revenue</div>
    </div>
    <div class="stat-block">
      <h1>₹{{ total_profit }} M</h1>
      <div>Total Profit</div>
    </div>
    <div class="stat-block">
      <h1>{{ total_km }} K</h1>
      <div>Total KM Cost</div>
    </div>
  </div>

  <div class="legend">
    <label><input type="checkbox" id="revenueCheckbox" checked> Total Revenue</label>
    <label><input type="checkbox" id="expenseCheckbox" checked> Total Expense</label>
    <label><input type="checkbox" id="profitCheckbox" checked> Trip Profit</label>
  </div>

  <canvas id="financeChart" height="100"></canvas>

  <script>
    const ctx = document.getElementById('financeChart').getContext('2d');
    const days = {{ days | safe }};
    const revenueData = {{ revenue | safe }};
    const expenseData = {{ expense | safe }};
    const profitData = {{ profit | safe }};

    const chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: days,
        datasets: [
          {
            label: 'Total Revenue',
            backgroundColor: '#f5c518',
            data: revenueData
          },
          {
            label: 'Total Expense',
            backgroundColor: '#007bff',
            data: expenseData
          },
          {
            label: 'Trip Profit',
            backgroundColor: '#00c896',
            data: profitData
          }
        ]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false }
        },
        scales: {
          x: {
            ticks: { color: 'white' },
            grid: { display: false }
          },
          y: {
            ticks: { color: 'white' },
            grid: { color: '#33415c' }
          }
        }
      }
    });

    document.getElementById('revenueCheckbox').addEventListener('change', function () {
      chart.data.datasets[0].hidden = !this.checked;
      chart.update();
    });
    document.getElementById('expenseCheckbox').addEventListener('change', function () {
      chart.data.datasets[1].hidden = !this.checked;
      chart.update();
    });
    document.getElementById('profitCheckbox').addEventListener('change', function () {
      chart.data.datasets[2].hidden = !this.checked;
      chart.update();
    });
  </script>
</body>
</html>
    """, days=day_labels, revenue=revenue_data, expense=expense_data, profit=profit_data,
         total_revenue=total_revenue, total_profit=total_profit, total_km=total_km)



def load_trip_statistics(filepath):
    df = pd.read_excel(filepath)
    df.columns = df.columns.str.strip()
    df['Trip Date'] = pd.to_datetime(df['Trip Date'], errors='coerce')
    df['Day'] = df['Trip Date'].dt.day
    return df

@app.route('/trip-statistics', methods=['GET', 'POST'])
def trip_statistics_dashboard():
    global uploaded_trip_stats_file
    file_path = uploaded_trip_stats_file if uploaded_trip_stats_file else DEFAULT_FILE

    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename.endswith('.xlsx'):
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(upload_path)
            uploaded_trip_stats_file = upload_path
            return redirect(url_for('trip_statistics_dashboard'))

    df = load_trip_statistics(file_path)

    days = list(range(1, 32))
    total = df.groupby('Day')['Trip ID'].count().reindex(days, fill_value=0).tolist()
    ongoing = df[df['Trip Status'].str.lower() == 'pending closure'].groupby('Day')['Trip ID'].count().reindex(days, fill_value=0).tolist()
    closed = df[df['Trip Status'].str.lower() == 'completed'].groupby('Day')['Trip ID'].count().reindex(days, fill_value=0).tolist()

    return render_template_string(TEMPLATE_TRIP_STATISTICS,
        total=total,
        ongoing=ongoing,
        closed=closed,
        total_sum=sum(total),
        ongoing_sum=sum(ongoing),
        closed_sum=sum(closed)
    )

TEMPLATE_TRIP_STATISTICS = '''
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Trip Statistics Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body {
      background-color: #0d1b2a;
      font-family: Arial, sans-serif;
      color: white;
      padding: 20px;
    }
    .stats {
      display: flex;
      justify-content: space-around;
      margin-bottom: 20px;
      text-align: center;
    }
    .stat-block h1 {
      font-size: 48px;
      margin: 0;
      color: #f5c518;
    }
    .upload {
      margin-bottom: 30px;
      text-align: center;
    }
    input[type="file"] {
      background: white;
      color: black;
      padding: 6px;
      border-radius: 4px;
    }
    input[type="submit"] {
      padding: 6px 12px;
      background-color: #2563EB;
      color: white;
      border: none;
      border-radius: 4px;
      margin-left: 10px;
    }
    .legend {
      display: flex;
      justify-content: center;
      gap: 30px;
      margin-bottom: 20px;
    }
    .legend label {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 16px;
    }
    canvas {
      background-color: #0d1b2a;
    }
    input[type="checkbox"] {
      transform: scale(1.2);
    }
  </style>
</head>
<body>

  <div class="upload">
    <form method="POST" enctype="multipart/form-data">
      <label><b>Upload Excel (.xlsx):</b></label>
      <input type="file" name="file" accept=".xlsx" required>
      <input type="submit" value="Upload">
    </form>
  </div>

  <div class="stats">
    <div class="stat-block">
      <h1>{{ total_sum }}</h1>
      <div>Total Trips</div>
    </div>
    <div class="stat-block">
      <h1>{{ ongoing_sum }}</h1>
      <div>On-going</div>
    </div>
    <div class="stat-block">
      <h1>{{ closed_sum }}</h1>
      <div>Trip Closed</div>
    </div>
  </div>

  <div class="legend">
    <label><input type="checkbox" id="totalCheckbox" checked> Total Trips</label>
    <label><input type="checkbox" id="ongoingCheckbox" checked> On-going</label>
    <label><input type="checkbox" id="closedCheckbox" checked> Trip Closed</label>
  </div>

  <canvas id="tripChart" height="100"></canvas>

  <script>
    const ctx = document.getElementById('tripChart').getContext('2d');
    const labels = Array.from({ length: 31 }, (_, i) => i + 1);
    const chartData = {
      labels: labels,
      datasets: [
        {
          label: 'Total Trips',
          backgroundColor: '#f5c518',
          data: {{ total | safe }}
        },
        {
          label: 'On-going',
          backgroundColor: '#00c896',
          data: {{ ongoing | safe }}
        },
        {
          label: 'Trip Closed',
          backgroundColor: '#007bff',
          data: {{ closed | safe }}
        }
      ]
    };

    const config = {
      type: 'bar',
      data: chartData,
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: 'white' }, grid: { display: false } },
          y: { ticks: { color: 'white' }, grid: { color: '#33415c' } }
        }
      }
    };

    const tripChart = new Chart(ctx, config);

    document.getElementById('totalCheckbox').addEventListener('change', function() {
      tripChart.data.datasets[0].hidden = !this.checked;
      tripChart.update();
    });
    document.getElementById('ongoingCheckbox').addEventListener('change', function() {
      tripChart.data.datasets[1].hidden = !this.checked;
      tripChart.update();
    });
    document.getElementById('closedCheckbox').addEventListener('change', function() {
      tripChart.data.datasets[2].hidden = !this.checked;
      tripChart.update();
    });
  </script>
</body>
</html>
'''

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False

# ---- Flask app ----
app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---- In-memory Excel store (latest uploaded) ----
excel_data = None  # pandas.DataFrame or None

# -------------------------
# ---- Helper / Utilities
# -------------------------
def normalize_cols(df):
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    return df

def find_col(df, *keywords):
    """Return first column name that contains any of the keywords (substring match)."""
    cols = list(df.columns)
    for k in keywords:
        k = k.lower()
        for c in cols:
            if k in c:
                return c
    return None

# small helper to render a short row line
def format_row_short(row, trip_id_col, origin_col, dest_col, status_col):
    tid = row.get(trip_id_col, "") if trip_id_col else ""
    origin = row.get(origin_col, "") if origin_col else ""
    dest = row.get(dest_col, "") if dest_col else ""
    status = row.get(status_col, "") if status_col else ""
    return f"{tid} | {origin} → {dest} | {status}"

# -------------------------
# ---- Simple FAQ knowledge (signup/login/dashboard) ----
# --# ================== FAQ KNOWLEDGE BASE ==================
FAQ_KB = {
    # ===== Account & Login =====
    "explain account creation": "To create an account: go to Signup → fill Full Name, Email, Phone, Password and Confirm Password → Click Sign Up. You'll then be able to login.",
    "explain password reset": "Use 'Forgot / Change Password?' on the login page to reset your password. You'll receive instructions via email.",
    "explain email change": "Yes — go to User Settings on the dashboard, find your profile and update the email or phone number.",
    "explain password policy": "Password should be at least 8 characters (include letters & numbers). We recommend using a strong unique password.",
    "explain verification emails issue": "Check your spam folder, ensure your email is correct, and that your mail server is not blocking messages from the app domain.",
    "explain signup vs login": "Signup creates a new account. Login lets existing users enter the dashboard using their credentials.",
    "explain role-based access": "Each person gets their own secure login – owner, manager, driver, finance, auditor. Everyone only sees what they need to. This increases security and avoids confusion.",
    
    # ===== Trips & Reports =====
    "explain trip reports": "Open 'View Trip Reports' on the dashboard or ask the bot to 'Show trips' or 'List trips'. You can also upload an Excel and ask the bot questions directly.",
    "explain excel upload": "Open the chat widget bottom-right and use 'Upload Excel' or use the dashboard Upload Files area. The bot will parse uploaded Excel and answer queries.",
    "explain trip generator": "Trip Generator lets you create a trip – assign vehicle, driver, origin, destination, and planned expenses. Example: Bangalore–Hyderabad trip with fuel ₹25,000, tolls ₹4,000, food ₹2,000. Features: Budgeting upfront → cost control before trip starts.",
    "explain trip closure": "At trip end, driver/manager enters actual data – fuel, tolls, food, lodging, penalties. System auto-calculates net profit. Example: Planned ₹30,000 but actual spent ₹28,000 → profit shown instantly. Features: Stops leakages, increases accountability, ensures transparency.",
    "explain trip audit": "Audit compares planned vs actual and flags mismatches. Example: Planned distance 500 km but actual 650 km → system auto-flags. Auditor checks if genuine or misuse. Features: Fraud detection, cleaner books, automatic checks.",
    
    "explain revenue": "Ask 'Show revenue' — the bot will compute revenue if the uploaded file contains 'revenue'/'freight' columns.",
    "explain ongoing trips": "Ask 'How many trips are ongoing?' or 'List ongoing trips' — the bot will use the trip_status column to answer.",
    "explain top vehicle performance": "Ask 'Top vehicle' or 'Which vehicle has the highest profit' — the bot will infer from 'net_profit' or similar columns.",
    
    # ===== Dashboard & Features =====
    "explain smart fleet ai": "Smart Fleet AI helps transport & logistics companies reduce trip costs by 10–20% and also bring new customer bookings online. Everything is managed in one dashboard – trip planning, closure, expenses, auditing, and financial analysis.",
    "explain dashboard": "Dashboard shows KPIs like Total Trips, Ongoing Trips, Closed Trips, and Flags. At a glance, you know running trips, profits/losses, revenue vs expenses. Features: Instant visibility → faster decisions → less losses.",
    "explain financial dashboard": "Finance team can upload Excel or directly see revenue, expenses, KM costs, and profit margins. Owners know if a trip is profitable without waiting weeks. Features: Faster reporting, faster invoicing, better cash flow.",
    "explain users dashboard": "Manage who has access – owner, manager, trip closer, auditor. Example: Driver can close trips but not see finance data. Features: Role-based rights, prevents misuse.",
    "explain fleet owner settings": "Owner can update info, manage roles, reset passwords, and stay in control. Features: Security and flexibility.",
    "explain booking app": "Future expansion: Transport App will bring new customer bookings online. Companies listed get direct bookings. We charge only 2–5% booking fee. Features: Save 20% costs + get new business.",
    "explain closing summary": "Smart Fleet AI saves money, prevents misuse, and grows business. Fleet owners get instant profit visibility, managers plan & close trips faster, finance sees clear reports, drivers manage trips easily without paperwork.",
    
    # ===== Customer FAQ Questions (from demo prep) =====
    "how much does it cost to implement": "Cost depends on fleet size; we can provide a tailored proposal.",
    "is this suitable for small fleets or only big companies": "Works for both small and large fleets – scalable.",
    "how quickly can we start using it": "Setup can be done in a few days; training is quick.",
    "is it cloud-based or on-premise": "Cloud-based with secure login; no complex installation.",
    "do we need technical staff to maintain it": "Very minimal technical maintenance; we provide support.",
    "can we integrate with existing employee credentials": "Yes, supports role-based access; can integrate with your LDAP/Active Directory.",
    "what happens if someone forgets the password": "Forgot password triggers email reset.",
    "can we track who logs in and when": "Yes, we maintain login audit trails.",
    "how real-time is this data": "Almost real-time; dashboard updates as soon as data is entered.",
    "can we customize kpis shown": "Yes, KPIs can be customized per user.",
    "can we export these stats": "Absolutely, export as Excel/PDF for reports or presentations.",
    "can trips be recurring": "Yes, recurring trips can be pre-scheduled.",
    "can we assign multiple vehicles for one trip": "Each trip is assigned one vehicle; multiple trips can be linked.",
    "can the system suggest optimized routes or costs": "Future updates may include route optimization; currently supports planned cost tracking.",
    "can drivers submit via mobile app": "Yes, mobile submission available; supervisor approval optional.",
    "how do we prevent false data entry": "System flags mismatches, and audit team verifies data.",
    "can penalties/deductions be automated": "Yes, penalties can be defined in the system for automated calculation.",
    "can we generate audit reports for multiple trips at once": "Yes, batch audit reports are available.",
    "can it detect fuel theft or misuse": "Yes, deviations like extra distance, fuel, or costs are flagged.",
    "what if we disagree with a flagged mismatch": "Audit disputes can be reviewed with evidence stored in the system.",
    "can we integrate with accounting software": "Yes, CSV/Excel export makes integration simple; API support possible.",
    "can it generate profit/loss per vehicle": "Yes, shows vehicle-wise profitability and trip-wise breakdown.",
    "how detailed are the reports per trip or per month": "Detailed reports available; can filter by date, vehicle, driver, or route.",
    "can we add new roles or custom permissions": "Yes, roles are customizable.",
    "how easy is it to deactivate users": "Deactivation/reactivation is one click.",
    "can one person have multiple roles": "Yes, multiple roles per user supported.",
    "can we track system changes": "Yes, audit trail for changes is available.",
    "is there a backup option for settings and data": "Yes, daily/weekly backup can be automated.",
    "can owner set alerts for unusual spending": "Yes, thresholds for costs, mileage, or delays can trigger alerts.",
    "how will this integrate with current bookings": "App can link directly to fleet info; only listed vehicles appear.",
    "how will payments and commissions work": "Payments managed through secure gateway; 2–5% booking fee deducted automatically.",
    "can we control which customers see our fleet": "Yes, visibility and bookings are fully under your control.",
    "how soon can we expect cost savings": "Typically, companies see 10–20% cost reduction in first 1–2 months.",
    "any case studies or reference clients": "Yes, we have pilot results showing real savings.",
    "can we try a demo with our own data": "Yes, we can onboard your sample data for a trial demo."
}

# ================== CHAT ENDPOINT ==================
@app.route("/chat", methods=["POST"])
def chat():
    global df
    user_message = request.json.get("message", "")
    msg = user_message.lower().strip()

    # --- Greeting / Welcome ---
    if msg in ["hi", "hello", "hey", "hi there", "hello there"]:
        return jsonify({
            "message": (
                "👋 Hi! I’m Smart Fleet AI assistant. "
                "I help logistics owners save costs, prevent misuse, and grow business. "
                "You can ask me things like:\n"
                "• explain trip generator\n"
                "• explain trip closure\n"
                "• explain trip audit\n"
                "• show revenue\n"
                "• show ongoing trips\n"
                "• explain financial dashboard\n\n"
                "How can I help you today?"
            )
        })

    # --- FAQ Lookup ---
    for q, ans in FAQ_KB.items():
        if q in msg:
            return jsonify({"message": ans})

    # --- Excel related queries ---
    # (your existing Excel logic continues here…)


def handle_faq(msg):
    # try to match FAQ keys by substring
    lm = msg.lower().strip()
    for k, v in FAQ_KB.items():
        if k in lm:
            return v
    # fuzzy-ish checks
    if "create account" in lm or "sign up" in lm or "signup" in lm:
        return FAQ_KB["how do i create an account"]
    if "forgot" in lm or "reset password" in lm or "forgot password" in lm:
        return FAQ_KB["what if i forget my password"]
    if "upload excel" in lm or "upload file" in lm:
        return FAQ_KB["how do i upload excel files"]
    return None

# -------------------------
# ---- Intent classifier (small) + rules
# -------------------------
INTENT_SAMPLES = [
    ("hi", "greeting"),
    ("hello", "greeting"),
    ("how are you", "greeting"),
    ("thanks", "thanks"),
    ("bye", "goodbye"),
    ("how many trips", "total_trips"),
    ("total trips", "total_trips"),
    ("show trip id t50382", "trip_by_id"),
    ("pod pending", "pod_pending"),
    ("freight > 5000", "freight_filter"),
    ("trips for driver dr001", "trips_by_driver"),
    ("trips from delhi to chennai", "route_query"),
    ("show revenue", "revenue"),
    ("today trips", "today_trips"),
    ("list all trips", "list_trips"),
    ("columns", "list_columns"),
]

classifier = None
vectorizer = None
if SKLEARN_AVAILABLE:
    try:
        texts = [t for t, label in INTENT_SAMPLES]
        labels = [label for t, label in INTENT_SAMPLES]
        vectorizer = TfidfVectorizer(ngram_range=(1,2), lowercase=True)
        X = vectorizer.fit_transform(texts)
        classifier = LogisticRegression(max_iter=400)
        classifier.fit(X, labels)
    except Exception:
        classifier = None
        vectorizer = None

def predict_intent(text):
    t = text.lower()
    if re.search(r"\b(hi|hello|hey|good morning|good afternoon|good evening)\b", t):
        return "greeting"
    if re.search(r"\b(thank|thanks)\b", t):
        return "thanks"
    if re.search(r"\b(bye|goodbye|see you)\b", t):
        return "goodbye"
    if classifier and vectorizer:
        try:
            Xq = vectorizer.transform([t])
            return classifier.predict(Xq)[0]
        except Exception:
            pass
    # fallback rules:
    if re.search(r"(how many trips|total trips|number of trips|how many)", t):
        return "total_trips"
    if re.search(r"(ongoing|in progress|pending|open)", t):
        return "ongoing_trips"
    if re.search(r"(closed|completed|finished)", t):
        return "closed_trips"
    if "pod" in t:
        return "pod_pending"
    if re.search(r"trip\s*(?:id)?\s*[:#]?\s*[a-z0-9\-_]+", t):
        return "trip_by_id"
    if re.search(r"freight\s*(>=|<=|>|<|=)|\bfreight\b", t):
        return "freight_filter"
    if re.search(r"driver\s*[:#]?\s*[a-z0-9\-_]+", t):
        return "trips_by_driver"
    if re.search(r"from\s+[a-z]+.*to\s+[a-z]+", t):
        return "route_query"
    if "revenue" in t:
        return "revenue"
    if "expense" in t:
        return "expense"
    if "profit" in t:
        return "profit"
    if "today" in t:
        return "today_trips"
    if any(x in t for x in ["list trips", "all trips", "show trips"]):
        return "list_trips"
    if "column" in t or "columns" in t:
        return "list_columns"
    return "unknown"

# -------------------------
# ---- Excel upload endpoint
# -------------------------
@app.route("/upload_excel", methods=["POST"])
def upload_excel_endpoint():
    global excel_data
    if 'file' not in request.files:
        return jsonify({"message": "No file uploaded (field name must be 'file')."}), 400
    f = request.files['file']
    if f.filename == '':
        return jsonify({"message": "No file selected."}), 400
    os.makedirs("uploads", exist_ok=True)
    safe_path = os.path.join("uploads", f.filename)
    f.save(safe_path)
    try:
        df = pd.read_excel(safe_path, engine="openpyxl")
    except Exception as e:
        return jsonify({"message": f"Error reading Excel: {e}"}), 400
    df = normalize_cols(df)
    excel_data = df
    return jsonify({"message": f"Excel '{f.filename}' uploaded successfully and data loaded!"})

# -------------------------
# ---- Handlers for common intents (work on df)
# -------------------------
def handle_trip_by_id(msg, df):
    trip_id_col = find_col(df, "trip_id", "tripid", "trip")
    m = re.search(r"trip\s*(?:id)?\s*[:#]?\s*([a-z0-9\-_]+)", msg, re.I)
    if not m:
        return "Please tell me the Trip ID (e.g., 'Show Trip ID T50382')."
    q = m.group(1)
    if not trip_id_col:
        return "Uploaded file doesn't seem to have a Trip ID column."
    matched = df[df[trip_id_col].str.lower() == q.lower()]
    if matched.empty:
        return f"I couldn't find Trip ID {q} in the uploaded data."
    row = matched.iloc[0]
    lines = [f"📋 Details for Trip {q}:"]
    # show key columns first (if present), then all columns
    priority = ["trip_id","trip_date","vehicle_id","driver_id","origin","destination","trip_status","freight_amount","total_trip_expense","net_profit","pod_status"]
    for p in priority:
        col = find_col(df, p)
        if col and col in df.columns:
            lines.append(f"{col}: {row[col]}")
    # then include rest
    for col in df.columns:
        if col not in [find_col(df, p) for p in priority if find_col(df,p)]:
            lines.append(f"{col}: {row[col]}")
    return "\n".join(lines)

def handle_total_trips(df):
    total = len(df)
    status_col = find_col(df, "trip_status", "status", "state")
    ongoing = closed = None
    if status_col:
        ongoing = len(df[df[status_col].str.contains("pending|ongoing|in progress|active", case=False, na=False)])
        closed = len(df[df[status_col].str.contains("completed|closed|finished", case=False, na=False)])
    lines = [f"📊 Trip Summary (from uploaded file):", f"Total trips: {total}"]
    if ongoing is not None:
        lines.append(f"Ongoing: {ongoing}")
    if closed is not None:
        lines.append(f"Closed: {closed}")
    return "\n".join(lines)

def handle_pod_pending(df):
    pod_col = find_col(df, "pod", "pod_status")
    if not pod_col:
        return "I couldn't find a POD/POD_Status column in the uploaded file."
    pending = df[df[pod_col].str.lower().isin(["no", "pending", "false", "0", "n"])]
    if pending.empty:
        return "Good news — there are no trips with POD pending."
    lines = [f"📦 Trips with POD pending ({len(pending)}):"]
    trip_id_col = find_col(df, "trip_id", "tripid", "trip")
    origin_col = find_col(df, "origin", "from")
    dest_col = find_col(df, "destination", "to")
    status_col = find_col(df, "trip_status", "status", "state")
    for _, r in pending.head(20).iterrows():
        lines.append(format_row_short(r, trip_id_col, origin_col, dest_col, status_col))
    return "\n".join(lines)

def handle_trips_by_driver(msg, df):
    driver_col = find_col(df, "driver", "driver_id", "driverid")
    if not driver_col:
        return "Driver column not found in uploaded file."
    m = re.search(r"driver\s*[:#]?\s*([a-z0-9\-_]+)", msg, re.I)
    if not m:
        return "Please specify driver id (e.g., 'Trips for driver DR001')."
    dv = m.group(1)
    matched = df[df[driver_col].str.lower() == dv.lower()]
    if matched.empty:
        return f"No trips found for driver {dv}."
    lines = [f"🚚 Trips for driver {dv} ({len(matched)}):"]
    trip_id_col = find_col(df, "trip_id", "tripid", "trip")
    origin_col = find_col(df, "origin", "from")
    dest_col = find_col(df, "destination", "to")
    status_col = find_col(df, "trip_status", "status", "state")
    for _, r in matched.head(50).iterrows():
        lines.append(format_row_short(r, trip_id_col, origin_col, dest_col, status_col))
    return "\n".join(lines)

def handle_freight_filter(msg, df):
    # between
    m_between = re.search(r"([a-z_0-9]+)\s+between\s+([0-9]+(?:\.[0-9]+)?)\s+and\s+([0-9]+(?:\.[0-9]+)?)", msg, re.I)
    if m_between:
        col_raw, v1, v2 = m_between.group(1).lower(), float(m_between.group(2)), float(m_between.group(3))
        target_col = None
        if col_raw in df.columns: target_col = col_raw
        else:
            for c in df.columns:
                if col_raw in c: target_col = c; break
        if not target_col: return f"Column '{col_raw}' not found."
        if not pd.api.types.is_numeric_dtype(df[target_col]):
            return f"Column '{target_col}' is not numeric."
        filtered = df[(df[target_col] >= v1) & (df[target_col] <= v2)]
        if filtered.empty: return f"No trips found where {target_col} between {v1} and {v2}."
        lines = [f"📈 Trips where {target_col} between {v1} and {v2} ({len(filtered)}):"]
        trip_id_col = find_col(df, "trip_id", "tripid", "trip")
        origin_col = find_col(df, "origin", "from")
        dest_col = find_col(df, "destination", "to")
        status_col = find_col(df, "trip_status", "status")
        for _, r in filtered.head(20).iterrows():
            lines.append(format_row_short(r, trip_id_col, origin_col, dest_col, status_col))
        return "\n".join(lines)
    # other ops
    m = re.search(r"([a-z_0-9]+)\s*(>=|<=|>|<|=)\s*([0-9]+(?:\.[0-9]+)?)", msg, re.I)
    if not m:
        # try "freight > value"
        m2 = re.search(r"freight\s*(?:greater than|>)\s*([0-9]+(?:\.[0-9]+)?)", msg, re.I)
        if not m2:
            return "Please specify a numeric filter (e.g., 'freight > 5000' or 'freight between 1000 and 5000')."
        else:
            col_raw = "freight"; op = ">"; val = float(m2.group(1))
    else:
        col_raw, op, val = m.group(1).lower(), m.group(2), float(m.group(3))
    target_col = None
    if col_raw in df.columns:
        target_col = col_raw
    else:
        for c in df.columns:
            if col_raw in c:
                target_col = c; break
    if not target_col:
        return f"Column '{col_raw}' not found in uploaded file."
    if not pd.api.types.is_numeric_dtype(df[target_col]):
        return f"Column '{target_col}' is not numeric."
    if op == ">": filtered = df[df[target_col] > val]
    elif op == "<": filtered = df[df[target_col] < val]
    elif op == ">=": filtered = df[df[target_col] >= val]
    elif op == "<=": filtered = df[df[target_col] <= val]
    else: filtered = df[df[target_col] == val]
    if filtered.empty: return f"No trips found where {target_col} {op} {val}."
    lines = [f"📈 Trips where {target_col} {op} {val} ({len(filtered)}):"]
    trip_id_col = find_col(df, "trip_id", "tripid", "trip")
    origin_col = find_col(df, "origin", "from")
    dest_col = find_col(df, "destination", "to")
    status_col = find_col(df, "trip_status", "status")
    for _, r in filtered.head(20).iterrows():
        lines.append(format_row_short(r, trip_id_col, origin_col, dest_col, status_col))
    return "\n".join(lines)

def handle_route_query(msg, df):
    rm = re.search(r"from\s+([a-z0-9\-_]+)\s+to\s+([a-z0-9\-_]+)", msg, re.I)
    if not rm:
        return "Please ask like 'Trips from Delhi to Chennai'."
    origin_val, dest_val = rm.group(1), rm.group(2)
    origin_col = find_col(df, "origin", "from")
    dest_col = find_col(df, "destination", "to")
    if not origin_col or not dest_col:
        return "Origin or Destination column not found in uploaded file."
    matched = df[(df[origin_col].str.lower() == origin_val.lower()) & (df[dest_col].str.lower() == dest_val.lower())]
    if matched.empty:
        return f"No trips found from {origin_val} to {dest_val}."
    lines = [f"🗺️ Trips from {origin_val} to {dest_val} ({len(matched)}):"]
    trip_id_col = find_col(df, "trip_id", "tripid", "trip")
    status_col = find_col(df, "trip_status", "status")
    for _, r in matched.iterrows():
        lines.append(format_row_short(r, trip_id_col, origin_col, dest_col, status_col))
    return "\n".join(lines)

def handle_financials(intent, df):
    fin_col = find_col(df, "revenue", "total_revenue", "total_revenues")
    expense_col = find_col(df, "expense", "total_expense", "total_expenses")
    profit_col = find_col(df, "profit", "net_profit")
    if intent == "revenue":
        if fin_col:
            s = df[fin_col].dropna()
            if pd.api.types.is_numeric_dtype(s):
                return f"💰 Revenue (in data): sum = ₹{s.sum():,.2f}, count = {len(s)}"
            else:
                return f"Revenue column found but not numeric."
    if intent == "expense":
        if expense_col:
            s = df[expense_col].dropna()
            if pd.api.types.is_numeric_dtype(s):
                return f"💸 Expense (in data): sum = ₹{s.sum():,.2f}, count = {len(s)}"
            else:
                return f"Expense column found but not numeric."
    if intent == "profit":
        if profit_col:
            s = df[profit_col].dropna()
            if pd.api.types.is_numeric_dtype(s):
                return f"📈 Profit (in data): sum = ₹{s.sum():,.2f}, count = {len(s)}"
            else:
                return f"Profit column found but not numeric."
    # fallback: compute from freight & total_expense
    freight_col = find_col(df, "freight", "freight_amount")
    expense_col2 = find_col(df, "total_trip_expense", "total_expense", "expense")
    if freight_col and expense_col2 and pd.api.types.is_numeric_dtype(df[freight_col]) and pd.api.types.is_numeric_dtype(df[expense_col2]):
        if intent == "revenue":
            return f"💰 Total freight (revenue proxy): ₹{df[freight_col].sum():,.2f}"
        if intent == "expense":
            return f"💸 Total expense: ₹{df[expense_col2].sum():,.2f}"
        if intent == "profit":
            rev = df[freight_col].sum()
            exp = df[expense_col2].sum()
            profit = rev - exp
            pct = (profit / rev * 100) if rev else 0
            return f"📈 Estimated Profit: ₹{profit:,.2f} (Profit %: {pct:.2f}%)"
    return f"I couldn't compute {intent} from the uploaded data. Ensure there are numeric columns like 'freight_amount' and 'total_trip_expense' or 'revenue/expense' columns."

def handle_list_columns(df):
    cols = list(df.columns)
    return "Detected columns:\n- " + "\n- ".join(cols)

def handle_today_trips(df):
    date_col = find_col(df, "trip_date", "date", "delivery_date")
    if not date_col:
        return "No date-like column found to check today's trips."
    try:
        temp = pd.to_datetime(df[date_col], errors="coerce").dt.date
        today_dt = date.today()
        matched = df[temp == today_dt]
        if matched.empty:
            return f"No trips scheduled for today ({today_dt})."
        lines = [f"📅 Trips scheduled for today ({today_dt}):"]
        trip_id_col = find_col(df, "trip_id", "tripid", "trip")
        origin_col = find_col(df, "origin", "from")
        dest_col = find_col(df, "destination", "to")
        status_col = find_col(df, "trip_status", "status")
        for _, r in matched.iterrows():
            lines.append(format_row_short(r, trip_id_col, origin_col, dest_col, status_col))
        return "\n".join(lines)
    except Exception:
        return "Couldn't parse dates in your date column."

def fallback_insights(df):
    lines = ["Here are quick insights from your uploaded file:"]
    lines.append(f"- Total trips: {len(df)}")
    status_col = find_col(df, "trip_status", "status", "state")
    if status_col:
        o = len(df[df[status_col].str.contains("pending|ongoing|in progress|active", case=False, na=False)])
        c = len(df[df[status_col].str.contains("completed|closed|finished", case=False, na=False)])
        lines.append(f"- Ongoing: {o}, Closed: {c}")
    pod_col = find_col(df, "pod", "pod_status")
    if pod_col:
        pending = len(df[df[pod_col].str.lower().isin(["no","pending","false","0","n"])])
        lines.append(f"- POD pending: {pending}")
    freight_col = find_col(df, "freight", "freight_amount")
    if freight_col and pd.api.types.is_numeric_dtype(df[freight_col]):
        top = df.sort_values(by=freight_col, ascending=False).head(3)
        lines.append(f"- Top freight trips (sample): " + ", ".join([str(x) for x in top[freight_col].head(3).tolist()]))
    return "\n".join(lines)

# -------------------------
# ---- /chat endpoint (main)
# -------------------------
@app.route("/another_chat_route", methods=["POST"])
def chat_alternative():
    # some code

    global excel_data
    data = request.json or {}
    user_msg = (data.get("message", "") or "").strip()
    if user_msg == "":
        return jsonify({"message": "Please type a message or upload an Excel file."})
    msg = user_msg.strip()

    # small-talk & FAQ (always answer even if Excel not uploaded)
    if re.search(r"\b(hi|hello|hey|good morning|good afternoon|good evening)\b", msg, re.I):
        return jsonify({"message":
            "Hello! 👋 I'm SmartFleet AI — your dashboard assistant.\n"
            "I can help with trips, drivers, financials, audits, and data from uploaded Excel files.\n"
            "Try: 'How many trips are ongoing?', 'Show Trip ID T50382', 'Which trips have POD pending?', or upload an Excel now."
        })
    if re.search(r"\b(thank(s)?|thanks|thank you)\b", msg, re.I):
        return jsonify({"message": "You're welcome! 😊 Anything else I can help with?"})
    if re.search(r"\b(bye|goodbye|see you|take care)\b", msg, re.I):
        return jsonify({"message": "Goodbye! Safe journeys 🚛 — ping me any time for SmartFleet data."})

    # FAQ mapping for login/signup/dashboard questions (works even without Excel)
    faq_answer = handle_faq(msg)
    if faq_answer and excel_data is None:
        return jsonify({"message": faq_answer})

    # If Excel not uploaded yet, guide user and answer general FAQs
    if excel_data is None:
        # if user asked about uploading
        if any(k in msg.lower() for k in ["upload", "excel", "file", "spreadsheet", "how to add"]):
            return jsonify({"message": "Please use the 'Upload Excel' button inside the chat widget (bottom-right). Once uploaded, I will analyze it and you can ask data queries."})
        # if user asked a dashboard question answer from KB if possible
        if faq_answer:
            return jsonify({"message": faq_answer})
        return jsonify({"message": "No Excel uploaded yet. Please upload an Excel file using the widget and then ask your query (e.g., 'How many trips are ongoing?')."})

    # Excel is available — proceed to interpret
    df = excel_data.copy()
    # ensure object dtype columns are strings
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype(str)

    # predict intent
    intent = predict_intent(msg)

    try:
        if intent == "trip_by_id":
            return jsonify({"message": handle_trip_by_id(msg, df)})
        if intent in ("total_trips", "ongoing_trips", "closed_trips"):
            return jsonify({"message": handle_total_trips(df)})
        if intent == "pod_pending":
            return jsonify({"message": handle_pod_pending(df)})
        if intent == "trips_by_driver":
            return jsonify({"message": handle_trips_by_driver(msg, df)})
        if intent == "freight_filter":
            return jsonify({"message": handle_freight_filter(msg, df)})
        if intent == "route_query":
            return jsonify({"message": handle_route_query(msg, df)})
        if intent in ("revenue", "expense", "profit"):
            return jsonify({"message": handle_financials(intent, df)})
        if intent == "today_trips":
            return jsonify({"message": handle_today_trips(df)})
        if intent == "list_trips":
            trip_id_col = find_col(df, "trip_id", "tripid", "trip")
            origin_col = find_col(df, "origin", "from")
            dest_col = find_col(df, "destination", "to")
            status_col = find_col(df, "trip_status", "status", "state")
            lines = [f"All trips sample (first 20 of {len(df)}):"]
            for _, r in df.head(20).iterrows():
                lines.append(format_row_short(r, trip_id_col, origin_col, dest_col, status_col))
            return jsonify({"message": "\n".join(lines)})
        if intent == "list_columns":
            return jsonify({"message": handle_list_columns(df)})
    except Exception as e:
        return jsonify({"message": f"Sorry — I encountered an internal error while processing your request: {e}"})

    # fallback: if user mentions a known column
    words = re.findall(r"[a-z_0-9]+", msg.lower())
    for w in words:
        if w in df.columns:
            if pd.api.types.is_numeric_dtype(df[w]):
                s = df[w].describe()
                reply = f"Stats for '{w}': count={s['count']}, mean={s['mean']:.2f}, min={s['min']}, max={s['max']}"
            else:
                vals = df[w].value_counts().head(10)
                reply = f"Top values for '{w}':\n" + "\n".join([f"{idx}: {cnt}" for idx, cnt in vals.items()])
            return jsonify({"message": reply})

    # last resort: show insights
    return jsonify({"message": fallback_insights(df)})

# -------------------------
# ---- Frontend widget (Tailwind dark) served at /
# -------------------------
chatbot_widget = Markup("""
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>SmartFleet AI — Chat</title>
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
      .fade-in { animation: fadeIn 220ms ease-out; }
      @keyframes fadeIn { from { opacity: 0; transform: translateY(6px);} to { opacity: 1; transform: translateY(0);} }
      .scroll-smooth::-webkit-scrollbar { width: 8px; }
      .scroll-smooth::-webkit-scrollbar-thumb { background-color: rgba(255,255,255,0.12); border-radius: 4px; }
    </style>
  </head>
  <body class="bg-gray-900 text-gray-100">
    <div class="min-h-screen p-6">
      <h1 class="text-2xl font-semibold text-white">SmartFleet Dashboard — Chat Assistant</h1>
      <p class="text-sm text-gray-300 mt-2">Open the assistant at bottom-right to ask about trips, drivers, finances and upload Excel data.</p>
    </div>

    <!-- Chatbot Widget -->
    <div id="chatbot-container" class="fixed bottom-6 right-6 w-96 z-50">
      <div id="chatbot-card" class="shadow-2xl rounded-2xl overflow-hidden bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700">
        <div id="chatbot-header" class="flex items-center justify-between px-4 py-3 cursor-pointer bg-slate-800">
          <div class="flex items-center space-x-3">
            <div class="bg-blue-500 text-white rounded-full w-9 h-9 flex items-center justify-center text-lg font-bold">SF</div>
            <div>
              <div class="font-semibold text-white">SmartFleet Bot</div>
              <div class="text-xs text-slate-300">AI Assistant • Ask about trips or upload a file</div>
            </div>
          </div>
          <div class="flex items-center space-x-2">
            <button id="minimize-btn" class="text-slate-300 hover:text-white">—</button>
            <button id="close-btn" class="text-slate-300 hover:text-white">✕</button>
          </div>
        </div>

        <div id="chatbot-body" class="hidden flex flex-col h-[520px]">
          <div id="chat-messages" class="flex-1 overflow-y-auto p-4 space-y-3 scroll-smooth"></div>

          <div class="px-4 pb-4 pt-2 border-t border-slate-700">
            <div class="flex items-center space-x-2 mb-2">
              <label for="chat-excel" class="flex items-center space-x-2 cursor-pointer bg-slate-800 hover:bg-slate-700 px-3 py-2 rounded-lg text-sm">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 5v14m7-7H5"/></svg>
                <span class="text-slate-300">Upload Excel</span>
              </label>
              <input id="chat-excel" type="file" accept=".xlsx,.xls" class="hidden" />
              <button id="example-btn" class="ml-auto text-xs bg-blue-600 hover:bg-blue-700 px-3 py-2 rounded-lg">Example Queries</button>
            </div>

            <div class="flex space-x-2">
              <input id="chat-input" type="text" placeholder="Ask anything about trips, e.g. 'How many trips are ongoing?'" class="flex-1 px-3 py-2 rounded-lg bg-slate-800 text-white focus:outline-none" />
              <button id="chat-send" class="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg">Send</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <script>
      const header = document.getElementById('chatbot-header');
      const body = document.getElementById('chatbot-body');
      const messagesDiv = document.getElementById('chat-messages');
      const input = document.getElementById('chat-input');
      const sendBtn = document.getElementById('chat-send');
      const excelInput = document.getElementById('chat-excel');
      const closeBtn = document.getElementById('close-btn');
      const minimizeBtn = document.getElementById('minimize-btn');
      const exampleBtn = document.getElementById('example-btn');

      // collapsed by default: click header to toggle
      header.addEventListener('click', ()=>{ body.classList.toggle('hidden'); });

      closeBtn.addEventListener('click', ()=>{ body.classList.add('hidden'); });
      minimizeBtn.addEventListener('click', ()=>{ body.classList.toggle('hidden'); });

      function addUserMessage(text){
        const wrap = document.createElement('div');
        wrap.className = "flex justify-end";
        const msg = document.createElement('div');
        msg.className = "fade-in bg-blue-600 text-white px-3 py-2 rounded-lg max-w-[80%] whitespace-pre-wrap";
        msg.innerText = text;
        wrap.appendChild(msg);
        messagesDiv.appendChild(wrap);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
      }
      function addBotMessage(text){
        const wrap = document.createElement('div');
        wrap.className = "flex";
        const msg = document.createElement('div');
        msg.className = "fade-in bg-slate-800 text-slate-200 px-3 py-2 rounded-lg max-w-[80%] whitespace-pre-wrap";
        msg.innerText = text;
        wrap.appendChild(msg);
        messagesDiv.appendChild(wrap);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
      }

      // welcome
      addBotMessage("Hello! I'm SmartFleet AI 🤖\\nUpload an Excel file and ask about trips, drivers, financials and audits. Try: 'How many trips are ongoing?' or 'Show Trip ID T50382'.");

      async function sendMessage(){
        const msg = input.value.trim();
        if(!msg) return;
        addUserMessage(msg);
        input.value = '';
        try{
          const res = await fetch('/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message: msg})
          });
          const data = await res.json();
          addBotMessage(data.message || "No response.");
        }catch(e){
          addBotMessage("Error connecting to the bot. Please try again.");
        }
      }

      sendBtn.addEventListener('click', sendMessage);
      input.addEventListener('keydown', (e)=>{ if(e.key === 'Enter') sendMessage(); });

      // Excel upload handling
      excelInput.addEventListener('change', async (e)=> {
        const file = e.target.files[0];
        if(!file) return;
        addUserMessage(`Uploading Excel: ${file.name}`);
        const form = new FormData();
        form.append('file', file);
        try {
          const res = await fetch('/upload_excel', { method: 'POST', body: form });
          const data = await res.json();
          addBotMessage(data.message || "Upload successful.");
        } catch(err){
          addBotMessage("Upload failed. Try again.");
        }
      });

      // Example queries quick help
      exampleBtn.addEventListener('click', ()=> {
        const examples = [
          "How many trips are ongoing?",
          "Show Trip ID T50382",
          "Which trips have POD pending?",
          "List trips with freight > 5000",
          "Trips for driver DR001",
          "Show revenue",
        ];
        addBotMessage("Example queries:\\n- " + examples.join("\\n- "));
      });
    </script>
  </body>
</html>
""")

@app.route("/")
def home():
    return chatbot_widget

# ---- Run ----
if __name__ == "__main__":
    init_db()
    os.makedirs("uploads", exist_ok=True)
    
    app.run(host="0.0.0.0", port=5000, debug=True)







