from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import Error
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Database configuration for XAMPP
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  # Empty password for XAMPP default
    'database': 'hostel_management'
}

def create_connection():
    """Create and return a database connection"""
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except Error as e:
        flash(f"Database connection error: {str(e)}", 'danger')
        return None

def init_db():
    """Initialize the database tables"""
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Create tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rooms (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    room_number VARCHAR(20) UNIQUE NOT NULL,
                    capacity INT NOT NULL,
                    current_occupancy INT DEFAULT 0,
                    status VARCHAR(20) DEFAULT 'available'
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    roll_number VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100),
                    phone VARCHAR(20),
                    room_id INT,
                    check_in_date DATE,
                    check_out_date DATE,
                    FOREIGN KEY (room_id) REFERENCES rooms(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS staff (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    role VARCHAR(50) NOT NULL,
                    email VARCHAR(100),
                    phone VARCHAR(20),
                    shift VARCHAR(20)
                )
            """)
            
            conn.commit()
        except Error as e:
            flash(f"Database initialization error: {str(e)}", 'danger')
        finally:
            cursor.close()
            conn.close()

# Home page
@app.route('/')
def index():
    conn = create_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # Get current residents count
            cursor.execute("SELECT COUNT(*) as count FROM students WHERE check_out_date IS NULL")
            current_residents = cursor.fetchone()['count']
            
            # Get available rooms count
            cursor.execute("SELECT COUNT(*) as count FROM rooms WHERE status='available'")
            available_rooms = cursor.fetchone()['count']
            
            # Calculate occupancy rate
            cursor.execute("SELECT SUM(capacity) as total_capacity, SUM(current_occupancy) as total_occupancy FROM rooms")
            stats = cursor.fetchone()
            occupancy_rate = round((stats['total_occupancy'] / stats['total_capacity']) * 100 if stats['total_capacity'] else 0
            
            return render_template('index.html', 
                                current_residents=current_residents,
                                available_rooms=available_rooms,
                                occupancy_rate=occupancy_rate)
        except Error as e:
            flash(f"Database error: {str(e)}", 'danger')
            return render_template('index.html', 
                                current_residents=0,
                                available_rooms=0,
                                occupancy_rate=0)
        finally:
            cursor.close()
            conn.close()
    return render_template('index.html', 
                         current_residents=0,
                         available_rooms=0,
                         occupancy_rate=0)

# Student management
@app.route('/students')
def students():
    conn = create_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # Get all students
            cursor.execute("""
                SELECT s.*, r.room_number 
                FROM students s 
                LEFT JOIN rooms r ON s.room_id = r.id
            """)
            students = cursor.fetchall()
            
            # Get available rooms
            cursor.execute("""
                SELECT id, room_number 
                FROM rooms 
                WHERE status='available' OR status='partially_occupied'
            """)
            available_rooms = cursor.fetchall()
            
            return render_template('students.html', 
                                students=students, 
                                available_rooms=available_rooms)
        except Error as e:
            flash(f"Database error: {str(e)}", 'danger')
            return render_template('students.html', students=[], available_rooms=[])
        finally:
            cursor.close()
            conn.close()
    return render_template('students.html', students=[], available_rooms=[])

@app.route('/add_student', methods=['POST'])
def add_student():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        roll_number = request.form.get('roll_number', '').strip()
        room_id = request.form.get('room_id', '').strip()
        
        if not all([name, roll_number, room_id]):
            flash('Please fill all required fields', 'danger')
            return redirect(url_for('students'))
            
        conn = create_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            try:
                # Add student
                cursor.execute("""
                    INSERT INTO students (name, roll_number, room_id, check_in_date)
                    VALUES (%s, %s, %s, %s)
                """, (name, roll_number, room_id, datetime.now().date()))
                
                # Get room capacity
                cursor.execute("""
                    SELECT capacity, current_occupancy 
                    FROM rooms 
                    WHERE id = %s
                """, (room_id,))
                room = cursor.fetchone()
                
                # Update room status
                new_occupancy = room['current_occupancy'] + 1
                if new_occupancy == room['capacity']:
                    status = 'occupied'
                else:
                    status = 'partially_occupied'
                
                cursor.execute("""
                    UPDATE rooms 
                    SET current_occupancy = %s,
                        status = %s
                    WHERE id = %s
                """, (new_occupancy, status, room_id))
                
                conn.commit()
                flash('Student added successfully!', 'success')
            except Error as e:
                conn.rollback()
                if "Duplicate entry" in str(e):
                    flash('Roll number already exists!', 'danger')
                else:
                    flash(f'Database error: {str(e)}', 'danger')
            finally:
                cursor.close()
                conn.close()
    
    return redirect(url_for('students'))

@app.route('/check_out/<int:student_id>')
def check_out(student_id):
    conn = create_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # Get student's room
            cursor.execute("""
                SELECT room_id 
                FROM students 
                WHERE id = %s
            """, (student_id,))
            result = cursor.fetchone()
            
            if not result or not result['room_id']:
                flash('Student or room not found!', 'danger')
                return redirect(url_for('students'))
                
            room_id = result['room_id']
            
            # Update student record
            cursor.execute("""
                UPDATE students 
                SET check_out_date = %s 
                WHERE id = %s
            """, (datetime.now().date(), student_id))
            
            # Update room status
            cursor.execute("""
                UPDATE rooms 
                SET current_occupancy = current_occupancy - 1
                WHERE id = %s
            """, (room_id,))
            
            # Check if room became available
            cursor.execute("""
                SELECT capacity, current_occupancy 
                FROM rooms 
                WHERE id = %s
            """, (room_id,))
            room = cursor.fetchone()
            
            if room['current_occupancy'] == 0:
                cursor.execute("""
                    UPDATE rooms 
                    SET status = 'available' 
                    WHERE id = %s
                """, (room_id,))
            else:
                cursor.execute("""
                    UPDATE rooms 
                    SET status = 'partially_occupied' 
                    WHERE id = %s
                """, (room_id,))
            
            conn.commit()
            flash('Student checked out successfully!', 'success')
        except Error as e:
            conn.rollback()
            flash(f'Database error: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()
    
    return redirect(url_for('students'))

# Room management
@app.route('/rooms')
def rooms():
    conn = create_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM rooms")
            rooms = cursor.fetchall()
            return render_template('rooms.html', rooms=rooms)
        except Error as e:
            flash(f"Database error: {str(e)}", 'danger')
            return render_template('rooms.html', rooms=[])
        finally:
            cursor.close()
            conn.close()
    return render_template('rooms.html', rooms=[])

@app.route('/add_room', methods=['POST'])
def add_room():
    if request.method == 'POST':
        room_number = request.form.get('room_number', '').strip()
        capacity = request.form.get('capacity', '0').strip()
        
        if not room_number or not capacity.isdigit():
            flash('Please provide valid room details', 'danger')
            return redirect(url_for('rooms'))
            
        conn = create_connection()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO rooms (room_number, capacity)
                    VALUES (%s, %s)
                """, (room_number, int(capacity)))
                
                conn.commit()
                flash('Room added successfully!', 'success')
            except Error as e:
                conn.rollback()
                if "Duplicate entry" in str(e):
                    flash('Room number already exists!', 'danger')
                else:
                    flash(f'Database error: {str(e)}', 'danger')
            finally:
                cursor.close()
                conn.close()
    
    return redirect(url_for('rooms'))

# Staff management
@app.route('/staff')
def staff():
    conn = create_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM staff")
            staff_members = cursor.fetchall()
            return render_template('staff.html', staff_members=staff_members)
        except Error as e:
            flash(f"Database error: {str(e)}", 'danger')
            return render_template('staff.html', staff_members=[])
        finally:
            cursor.close()
            conn.close()
    return render_template('staff.html', staff_members=[])

@app.route('/add_staff', methods=['POST'])
def add_staff():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        role = request.form.get('role', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        shift = request.form.get('shift', 'Morning').strip()
        
        if not name or not role:
            flash('Name and role are required', 'danger')
            return redirect(url_for('staff'))
        
        conn = create_connection()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO staff (name, role, email, phone, shift)
                    VALUES (%s, %s, %s, %s, %s)
                """, (name, role, email, phone, shift))
                
                conn.commit()
                flash('Staff member added successfully!', 'success')
            except Error as e:
                conn.rollback()
                flash(f'Database error: {str(e)}', 'danger')
            finally:
                cursor.close()
                conn.close()
        
    return redirect(url_for('staff'))

# Reports
@app.route('/reports')
def reports():
    conn = create_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # Current residents
            cursor.execute("SELECT COUNT(*) as count FROM students WHERE check_out_date IS NULL")
            current_residents = cursor.fetchone()['count']
            
            # Available rooms
            cursor.execute("SELECT COUNT(*) as count FROM rooms WHERE status='available'")
            available_rooms = cursor.fetchone()['count']
            
            # Partially occupied rooms
            cursor.execute("SELECT COUNT(*) as count FROM rooms WHERE status='partially_occupied'")
            partially_occupied_rooms = cursor.fetchone()['count']
            
            # Occupied rooms
            cursor.execute("SELECT COUNT(*) as count FROM rooms WHERE status='occupied'")
            occupied_rooms = cursor.fetchone()['count']
            
            # Occupancy rate
            cursor.execute("SELECT SUM(capacity) as total_capacity, SUM(current_occupancy) as total_occupancy FROM rooms")
            stats = cursor.fetchone()
            total_capacity = stats['total_capacity'] or 0
            total_occupancy = stats['total_occupancy'] or 0
            occupancy_rate = round((total_occupancy / total_capacity * 100) if total_capacity else 0
            
            # Recent check-ins
            cursor.execute("""
                SELECT s.name, s.roll_number, r.room_number, s.check_in_date
                FROM students s
                JOIN rooms r ON s.room_id = r.id
                WHERE s.check_out_date IS NULL
                ORDER BY s.check_in_date DESC
                LIMIT 5
            """)
            recent_checkins = cursor.fetchall()
            
            # Room distribution
            cursor.execute("SELECT * FROM rooms ORDER BY room_number")
            room_distribution = cursor.fetchall()
            
            return render_template('reports.html', 
                                current_residents=current_residents,
                                available_rooms=available_rooms,
                                partially_occupied_rooms=partially_occupied_rooms,
                                occupied_rooms=occupied_rooms,
                                occupancy_rate=occupancy_rate,
                                recent_checkins=recent_checkins,
                                room_distribution=room_distribution)
            
        except Error as e:
            flash(f"Database error: {str(e)}", 'danger')
            return render_template('reports.html', 
                                current_residents=0,
                                available_rooms=0,
                                partially_occupied_rooms=0,
                                occupied_rooms=0,
                                occupancy_rate=0,
                                recent_checkins=[],
                                room_distribution=[])
        finally:
            cursor.close()
            conn.close()
    return render_template('reports.html', 
                         current_residents=0,
                         available_rooms=0,
                         partially_occupied_rooms=0,
                         occupied_rooms=0,
                         occupancy_rate=0,
                         recent_checkins=[],
                         room_distribution=[])

if __name__ == '__main__':
    init_db()
    app.run(debug=True)