from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify
import mysql.connector
from datetime import date, datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
import uuid
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

import sqlite3
import os

# Detect if running on Render
IS_RENDER = os.environ.get('RENDER', False)

# ==================== UPLOAD CONFIGURATION ====================
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==================== EMAIL CONFIGURATION ====================
EMAIL_ADDRESS = "nehakaurdgp001@gmail.com"
EMAIL_PASSWORD = "avoq feqn shxs ilai"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587

# ==================== DATABASE CONNECTION ====================
def get_db():
    if IS_RENDER:
        # On Render - use SQLite
        conn = sqlite3.connect('dogs.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Create all tables if they don't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert admin user (ONLY ONCE - keep this one)
        cursor.execute("SELECT * FROM users WHERE username = 'admin'")
        admin = cursor.fetchone()
        if not admin:
            cursor.execute("INSERT INTO users (username, password, email, role) VALUES ('admin', 'admin123', 'admin@streetdogwelfare.org', 'admin')")
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dogs (
                dog_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT NOT NULL,
                area TEXT,
                age TEXT,
                gender TEXT,
                health_status TEXT,
                vaccination INTEGER DEFAULT 0,
                sterilized INTEGER DEFAULT 0,
                personality TEXT,
                food_type TEXT,
                feeding_time TEXT,
                special_needs TEXT,
                image_path TEXT,
                status TEXT DEFAULT 'Available',
                created_date DATE,
                adopted_date DATE,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS donors (
                donor_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                city TEXT,
                donation_date DATE,
                amount REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS donations (
                donation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                donor_id INTEGER,
                dog_id INTEGER,
                amount REAL NOT NULL,
                purpose TEXT,
                donation_date DATE,
                status TEXT DEFAULT 'Completed',
                payment_id TEXT,
                FOREIGN KEY (donor_id) REFERENCES donors(donor_id),
                FOREIGN KEY (dog_id) REFERENCES dogs(dog_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS adoption_requests (
                request_id INTEGER PRIMARY KEY AUTOINCREMENT,
                dog_id INTEGER,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT,
                city TEXT,
                home_type TEXT,
                has_pets TEXT,
                reason TEXT,
                request_date DATE,
                status TEXT DEFAULT 'Pending',
                reviewed_by INTEGER,
                review_notes TEXT,
                reviewed_date TIMESTAMP,
                approved_date DATE,
                FOREIGN KEY (dog_id) REFERENCES dogs(dog_id),
                FOREIGN KEY (reviewed_by) REFERENCES users(user_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS volunteers (
                volunteer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                availability TEXT,
                skills TEXT,
                joined_date DATE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feeding_schedules (
                schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
                dog_id INTEGER,
                volunteer_id INTEGER,
                feeding_date DATE,
                feeding_time TEXT,
                food_provided TEXT,
                quantity TEXT,
                notes TEXT,
                completed INTEGER DEFAULT 0,
                FOREIGN KEY (dog_id) REFERENCES dogs(dog_id),
                FOREIGN KEY (volunteer_id) REFERENCES volunteers(volunteer_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                expense_id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_type TEXT,
                amount REAL,
                description TEXT,
                expense_date DATE,
                dog_id INTEGER,
                receipt_path TEXT,
                FOREIGN KEY (dog_id) REFERENCES dogs(dog_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contact_messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT,
                phone TEXT,
                subject TEXT,
                message TEXT,
                category TEXT,
                sent_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_read INTEGER DEFAULT 0,
                replied INTEGER DEFAULT 0
            )
        ''')
        
        # Insert sample dogs if table is empty
        cursor.execute("SELECT COUNT(*) FROM dogs")
        dog_count = cursor.fetchone()[0]
        if dog_count == 0:
            cursor.execute('''
                INSERT INTO dogs (name, location, area, age, gender, health_status, vaccination, sterilized, personality, food_type, feeding_time, status, created_date)
                VALUES 
                ('Tommy', 'MG Road near Coffee Day', 'MG Road Zone', 'Adult', 'Male', 'Healthy', 1, 1, 'Friendly, loves people', 'Dry Food', 'Evening', 'Available', date('now')),
                ('Brownie', 'Central Park near Bench', 'Central Park', 'Puppy', 'Female', 'Injured', 0, 0, 'Shy but gentle', 'Milk + Soft food', 'Morning', 'Available', date('now')),
                ('Blacky', 'Railway Station Platform 1', 'Railway Station', 'Adult', 'Male', 'Vaccinated', 1, 1, 'Protective, loyal', 'Dry Food', 'Both', 'Available', date('now'))
            ''')
        
        conn.commit()
        return conn
    else:
        # On your computer - use MySQL
        import mysql.connector
        return mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='street_dog_welfare'
        )
# ==================== EMAIL FUNCTIONS ====================
def send_email(to_email, subject, message):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'html'))
        
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def send_donation_email(name, email, amount, purpose, transaction_id):
    subject = f"Thank You for Your Donation of ₹{amount}!"
    meals = int(amount / 50)
    message = f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <div style="max-width: 600px; margin: auto; padding: 20px; background: #f9f9f9; border-radius: 10px;">
            <h1 style="color: #667eea;">🐕 Thank You, {name}!</h1>
            <p>Your donation of <strong>₹{amount}</strong> has been received successfully.</p>
            <p><strong>Transaction ID:</strong> {transaction_id}</p>
            <p><strong>Purpose:</strong> {purpose}</p>
            <hr>
            <p>Your support helps us provide:</p>
            <ul>
                <li>🍖 Food for <strong>{meals}</strong> street dogs</li>
                <li>💊 Medical care for injured dogs</li>
                <li>🏠 Shelter for abandoned dogs</li>
            </ul>
            <p>You're making a real difference in their lives!</p>
            <br>
            <p>With gratitude,<br><strong>Street Dog Welfare Trust</strong></p>
        </div>
    </body>
    </html>
    """
    return send_email(email, subject, message)

def send_adoption_email(name, email, dog_name):
    subject = f"Adoption Application Received - {dog_name}"
    message = f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <div style="max-width: 600px; margin: auto; padding: 20px; background: #f9f9f9; border-radius: 10px;">
            <h1 style="color: #667eea;">🏠 Adoption Application Received</h1>
            <p>Dear {name},</p>
            <p>Thank you for your interest in adopting <strong>{dog_name}</strong>!</p>
            <p>Our team will review your application within 2-3 business days.</p>
            <p><strong>Next Steps:</strong> Phone interview → Home visit → Meet the dog → Adoption finalization</p>
            <br>
            <p>Thank you for giving a street dog a second chance! 🐕</p>
            <p><strong>Street Dog Welfare Trust</strong></p>
        </div>
    </body>
    </html>
    """
    return send_email(email, subject, message)

def send_volunteer_email(name, email):
    subject = "Welcome to Street Dog Welfare Volunteer Team!"
    message = f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <div style="max-width: 600px; margin: auto; padding: 20px; background: #f9f9f9; border-radius: 10px;">
            <h1 style="color: #667eea;">🤝 Welcome to the Team, {name}!</h1>
            <p>Thank you for joining us as a volunteer!</p>
            <p>Our volunteer coordinator will contact you within 48 hours.</p>
            <p>Together, we can make a difference! 🐕</p>
            <br>
            <p>Warm regards,<br><strong>Street Dog Welfare Team</strong></p>
        </div>
    </body>
    </html>
    """
    return send_email(email, subject, message)

# ==================== HOMEPAGE ====================
@app.route('/')
def index():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM dogs")
    total_dogs = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM dogs WHERE status = 'Available'")
    available_dogs = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(amount) FROM donations")
    total_donations = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM volunteers")
    total_volunteers = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM adoption_requests WHERE status = 'Pending'")
    pending_adoptions = cursor.fetchone()[0]
    
    cursor.execute("SELECT dog_id, name, location, age, health_status, image_path FROM dogs WHERE status = 'Available' ORDER BY created_date DESC LIMIT 6")
    recent_dogs = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    html = f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Street Dog Welfare - Give Them a Second Chance</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        
        .navbar {{ background: white; padding: 15px 30px; border-radius: 15px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; box-shadow: 0 5px 20px rgba(0,0,0,0.1); }}
        .logo {{ font-size: 24px; font-weight: bold; color: #667eea; }}
        .logo span {{ color: #764ba2; }}
        .nav-links {{ display: flex; flex-wrap: wrap; gap: 10px; }}
        .nav-links a {{ color: #333; text-decoration: none; padding: 8px 16px; border-radius: 8px; transition: 0.3s; font-weight: 500; }}
        .nav-links a:hover {{ background: #667eea; color: white; }}
        
        .hero {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 60px 40px; border-radius: 20px; text-align: center; margin-bottom: 30px; }}
        .hero h1 {{ font-size: 48px; margin-bottom: 20px; }}
        .hero p {{ font-size: 18px; margin-bottom: 30px; opacity: 0.9; }}
        .btn {{ display: inline-block; padding: 12px 30px; background: white; color: #667eea; text-decoration: none; border-radius: 50px; font-weight: bold; margin: 0 10px; transition: 0.3s; }}
        .btn:hover {{ transform: translateY(-3px); box-shadow: 0 10px 20px rgba(0,0,0,0.2); }}
        
        .card {{ background: white; border-radius: 15px; padding: 25px; margin-bottom: 25px; box-shadow: 0 5px 20px rgba(0,0,0,0.1); }}
        .card h2 {{ color: #333; margin-bottom: 20px; border-left: 4px solid #667eea; padding-left: 15px; }}
        
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .stat-card {{ background: white; padding: 25px; border-radius: 15px; text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.1); transition: transform 0.3s; }}
        .stat-card:hover {{ transform: translateY(-5px); }}
        .stat-number {{ font-size: 36px; font-weight: bold; color: #667eea; }}
        .stat-label {{ color: #666; margin-top: 10px; }}
        
        .dog-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 25px; margin-top: 20px; }}
        .dog-card {{ background: white; border-radius: 15px; overflow: hidden; box-shadow: 0 5px 15px rgba(0,0,0,0.1); transition: transform 0.3s; }}
        .dog-card:hover {{ transform: translateY(-5px); }}
        .dog-image {{ width: 100%; height: 200px; background-size: cover; background-position: center; background-color: #f0f0f0; }}
        .dog-info {{ padding: 15px; }}
        .dog-info h3 {{ color: #333; margin-bottom: 10px; }}
        .dog-info p {{ color: #666; margin-bottom: 8px; font-size: 14px; }}
        .badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; background: #27ae60; color: white; }}
        .dog-actions {{ display: flex; gap: 10px; margin-top: 15px; }}
        .btn-small {{ flex: 1; text-align: center; padding: 8px; background: #667eea; color: white; text-decoration: none; border-radius: 8px; font-size: 12px; transition: 0.3s; }}
        .btn-small:hover {{ background: #764ba2; }}
        
        .footer {{ background: white; padding: 30px; text-align: center; border-radius: 15px; margin-top: 30px; color: #666; }}
        
        @media (max-width: 768px) {{ .navbar {{ flex-direction: column; gap: 15px; }} .hero h1 {{ font-size: 32px; }} .stats-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
    </style>
</head>
<body>
    <div class="container">
        <div class="navbar">
            <div class="logo">🐕 Street Dog <span>Welfare</span></div>
            <div class="nav-links">
                <a href="/">🏠 Home</a>
                <a href="/dogs">🐕 Dogs</a>
                <a href="/donate">💰 Donate</a>
                <a href="/adopt">🏠 Adopt</a>
                <a href="/volunteer">🤝 Volunteer</a>
                <a href="/register_dog">📢 Report Dog</a>
                <a href="/admin">🔐 Admin</a>
            </div>
        </div>
        
        <div class="hero">
            <h1>Give Street Dogs a Second Chance</h1>
            <p>Every dog deserves a loving home and proper care. Join us in making a difference!</p>
            <a href="/donate" class="btn">💰 Donate Now</a>
            <a href="/adopt" class="btn">🏠 Adopt a Dog</a>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card"><div class="stat-number">{total_dogs}</div><div class="stat-label">🐕 Dogs Rescued</div></div>
            <div class="stat-card"><div class="stat-number">{available_dogs}</div><div class="stat-label">🏠 Available for Adoption</div></div>
            <div class="stat-card"><div class="stat-number">₹{int(total_donations)}</div><div class="stat-label">💰 Total Donations</div></div>
            <div class="stat-card"><div class="stat-number">{total_volunteers}</div><div class="stat-label">🤝 Active Volunteers</div></div>
            <div class="stat-card"><div class="stat-number">{pending_adoptions}</div><div class="stat-label">📝 Adoption Requests</div></div>
        </div>
        
        <div class="card">
            <h2>🐕 Dogs Looking for Forever Homes</h2>
            <div class="dog-grid">
    '''
    
    for dog in recent_dogs:
        dog_id = dog[0]
        dog_name = dog[1]
        dog_location = dog[2]
        dog_age = dog[3]
        dog_health = dog[4]
        image_path = dog[5] if dog[5] else 'static/images/default_dog.jpg'
        
        html += f'''
                <div class="dog-card">
                    <div class="dog-image" style="background-image: url('/{image_path}');"></div>
                    <div class="dog-info">
                        <h3>{dog_name}</h3>
                        <p>📍 Location: {dog_location}</p>
                        <p>🎂 Age: {dog_age}</p>
                        <p><span class="badge">{dog_health}</span></p>
                        <div class="dog-actions">
                            <a href="/dog/{dog_id}" class="btn-small">View Details</a>
                            <a href="/adopt/{dog_id}" class="btn-small">Adopt Me</a>
                        </div>
                    </div>
                </div>
        '''
    
    html += '''
            </div>
        </div>
        
        <div class="footer">
            <p>🐕 Street Dog Welfare Trust | Giving Street Dogs a Second Chance</p>
            <p style="margin-top: 10px;">📍 Bangalore | 📞 +91 80 1234 5678 | 📧 hello@streetdogwelfare.org</p>
            <p style="margin-top: 5px; font-size: 12px;">❤️ Every donation helps save a life</p>
        </div>
    </div>
</body>
</html>
    '''
    return html

# ==================== VIEW ALL DOGS ====================
@app.route('/dogs')
def dogs():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT dog_id, name, location, age, health_status, status, image_path FROM dogs ORDER BY dog_id")
    all_dogs = cursor.fetchall()
    cursor.close()
    conn.close()
    
    html = '''
<!DOCTYPE html>
<html>
<head>
    <title>All Dogs - Street Dog Welfare</title>
    <style>
        body { font-family: 'Segoe UI', Arial; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); margin: 0; padding: 20px; }
        .container { max-width: 1200px; margin: auto; background: white; border-radius: 20px; padding: 30px; }
        h1 { color: #333; margin-bottom: 20px; border-left: 4px solid #667eea; padding-left: 15px; }
        .dog-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 25px; margin-top: 20px; }
        .dog-card { background: white; border-radius: 15px; overflow: hidden; box-shadow: 0 5px 15px rgba(0,0,0,0.1); transition: transform 0.3s; }
        .dog-card:hover { transform: translateY(-5px); }
        .dog-image { width: 100%; height: 200px; background-size: cover; background-position: center; }
        .dog-info { padding: 15px; }
        .dog-info h3 { margin-bottom: 10px; color: #333; }
        .dog-info p { color: #666; margin-bottom: 8px; font-size: 14px; }
        .badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; background: #27ae60; color: white; }
        .dog-actions { display: flex; gap: 10px; margin-top: 15px; }
        .btn { background: #667eea; color: white; padding: 8px 15px; text-decoration: none; border-radius: 5px; display: inline-block; font-size: 12px; }
        .btn:hover { background: #764ba2; }
        .back-btn { margin-bottom: 20px; display: inline-block; }
    </style>
</head>
<body>
<div class="container">
    <a href="/" class="btn back-btn">← Back to Home</a>
    <h1>🐕 All Registered Dogs</h1>
    <div class="dog-grid">
    '''
    
    for dog in all_dogs:
        image_path = dog[6] if dog[6] else 'static/images/default_dog.jpg'
        html += f'''
        <div class="dog-card">
            <div class="dog-image" style="background-image: url('/{image_path}');"></div>
            <div class="dog-info">
                <h3>{dog[1]}</h3>
                <p>📍 {dog[2]}</p>
                <p>🎂 {dog[3]}</p>
                <p><span class="badge">{dog[4]}</span></p>
                <div class="dog-actions">
                    <a href="/dog/{dog[0]}" class="btn">View Details</a>
                    <a href="/adopt/{dog[0]}" class="btn">Adopt</a>
                </div>
            </div>
        </div>
        '''
    
    html += '''
    </div>
</div>
</body>
</html>
    '''
    return html

# ==================== DOG DETAILS ====================
@app.route('/dog/<int:dog_id>')
def dog_detail(dog_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM dogs WHERE dog_id = %s", (dog_id,))
    dog = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not dog:
        return "<h1>Dog not found</h1><a href='/'>Go Home</a>"
    
    # Column indices based on your table structure
    # 0:dog_id, 1:name, 2:location, 3:area, 4:age, 5:gender, 6:health_status, 
    # 7:vaccination, 8:sterilized, 9:personality, 10:food_type, 11:feeding_time, 
    # 12:special_needs, 13:image_path, 14:status, 15:created_date
    
    image_path = dog[13] if dog[13] else 'static/images/default_dog.jpg'
    
    html = f'''
<!DOCTYPE html>
<html>
<head>
    <title>{dog[1]} - Street Dog Welfare</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); margin: 0; padding: 20px; }}
        .container {{ max-width: 800px; margin: auto; background: white; border-radius: 20px; padding: 30px; }}
        h1 {{ text-align: center; color: #333; }}
        .dog-image {{ 
            width: 300px; 
            height: 300px; 
            background-image: url('/{image_path}');
            background-size: cover;
            background-position: center;
            border-radius: 20px;
            margin: 0 auto 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        .info {{ margin: 20px 0; }}
        .info p {{ padding: 10px; border-bottom: 1px solid #eee; }}
        .label {{ font-weight: bold; color: #667eea; width: 140px; display: inline-block; }}
        .btn {{ background: #667eea; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px 5px; }}
        .btn:hover {{ background: #764ba2; }}
    </style>
</head>
<body>
<div class="container">
    <a href="/dogs" class="btn">← Back to Dogs</a>
    <div class="dog-image"></div>
    <h1>{dog[1]}</h1>
    <div class="info">
        <p><span class="label">📍 Location:</span> {dog[2] if dog[2] else 'Not specified'}</p>
        <p><span class="label">📍 Area:</span> {dog[3] if dog[3] else 'Not specified'}</p>
        <p><span class="label">🎂 Age:</span> {dog[4] if dog[4] else 'Unknown'}</p>
        <p><span class="label">⚥ Gender:</span> {dog[5] if dog[5] else 'Unknown'}</p>
        <p><span class="label">💊 Health:</span> {dog[6] if dog[6] else 'Unknown'}</p>
        <p><span class="label">💉 Vaccination:</span> {'✅ Yes' if dog[7] else '❌ No'}</p>
        <p><span class="label">✂️ Sterilized:</span> {'✅ Yes' if dog[8] else '❌ No'}</p>
        <p><span class="label">🍖 Food Type:</span> {dog[10] if dog[10] else 'Not specified'}</p>
        <p><span class="label">⏰ Feeding Time:</span> {dog[11] if dog[11] else 'Not specified'}</p>
        <p><span class="label">📝 Special Needs:</span> {dog[12] if dog[12] else 'None'}</p>
        <p><span class="label">📅 Registered:</span> {dog[15] if dog[15] else 'Unknown'}</p>
        <p><span class="label">🏷️ Status:</span> <strong style="color: {'#27ae60' if dog[14] == 'Available' else '#f39c12'}">{dog[14]}</strong></p>
    </div>
    <div style="text-align: center;">
        <a href="/adopt/{dog[0]}" class="btn">🏠 Adopt {dog[1]}</a>
        <a href="/donate?dog_id={dog[0]}" class="btn">💰 Donate for {dog[1]}</a>
    </div>
</div>
</body>
</html>
    '''
    return html

# ==================== DONATION PAGE ====================
@app.route('/donate', methods=['GET', 'POST'])
def donate():
    dog_id = request.args.get('dog_id')
    dog_name = ""
    
    if dog_id:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM dogs WHERE dog_id = %s", (dog_id,))
        dog = cursor.fetchone()
        if dog:
            dog_name = dog[0]
        cursor.close()
        conn.close()
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        city = request.form['city']
        amount = float(request.form['amount'])
        purpose = request.form['purpose']
        dog_id = request.form.get('dog_id')
        
        transaction_id = f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO donors (name, email, phone, city, donation_date, amount)
            VALUES (%s, %s, %s, %s, CURDATE(), %s)
        """, (name, email, phone, city, amount))
        donor_id = cursor.lastrowid
        
        dog_id_val = int(dog_id) if dog_id and dog_id != '' else None
        cursor.execute("""
            INSERT INTO donations (donor_id, dog_id, amount, purpose, donation_date, status, payment_id)
            VALUES (%s, %s, %s, %s, CURDATE(), 'Completed', %s)
        """, (donor_id, dog_id_val, amount, purpose, transaction_id))
        
        conn.commit()
        
        cursor.execute("SELECT SUM(amount) FROM donations")
        total = cursor.fetchone()[0] or 0
        cursor.close()
        conn.close()
        
        send_donation_email(name, email, amount, purpose, transaction_id)
        
        meals = int(amount / 50)
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Thank You - Street Dog Welfare</title>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ font-family: 'Segoe UI', Arial; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; }}
                .container {{ background: white; max-width: 500px; margin: 50px auto; padding: 40px; border-radius: 20px; text-align: center; box-shadow: 0 20px 40px rgba(0,0,0,0.2); }}
                h1 {{ color: #27ae60; margin-bottom: 20px; }}
                .amount {{ font-size: 36px; color: #667eea; margin: 20px 0; }}
                .btn {{ background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 50px; display: inline-block; margin-top: 20px; }}
                .btn:hover {{ background: #764ba2; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎉 Thank You, {name}!</h1>
                <div class="amount">₹{amount:,.0f}</div>
                <p>Your donation can provide <strong>{meals} meals</strong> for street dogs!</p>
                <p>Total raised: <strong>₹{total:,.0f}</strong></p>
                <p>📧 Receipt sent to <strong>{email}</strong></p>
                <a href="/" class="btn">🏠 Return Home</a>
            </div>
        </body>
        </html>
        '''
    
    html = f'''
<!DOCTYPE html>
<html>
<head>
    <title>Donate - Street Dog Welfare</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Arial; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 40px 20px; }}
        .container {{ max-width: 500px; margin: 0 auto; background: white; border-radius: 20px; padding: 40px; box-shadow: 0 20px 40px rgba(0,0,0,0.2); }}
        h1 {{ color: #333; margin-bottom: 10px; border-left: 4px solid #667eea; padding-left: 15px; }}
        input, select {{ width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 10px; font-size: 14px; }}
        .btn {{ width: 100%; background: #667eea; color: white; padding: 14px; border: none; border-radius: 10px; font-size: 16px; cursor: pointer; margin-top: 20px; font-weight: bold; }}
        .btn:hover {{ background: #764ba2; }}
        .back-btn {{ display: inline-block; margin-bottom: 20px; color: #667eea; text-decoration: none; }}
        .info {{ background: #f0f0f0; padding: 15px; border-radius: 10px; margin-top: 20px; text-align: center; }}
        .dog-info {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px; border-radius: 10px; margin-bottom: 20px; text-align: center; }}
    </style>
</head>
<body>
<div class="container">
    <a href="/" class="back-btn">← Back to Home</a>
    <h1>💰 Make a Donation</h1>
    {f'<div class="dog-info">🐕 Donating for: <strong>{dog_name}</strong></div>' if dog_name else ''}
    
    <form method="POST">
        <input type="hidden" name="dog_id" value="{dog_id if dog_id else ''}">
        <input type="text" name="name" placeholder="Your Full Name" required>
        <input type="email" name="email" placeholder="Email Address" required>
        <input type="tel" name="phone" placeholder="Phone Number">
        <input type="text" name="city" placeholder="City">
        <input type="number" name="amount" placeholder="Amount (₹)" required>
        <select name="purpose">
            <option value="General">General Fund (For all dogs)</option>
            <option value="Food">Food (₹50 per meal)</option>
            <option value="Medical">Medical Care</option>
            <option value="Shelter">Shelter</option>
            {"<option value='Specific Dog'>For " + dog_name + "</option>" if dog_name else ""}
        </select>
        <button type="submit" class="btn">💝 Donate Now</button>
    </form>
    
    <div class="info">
        <p>💡 ₹50 = 1 meal for a dog</p>
        <p>💡 ₹500 = 1 week of food</p>
        <p>💡 ₹1500 = Vaccination for a dog</p>
        <p>📧 You'll receive an email receipt</p>
    </div>
</div>
</body>
</html>
    '''
    return html

# ==================== ADOPTION PAGE ====================
@app.route('/adopt')
@app.route('/adopt/<dog_id>')
def adopt(dog_id=None):
    conn = get_db()
    cursor = conn.cursor()
    
    dog_name = "Not Specified"
    dog_id_value = None
    
    if dog_id and dog_id != 'None':
        cursor.execute("SELECT name FROM dogs WHERE dog_id = %s", (dog_id,))
        dog = cursor.fetchone()
        if dog:
            dog_name = dog[0]
            dog_id_value = dog_id
    
    cursor.close()
    conn.close()
    
    html = f'''
<!DOCTYPE html>
<html>
<head>
    <title>Adopt a Dog - Street Dog Welfare</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Arial; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 40px 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 20px; padding: 40px; box-shadow: 0 20px 40px rgba(0,0,0,0.2); }}
        h1 {{ color: #333; margin-bottom: 10px; border-left: 4px solid #667eea; padding-left: 15px; }}
        .dog-info {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 15px; margin: 20px 0; text-align: center; }}
        input, textarea {{ width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 10px; font-family: inherit; }}
        .btn {{ width: 100%; background: #667eea; color: white; padding: 14px; border: none; border-radius: 10px; font-size: 16px; cursor: pointer; margin-top: 20px; font-weight: bold; }}
        .btn:hover {{ background: #764ba2; }}
        .back-btn {{ display: inline-block; margin-bottom: 20px; color: #667eea; text-decoration: none; }}
        .form-group {{ margin-bottom: 15px; }}
        label {{ font-weight: 600; color: #333; display: block; margin-bottom: 5px; }}
    </style>
</head>
<body>
<div class="container">
    <a href="/" class="back-btn">← Back to Home</a>
    <h1>🏠 Adopt a Dog</h1>
    <div class="dog-info">
        <p>🐕 <strong>You are applying to adopt:</strong></p>
        <p style="font-size: 24px;">{dog_name}</p>
    </div>
    
    <form method="POST" action="/adopt_submit">
        <input type="hidden" name="dog_id" value="{dog_id_value if dog_id_value else ''}">
        
        <div class="form-group">
            <label>Full Name *</label>
            <input type="text" name="full_name" placeholder="Enter your full name" required>
        </div>
        
        <div class="form-group">
            <label>Email Address *</label>
            <input type="email" name="email" placeholder="you@example.com" required>
        </div>
        
        <div class="form-group">
            <label>Phone Number *</label>
            <input type="tel" name="phone" placeholder="9876543210" required>
        </div>
        
        <div class="form-group">
            <label>Address</label>
            <textarea name="address" placeholder="Your complete address" rows="3"></textarea>
        </div>
        
        <div class="form-group">
            <label>City</label>
            <input type="text" name="city" placeholder="City name">
        </div>
        
        <div class="form-group">
            <label>Home Type</label>
            <input type="text" name="home_type" placeholder="Apartment / House / Villa">
        </div>
        
        <div class="form-group">
            <label>Do you have other pets?</label>
            <input type="text" name="has_pets" placeholder="Yes / No">
        </div>
        
        <div class="form-group">
            <label>Why do you want to adopt this dog? *</label>
            <textarea name="reason" placeholder="Tell us why you'd like to adopt..." rows="3" required></textarea>
        </div>
        
        <button type="submit" class="btn">📝 Submit Application</button>
    </form>
</div>
</body>
</html>
    '''
    return html

# ==================== ADOPTION SUBMISSION ====================
@app.route('/adopt_submit', methods=['POST'])
def adopt_submit():
    dog_id = request.form.get('dog_id')
    full_name = request.form['full_name']
    email = request.form['email']
    phone = request.form['phone']
    address = request.form.get('address', '')
    city = request.form.get('city', '')
    home_type = request.form.get('home_type', '')
    has_pets = request.form.get('has_pets', '')
    reason = request.form.get('reason', '')
    
    conn = get_db()
    cursor = conn.cursor()
    
    dog_name = "a dog"
    
    if dog_id and dog_id.strip():
        cursor.execute("SELECT name FROM dogs WHERE dog_id = %s", (dog_id,))
        dog = cursor.fetchone()
        if dog:
            dog_name = dog[0]
            cursor.execute("""
                INSERT INTO adoption_requests (dog_id, full_name, email, phone, address, city, home_type, has_pets, reason, request_date, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURDATE(), 'Pending')
            """, (dog_id, full_name, email, phone, address, city, home_type, has_pets, reason))
            cursor.execute("UPDATE dogs SET status = 'Pending Adoption' WHERE dog_id = %s", (dog_id,))
        else:
            cursor.execute("""
                INSERT INTO adoption_requests (dog_id, full_name, email, phone, address, city, home_type, has_pets, reason, request_date, status)
                VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, CURDATE(), 'Pending')
            """, (full_name, email, phone, address, city, home_type, has_pets, reason))
    else:
        cursor.execute("""
            INSERT INTO adoption_requests (dog_id, full_name, email, phone, address, city, home_type, has_pets, reason, request_date, status)
            VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, CURDATE(), 'Pending')
        """, (full_name, email, phone, address, city, home_type, has_pets, reason))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    send_adoption_email(full_name, email, dog_name)
    
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Application Submitted - Street Dog Welfare</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Segoe UI', Arial; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; }
            .container { background: white; max-width: 500px; margin: 50px auto; padding: 40px; border-radius: 20px; text-align: center; box-shadow: 0 20px 40px rgba(0,0,0,0.2); }
            h1 { color: #27ae60; margin-bottom: 20px; }
            p { color: #666; margin-bottom: 30px; line-height: 1.6; }
            .btn { background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 50px; display: inline-block; }
            .btn:hover { background: #764ba2; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>✅ Application Submitted!</h1>
            <p>Thank you for your interest in adopting.<br>
            A confirmation email has been sent to your inbox.<br>
            Our team will contact you within 2-3 days.</p>
            <a href="/" class="btn">🏠 Return Home</a>
        </div>
    </body>
    </html>
    '''

# ==================== VOLUNTEER PAGE ====================
@app.route('/volunteer', methods=['GET', 'POST'])
def volunteer():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        availability = request.form.get('availability', '')
        skills = request.form.get('skills', '')
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO volunteers (name, email, phone, availability, skills, joined_date)
            VALUES (%s, %s, %s, %s, %s, CURDATE())
        """, (name, email, phone, availability, skills))
        conn.commit()
        cursor.close()
        conn.close()
        
        send_volunteer_email(name, email)
        
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Welcome - Street Dog Welfare</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { font-family: 'Segoe UI', Arial; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; }
                .container { background: white; max-width: 500px; margin: 50px auto; padding: 40px; border-radius: 20px; text-align: center; box-shadow: 0 20px 40px rgba(0,0,0,0.2); }
                h1 { color: #27ae60; margin-bottom: 20px; }
                p { color: #666; margin-bottom: 30px; line-height: 1.6; }
                .btn { background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 50px; display: inline-block; }
                .btn:hover { background: #764ba2; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤝 Welcome to the Team!</h1>
                <p>Thank you for volunteering! A welcome email has been sent.<br>
                Our coordinator will contact you within 48 hours.</p>
                <a href="/" class="btn">🏠 Return Home</a>
            </div>
        </body>
        </html>
        '''
    
    html = '''
<!DOCTYPE html>
<html>
<head>
    <title>Volunteer - Street Dog Welfare</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Arial; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 40px 20px; }
        .container { max-width: 500px; margin: 0 auto; background: white; border-radius: 20px; padding: 40px; box-shadow: 0 20px 40px rgba(0,0,0,0.2); }
        h1 { color: #333; margin-bottom: 10px; border-left: 4px solid #667eea; padding-left: 15px; }
        input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 10px; font-size: 14px; }
        .btn { width: 100%; background: #667eea; color: white; padding: 14px; border: none; border-radius: 10px; font-size: 16px; cursor: pointer; margin-top: 20px; font-weight: bold; }
        .btn:hover { background: #764ba2; }
        .back-btn { display: inline-block; margin-bottom: 20px; color: #667eea; text-decoration: none; }
        .info { background: #f0f0f0; padding: 15px; border-radius: 10px; margin-top: 20px; text-align: center; }
    </style>
</head>
<body>
<div class="container">
    <a href="/" class="back-btn">← Back to Home</a>
    <h1>🤝 Become a Volunteer</h1>
    <form method="POST">
        <input type="text" name="name" placeholder="Full Name" required>
        <input type="email" name="email" placeholder="Email Address" required>
        <input type="tel" name="phone" placeholder="Phone Number" required>
        <input type="text" name="availability" placeholder="Availability (Morning/Evening/Weekend)">
        <input type="text" name="skills" placeholder="Skills (Feeding/Medical/Transport)">
        <button type="submit" class="btn">Join Us</button>
    </form>
    <div class="info">
        <p>💡 As a volunteer you can:</p>
        <p>• Feed street dogs in your area</p>
        <p>• Help with medical care</p>
        <p>• Transport dogs to shelters</p>
        <p>📧 You'll receive a welcome email</p>
    </div>
</div>
</body>
</html>
    '''
    return html

# ==================== REGISTER DOG PAGE ====================
@app.route('/register_dog', methods=['GET', 'POST'])
def register_dog():
    if request.method == 'POST':
        name = request.form.get('name', 'Unknown')
        location = request.form['location']
        area = request.form.get('area', '')
        age = request.form.get('age', '')
        gender = request.form.get('gender', '')
        health_status = request.form.get('health_status', '')
        food_type = request.form.get('food_type', '')
        feeding_time = request.form.get('feeding_time', '')
        special_needs = request.form.get('special_needs', '')
        
        # Handle image upload
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                
                # Create upload folder if not exists
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = f"{app.config['UPLOAD_FOLDER']}/{filename}"
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO dogs (name, location, area, age, gender, health_status, food_type, feeding_time, special_needs, image_path, status, created_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Available', CURDATE())
        """, (name, location, area, age, gender, health_status, food_type, feeding_time, special_needs, image_path))
        conn.commit()
        cursor.close()
        conn.close()
        
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Dog Registered - Street Dog Welfare</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { font-family: 'Segoe UI', Arial; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; }
                .container { background: white; max-width: 500px; margin: 50px auto; padding: 40px; border-radius: 20px; text-align: center; box-shadow: 0 20px 40px rgba(0,0,0,0.2); }
                h1 { color: #27ae60; margin-bottom: 20px; }
                p { color: #666; margin-bottom: 30px; line-height: 1.6; }
                .btn { background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 50px; display: inline-block; }
                .btn:hover { background: #764ba2; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🐕 Dog Registered Successfully!</h1>
                <p>Thank you for reporting. Our team will check on the dog soon.</p>
                <a href="/" class="btn">🏠 Return Home</a>
            </div>
        </body>
        </html>
        '''
    
    html = '''
<!DOCTYPE html>
<html>
<head>
    <title>Register a Dog - Street Dog Welfare</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Arial; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 40px 20px; }
        .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 20px; padding: 40px; box-shadow: 0 20px 40px rgba(0,0,0,0.2); }
        h1 { color: #333; margin-bottom: 10px; border-left: 4px solid #667eea; padding-left: 15px; }
        input, select, textarea { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 10px; font-size: 14px; font-family: inherit; }
        input[type="file"] { padding: 8px; }
        .btn { width: 100%; background: #667eea; color: white; padding: 14px; border: none; border-radius: 10px; font-size: 16px; cursor: pointer; margin-top: 20px; font-weight: bold; }
        .btn:hover { background: #764ba2; }
        .back-btn { display: inline-block; margin-bottom: 20px; color: #667eea; text-decoration: none; }
        .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        .image-preview { max-width: 200px; margin: 10px 0; display: none; border-radius: 10px; }
        @media (max-width: 600px) { .form-row { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
<div class="container">
    <a href="/" class="back-btn">← Back to Home</a>
    <h1>📢 Report a Street Dog</h1>
    <p style="margin-bottom: 20px;">Help us identify dogs that need food, medical care, or a loving home.</p>
    <form method="POST" enctype="multipart/form-data">
        <input type="text" name="name" placeholder="Dog Name (optional)">
        <input type="text" name="location" placeholder="Location * (e.g., MG Road near Coffee Shop)" required>
        <input type="text" name="area" placeholder="Area/Zone (e.g., MG Road Zone)">
        <div class="form-row">
            <select name="age">
                <option value="">Select Age</option>
                <option>Puppy</option>
                <option>Young</option>
                <option>Adult</option>
                <option>Senior</option>
            </select>
            <select name="gender">
                <option value="">Select Gender</option>
                <option>Male</option>
                <option>Female</option>
            </select>
        </div>
        <select name="health_status">
            <option value="">Health Status</option>
            <option>Healthy</option>
            <option>Injured</option>
            <option>Sick</option>
            <option>Vaccinated</option>
        </select>
        <div class="form-row">
            <select name="food_type">
                <option value="">Food Type</option>
                <option>Dry Food</option>
                <option>Wet Food</option>
                <option>Milk</option>
                <option>Both</option>
            </select>
            <select name="feeding_time">
                <option value="">Feeding Time</option>
                <option>Morning</option>
                <option>Evening</option>
                <option>Both</option>
            </select>
        </div>
        <textarea name="special_needs" placeholder="Special Needs / Additional Info" rows="3"></textarea>
        <input type="file" name="image" accept="image/*" onchange="previewImage(this)">
        <img id="preview" class="image-preview" alt="Preview">
        <button type="submit" class="btn">🐕 Register Dog</button>
    </form>
</div>
<script>
function previewImage(input) {
    var preview = document.getElementById('preview');
    if (input.files && input.files[0]) {
        var reader = new FileReader();
        reader.onload = function(e) {
            preview.src = e.target.result;
            preview.style.display = 'block';
        }
        reader.readAsDataURL(input.files[0]);
    }
}
</script>
</body>
</html>
    '''
    return html

# ==================== ADMIN PANEL ====================

# Admin login page
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db()
        cursor = conn.cursor()
        # Use ? for SQLite compatibility
        cursor.execute("SELECT user_id, role FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user and user[1] == 'admin':
            session['admin_logged_in'] = True
            session['admin_id'] = user[0]
            return redirect(url_for('admin_dashboard'))
        else:
            return '''
            <script>
                alert('Invalid credentials!');
                window.location.href = '/admin/login';
            </script>
            '''
    
    return ''' [rest of your login HTML] '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Login - Street Dog Welfare</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Segoe UI', Arial; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; }
            .container { background: white; max-width: 400px; margin: auto; padding: 40px; border-radius: 20px; box-shadow: 0 20px 40px rgba(0,0,0,0.2); }
            h1 { color: #333; margin-bottom: 30px; text-align: center; }
            input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 10px; }
            .btn { width: 100%; background: #667eea; color: white; padding: 12px; border: none; border-radius: 10px; cursor: pointer; font-size: 16px; }
            .btn:hover { background: #764ba2; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔐 Admin Login</h1>
            <form method="POST">
                <input type="text" name="username" placeholder="Username" required>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit" class="btn">Login</button>
            </form>
            <!-- <p style="text-align: center; margin-top: 20px;">Demo: admin / admin123</p> -->
        </div>
    </body>
    </html>
    '''

# Admin dashboard
@app.route('/admin')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM dogs")
    total_dogs = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM dogs WHERE status = 'Available'")
    available_dogs = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(amount) FROM donations")
    total_donations = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM volunteers")
    total_volunteers = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM adoption_requests WHERE status = 'Pending'")
    pending_adoptions = cursor.fetchone()[0]
    
    cursor.execute("SELECT dog_id, name, location, health_status, image_path, status FROM dogs ORDER BY dog_id DESC LIMIT 10")
    recent_dogs = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Dashboard - Street Dog Welfare</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: 'Segoe UI', Arial; background: #f5f5f5; }}
            .sidebar {{ width: 250px; background: #2c3e50; color: white; height: 100vh; position: fixed; padding: 20px; }}
            .sidebar h2 {{ margin-bottom: 30px; }}
            .sidebar a {{ display: block; color: white; text-decoration: none; padding: 10px; margin: 5px 0; border-radius: 5px; }}
            .sidebar a:hover {{ background: #667eea; }}
            .content {{ margin-left: 250px; padding: 30px; }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
            .stat-card {{ background: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            .stat-number {{ font-size: 32px; font-weight: bold; color: #667eea; }}
            .stat-label {{ color: #666; margin-top: 5px; }}
            table {{ width: 100%; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background: #667eea; color: white; }}
            .btn {{ background: #667eea; color: white; padding: 5px 10px; text-decoration: none; border-radius: 5px; font-size: 12px; display: inline-block; margin: 2px; }}
            .btn-danger {{ background: #e74c3c; }}
            .btn-success {{ background: #27ae60; }}
            .btn:hover {{ opacity: 0.8; }}
            .dog-image {{ width: 50px; height: 50px; object-fit: cover; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="sidebar">
            <h2>🐕 Admin Panel</h2>
            <a href="/admin">📊 Dashboard</a>
            <a href="/admin/dogs">🐕 Manage Dogs</a>
            <a href="/admin/add_dog">➕ Add New Dog</a>
            <a href="/admin/applications">📝 Adoption Requests</a>
            <a href="/admin/logout">🚪 Logout</a>
        </div>
        
        <div class="content">
            <h1>Admin Dashboard</h1>
            
            <div class="stats-grid">
                <div class="stat-card"><div class="stat-number">{total_dogs}</div><div class="stat-label">Total Dogs</div></div>
                <div class="stat-card"><div class="stat-number">{available_dogs}</div><div class="stat-label">Available for Adoption</div></div>
                <div class="stat-card"><div class="stat-number">₹{int(total_donations)}</div><div class="stat-label">Total Donations</div></div>
                <div class="stat-card"><div class="stat-number">{total_volunteers}</div><div class="stat-label">Volunteers</div></div>
                <div class="stat-card"><div class="stat-number">{pending_adoptions}</div><div class="stat-label">Pending Applications</div></div>
            </div>
            
            <h2>Recent Dogs</h2>
            <table>
                <tr><th>ID</th><th>Image</th><th>Name</th><th>Location</th><th>Health</th><th>Status</th><th>Actions</th></tr>
    '''
    
    for dog in recent_dogs:
        image_html = f'<img class="dog-image" src="/{dog[4]}" onerror="this.src=\'/static/images/default_dog.jpg\'">' if dog[4] else 'No Image'
        html += f'''
                <tr>
                    <td>{dog[0]}</td>
                    <td>{image_html}</td>
                    <td>{dog[1]}</td>
                    <td>{dog[2]}</td>
                    <td>{dog[3]}</td>
                    <td>{dog[5]}</td>
                    <td>
                        <a href="/admin/edit_dog/{dog[0]}" class="btn">Edit</a>
                        <a href="/admin/delete_dog/{dog[0]}" class="btn btn-danger" onclick="return confirm('Delete this dog?')">Delete</a>
                    </td>
                </tr>
        '''
    
    html += '''
            </table>
        </div>
    </body>
    </html>
    '''
    return html

# Admin - Manage all dogs
@app.route('/admin/dogs')
def admin_dogs():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT dog_id, name, location, age, gender, health_status, status, image_path FROM dogs ORDER BY dog_id DESC")
    dogs = cursor.fetchall()
    cursor.close()
    conn.close()
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Manage Dogs - Admin</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Segoe UI', Arial; background: #f5f5f5; }
            .sidebar { width: 250px; background: #2c3e50; color: white; height: 100vh; position: fixed; padding: 20px; }
            .sidebar a { display: block; color: white; text-decoration: none; padding: 10px; margin: 5px 0; border-radius: 5px; }
            .sidebar a:hover { background: #667eea; }
            .content { margin-left: 250px; padding: 30px; }
            table { width: 100%; background: white; border-radius: 10px; overflow-x: auto; display: block; }
            th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background: #667eea; color: white; }
            .btn { background: #667eea; color: white; padding: 5px 10px; text-decoration: none; border-radius: 5px; font-size: 12px; display: inline-block; margin: 2px; }
            .btn-danger { background: #e74c3c; }
            .dog-image { width: 50px; height: 50px; object-fit: cover; border-radius: 5px; }
            h1 { margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <div class="sidebar">
            <h2>🐕 Admin Panel</h2>
            <a href="/admin">📊 Dashboard</a>
            <a href="/admin/dogs">🐕 Manage Dogs</a>
            <a href="/admin/add_dog">➕ Add New Dog</a>
            <a href="/admin/applications">📝 Adoption Requests</a>
            <a href="/admin/logout">🚪 Logout</a>
        </div>
        
        <div class="content">
            <h1>🐕 Manage Dogs</h1>
            <a href="/admin/add_dog" class="btn" style="margin-bottom: 20px;">➕ Add New Dog</a>
            <table>
                <tr><th>ID</th><th>Image</th><th>Name</th><th>Location</th><th>Age</th><th>Gender</th><th>Health</th><th>Status</th><th>Actions</th></tr>
    '''
    
    for dog in dogs:
        image_html = f'<img class="dog-image" src="/{dog[7]}" onerror="this.src=\'/static/images/default_dog.jpg\'">' if dog[7] else 'No Image'
        html += f'''
                <tr>
                    <td>{dog[0]}</td>
                    <td>{image_html}</td>
                    <td>{dog[1]}</td>
                    <td>{dog[2]}</td>
                    <td>{dog[3]}</td>
                    <td>{dog[4]}</td>
                    <td>{dog[5]}</td>
                    <td>{dog[6]}</td>
                    <td>
                        <a href="/admin/edit_dog/{dog[0]}" class="btn">Edit</a>
                        <a href="/admin/delete_dog/{dog[0]}" class="btn btn-danger" onclick="return confirm('Delete this dog?')">Delete</a>
                    </td>
                </tr>
        '''
    
    html += '''
            </table>
        </div>
    </body>
    </html>
    '''
    return html

# Admin - Add new dog with image upload
@app.route('/admin/add_dog', methods=['GET', 'POST'])
def admin_add_dog():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        name = request.form.get('name', 'Unknown')
        location = request.form['location']
        area = request.form.get('area', '')
        age = request.form.get('age', '')
        gender = request.form.get('gender', '')
        health_status = request.form.get('health_status', '')
        vaccination = 1 if request.form.get('vaccination') == 'on' else 0
        sterilized = 1 if request.form.get('sterilized') == 'on' else 0
        personality = request.form.get('personality', '')
        food_type = request.form.get('food_type', '')
        feeding_time = request.form.get('feeding_time', '')
        special_needs = request.form.get('special_needs', '')
        status = request.form.get('status', 'Available')
        
        # Handle image upload
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = f"{app.config['UPLOAD_FOLDER']}/{filename}"
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO dogs (name, location, area, age, gender, health_status, vaccination, sterilized, personality, food_type, feeding_time, special_needs, image_path, status, created_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURDATE())
        """, (name, location, area, age, gender, health_status, vaccination, sterilized, personality, food_type, feeding_time, special_needs, image_path, status))
        conn.commit()
        cursor.close()
        conn.close()
        
        return '<script>alert("Dog added successfully!"); window.location.href="/admin/dogs";</script>'
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Add Dog - Admin</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Segoe UI', Arial; background: #f5f5f5; }
            .sidebar { width: 250px; background: #2c3e50; color: white; height: 100vh; position: fixed; padding: 20px; }
            .sidebar a { display: block; color: white; text-decoration: none; padding: 10px; margin: 5px 0; border-radius: 5px; }
            .sidebar a:hover { background: #667eea; }
            .content { margin-left: 250px; padding: 30px; }
            .form-container { background: white; padding: 30px; border-radius: 10px; max-width: 800px; }
            input, select, textarea { width: 100%; padding: 10px; margin: 8px 0; border: 1px solid #ddd; border-radius: 5px; }
            .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
            .btn { background: #667eea; color: white; padding: 12px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; margin-top: 20px; }
            .btn:hover { background: #764ba2; }
            h1 { margin-bottom: 20px; }
            .checkbox { width: auto; margin-right: 10px; }
        </style>
    </head>
    <body>
        <div class="sidebar">
            <h2>🐕 Admin Panel</h2>
            <a href="/admin">📊 Dashboard</a>
            <a href="/admin/dogs">🐕 Manage Dogs</a>
            <a href="/admin/add_dog">➕ Add New Dog</a>
            <a href="/admin/applications">📝 Adoption Requests</a>
            <a href="/admin/logout">🚪 Logout</a>
        </div>
        
        <div class="content">
            <div class="form-container">
                <h1>➕ Add New Dog</h1>
                <form method="POST" enctype="multipart/form-data">
                    <div class="form-row">
                        <div><label>Name *</label><input type="text" name="name" required></div>
                        <div><label>Location *</label><input type="text" name="location" required></div>
                    </div>
                    <div class="form-row">
                        <div><label>Area</label><input type="text" name="area"></div>
                        <div><label>Age</label>
                            <select name="age">
                                <option value="">Select Age</option>
                                <option>Puppy</option><option>Young</option>
                                <option>Adult</option><option>Senior</option>
                            </select>
                        </div>
                    </div>
                    <div class="form-row">
                        <div><label>Gender</label>
                            <select name="gender"><option value="">Select</option><option>Male</option><option>Female</option></select>
                        </div>
                        <div><label>Health Status</label>
                            <select name="health_status"><option>Healthy</option><option>Injured</option><option>Sick</option><option>Vaccinated</option></select>
                        </div>
                    </div>
                    <div class="form-row">
                        <div><label>Food Type</label>
                            <select name="food_type"><option>Dry Food</option><option>Wet Food</option><option>Milk</option><option>Both</option></select>
                        </div>
                        <div><label>Feeding Time</label>
                            <select name="feeding_time"><option>Morning</option><option>Evening</option><option>Both</option></select>
                        </div>
                    </div>
                    <div class="form-row">
                        <div><label><input type="checkbox" name="vaccination" class="checkbox"> Vaccinated</label></div>
                        <div><label><input type="checkbox" name="sterilized" class="checkbox"> Sterilized</label></div>
                    </div>
                    <div><label>Personality</label><textarea name="personality" rows="2" placeholder="Friendly, playful, good with kids..."></textarea></div>
                    <div><label>Special Needs</label><textarea name="special_needs" rows="2" placeholder="Any special requirements..."></textarea></div>
                    <div><label>Status</label>
                        <select name="status"><option>Available</option><option>Pending Adoption</option><option>Adopted</option><option>Treatment</option></select>
                    </div>
                    <div><label>Dog Photo</label><input type="file" name="image" accept="image/*"></div>
                    <button type="submit" class="btn">🐕 Add Dog</button>
                </form>
            </div>
        </div>
    </body>
    </html>
    '''
    return html

# Admin - Edit dog
@app.route('/admin/edit_dog/<int:dog_id>', methods=['GET', 'POST'])
def admin_edit_dog(dog_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        name = request.form['name']
        location = request.form['location']
        area = request.form.get('area', '')
        age = request.form.get('age', '')
        gender = request.form.get('gender', '')
        health_status = request.form.get('health_status', '')
        vaccination = 1 if request.form.get('vaccination') == 'on' else 0
        sterilized = 1 if request.form.get('sterilized') == 'on' else 0
        personality = request.form.get('personality', '')
        food_type = request.form.get('food_type', '')
        feeding_time = request.form.get('feeding_time', '')
        special_needs = request.form.get('special_needs', '')
        status = request.form.get('status', 'Available')
        
        # Handle image upload
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = f"{app.config['UPLOAD_FOLDER']}/{filename}"
                
                cursor.execute("UPDATE dogs SET image_path = %s WHERE dog_id = %s", (image_path, dog_id))
        
        cursor.execute("""
            UPDATE dogs SET name=%s, location=%s, area=%s, age=%s, gender=%s, health_status=%s, 
            vaccination=%s, sterilized=%s, personality=%s, food_type=%s, feeding_time=%s, 
            special_needs=%s, status=%s WHERE dog_id=%s
        """, (name, location, area, age, gender, health_status, vaccination, sterilized, personality, food_type, feeding_time, special_needs, status, dog_id))
        conn.commit()
        cursor.close()
        conn.close()
        
        return '<script>alert("Dog updated successfully!"); window.location.href="/admin/dogs";</script>'
    
    cursor.execute("SELECT * FROM dogs WHERE dog_id = %s", (dog_id,))
    dog = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not dog:
        return "Dog not found"
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Edit Dog - Admin</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: 'Segoe UI', Arial; background: #f5f5f5; }}
            .sidebar {{ width: 250px; background: #2c3e50; color: white; height: 100vh; position: fixed; padding: 20px; }}
            .sidebar a {{ display: block; color: white; text-decoration: none; padding: 10px; margin: 5px 0; border-radius: 5px; }}
            .sidebar a:hover {{ background: #667eea; }}
            .content {{ margin-left: 250px; padding: 30px; }}
            .form-container {{ background: white; padding: 30px; border-radius: 10px; max-width: 800px; }}
            input, select, textarea {{ width: 100%; padding: 10px; margin: 8px 0; border: 1px solid #ddd; border-radius: 5px; }}
            .form-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
            .btn {{ background: #667eea; color: white; padding: 12px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; margin-top: 20px; }}
            .btn-danger {{ background: #e74c3c; }}
            .current-image {{ max-width: 150px; margin: 10px 0; border-radius: 10px; }}
            h1 {{ margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <div class="sidebar">
            <h2>🐕 Admin Panel</h2>
            <a href="/admin">📊 Dashboard</a>
            <a href="/admin/dogs">🐕 Manage Dogs</a>
            <a href="/admin/add_dog">➕ Add New Dog</a>
            <a href="/admin/logout">🚪 Logout</a>
        </div>
        
        <div class="content">
            <div class="form-container">
                <h1>✏️ Edit Dog: {dog[1]}</h1>
                <form method="POST" enctype="multipart/form-data">
                    <div class="form-row">
                        <div><label>Name *</label><input type="text" name="name" value="{dog[1]}" required></div>
                        <div><label>Location *</label><input type="text" name="location" value="{dog[2]}" required></div>
                    </div>
                    <div class="form-row">
                        <div><label>Area</label><input type="text" name="area" value="{dog[3] if dog[3] else ''}"></div>
                        <div><label>Age</label><input type="text" name="age" value="{dog[4] if dog[4] else ''}"></div>
                    </div>
                    <div class="form-row">
                        <div><label>Gender</label>
                            <select name="gender"><option {dog[5] == 'Male' and 'selected' or ''}>Male</option><option {dog[5] == 'Female' and 'selected' or ''}>Female</option></select>
                        </div>
                        <div><label>Health Status</label>
                            <select name="health_status"><option {dog[6] == 'Healthy' and 'selected' or ''}>Healthy</option><option {dog[6] == 'Injured' and 'selected' or ''}>Injured</option><option {dog[6] == 'Sick' and 'selected' or ''}>Sick</option></select>
                        </div>
                    </div>
                    <div class="form-row">
                        <div><label>Food Type</label><input type="text" name="food_type" value="{dog[10] if dog[10] else ''}"></div>
                        <div><label>Feeding Time</label><input type="text" name="feeding_time" value="{dog[11] if dog[11] else ''}"></div>
                    </div>
                    <div class="form-row">
                        <div><label><input type="checkbox" name="vaccination" {'checked' if dog[7] else ''}> Vaccinated</label></div>
                        <div><label><input type="checkbox" name="sterilized" {'checked' if dog[8] else ''}> Sterilized</label></div>
                    </div>
                    <div><label>Personality</label><textarea name="personality" rows="2">{dog[9] if dog[9] else ''}</textarea></div>
                    <div><label>Special Needs</label><textarea name="special_needs" rows="2">{dog[12] if dog[12] else ''}</textarea></div>
                    <div><label>Status</label>
                        <select name="status"><option {dog[14] == 'Available' and 'selected' or ''}>Available</option><option {dog[14] == 'Pending Adoption' and 'selected' or ''}>Pending Adoption</option><option {dog[14] == 'Adopted' and 'selected' or ''}>Adopted</option></select>
                    </div>
                    <div><label>Current Photo</label><br>
                        {'<img class="current-image" src="/' + dog[13] + '">' if dog[13] else 'No image'}
                    </div>
                    <div><label>Upload New Photo</label><input type="file" name="image" accept="image/*"></div>
                    <button type="submit" class="btn">💾 Save Changes</button>
                    <a href="/admin/dogs" class="btn btn-danger" style="background:#95a5a6;">Cancel</a>
                </form>
            </div>
        </div>
    </body>
    </html>
    '''
    return html

# Admin - Delete dog
@app.route('/admin/delete_dog/<int:dog_id>')
def admin_delete_dog(dog_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM dogs WHERE dog_id = %s", (dog_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    return '<script>alert("Dog deleted successfully!"); window.location.href="/admin/dogs";</script>'

# Admin - View adoption applications
@app.route('/admin/applications')
def admin_applications():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Get filter from URL
    status_filter = request.args.get('status', 'Pending')
    
    conn = get_db()
    cursor = conn.cursor()
    
    if status_filter == 'All':
        cursor.execute("""
            SELECT r.request_id, r.full_name, r.email, r.phone, r.address, r.city, 
                   r.home_type, r.has_pets, r.reason, r.request_date, r.status, 
                   r.review_notes, d.name as dog_name, r.dog_id
            FROM adoption_requests r
            LEFT JOIN dogs d ON r.dog_id = d.dog_id
            ORDER BY 
                CASE r.status 
                    WHEN 'Pending' THEN 1
                    WHEN 'Approved' THEN 2
                    WHEN 'Rejected' THEN 3
                END,
                r.request_date DESC
        """)
    else:
        cursor.execute("""
            SELECT r.request_id, r.full_name, r.email, r.phone, r.address, r.city, 
                   r.home_type, r.has_pets, r.reason, r.request_date, r.status, 
                   r.review_notes, d.name as dog_name, r.dog_id
            FROM adoption_requests r
            LEFT JOIN dogs d ON r.dog_id = d.dog_id
            WHERE r.status = %s
            ORDER BY r.request_date DESC
        """, (status_filter,))
    
    applications = cursor.fetchall()
    
    # Get counts for tabs
    cursor.execute("SELECT COUNT(*) FROM adoption_requests WHERE status = 'Pending'")
    pending_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM adoption_requests WHERE status = 'Approved'")
    approved_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM adoption_requests WHERE status = 'Rejected'")
    rejected_count = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Adoption Applications - Admin</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: 'Segoe UI', Arial; background: #f5f5f5; }}
            .sidebar {{ width: 250px; background: #2c3e50; color: white; height: 100vh; position: fixed; padding: 20px; }}
            .sidebar a {{ display: block; color: white; text-decoration: none; padding: 10px; margin: 5px 0; border-radius: 5px; }}
            .sidebar a:hover {{ background: #667eea; }}
            .content {{ margin-left: 250px; padding: 30px; }}
            .tabs {{ display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }}
            .tab {{ padding: 10px 20px; background: #e0e0e0; border-radius: 8px; text-decoration: none; color: #333; }}
            .tab.active {{ background: #667eea; color: white; }}
            .tab:hover {{ background: #764ba2; color: white; }}
            table {{ width: 100%; background: white; border-radius: 10px; overflow: auto; display: block; border-collapse: collapse; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background: #667eea; color: white; position: sticky; top: 0; }}
            .status-pending {{ color: #f39c12; font-weight: bold; }}
            .status-approved {{ color: #27ae60; font-weight: bold; }}
            .status-rejected {{ color: #e74c3c; font-weight: bold; }}
            .btn {{ background: #667eea; color: white; padding: 5px 10px; text-decoration: none; border-radius: 5px; font-size: 12px; border: none; cursor: pointer; }}
            .btn-approve {{ background: #27ae60; }}
            .btn-reject {{ background: #e74c3c; }}
            .btn:hover {{ opacity: 0.8; }}
            .details-btn {{ background: #3498db; }}
            .modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; }}
            .modal-content {{ background: white; max-width: 500px; margin: 100px auto; padding: 20px; border-radius: 10px; }}
            textarea {{ width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }}
            h1 {{ margin-bottom: 20px; }}
            .action-buttons {{ display: flex; gap: 5px; flex-wrap: wrap; }}
        </style>
    </head>
    <body>
        <div class="sidebar">
            <h2>🐕 Admin Panel</h2>
            <a href="/admin">📊 Dashboard</a>
            <a href="/admin/dogs">🐕 Manage Dogs</a>
            <a href="/admin/add_dog">➕ Add New Dog</a>
            <a href="/admin/applications">📝 Adoption Requests</a>
            <a href="/admin/logout">🚪 Logout</a>
        </div>
        
        <div class="content">
            <h1>📝 Adoption Applications</h1>
            
            <div class="tabs">
                <a href="/admin/applications?status=Pending" class="tab {'active' if status_filter == 'Pending' else ''}">
                    ⏳ Pending ({pending_count})
                </a>
                <a href="/admin/applications?status=Approved" class="tab {'active' if status_filter == 'Approved' else ''}">
                    ✅ Approved ({approved_count})
                </a>
                <a href="/admin/applications?status=Rejected" class="tab {'active' if status_filter == 'Rejected' else ''}">
                    ❌ Rejected ({rejected_count})
                </a>
                <a href="/admin/applications?status=All" class="tab {'active' if status_filter == 'All' else ''}">
                    📋 All
                </a>
            </div>
            
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Dog</th>
                        <th>Applicant</th>
                        <th>Email</th>
                        <th>Phone</th>
                        <th>City</th>
                        <th>Date</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
    '''
    
    for app in applications:
        request_id = app[0]
        full_name = app[1]
        email = app[2]
        phone = app[3]
        address = app[4] if app[4] else ''
        city = app[5] if app[5] else ''
        home_type = app[6] if app[6] else ''
        has_pets = app[7] if app[7] else ''
        reason = app[8] if app[8] else ''
        request_date = app[9]
        status = app[10]
        review_notes = app[11] if app[11] else ''
        dog_name = app[12] if app[12] else 'General'
        dog_id = app[13]
        
        status_class = f"status-{status.lower()}"
        
        html += f'''
                    <tr>
                        <td>{request_id}</td>
                        <td><strong>{dog_name}</strong></td>
                        <td>{full_name}</td>
                        <td>{email}</td>
                        <td>{phone}</td>
                        <td>{city}</td>
                        <td>{request_date}</td>
                        <td class="{status_class}">{status}</td>
                        <td class="action-buttons">
                            <button onclick="showDetails({request_id})" class="btn details-btn">📋 Details</button>
        '''
        
        if status == 'Pending':
            html += f'''
                            <form method="POST" action="/admin/approve_application/{request_id}" style="display: inline-block;">
                                <button type="submit" class="btn btn-approve" onclick="return confirmApprove()">✅ Approve</button>
                            </form>
                            <button onclick="showRejectModal({request_id})" class="btn btn-reject">❌ Reject</button>
                    </td>
                </tr>
                
                <!-- Reject Modal -->
                <div id="rejectModal_{request_id}" class="modal">
                    <div class="modal-content">
                        <h3>Reject Application</h3>
                        <p><strong>Applicant:</strong> {full_name}</p>
                        <p><strong>Dog:</strong> {dog_name}</p>
                        <form method="POST" action="/admin/reject_application/{request_id}">
                            <label>Reason for rejection (optional):</label>
                            <textarea name="review_notes" rows="3" placeholder="Enter reason..."></textarea>
                            <button type="submit" class="btn btn-reject">Confirm Reject</button>
                            <button type="button" onclick="closeModal({request_id})" class="btn">Cancel</button>
                        </form>
                    </div>
                </div>
            '''
        else:
            html += f'''
                        </td>
                    </tr>
            '''
        
        # Details Modal
        html += f'''
                <!-- Details Modal -->
                <div id="detailsModal_{request_id}" class="modal">
                    <div class="modal-content">
                        <h3>Application Details</h3>
                        <p><strong>Request ID:</strong> {request_id}</p>
                        <p><strong>Dog:</strong> {dog_name}</p>
                        <p><strong>Applicant:</strong> {full_name}</p>
                        <p><strong>Email:</strong> {email}</p>
                        <p><strong>Phone:</strong> {phone}</p>
                        <p><strong>Address:</strong> {address if address else 'Not provided'}</p>
                        <p><strong>City:</strong> {city if city else 'Not provided'}</p>
                        <p><strong>Home Type:</strong> {home_type if home_type else 'Not provided'}</p>
                        <p><strong>Has Other Pets:</strong> {has_pets if has_pets else 'Not specified'}</p>
                        <p><strong>Reason for Adoption:</strong></p>
                        <p style="background: #f5f5f5; padding: 10px; border-radius: 5px;">{reason if reason else 'Not provided'}</p>
                        <p><strong>Application Date:</strong> {request_date}</p>
                        <p><strong>Status:</strong> <span class="{status_class}">{status}</span></p>
                        {f'<p><strong>Review Notes:</strong> {review_notes}</p>' if review_notes else ''}
                        <button onclick="closeDetailsModal({request_id})" class="btn">Close</button>
                    </div>
                </div>
        '''
    
    html += '''
                </tbody>
            </table>
        </div>
        
        <script>
            function showDetails(id) {
                document.getElementById('detailsModal_' + id).style.display = 'block';
            }
            
            function closeDetailsModal(id) {
                document.getElementById('detailsModal_' + id).style.display = 'none';
            }
            
            function showRejectModal(id) {
                document.getElementById('rejectModal_' + id).style.display = 'block';
            }
            
            function closeModal(id) {
                document.getElementById('rejectModal_' + id).style.display = 'none';
            }
            
            function confirmApprove() {
                return confirm('Are you sure you want to APPROVE this adoption application?\\n\\nThe applicant will receive an email notification.');
            }
            
            // Close modal when clicking outside
            window.onclick = function(event) {
                if (event.target.classList.contains('modal')) {
                    event.target.style.display = 'none';
                }
            }
        </script>
    </body>
    </html>
    '''
    return html

# ==================== ADMIN - APPROVE APPLICATION ====================
@app.route('/admin/approve_application/<int:request_id>', methods=['POST'])
def admin_approve_application(request_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Get application details
        cursor.execute("""
            SELECT r.full_name, r.email, d.name as dog_name, r.dog_id
            FROM adoption_requests r
            LEFT JOIN dogs d ON r.dog_id = d.dog_id
            WHERE r.request_id = %s
        """, (request_id,))
        application = cursor.fetchone()
        
        if application:
            full_name = application[0]
            email = application[1]
            dog_name = application[2] if application[2] else "a dog"
            dog_id = application[3]
            
            # Update application status
            cursor.execute("""
                UPDATE adoption_requests 
                SET status = 'Approved', 
                    reviewed_by = %s, 
                    reviewed_date = NOW()
                WHERE request_id = %s
            """, (session.get('admin_id'), request_id))
            
            # Update dog status if this was for a specific dog
            if dog_id:
                cursor.execute("""
                    UPDATE dogs 
                    SET status = 'Adopted', 
                        adopted_date = CURDATE() 
                    WHERE dog_id = %s
                """, (dog_id,))
            
            conn.commit()
            
            # Send approval email
            send_approval_email(full_name, email, dog_name)
            
            print(f"✅ Application {request_id} approved for {full_name}")
            
    except Exception as e:
        print(f"Error approving application: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('admin_applications', status='Pending'))

# ==================== ADMIN - REJECT APPLICATION ====================
@app.route('/admin/reject_application/<int:request_id>', methods=['POST'])
def admin_reject_application(request_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    review_notes = request.form.get('review_notes', '')
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Get application details
        cursor.execute("""
            SELECT r.full_name, r.email, d.name as dog_name, r.dog_id
            FROM adoption_requests r
            LEFT JOIN dogs d ON r.dog_id = d.dog_id
            WHERE r.request_id = %s
        """, (request_id,))
        application = cursor.fetchone()
        
        if application:
            full_name = application[0]
            email = application[1]
            dog_name = application[2] if application[2] else "a dog"
            dog_id = application[3]
            
            # Update application status
            cursor.execute("""
                UPDATE adoption_requests 
                SET status = 'Rejected', 
                    review_notes = %s,
                    reviewed_by = %s, 
                    reviewed_date = NOW()
                WHERE request_id = %s
            """, (review_notes, session.get('admin_id'), request_id))
            
            # Make dog available again if it was pending adoption
            if dog_id:
                cursor.execute("""
                    UPDATE dogs 
                    SET status = 'Available' 
                    WHERE dog_id = %s AND status = 'Pending Adoption'
                """, (dog_id,))
            
            conn.commit()
            
            # Send rejection email
            send_rejection_email(full_name, email, dog_name, review_notes)
            
            print(f"❌ Application {request_id} rejected for {full_name}")
            
    except Exception as e:
        print(f"Error rejecting application: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('admin_applications', status='Pending'))

# ==================== EMAIL FUNCTIONS FOR ADOPTION ====================
def send_approval_email(name, email, dog_name):
    """Send approval email to applicant"""
    subject = f"🎉 Congratulations! Your Adoption Application for {dog_name} is Approved!"
    
    message = f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <div style="max-width: 600px; margin: auto; padding: 20px; background: #f9f9f9; border-radius: 10px;">
            <h1 style="color: #27ae60;">🎉 Congratulations, {name}!</h1>
            <p>Your adoption application for <strong>{dog_name}</strong> has been <strong style="color: #27ae60;">APPROVED</strong>!</p>
            <p><strong>Next Steps:</strong></p>
            <ul>
                <li>📞 Our team will contact you within 24 hours to schedule a meet-and-greet</li>
                <li>🐕 You'll get to spend time with {dog_name} before finalizing adoption</li>
                <li>📝 Adoption documents will be shared with you</li>
                <li>🏠 A quick home visit will be arranged to ensure a safe environment</li>
            </ul>
            <p>Thank you for giving a street dog a forever home! 🐕❤️</p>
            <br>
            <p>Warm regards,<br><strong>Street Dog Welfare Trust</strong></p>
            <p><small>Contact us: +91 80 1234 5678 | adopt@streetdogwelfare.org</small></p>
        </div>
    </body>
    </html>
    """
    
    send_email(email, subject, message)

def send_rejection_email(name, email, dog_name, reason):
    """Send rejection email to applicant"""
    subject = f"Update on Your Adoption Application for {dog_name}"
    
    reason_text = reason if reason else "We regret to inform you that your application could not be approved at this time."
    
    message = f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <div style="max-width: 600px; margin: auto; padding: 20px; background: #f9f9f9; border-radius: 10px;">
            <h1 style="color: #e74c3c;">Update on Your Application</h1>
            <p>Dear {name},</p>
            <p>Thank you for your interest in adopting <strong>{dog_name}</strong>. After careful review, we regret to inform you that your application could not be approved at this time.</p>
            <p><strong>Reason:</strong> {reason_text}</p>
            <p>We encourage you to look at other wonderful dogs available for adoption on our website. Each dog is special and waiting for a loving home!</p>
            <p><a href="http://localhost:5000/dogs" style="background: #667eea; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">View Available Dogs</a></p>
            <br>
            <p>Thank you for your understanding,<br><strong>Street Dog Welfare Trust</strong></p>
        </div>
    </body>
    </html>
    """
    
    send_email(email, subject, message)

# ==================== SEND ADOPTION STATUS EMAIL ====================
def send_adoption_status_email(name, email, dog_name, status, notes):
    if status == 'Approved':
        subject = f"🎉 Congratulations! Your Adoption Application for {dog_name} is Approved!"
        message = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="max-width: 600px; margin: auto; padding: 20px; background: #f9f9f9; border-radius: 10px;">
                <h1 style="color: #27ae60;">🎉 Congratulations, {name}!</h1>
                <p>Your adoption application for <strong>{dog_name}</strong> has been <strong style="color: #27ae60;">APPROVED</strong>!</p>
                <p><strong>Next Steps:</strong></p>
                <ul>
                    <li>Our team will contact you within 24 hours to schedule a meet-and-greet</li>
                    <li>You'll get to spend time with {dog_name} before finalizing adoption</li>
                    <li>Adoption documents will be shared with you</li>
                </ul>
                <p>Thank you for giving a street dog a forever home! 🐕</p>
                <br>
                <p>Warm regards,<br><strong>Street Dog Welfare Trust</strong></p>
            </div>
        </body>
        </html>
        """
    elif status == 'Rejected':
        subject = f"Update on Your Adoption Application for {dog_name}"
        message = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="max-width: 600px; margin: auto; padding: 20px; background: #f9f9f9; border-radius: 10px;">
                <h1 style="color: #e74c3c;">Update on Your Application</h1>
                <p>Dear {name},</p>
                <p>Thank you for your interest in adopting <strong>{dog_name}</strong>. After careful review, we regret to inform you that your application could not be approved at this time.</p>
                <p><strong>Reason:</strong> {notes if notes else 'Application did not meet our adoption criteria'}</p>
                <p>We encourage you to look at other wonderful dogs available for adoption on our website. Each dog is special and waiting for a loving home!</p>
                <br>
                <p>Thank you for your understanding,<br><strong>Street Dog Welfare Trust</strong></p>
            </div>
        </body>
        </html>
        """
    else:
        return
    
    send_email(email, subject, message)

# ==================== ADMIN - BULK UPDATE ADOPTIONS ====================
@app.route('/admin/bulk_update_applications', methods=['POST'])
def admin_bulk_update_applications():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    action = request.form.get('action')
    application_ids = request.form.getlist('application_ids')
    
    if application_ids:
        conn = get_db()
        cursor = conn.cursor()
        
        if action == 'approve':
            status = 'Approved'
        elif action == 'reject':
            status = 'Rejected'
        else:
            return redirect(url_for('admin_applications'))
        
        for app_id in application_ids:
            cursor.execute("""
                UPDATE adoption_requests 
                SET status = %s, reviewed_by = %s, reviewed_date = NOW()
                WHERE request_id = %s
            """, (status, session.get('admin_id'), app_id))
            
            # Get dog_id to update dog status
            cursor.execute("SELECT dog_id FROM adoption_requests WHERE request_id = %s", (app_id,))
            dog = cursor.fetchone()
            if dog and dog[0]:
                if status == 'Approved':
                    cursor.execute("UPDATE dogs SET status = 'Adopted', adopted_date = CURDATE() WHERE dog_id = %s", (dog[0],))
                elif status == 'Rejected':
                    cursor.execute("UPDATE dogs SET status = 'Available' WHERE dog_id = %s AND status = 'Pending Adoption'", (dog[0],))
        
        conn.commit()
        cursor.close()
        conn.close()
    
    return redirect(url_for('admin_applications'))

# ==================== RUN APP ====================
if __name__ == '__main__':
    # Create necessary folders
    os.makedirs('static/images', exist_ok=True)
    os.makedirs('static/uploads', exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)
