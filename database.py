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

cursor.execute("""
CREATE TABLE IF NOT EXISTS conocimiento_struct (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entidad TEXT,
    atributo TEXT,
    valor TEXT
)
""")

conexion.commit()


def guardar(pregunta,respuesta,embedding):

    try:

        cursor.execute(
        "INSERT INTO conocimiento(pregunta,respuesta,embedding) VALUES(?,?,?)",
        (pregunta,respuesta,embedding)
        )

        conexion.commit()

    except sqlite3.IntegrityError:

        # si la pregunta ya existe, simplemente se ignora
        pass


def obtener_todo():
    cursor.execute("SELECT pregunta, respuesta, embedding FROM conocimiento")
    return cursor.fetchall()


def buscar_exacta(pregunta):
    cursor.execute("SELECT respuesta FROM conocimiento WHERE pregunta = ?", (pregunta,))
    return cursor.fetchone()

def guardar_struct(entidad, atributo, valor):

    cursor.execute(
        "INSERT INTO conocimiento_struct (entidad, atributo, valor) VALUES (?, ?, ?)",
        (entidad, atributo, valor)
    )

    conexion.commit()

def buscar_struct(entidad, atributo):

    cursor.execute(
        "SELECT valor FROM conocimiento_struct WHERE entidad=? AND atributo=?",
        (entidad, atributo)
    )

    resultado = cursor.fetchone()

    if resultado:
        return resultado[0]

    return None


