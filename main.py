import sqlite3

# Conectar (o crear) base de datos local
conexion = sqlite3.connect("conocimiento.db")
cursor = conexion.cursor()

# Crear tabla si no existe
cursor.execute("""
CREATE TABLE IF NOT EXISTS conocimiento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pregunta TEXT UNIQUE,
    respuesta TEXT
)
""")

conexion.commit()

print("Base de datos lista.")