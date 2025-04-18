import sqlite3
import logging
from datetime import datetime


# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Set the logging level
    format='%(asctime)s - %(levelname)s - %(message)s',  # Define the log message format
    handlers=[logging.StreamHandler()]  # Output logs to the console
)
logger = logging.getLogger(__name__)  # Create a logger for this module


# Function to create a connection to the database
def create_connection():
    try:
        conn = sqlite3.connect('attendance.db')
        return conn
    except sqlite3.Error as e:
        logger.error(f"Failed to connect to the database: {e}")
        return None


def execute_query(query, params=None, fetch=False, fetchone=False):
    try:
        conn = create_connection()
        if conn is None:
            return None
        cursor = conn.cursor()
        cursor.execute(query, params or ())

        result = None
        if fetch:
            result = cursor.fetchall()
        elif fetchone:
            result = cursor.fetchone()

        conn.commit()
        conn.close()
        return result if (fetch or fetchone) else True

    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        if conn:
            conn.close()
        return None



# Create the table for attendance if not exists
def create_table():
    query = '''
    CREATE TABLE IF NOT EXISTS attendance (
        user_id INTEGER PRIMARY KEY,
        date TEXT
    )'''
    execute_query(query)


# Function to retrieve the date of attendance for a user
def get_date_of_attendance(user_id):
    query = "SELECT date FROM attendance WHERE user_id = ?"
    return execute_query(query, (user_id,), fetchone=True)


# Insert today's attendance
def insert_attendance(user_id, today):
    query = "INSERT INTO attendance (user_id, date) VALUES (?, ?)"
    return execute_query(query, (user_id, today))


# Function to update attendance
def update_attendance(user_id, today):
    query = "UPDATE attendance SET date = ? WHERE user_id = ?"
    return execute_query(query, (today, user_id))


# Function to check if the user already marked 'hadir' today
def check_hadir(user_id):
    today = datetime.now().date()
    existing_attendance = get_date_of_attendance(user_id)

    if existing_attendance:
        if existing_attendance[0] != str(today):
            # If the attendance is not from today, update the record
            if not update_attendance(user_id, str(today)):
                return False  # Return False if update fails
            return True  # Successfully updated to today's attendance
        return False

    # Insert today's attendance if not marked already
    if not insert_attendance(user_id, str(today)):
        return False

    return True  # Successfully marked hadir
  

# Initial setup - Create table if not exists
create_table()
