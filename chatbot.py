import unicodedata
import numpy as np
from rapidfuzz import fuzz
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

import database

modelo = SentenceTransformer('all-MiniLM-L6-v2')

SALUDOS = ["hola", "buenos dias", "buenas tardes", "buenas noches"]

PALABRAS_PREGUNTA = [
"que","quien","cuando","donde","por que","como","cual","cuanto","porque","cuantos",
"cuantas","cuanta"
]


def normalizar(texto):
    texto = texto.lower()
    texto = texto.replace("¿","").replace("?","")
    texto = ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    return texto


def es_saludo(texto):
    return any(texto.startswith(s) for s in SALUDOS)


def es_pregunta(texto):
    if "?" in texto:
        return True
    return any(texto.startswith(p) for p in PALABRAS_PREGUNTA)


def obtener_embedding(texto):
    return modelo.encode(texto)


def buscar_fuzzy(pregunta):

    datos = database.obtener_todo()

    mejor_score = 0
    mejor_respuesta = None

    for p, r, _ in datos:
        score = fuzz.ratio(pregunta, p)

        if score > mejor_score:
            mejor_score = score
            mejor_respuesta = r

    if mejor_score > 80:
        return mejor_respuesta

    return None


def buscar_semantica(pregunta):

    datos = database.obtener_todo()

    if not datos:
        return None

    pregunta_vec = obtener_embedding(pregunta).reshape(1,-1)

    mejor_similitud = 0
    mejor_respuesta = None

    for p, r, emb_blob in datos:

        emb = np.frombuffer(emb_blob, dtype=np.float32).reshape(1,-1)

        similitud = cosine_similarity(pregunta_vec, emb)[0][0]

        if similitud > mejor_similitud:
            mejor_similitud = similitud
            mejor_respuesta = r

    if mejor_similitud > 0.70:
        return mejor_respuesta

    return None


def responder(entrada):

    entrada_norm = normalizar(entrada)

    if es_saludo(entrada_norm):
        return "Hola, ¿en qué puedo ayudarte?"

    if not es_pregunta(entrada_norm):
        return "No parece una pregunta. Intenta algo como: ¿Qué es Python?"

    resultado = database.buscar_exacta(entrada_norm)

    if resultado:
        return resultado[0]

    resultado = buscar_fuzzy(entrada_norm)

    if resultado:
        return resultado

    resultado = buscar_semantica(entrada_norm)

    if resultado:
        return resultado

    return None


def aprender(pregunta, respuesta):

    embedding = obtener_embedding(pregunta)

    database.guardar(
        pregunta,
        respuesta,
        embedding.tobytes()
    )