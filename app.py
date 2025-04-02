from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import Error
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Database configuration for XAMPP
# Remote MySQL Database Configuration
db_config = {
    'host': 'sql12.freesqldatabase.com',
    'user': 'sql12770929',
    'password': 'lUIEvklJ9n',
    'database': 'sql12770929',
    'port': 3306  # Default MySQL port
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
    return render_template('index.html')

# Student management
@app.route('/students')
def students():
    conn = create_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM students")
            students = cursor.fetchall()
            
            cursor.execute("SELECT id, room_number FROM rooms WHERE status='available'")
            available_rooms = cursor.fetchall()
            
            return render_template('students.html', students=students, available_rooms=available_rooms)
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
            cursor = conn.cursor()
            try:
                # Add student
                cursor.execute("""
                    INSERT INTO students (name, roll_number, room_id, check_in_date)
                    VALUES (%s, %s, %s, %s)
                """, (name, roll_number, room_id, datetime.now().date()))
                
                # Update room occupancy
                cursor.execute("""
                    UPDATE rooms 
                    SET current_occupancy = current_occupancy + 1,
                        status = CASE 
                            WHEN capacity = current_occupancy + 1 THEN 'occupied'
                            ELSE 'partially_occupied'
                        END
                    WHERE id = %s
                """, (room_id,))
                
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

if __name__ == '__main__':
    init_db()
    app.run(debug=True)