from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import random
from datetime import datetime

app = Flask(__name__)

# Run this once to create tables (or include it in your Flask code setup)
def init_db():
    conn = sqlite3.connect("clinic.db")
    c = conn.cursor()

    # Patients table
    c.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            age INTEGER,
            gender TEXT,
            phone TEXT,
            condition TEXT,
            token INTEGER,
            date_added TEXT
        )
    """)

    # Billing table
    c.execute("""
        CREATE TABLE IF NOT EXISTS billing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            consultation_fee REAL,
            medication_fee REAL,
            other_charges REAL,
            total REAL,
            FOREIGN KEY(patient_id) REFERENCES patients(id)
        )
    """)

    # Appointments table
    c.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT,
            age INTEGER,
            date TEXT,
            time TEXT
        )
    """)
    
    #Prescriptions Table
    c.execute("""
    CREATE TABLE IF NOT EXISTS prescriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        diagnosis TEXT,
        medication TEXT,
        instructions TEXT,
        date_added TEXT,
        FOREIGN KEY(patient_id) REFERENCES patients(id)
        )
    """)

    conn.commit()
    conn.close()
    
# ---------- Helper Function ----------
def get_db_connection():
    conn = sqlite3.connect("clinic.db")
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def home():
    return render_template("home.html")

@app.route("/login", methods=["POST"])
def login():
    username = request.form['username']
    password = request.form['password']
    
    if username == "receptionist" and password == "clinic123":
        return redirect(url_for("receptionist"))
    elif username == "doctor" and password == "clinic123":
        return redirect(url_for("doctor"))
    else:
        return render_template('home.html')
    
# ---------- Receptionist ----------
@app.route("/receptionist")
def receptionist():
    conn = get_db_connection()
    patients = conn.execute('''SELECT * FROM patients
                            WHERE id NOT IN (SELECT patient_id FROM billing)''').fetchall()
    billing = conn.execute("""
        SELECT billing.id, patients.name, billing.consultation_fee, billing.medication_fee, billing.other_charges, billing.total
        FROM billing
        JOIN patients ON billing.patient_id = patients.id
    """).fetchall()
    conn.close()
    return render_template("receptionist.html", patients=patients, billing=billing)

@app.route("/add_patient", methods=["POST"])
def add_patient():
    name = request.form["name"]
    age = request.form["age"]
    gender = request.form["gender"]
    phone = request.form["phone"]
    condition = request.form["condition"]
    token = random.randint(100, 999)

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO patients (name, age, gender, phone, condition, token, date_added) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (name, age, gender, phone, condition, token, datetime.now().strftime("%Y-%m-%d"))
    )
    conn.commit()
    conn.close()
    return redirect(url_for("receptionist"))

@app.route("/generate_bill", methods=["POST"])
def generate_bill():
    patient_id = request.form.get("patient_id")
    consultation = float(request.form.get("consultation_fee", 0))
    medication = float(request.form.get("medication_fee", 0))
    other = float(request.form.get("other_charges", 0))
    total = consultation + medication + other

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO billing (patient_id, consultation_fee, medication_fee, other_charges, total) VALUES (?, ?, ?, ?, ?)",
        (patient_id, consultation, medication, other, total)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("receptionist"))

@app.route("/schedule_appointment", methods=["POST"])
def schedule_appointment():
    name = request.form["patient_name"]
    age = request.form["age"]
    date = request.form["date"]
    time = request.form["time"]

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO appointments (patient_name, age, date, time) VALUES (?, ?, ?, ?)",
        (name, age, date, time)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("receptionist"))

# ---------- Doctor ----------
@app.route("/doctor")
def doctor():
    conn = get_db_connection()
    # Delete expired appointments (past date and time)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn.execute("""
        DELETE FROM appointments 
        WHERE date || ' ' || time < ?
    """, (now,))
    patients = conn.execute("""
        SELECT * FROM patients
        WHERE id NOT IN (SELECT patient_id FROM prescriptions)
    """).fetchall()
    billing = conn.execute("""
        SELECT billing.id, patients.name, billing.consultation_fee, billing.medication_fee, billing.other_charges, billing.total
        FROM billing
        JOIN patients ON billing.patient_id = patients.id
    """).fetchall()

    # Fetch prescriptions joined with patient info
    prescriptions = conn.execute("""
        SELECT prescriptions.*, patients.name AS patient_name, patients.age
        FROM prescriptions
        JOIN patients ON prescriptions.patient_id = patients.id
    """).fetchall()

    # Fetch appointments
    appointments = conn.execute("SELECT * FROM appointments").fetchall()

    conn.close()
    return render_template("doctor.html", patients=patients, billing=billing, prescriptions=prescriptions, appointments=appointments)


@app.route("/add_prescription", methods=["POST"])
def add_prescription():
    patient_id = request.form["patient_id"]
    diagnosis = request.form["diagnosis"]
    medication = request.form["medication"]
    instructions = request.form["instructions"]

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO prescriptions (patient_id, diagnosis, medication, instructions, date_added) VALUES (?, ?, ?, ?, ?)",
        (patient_id, diagnosis, medication, instructions, datetime.now().strftime("%Y-%m-%d"))
    )
    conn.commit()
    conn.close()
    return redirect(url_for("doctor"))

def remove_expired_appointments():
    conn = get_db_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn.execute("""
        DELETE FROM appointments 
        WHERE date || ' ' || time < ?
    """, (now,))
    conn.commit()
    conn.close()
    
@app.route("/delete_patient/<int:patient_id>")
def delete_patient(patient_id):
    conn = get_db_connection()
    
    # Delete from billing
    conn.execute("DELETE FROM billing WHERE patient_id = ?", (patient_id,))
    
    # Delete from prescriptions
    conn.execute("DELETE FROM prescriptions WHERE patient_id = ?", (patient_id,))
    
    # Delete from appointments
    conn.execute("DELETE FROM appointments WHERE patient_name = (SELECT name FROM patients WHERE id = ?)", (patient_id,))
    
    # Delete from patients table
    conn.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
    
    conn.commit()
    conn.close()
    return redirect(url_for("receptionist"))

    
@app.route("/logout")
def logout():
    return redirect(url_for('home'))

if(__name__) == '__main__':
    init_db()
    app.run(debug = True)