import bcrypt

def verify_password(plain_password, hashed_password):
    try:
        # Compatibility check for bcrypt strings
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def hash_new_password(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')