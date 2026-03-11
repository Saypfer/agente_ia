import sqlite3
import unicodedata
import numpy as np
from rapidfuzz import fuzz
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

#conectar base de datos

modelo = SentenceTransformer('all-MiniLM-L6-v2')

conexion = sqlite3.connect("conocimiento.db")
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

SALUDOS = ["hola", "buenos dias", "buenas tardes", "buenas noches"]

# Funciones

#normaliza datos identificando las mismas preguntas pero escritas de diferente manera
def normalizar(texto):
    texto = texto.lower()
    texto = ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    return texto

# identifica si es saludo o pregunta
def es_saludo(texto):
    return any(texto.startswith(s) for s in SALUDOS)

#ordena las preguntas
def obtener_embedding(texto):
    return modelo.encode(texto)

#guarda informacion nueva
def guardar_conocimiento(pregunta, respuesta):
    embedding = obtener_embedding(pregunta)
    cursor.execute(
        "INSERT INTO conocimiento (pregunta, respuesta, embedding) VALUES (?, ?, ?)",
        (pregunta, respuesta, embedding.tobytes())
    )
    conexion.commit()
    print("IA: He aprendido algo nuevo.")

def buscar_exacta(pregunta):
    cursor.execute("SELECT respuesta FROM conocimiento WHERE pregunta = ?", (pregunta,))
    return cursor.fetchone()

def buscar_fuzzy(pregunta):
    cursor.execute("SELECT pregunta, respuesta FROM conocimiento")
    datos = cursor.fetchall()
    
    mejor_score = 0
    mejor_respuesta = None

    for p, r in datos:
        score = fuzz.ratio(pregunta, p)
        if score > mejor_score:
            mejor_score = score
            mejor_respuesta = r

    if mejor_score > 80:
        return mejor_respuesta

    return None

def buscar_semantica(pregunta):
    cursor.execute("SELECT pregunta, respuesta, embedding FROM conocimiento")
    datos = cursor.fetchall()

    if not datos:
        return None

    pregunta_vec = obtener_embedding(pregunta).reshape(1, -1)

    mejor_similitud = 0
    mejor_respuesta = None

    for p, r, emb_blob in datos:
        emb = np.frombuffer(emb_blob, dtype=np.float32).reshape(1, -1)
        similitud = cosine_similarity(pregunta_vec, emb)[0][0]

        if similitud > mejor_similitud:
            mejor_similitud = similitud
            mejor_respuesta = r

    if mejor_similitud > 0.70:
        return mejor_respuesta

    return None


def iniciar():
    print("Chatbot IA iniciado. Escribe 'salir' para terminar.\n")

    while True:
        entrada = input("Tú: ")

        if entrada.lower() == "salir":
            print("IA: Hasta luego.")
            break

        entrada_norm = normalizar(entrada)

        # Saludo
        if es_saludo(entrada_norm):
            print("IA: Hola, ¿en qué puedo ayudarte hoy?")
            continue

        #  Búsqueda exacta
        resultado = buscar_exacta(entrada_norm)
        if resultado:
            print("IA:", resultado[0])
            continue

        #  Búsqueda fuzzy
        resultado = buscar_fuzzy(entrada_norm)
        if resultado:
            print("IA:", resultado)
            continue

        # Búsqueda semántica
        resultado = buscar_semantica(entrada_norm)
        if resultado:
            print("IA:", resultado)
            continue

        # Aprender
        print("IA: No conozco la respuesta. ¿Cuál debería ser?")
        nueva_respuesta = input("Respuesta: ")
        guardar_conocimiento(entrada_norm, nueva_respuesta)

#ejecuta

if __name__ == "__main__":
    iniciar()