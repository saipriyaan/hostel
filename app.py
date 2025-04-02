from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import Error
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# MySQL Database Configuration
db_config = {
    'host': 'sql12.freesqldatabase.com',
    'user': 'sql12770929',
    'password': 'lUIEvklJ9n',
    'database': 'sql12770929',
 # Update this if your MySQL server uses a different port
}
def create_connection():
    """Create and return a MySQL database connection"""
    try:
        print(f"Connecting with config: {db_config}")
        conn = mysql.connector.connect(**db_config)
        if conn.is_connected():
            print("Connection successful")
        return conn
    except mysql.connector.Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def init_db():
    print("Database initialized")
    """Initialize the database with required tables"""
    try:
        conn = create_connection()
        print('conn')
        if conn:
            cursor = conn.cursor()
            
            # Create database if not exists
            cursor.execute("CREATE DATABASE IF NOT EXISTS hostel_management")
            cursor.execute("USE hostel_management")
            
            # Create rooms table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rooms (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    room_number VARCHAR(20) UNIQUE NOT NULL,
                    capacity INT NOT NULL,
                    current_occupancy INT DEFAULT 0,
                    status ENUM('available', 'partially_occupied', 'occupied') DEFAULT 'available',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB
            """)
            
            # Create students table
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (room_id) REFERENCES rooms(id)
                    ON DELETE SET NULL
                    ON UPDATE CASCADE
                ) ENGINE=InnoDB
            """)
            
            # Create staff table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS staff (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    role VARCHAR(50) NOT NULL,
                    email VARCHAR(100),
                    phone VARCHAR(20),
                    shift ENUM('Morning', 'Evening', 'Night'),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB
            """)
            
            conn.commit()
            print("Database tables created successfully")
            
    except Error as e:
        print(f"Error initializing database: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# Home page
@app.route('/')
def index():
    return render_template('index.html')

# Student management
@app.route('/students')
def students():
    conn = None
    cursor = None
    try:
        conn = create_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute('SELECT * FROM students')
            students = cursor.fetchall()
            
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
        flash(f'Database error: {str(e)}', 'danger')
        return render_template('students.html', students=[], available_rooms=[])
    finally:
        if conn and conn.is_connected():
            if cursor:
                cursor.close()
            conn.close()

@app.route('/add_student', methods=['POST'])
def add_student():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        roll_number = request.form.get('roll_number', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        room_id = request.form.get('room_id', '').strip()
        
        if not all([name, roll_number, room_id]):
            flash('Please fill all required fields', 'danger')
            return redirect(url_for('students'))
        
        check_in_date = datetime.now().strftime('%Y-%m-%d')
        conn = None
        cursor = None
        
        try:
            conn = create_connection()
            if conn:
                cursor = conn.cursor()
                
                # Add student
                cursor.execute("""
                    INSERT INTO students (name, roll_number, email, phone, room_id, check_in_date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (name, roll_number, email, phone, room_id, check_in_date))
                
                # Update room occupancy
                cursor.execute("""
                    UPDATE rooms 
                    SET current_occupancy = current_occupancy + 1 
                    WHERE id = %s
                """, (room_id,))
                
                # Update room status
                cursor.execute("""
                    SELECT capacity, current_occupancy 
                    FROM rooms 
                    WHERE id = %s
                """, (room_id,))
                room = cursor.fetchone()
                
                if room and room['capacity'] == room['current_occupancy']:
                    cursor.execute("""
                        UPDATE rooms 
                        SET status = 'occupied' 
                        WHERE id = %s
                    """, (room_id,))
                else:
                    cursor.execute("""
                        UPDATE rooms 
                        SET status = 'partially_occupied' 
                        WHERE id = %s
                    """, (room_id,))
                
                conn.commit()
                flash('Student added successfully!', 'success')
                
        except Error as e:
            if conn:
                conn.rollback()
            if "Duplicate entry" in str(e):
                flash('Roll number already exists!', 'danger')
            else:
                flash(f'Database error: {str(e)}', 'danger')
        finally:
            if conn and conn.is_connected():
                if cursor:
                    cursor.close()
                conn.close()
    
    return redirect(url_for('students'))

# Check out student
@app.route('/check_out/<int:student_id>')
def check_out(student_id):
    conn = None
    cursor = None
    try:
        conn = create_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            
            # Get student's room
            cursor.execute('SELECT room_id FROM students WHERE id = %s', (student_id,))
            result = cursor.fetchone()
            
            if not result or not result['room_id']:
                flash('Student or room not found!', 'danger')
                return redirect(url_for('students'))
                
            room_id = result['room_id']
            
            # Update student record
            check_out_date = datetime.now().strftime('%Y-%m-%d')
            cursor.execute("""
                UPDATE students 
                SET check_out_date = %s 
                WHERE id = %s
            """, (check_out_date, student_id))
            
            # Update room occupancy
            cursor.execute("""
                UPDATE rooms 
                SET current_occupancy = current_occupancy - 1 
                WHERE id = %s
            """, (room_id,))
            
            # Update room status
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
        if conn:
            conn.rollback()
        flash(f'Database error: {str(e)}', 'danger')
    finally:
        if conn and conn.is_connected():
            if cursor:
                cursor.close()
            conn.close()
    
    return redirect(url_for('students'))

# Room management
@app.route('/rooms')
def rooms():
    conn = None
    cursor = None
    try:
        conn = create_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute('SELECT * FROM rooms')
            rooms = cursor.fetchall()
            
            return render_template('rooms.html', rooms=rooms)
            
    except Error as e:
        flash(f'Database error: {str(e)}', 'danger')
        return render_template('rooms.html', rooms=[])
    finally:
        if conn and conn.is_connected():
            if cursor:
                cursor.close()
            conn.close()

@app.route('/add_room', methods=['POST'])
def add_room():
    if request.method == 'POST':
        room_number = request.form.get('room_number', '').strip()
        capacity = request.form.get('capacity', '0').strip()
        
        if not room_number or not capacity.isdigit():
            flash('Please provide valid room details', 'danger')
            return redirect(url_for('rooms'))
        
        capacity = int(capacity)
        conn = None
        cursor = None
        
        try:
            conn = create_connection()
            if conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO rooms (room_number, capacity)
                    VALUES (%s, %s)
                """, (room_number, capacity))
                
                conn.commit()
                flash('Room added successfully!', 'success')
                
        except Error as e:
            if conn:
                conn.rollback()
            if "Duplicate entry" in str(e):
                flash('Room number already exists!', 'danger')
            else:
                flash(f'Database error: {str(e)}', 'danger')
        finally:
            if conn and conn.is_connected():
                if cursor:
                    cursor.close()
                conn.close()
    
    return redirect(url_for('rooms'))

# Staff management
@app.route('/staff')
def staff():
    conn = None
    cursor = None
    try:
        conn = create_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute('SELECT * FROM staff')
            staff_members = cursor.fetchall()
            
            return render_template('staff.html', staff_members=staff_members)
            
    except Error as e:
        flash(f'Database error: {str(e)}', 'danger')
        return render_template('staff.html', staff_members=[])
    finally:
        if conn and conn.is_connected():
            if cursor:
                cursor.close()
            conn.close()

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
        
        conn = None
        cursor = None
        
        try:
            conn = create_connection()
            if conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO staff (name, role, email, phone, shift)
                    VALUES (%s, %s, %s, %s, %s)
                """, (name, role, email, phone, shift))
                
                conn.commit()
                flash('Staff member added successfully!', 'success')
                
        except Error as e:
            if conn:
                conn.rollback()
            flash(f'Database error: {str(e)}', 'danger')
        finally:
            if conn and conn.is_connected():
                if cursor:
                    cursor.close()
                conn.close()
        
    return redirect(url_for('staff'))

# Reports
@app.route('/reports')
def reports():
    conn = None
    cursor = None
    try:
        conn = create_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            
            # Current residents
            cursor.execute('SELECT COUNT(*) AS count FROM students WHERE check_out_date IS NULL')
            current_residents = cursor.fetchone()['count']
            
            # Available rooms
            cursor.execute("SELECT COUNT(*) AS count FROM rooms WHERE status = 'available'")
            available_rooms = cursor.fetchone()['count']
            
            # Occupancy rate
            cursor.execute('SELECT SUM(capacity) AS capacity, SUM(current_occupancy) AS occupancy FROM rooms')
            result = cursor.fetchone()
            total_capacity = result['capacity'] or 0
            total_occupancy = result['occupancy'] or 0
            occupancy_rate = (total_occupancy / total_capacity * 100) if total_capacity else 0
            
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
            
            return render_template('reports.html', 
                                current_residents=current_residents,
                                available_rooms=available_rooms,
                                occupancy_rate=round(occupancy_rate, 2),
                                recent_checkins=recent_checkins)
            
    except Error as e:
        flash(f'Database error: {str(e)}', 'danger')
        return render_template('reports.html', 
                            current_residents=0,
                            available_rooms=0,
                            occupancy_rate=0,
                            recent_checkins=[])
    finally:
        if conn and conn.is_connected():
            if cursor:
                cursor.close()
            conn.close()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)