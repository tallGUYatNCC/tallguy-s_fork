import mysql.connector
mydb = mysql.connector.connect(
    host="localhost",
    password="viRdyc-gucky7-hidceh",
    database="responses"
)

mycursor = mydb.cursor()

sql = "INSERT INTO atendees (name, age) VALUES (%s, %s)"
val = [
    ('Gio', '17'),
    ('Josiah', '7'),
    ('Molly', '3')
]

mycursor.executemany(sql, val)

mydb.commit()