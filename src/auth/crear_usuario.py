import bcrypt
import mysql.connector

password = "m4rK3t!!!"
salt = bcrypt.gensalt(rounds=12)
hashed = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

conn = mysql.connector.connect(
    host='127.0.0.1',
    user='market_user',
    password='m4rK3t!!!',
    database='market',
    auth_plugin='mysql_native_password'
)
cursor = conn.cursor()
cursor.execute(
    "INSERT INTO usuarios_sistema (username, password_hash, nombre_completo, rol) VALUES (%s, %s, %s, %s)",
    ('valeria', hashed, 'Valeria (Administrador)', 'admin')
)
conn.commit()
print(f"Usuario 'valeria' creado con password: {password}")
print(f"Hash generado: {hashed}")
cursor.close()
conn.close()