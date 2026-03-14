import sqlite3
from typing import List, Optional, Tuple

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

cursor.execute("""
CREATE TABLE IF NOT EXISTS memoria_conversacion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tema TEXT,
    entidad TEXT,
    atributo TEXT,
    pregunta TEXT,
    respuesta TEXT,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conexion.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS documentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fuente TEXT,
    tipo TEXT,
    chunk TEXT,
    embedding BLOB
)
""")
conexion.commit()


def guardar(pregunta: str, respuesta: str, embedding: bytes) -> None:
    try:
        cursor.execute(
            "INSERT INTO conocimiento(pregunta,respuesta,embedding) VALUES(?,?,?)",
            (pregunta, respuesta, embedding),
        )
        conexion.commit()
    except sqlite3.IntegrityError:
        cursor.execute(
            "UPDATE conocimiento SET respuesta = ?, embedding = ? WHERE pregunta = ?",
            (respuesta, embedding, pregunta),
        )
        conexion.commit()


def obtener_todo() -> List[Tuple[str, str, bytes]]:
    cursor.execute("SELECT pregunta, respuesta, embedding FROM conocimiento")
    return cursor.fetchall()


def buscar_exacta(pregunta: str) -> Optional[Tuple[str]]:
    cursor.execute("SELECT respuesta FROM conocimiento WHERE pregunta = ?", (pregunta,))
    return cursor.fetchone()


def guardar_struct(entidad: str, atributo: str, valor: str) -> None:
    cursor.execute(
        "INSERT INTO conocimiento_struct (entidad, atributo, valor) VALUES (?, ?, ?)",
        (entidad, atributo, valor),
    )
    conexion.commit()


def buscar_struct(entidad: str, atributo: str) -> Optional[str]:
    cursor.execute(
        "SELECT valor FROM conocimiento_struct WHERE entidad=? AND atributo=? ORDER BY id DESC LIMIT 1",
        (entidad, atributo),
    )
    resultado = cursor.fetchone()
    if resultado:
        return resultado[0]
    return None


def guardar_memoria(tema: str, entidad: str, atributo: str, pregunta: str, respuesta: str) -> None:
    cursor.execute(
        """
        INSERT INTO memoria_conversacion (tema, entidad, atributo, pregunta, respuesta)
        VALUES (?, ?, ?, ?, ?)
        """,
        (tema, entidad, atributo, pregunta, respuesta),
    )
    conexion.commit()


def obtener_ultima_memoria() -> Optional[Tuple[str, str, str, str, str]]:
    cursor.execute(
        """
        SELECT tema, entidad, atributo, pregunta, respuesta
        FROM memoria_conversacion
        ORDER BY id DESC LIMIT 1
        """
    )
    return cursor.fetchone()


def limpiar_memoria() -> None:
    cursor.execute("DELETE FROM memoria_conversacion")
    conexion.commit()


def guardar_documento(fuente: str, tipo: str, chunk: str, embedding: bytes) -> None:
    cursor.execute(
        "INSERT INTO documentos (fuente, tipo, chunk, embedding) VALUES (?, ?, ?, ?)",
        (fuente, tipo, chunk, embedding),
    )
    conexion.commit()


def eliminar_documento_fuente(fuente: str) -> None:
    cursor.execute("DELETE FROM documentos WHERE fuente = ?", (fuente,))
    conexion.commit()


def obtener_documentos() -> List[Tuple[str, str, str, bytes]]:
    cursor.execute("SELECT fuente, tipo, chunk, embedding FROM documentos")
    return cursor.fetchall()


def contar_documentos() -> int:
    cursor.execute("SELECT COUNT(*) FROM documentos")
    return cursor.fetchone()[0]