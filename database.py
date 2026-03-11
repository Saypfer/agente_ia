import sqlite3

conexion = sqlite3.connect("conocimiento.db", check_same_thread=False)
cursor = conexion.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS conocimiento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pregunta TEXT UNIQUE,
    respuesta TEXT,
    embedding BLOB
)
""")

conexion.commit()


def guardar(pregunta, respuesta, embedding):
    cursor.execute(
        "INSERT INTO conocimiento (pregunta, respuesta, embedding) VALUES (?, ?, ?)",
        (pregunta, respuesta, embedding)
    )
    conexion.commit()


def obtener_todo():
    cursor.execute("SELECT pregunta, respuesta, embedding FROM conocimiento")
    return cursor.fetchall()


def buscar_exacta(pregunta):
    cursor.execute("SELECT respuesta FROM conocimiento WHERE pregunta = ?", (pregunta,))
    return cursor.fetchone()