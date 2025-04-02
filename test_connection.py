import pymysql

host = 'localhost'
username = 'root'
password = ''
database = 'hostel_management'
connection = pymysql.connect(host=host, user=username, password=password, database=database)
cursor= connection.cursor()
cursor.execute('SELECT VERSION()')
print(cursor.fetchone())