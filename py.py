import mysql.connector
from mysql.connector import Error

# Remote MySQL Database Configuration
db_config = {
    'host': 'sql12.freesqldatabase.com',
    'user': 'sql12770929',
    'password': 'lUIEvklJ9n',
    'database': 'sql12770929',
    'port': 3306  # Default MySQL port
}

def test_connection():
    """Test connection to the remote MySQL server"""
    try:
        print("Attempting to connect to the remote MySQL server...")
        conn = mysql.connector.connect(**db_config)
        if conn.is_connected():
            print("Connection successful!")
            print(f"MySQL Server Info: {conn.get_server_info()}")
            conn.close()
        else:
            print("Connection failed!")
    except Error as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_connection()