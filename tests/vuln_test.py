import sqlite3
import os

def get_user_data(user_input):
    """
    Intentionally vulnerable function for testing RedEye Scanner.
    Vulnerability: SQL Injection
    """
    conn = sqlite3.connect('example.db')
    cursor = conn.cursor()
    
    # VULNERABLE: Direct string concatenation
    query = "SELECT * FROM users WHERE name = '" + user_input + "'"
    
    cursor.execute(query)
    data = cursor.fetchall()
    conn.close()
    return data

if __name__ == "__main__":
    uname = os.getenv("USERNAME")
    print(get_user_data(uname))
