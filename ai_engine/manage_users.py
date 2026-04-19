import bcrypt
from database import get_db_connection

def add_new_user(username, password, roleid):
    # 1. Securely hash the password
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 2. Insert into the users table
        cur.execute(
            "INSERT INTO users (username, password, roleid) VALUES (%s, %s, %s)",
            (username, hashed, roleid)
        )
        
        conn.commit()
        print(f"✅ User '{username}' created successfully!")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if conn:
            conn.close()

