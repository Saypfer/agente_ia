import csv
import importlib.util
import json
import os
import re
import threading
import unicodedata
from typing import Callable, List, Optional, Tuple

import numpy as np
from rapidfuzz import fuzz
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from pypdf import PdfReader

import database

try:
    import speech_recognition as sr
except Exception:
    sr = None

modelo = SentenceTransformer("all-MiniLM-L6-v2")

SALUDOS = ["hola", "buenos dias", "buenas tardes", "buenas noches"]

PALABRAS_PREGUNTA = [
    "que", "quien", "cuando", "donde", "por que", "como", "cual", "cuanto", "porque",
    "cuantos", "cuantas", "cuanta", "ano", "año"
]

ATRIBUTOS = {
    "quien creo": "creador",
    "quien desarrollo": "creador",
    "quien invento": "creador",
    "quien lo creo": "creador",
    "quien lo hizo": "creador",
    "quien la creo": "creador",
    "en que ano": "año",
    "en que año": "año",
    "cuando se creo": "año",
    "cuando se creó": "año",
    "que tipo": "tipo",
    "que es": "tipo",
    "que edad": "edad",
    "cuantos anos": "edad",
    "cuantos años": "edad",
    "edad": "edad",
    "cuantos hijos": "hijos",
    "cuantas esposas": "esposas",
    "cuantos equipos": "equipos",
}

PRONOMBRES_CONTEXTO = {
    "eso", "esa", "ese", "ello", "lo", "la", "el", "su", "sus", "tema", "anterior"
}

STOPWORDS = {
    "que", "quien", "cuando", "donde", "como", "cual", "cuanto", "cuantos", "cuantas",
    "cuanta", "por", "porque", "de", "del", "la", "el", "los", "las", "un", "una",
    "unos", "unas", "se", "es", "son", "fue", "fueron", "tiene", "tienen", "tenia",
    "tenían", "ano", "años", "año", "edad", "lo", "le", "les", "y", "en", "al"
}


def normalizar(texto: str) -> str:
    texto = (texto or "").lower().strip()
    texto = texto.replace("¿", "").replace("?", "")
    texto = ''.join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    texto = re.sub(r"\s+", " ", texto)
    return texto


def es_saludo(texto: str) -> bool:
    return any(texto.startswith(s) for s in SALUDOS)


def es_pregunta(texto: str) -> bool:
    palabras = texto.split()
    return any(p in palabras or texto.startswith(p + " ") for p in PALABRAS_PREGUNTA)


def obtener_embedding(texto: str):
    return np.array(modelo.encode(texto), dtype=np.float32)


def dividir_texto(texto: str, tamano_chunk: int = 500) -> List[str]:
    texto = re.sub(r"\s+", " ", texto).strip()
    if not texto:
        return []

    palabras = texto.split()
    chunks = []
    actual = []
    longitud = 0

    for palabra in palabras:
        actual.append(palabra)
        longitud += len(palabra) + 1
        if longitud >= tamano_chunk:
            chunks.append(" ".join(actual))
            actual = []
            longitud = 0

    if actual:
        chunks.append(" ".join(actual))

    return chunks


def tokens_significativos(texto: str) -> List[str]:
    texto = normalizar(texto)
    tokens = re.findall(r"\b[a-zA-Z0-9áéíóúñ]+\b", texto)
    return [t for t in tokens if t not in STOPWORDS and len(t) > 2]


def contar_tokens_comunes(texto1: str, texto2: str) -> int:
    s1 = set(tokens_significativos(texto1))
    s2 = set(tokens_significativos(texto2))
    return len(s1.intersection(s2))


def tiene_minimo_contexto_similar(texto1: str, texto2: str, minimo: int = 2) -> bool:
    return contar_tokens_comunes(texto1, texto2) >= minimo


def extraer_entidad_desde_texto(texto: str) -> Optional[str]:
    texto = normalizar(texto)
    palabras = texto.split()
    if not palabras:
        return None

    palabras_ruido = {
        "quien", "que", "como", "cuando", "donde", "por", "porque", "cual", "cuanto",
        "cuantos", "cuantas", "cuanta", "en", "ano", "año", "anos", "años",
        "se", "creo", "creó", "desarrollo", "desarrolló", "invento", "inventó",
        "tipo", "es", "de", "del", "la", "el", "los", "las", "un", "una",
        "edad", "tiene", "hijos", "esposas", "equipos", "lo", "hizo"
    }

    candidatas = [p for p in palabras if p not in palabras_ruido]
    if not candidatas:
        return None
    return candidatas[-1]


def detectar_atributo(pregunta: str) -> Optional[str]:
    pregunta = normalizar(pregunta)
    for clave, atributo in ATRIBUTOS.items():
        if clave in pregunta:
            return atributo

    if "edad" in pregunta or "cuantos anos" in pregunta or "cuantos años" in pregunta:
        return "edad"

    return None


def es_pregunta_dependiente_contexto(pregunta: str) -> bool:
    pregunta = normalizar(pregunta)
    palabras = set(pregunta.split())
    if palabras.intersection(PRONOMBRES_CONTEXTO):
        return True

    patrones_cortos = [
        r"^en que ano$",
        r"^en que año$",
        r"^y en que ano$",
        r"^y en que año$",
        r"^quien lo creo$",
        r"^quien la creo$",
        r"^quien lo desarrollo$",
        r"^que tipo$",
        r"^que es$",
        r"^que edad tiene$",
        r"^cuantos anos tiene$",
        r"^cuantos años tiene$",
        r"^quien lo hizo$",
    ]
    return any(re.match(p, pregunta) for p in patrones_cortos)


def resolver_pregunta_con_contexto(pregunta: str) -> str:
    pregunta_norm = normalizar(pregunta)
    memoria = database.obtener_ultima_memoria()
    if not memoria:
        return pregunta_norm

    tema, entidad, atributo_anterior, _, _ = memoria
    atributo_actual = detectar_atributo(pregunta_norm)
    entidad_actual = extraer_entidad_desde_texto(pregunta_norm)

    if entidad_actual:
        return pregunta_norm

    if not atributo_actual and es_pregunta_dependiente_contexto(pregunta_norm):
        atributo_actual = atributo_anterior or "tipo"

    if atributo_actual and entidad:
        if atributo_actual == "creador":
            return f"quien creo {entidad}"
        if atributo_actual == "año":
            return f"en que año se creo {entidad}"
        if atributo_actual == "tipo":
            return f"que es {entidad}"
        if atributo_actual == "edad":
            return f"que edad tiene {entidad}"
        if atributo_actual == "hijos":
            return f"cuantos hijos tiene {entidad}"
        if atributo_actual == "esposas":
            return f"cuantas esposas tiene {entidad}"
        if atributo_actual == "equipos":
            return f"cuantos equipos tiene {entidad}"

    if entidad and es_pregunta_dependiente_contexto(pregunta_norm):
        return f"{pregunta_norm} {entidad}"

    return pregunta_norm


def guardar_contexto(pregunta: str, respuesta: str) -> None:
    pregunta_norm = normalizar(pregunta)
    atributo = detectar_atributo(pregunta_norm)
    entidad = extraer_entidad_desde_texto(pregunta_norm)

    if not entidad:
        memoria = database.obtener_ultima_memoria()
        if memoria and es_pregunta_dependiente_contexto(pregunta_norm):
            entidad = memoria[1]

    if entidad or atributo:
        database.guardar_memoria(
            tema=entidad or "general",
            entidad=entidad or "",
            atributo=atributo or "",
            pregunta=pregunta_norm,
            respuesta=respuesta,
        )


def buscar_exacta(pregunta: str):
    resultado = database.buscar_exacta(pregunta)
    if resultado:
        return resultado[0]
    return None


def buscar_fuzzy(pregunta: str):
    datos = database.obtener_todo()
    if len(datos) < 1:
        return None

    mejor_score = 0
    mejor_respuesta = None
    minimo_tokens = 2

    tokens_pregunta = tokens_significativos(pregunta)
    if len(tokens_pregunta) <= 1:
        minimo_tokens = 1

    for p, r, _ in datos:
        comunes = contar_tokens_comunes(pregunta, p)
        if comunes < minimo_tokens:
            continue

        score_ratio = fuzz.ratio(pregunta, p)
        score_token = fuzz.token_set_ratio(pregunta, p)
        score = max(score_ratio, score_token)

        if score > mejor_score:
            mejor_score = score
            mejor_respuesta = r

    if mejor_score >= 90:
        return mejor_respuesta
    return None


def buscar_semantica(pregunta: str):
    datos = database.obtener_todo()
    if len(datos) < 1:
        return None

    pregunta_vec = obtener_embedding(pregunta).reshape(1, -1)
    mejor_similitud = 0
    mejor_respuesta = None

    tokens_pregunta = tokens_significativos(pregunta)
    minimo_tokens = 2 if len(tokens_pregunta) >= 2 else 1

    for p, r, emb_blob in datos:
        if not emb_blob:
            continue

        comunes = contar_tokens_comunes(pregunta, p)
        if comunes < minimo_tokens:
            continue

        emb = np.frombuffer(emb_blob, dtype=np.float32).reshape(1, -1)
        similitud = cosine_similarity(pregunta_vec, emb)[0][0]

        if similitud > mejor_similitud:
            mejor_similitud = similitud
            mejor_respuesta = r

    if mejor_similitud >= 0.90:
        return mejor_respuesta
    return None


def buscar_structurado(pregunta: str):
    pregunta_resuelta = resolver_pregunta_con_contexto(pregunta)
    atributo = detectar_atributo(pregunta_resuelta)
    entidad = extraer_entidad_desde_texto(pregunta_resuelta)

    if atributo and entidad:
        resultado = database.buscar_struct(entidad, atributo)
        if resultado:
            return resultado
    return None


def buscar_documentos(pregunta: str) -> Optional[str]:
    datos = database.obtener_documentos()
    if not datos:
        return None

    pregunta_vec = obtener_embedding(pregunta).reshape(1, -1)
    mejor_chunk = None
    mejor_fuente = None
    mejor_similitud = 0

    tokens_pregunta = tokens_significativos(pregunta)
    minimo_tokens = 2 if len(tokens_pregunta) >= 2 else 1

    for fuente, _, chunk, emb_blob in datos:
        if not emb_blob:
            continue

        comunes = contar_tokens_comunes(pregunta, chunk)
        if comunes < minimo_tokens:
            continue

        emb = np.frombuffer(emb_blob, dtype=np.float32).reshape(1, -1)
        similitud = cosine_similarity(pregunta_vec, emb)[0][0]

        if similitud > mejor_similitud:
            mejor_similitud = similitud
            mejor_chunk = chunk
            mejor_fuente = os.path.basename(fuente)

    if mejor_similitud >= 0.62 and mejor_chunk:
        return f"Según {mejor_fuente}: {mejor_chunk}"
    return None


def responder(entrada: str):
    entrada_norm = normalizar(entrada)

    if es_saludo(entrada_norm):
        return "Hola, ¿en qué puedo ayudarte?"

    pregunta_resuelta = resolver_pregunta_con_contexto(entrada_norm)

    if not es_pregunta(pregunta_resuelta) and not es_pregunta_dependiente_contexto(entrada_norm):
        return "No parece una pregunta. Intenta algo como: ¿Qué es Python?"

    resultado = buscar_exacta(pregunta_resuelta)
    if resultado:
        guardar_contexto(pregunta_resuelta, resultado)
        return resultado

    resultado = buscar_structurado(pregunta_resuelta)
    if resultado:
        guardar_contexto(pregunta_resuelta, resultado)
        return resultado

    resultado = buscar_fuzzy(pregunta_resuelta)
    if resultado:
        guardar_contexto(pregunta_resuelta, resultado)
        return resultado

    resultado = buscar_semantica(pregunta_resuelta)
    if resultado:
        guardar_contexto(pregunta_resuelta, resultado)
        return resultado

    resultado = buscar_documentos(pregunta_resuelta)
    if resultado:
        guardar_contexto(pregunta_resuelta, resultado)
        return resultado

    return None


def aprender(pregunta: str, respuesta: str):
    pregunta_norm = normalizar(pregunta)
    embedding = obtener_embedding(pregunta_norm)
    database.guardar(pregunta_norm, respuesta, embedding.tobytes())


def aprender_struct(entidad: str, atributo: str, valor: str):
    database.guardar_struct(normalizar(entidad), atributo, valor)


def importar_csv(ruta_archivo: str) -> Tuple[bool, str]:
    try:
        database.eliminar_documento_fuente(ruta_archivo)
        total = 0

        with open(ruta_archivo, "r", encoding="utf-8-sig", newline="") as archivo:
            lector = csv.reader(archivo)
            for fila in lector:
                texto = " ".join([str(celda).strip() for celda in fila if str(celda).strip()])
                for chunk in dividir_texto(texto):
                    embedding = obtener_embedding(chunk)
                    database.guardar_documento(ruta_archivo, "csv", chunk, embedding.tobytes())
                    total += 1

        if total == 0:
            return False, "El CSV no contenía texto utilizable."
        return True, f"CSV importado correctamente. Fragmentos indexados: {total}."
    except Exception as e:
        return False, f"Error al importar CSV: {e}"


def importar_pdf(ruta_archivo: str) -> Tuple[bool, str]:
    try:
        database.eliminar_documento_fuente(ruta_archivo)
        lector = PdfReader(ruta_archivo)
        total = 0

        for pagina in lector.pages:
            texto = pagina.extract_text() or ""
            for chunk in dividir_texto(texto):
                embedding = obtener_embedding(chunk)
                database.guardar_documento(ruta_archivo, "pdf", chunk, embedding.tobytes())
                total += 1

        if total == 0:
            return False, "El PDF no contenía texto extraíble."
        return True, f"PDF importado correctamente. Fragmentos indexados: {total}."
    except Exception as e:
        return False, f"Error al importar PDF: {e}"


def importar_documento(ruta_archivo: str) -> Tuple[bool, str]:
    extension = os.path.splitext(ruta_archivo)[1].lower()
    if extension == ".pdf":
        return importar_pdf(ruta_archivo)
    if extension == ".csv":
        return importar_csv(ruta_archivo)
    return False, "Formato no soportado. Usa archivos .pdf o .csv"


def buscar_modelo_vosk():
    base = os.path.dirname(os.path.abspath(__file__))

    posibles = [
        os.path.join(base, "vosk-model-small-es-0.42"),
        os.path.join(base, "vosk-model-es-0.42"),
        os.path.join(base, "vosk-model-es"),
        os.path.join(base, "model"),
    ]

    for ruta in posibles:
        if os.path.isdir(ruta):
            return ruta

    env_path = os.environ.get("VOSK_MODEL_PATH")
    if env_path and os.path.isdir(env_path):
        return env_path

    return None


def motores_voz_disponibles() -> Tuple[bool, str]:
    if sr is None:
        return False, "Falta instalar SpeechRecognition."

    tiene_vosk = importlib.util.find_spec("vosk") is not None
    tiene_sphinx = importlib.util.find_spec("pocketsphinx") is not None

    if tiene_vosk:
        modelo_vosk = buscar_modelo_vosk()
        if modelo_vosk:
            return True, "OK"

    if tiene_sphinx:
        return True, "OK"

    return False, (
        "No hay reconocimiento de voz listo para usar. "
        "Si usarás Vosk, además de instalar la librería debes descargar un modelo en español "
        "y colocarlo en una carpeta como 'vosk-model-small-es-0.42'."
    )


def escuchar_voz_local(timeout: int = 8, phrase_time_limit: int = 10) -> Tuple[bool, str]:
    disponible, mensaje = motores_voz_disponibles()
    if not disponible:
        return False, mensaje

    try:
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.8

        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(
                source,
                timeout=timeout,
                phrase_time_limit=phrase_time_limit
            )

        if importlib.util.find_spec("vosk") is not None:
            modelo_vosk = buscar_modelo_vosk()
            if modelo_vosk:
                try:
                    texto = recognizer.recognize_vosk(audio, model=modelo_vosk)
                    try:
                        data = json.loads(texto)
                        texto = data.get("text", "").strip()
                    except Exception:
                        texto = str(texto).strip()

                    if texto:
                        return True, texto
                except Exception:
                    pass

        if importlib.util.find_spec("pocketsphinx") is not None:
            try:
                texto = recognizer.recognize_sphinx(audio, language="es-ES")
                if texto:
                    return True, texto
            except Exception:
                pass

        return False, (
            "No se pudo reconocer la voz. "
            "Si usas Vosk, verifica que el modelo en español esté descargado y en la carpeta correcta."
        )

    except Exception as e:
        nombre = type(e).__name__
        if nombre == "WaitTimeoutError":
            return False, "No detecté voz a tiempo. Presiona 'Hablar' y empieza a hablar inmediatamente."
        return False, f"Error al capturar audio: {e}"


def escuchar_voz_en_hilo(callback_ok: Callable[[str], None], callback_error: Callable[[str], None]) -> None:
    def tarea():
        ok, resultado = escuchar_voz_local()
        if ok:
            callback_ok(resultado)
        else:
            callback_error(resultado)

    threading.Thread(target=tarea, daemon=True).start()