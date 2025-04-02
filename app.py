from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Initialize database
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Create tables if they don't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll_number TEXT UNIQUE NOT NULL,
            email TEXT,
            phone TEXT,
            room_id INTEGER,
            check_in_date TEXT,
            check_out_date TEXT,
            FOREIGN KEY (room_id) REFERENCES rooms (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT UNIQUE NOT NULL,
            capacity INTEGER NOT NULL,
            current_occupancy INTEGER DEFAULT 0,
            status TEXT DEFAULT 'available'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            shift TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# Home page
@app.route('/')
def index():
    return render_template('index.html')

# Student management
@app.route('/students')
def students():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM students')
    students = cursor.fetchall()
    
    cursor.execute('SELECT id, room_number FROM rooms WHERE status="available" OR status="partially_occupied"')
    available_rooms = cursor.fetchall()
    
    conn.close()
    return render_template('students.html', students=students, available_rooms=available_rooms)

@app.route('/add_student', methods=['POST'])
def add_student():
    if request.method == 'POST':
        name = request.form['name']
        roll_number = request.form['roll_number']
        email = request.form['email']
        phone = request.form['phone']
        room_id = request.form['room_id']
        check_in_date = datetime.now().strftime('%Y-%m-%d')
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        try:
            # Add student
            cursor.execute('''
                INSERT INTO students (name, roll_number, email, phone, room_id, check_in_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, roll_number, email, phone, room_id, check_in_date))
            
            # Update room occupancy
            cursor.execute('UPDATE rooms SET current_occupancy = current_occupancy + 1 WHERE id = ?', (room_id,))
            
            # Update room status if full
            cursor.execute('SELECT capacity, current_occupancy FROM rooms WHERE id = ?', (room_id,))
            room = cursor.fetchone()
            if room and room[0] == room[1]:
                cursor.execute('UPDATE rooms SET status = "occupied" WHERE id = ?', (room_id,))
            else:
                cursor.execute('UPDATE rooms SET status = "partially_occupied" WHERE id = ?', (room_id,))
            
            conn.commit()
            flash('Student added successfully!', 'success')
        except sqlite3.IntegrityError:
            flash('Roll number already exists!', 'danger')
        finally:
            conn.close()
    
    return redirect(url_for('students'))

# Updated check_out route
@app.route('/check_out/<int:student_id>')
def check_out(student_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Get student's room
    cursor.execute('SELECT room_id FROM students WHERE id = ?', (student_id,))
    result = cursor.fetchone()
    if not result:
        flash('Student not found!', 'danger')
        return redirect(url_for('students'))
    room_id = result[0]
    
    # Update student record
    check_out_date = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('UPDATE students SET check_out_date = ? WHERE id = ?', 
                 (check_out_date, student_id))
    
    # Update room occupancy
    cursor.execute('UPDATE rooms SET current_occupancy = current_occupancy - 1 WHERE id = ?', 
                 (room_id,))
    
    # Update room status
    cursor.execute('SELECT capacity, current_occupancy FROM rooms WHERE id = ?', (room_id,))
    room = cursor.fetchone()
    if room[1] == 0:
        cursor.execute('UPDATE rooms SET status = "available" WHERE id = ?', (room_id,))
    else:
        cursor.execute('UPDATE rooms SET status = "partially_occupied" WHERE id = ?', (room_id,))
    
    conn.commit()
    conn.close()
    
    flash('Student checked out successfully!', 'success')
    return redirect(url_for('students'))

# Room management
@app.route('/rooms')
def rooms():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM rooms')
    rooms = cursor.fetchall()
    
    conn.close()
    return render_template('rooms.html', rooms=rooms)

@app.route('/add_room', methods=['POST'])
def add_room():
    if request.method == 'POST':
        room_number = request.form['room_number']
        capacity = request.form['capacity']
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO rooms (room_number, capacity)
                VALUES (?, ?)
            ''', (room_number, capacity))
            
            conn.commit()
            flash('Room added successfully!', 'success')
        except sqlite3.IntegrityError:
            flash('Room number already exists!', 'danger')
        finally:
            conn.close()
    
    return redirect(url_for('rooms'))

# Staff management
@app.route('/staff')
def staff():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM staff')
    staff_members = cursor.fetchall()
    
    conn.close()
    return render_template('staff.html', staff_members=staff_members)

@app.route('/add_staff', methods=['POST'])
def add_staff():
    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        email = request.form['email']
        phone = request.form['phone']
        shift = request.form['shift']
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO staff (name, role, email, phone, shift)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, role, email, phone, shift))
        
        conn.commit()
        conn.close()
        
        flash('Staff member added successfully!', 'success')
        return redirect(url_for('staff'))

# Reports
@app.route('/reports')
def reports():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Current residents
    cursor.execute('SELECT COUNT(*) FROM students WHERE check_out_date IS NULL')
    current_residents = cursor.fetchone()[0]
    
    # Available rooms
    cursor.execute('SELECT COUNT(*) FROM rooms WHERE status = "available"')
    available_rooms = cursor.fetchone()[0]
    
    # Occupancy rate
    cursor.execute('SELECT SUM(capacity), SUM(current_occupancy) FROM rooms')
    total_capacity, total_occupancy = cursor.fetchone()
    occupancy_rate = (total_occupancy / total_capacity * 100) if total_capacity else 0
    
    # Recent check-ins
    cursor.execute('''
        SELECT s.name, s.roll_number, r.room_number, s.check_in_date
        FROM students s
        JOIN rooms r ON s.room_id = r.id
        WHERE s.check_out_date IS NULL
        ORDER BY s.check_in_date DESC
        LIMIT 5
    ''')
    recent_checkins = cursor.fetchall()
    
    conn.close()
    
    return render_template('reports.html', 
                         current_residents=current_residents,
                         available_rooms=available_rooms,
                         occupancy_rate=round(occupancy_rate, 2),
                         recent_checkins=recent_checkins)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)