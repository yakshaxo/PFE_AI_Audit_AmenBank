import bcrypt
# This creates a secure hash for the password: admin123
password = "admin".encode('utf-8')
hashed = bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')
print(f"COPY THIS HASH: {hashed}")