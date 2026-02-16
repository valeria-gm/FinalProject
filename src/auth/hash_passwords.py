#!/usr/bin/env python3
"""
Script para generar hashes de las contraseñas existentes
Ejecutar una sola vez para obtener los hashes que se insertarán en la base de datos
"""

import bcrypt

def hash_password(password):
    """Generar hash seguro de una contraseña"""
    # Generar salt y hash
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def main():
    """Generar hashes para las contraseñas existentes"""
    passwords = {
        'valeria': 'proYect0.593'
    }
    
    print("Generando hashes de contraseñas...")
    print("=" * 50)
    
    for username, password in passwords.items():
        hashed = hash_password(password)
        print(f"\nUsuario: {username}")
        print(f"Contraseña original: {password}")
        print(f"Hash generado: {hashed}")
        print("-" * 30)
    
    print("\nSQL para insertar en la base de datos:")
    print("=" * 50)
    
    # Generar SQL statements
    for username, password in passwords.items():
        hashed = hash_password(password)
        nombre = "Valeria (Administrador)" 
        
        sql = f"INSERT INTO usuarios_sistema (username, password_hash, nombre_completo, rol) VALUES ('{username}', '{hashed}', '{nombre}', 'admin');"
        print(sql)
    
    print("\n" + "=" * 50)
    print("INSTRUCCIONES:")
    print("1. Copia los comandos SQL de arriba")
    print("2. Ejecuta auth_setup.sql (sin los INSERT)")
    print("3. Ejecuta los INSERT generados aquí")
    print("4. ¡Listo para usar el sistema de autenticación!")

if __name__ == "__main__":
    main()