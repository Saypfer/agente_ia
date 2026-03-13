import unicodedata
import numpy as np
from rapidfuzz import fuzz
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

import database

modelo = SentenceTransformer('all-MiniLM-L6-v2')

SALUDOS = ["hola", "buenos dias", "buenas tardes", "buenas noches"]

PALABRAS_PREGUNTA = [
"que","quien","cuando","donde","por que","como","cual","cuanto","porque",
"cuantos","cuantas","cuanta"
]

ATRIBUTOS = {
"quien creo": "creador",
"quien desarrollo": "creador",
"en que año": "año",
"cuando se creo": "año",
"que tipo": "tipo",
"que es": "tipo"
}

#Normaliza el texto cuando hay minusculas o mayusculas
def normalizar(texto):

    texto = texto.lower()
    texto = texto.replace("¿","").replace("?","")
    texto = ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    return texto

#Identifica si es un saludo
def es_saludo(texto):

    for s in SALUDOS:
        if texto.startswith(s):
            return True

    return False

#Identifica si es una pregunta
def es_pregunta(texto):

    palabras = texto.split()

    for p in PALABRAS_PREGUNTA:
        if p in palabras:
            return True

    return False


def obtener_embedding(texto):
    return modelo.encode(texto)

# BUSQUEDA EXACTA

def buscar_exacta(pregunta):

    resultado = database.buscar_exacta(pregunta)

    if resultado:
        return resultado[0]

    return None


# BUSQUEDA FUZZY

def buscar_fuzzy(pregunta):

    datos = database.obtener_todo()
    
    if len(datos) < 3:
        return None

    mejor_score = 0
    mejor_respuesta = None

    for p,r,_ in datos:

        score = fuzz.ratio(pregunta,p)

        if score > mejor_score:

            mejor_score = score
            mejor_respuesta = r

    if mejor_score > 85:
        return mejor_respuesta

    return None


# BUSQUEDA SEMANTICA

def buscar_semantica(pregunta):

    datos = database.obtener_todo()

    if len(datos) < 5:
        return None

    pregunta_vec = obtener_embedding(pregunta).reshape(1,-1)

    mejor_similitud = 0
    mejor_respuesta = None

    for p,r,emb_blob in datos:

        emb = np.frombuffer(emb_blob,dtype=np.float32).reshape(1,-1)

        similitud = cosine_similarity(pregunta_vec,emb)[0][0]

        if similitud > mejor_similitud:

            mejor_similitud = similitud
            mejor_respuesta = r

    if mejor_similitud > 0.70:
        return mejor_respuesta

    return None


# BUSQUEDA ESTRUCTURADA

def buscar_structurado(pregunta):

    for clave in ATRIBUTOS:

        if clave in pregunta:

            atributo = ATRIBUTOS[clave]

            palabras = pregunta.split()

            entidad = palabras[-1]

            resultado = database.buscar_struct(entidad,atributo)

            if resultado:
                return resultado

    return None


# RESPONDER

def responder(entrada):

    entrada_norm = normalizar(entrada)

    if es_saludo(entrada_norm):

        return "Hola, ¿en qué puedo ayudarte?"


    if not es_pregunta(entrada_norm):

        return "No parece una pregunta. Intenta algo como ¿Que es programacion?"


    resultado = buscar_exacta(entrada_norm)

    if resultado:
        return resultado


    resultado = buscar_structurado(entrada_norm)

    if resultado:
        return resultado


    resultado = buscar_fuzzy(entrada_norm)

    if resultado:
        return resultado


    resultado = buscar_semantica(entrada_norm)

    if resultado:
        return resultado


    return None


def aprender(pregunta,respuesta):

    embedding = obtener_embedding(pregunta)

    database.guardar(
        pregunta,
        respuesta,
        embedding.tobytes()
    )