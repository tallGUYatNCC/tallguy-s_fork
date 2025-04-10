# Imports mySQL stuff. You need to download mySQL on your computer (I used Homebrew) and also
# mySQL.connector
import mysql.connector
# Connects to server. I think you'll have to use giovanni.borja for host but if that doesn't work
# then let me know; it might be a config thing.
mydb = mysql.connector.connect(
    host="localhost",
    password="viRdyc-gucky7-hidceh",
    database="responses"
)
# responses is the name of the database, and then atendees is the name of the table. You gotta connect
# to the database to access the table.

#dunno what this does fully but mycursor I think is how you translate SQL commands to Python.
mycursor = mydb.cursor()

# This will make a table. So CREATE TABLE names it, then you can make as many columns as you want in the
# parenthesis, seperated by commas, so you just put the name of the column and then VARCHAR(255) (not
# entirely sure what that does), and theres also the column named id and that INT AUTO thing makes it so
# that each row has its own number, starting at 1.
mycursor.execute("CREATE TABLE atendees (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255), ageRange VARCHAR(255), age VARCHAR(255), local VARCHAR(255), country VARCHAR(255), state VARCHAR(255), christFollower VARCHAR(255), faithDecision VARCHAR(255), howYouFoundUs VARCHAR(255))")

# This is how you add inputs. Use executemany for more that one input or just execute for one, and it
# doesn't have to be an array if just one.
sql = "INSERT INTO atendees (name, age) VALUES (%s, %s)"
val = [
    ('Gio', '17'),
    ('Josiah', '7'),
    ('Molly', '3')
]

mycursor.executemany(sql, val)
# This makes sure to update the list for real on the server
mydb.commit() 

# This deletes all entries. If you put WHERE after table name, you can follow WHERE with something like
# name = Mr. Rod or whatever and it'll just delete what meets that. The second execute command here
# resets the id count back to 1.
mycursor.execute("DELETE FROM atendees")
mycursor.execute("ALTER TABLE atendees AUTO_INCREMENT = 1")
mydb.commit()

# These next few lines print the table in the terminal.
mycursor.execute("SELECT * FROM atendees")

myresult = mycursor.fetchall()

for x in myresult:
    print(x)

# This deletes the table from the database, not just the entries, so you would have to remake the table
# using CREATE TABLE if you did this.
mycursor.execute("DROP TABLE atendees")