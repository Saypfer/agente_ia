import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

import chatbot
import database


# =========================
# CONFIGURACIÓN DE COLORES
# =========================
BG_APP = "#1f2937"           # fondo general
BG_CHAT = "#111827"          # fondo zona de chat
BG_USER = "#2563eb"          # burbuja usuario
BG_AGENT = "#374151"         # burbuja agente
BG_INPUT = "#0f172a"         # caja entrada
BG_BUTTON = "#1f2937"        # botón normal
BG_BUTTON_ACTIVE = "#334155"
BG_SEND = "#3b82f6"          # botón enviar
BG_SEND_ACTIVE = "#2563eb"

TEXT_MAIN = "#f9fafb"
TEXT_SOFT = "#cbd5e1"
TEXT_MUTED = "#94a3b8"
BORDER = "#334155"


# =========================
# VENTANA PRINCIPAL
# =========================
ventana = tk.Tk()
ventana.title("Chatbot IA Local")
ventana.geometry("1000x680")
ventana.configure(bg=BG_APP)
ventana.minsize(820, 560)


# =========================
# CONTENEDOR PRINCIPAL
# =========================
contenedor = tk.Frame(ventana, bg=BG_APP)
contenedor.pack(fill="both", expand=True, padx=12, pady=12)


# =========================
# ÁREA DE CHAT CON SCROLL
# =========================
chat_outer = tk.Frame(contenedor, bg=BG_APP)
chat_outer.pack(fill="both", expand=True)

chat_canvas = tk.Canvas(
    chat_outer,
    bg=BG_CHAT,
    highlightthickness=0,
    bd=0
)
chat_canvas.pack(side="left", fill="both", expand=True)

scrollbar = tk.Scrollbar(chat_outer, orient="vertical", command=chat_canvas.yview)
scrollbar.pack(side="right", fill="y")

chat_canvas.configure(yscrollcommand=scrollbar.set)

chat_frame = tk.Frame(chat_canvas, bg=BG_CHAT)
chat_window = chat_canvas.create_window((0, 0), window=chat_frame, anchor="nw")


def ajustar_scroll(event=None):
    chat_canvas.configure(scrollregion=chat_canvas.bbox("all"))
    chat_canvas.itemconfig(chat_window, width=chat_canvas.winfo_width())


chat_frame.bind("<Configure>", ajustar_scroll)
chat_canvas.bind("<Configure>", ajustar_scroll)


def scroll_al_final():
    ventana.update_idletasks()
    chat_canvas.yview_moveto(1.0)


# =========================
# FUNCIONES PARA MENSAJES
# =========================
def crear_burbuja(remitente: str, mensaje: str, es_usuario: bool):
    fila = tk.Frame(chat_frame, bg=BG_CHAT)
    fila.pack(fill="x", padx=12, pady=8)

    if es_usuario:
        fila.columnconfigure(0, weight=1)
        fila.columnconfigure(1, weight=0)

        cont = tk.Frame(fila, bg=BG_CHAT)
        cont.grid(row=0, column=1, sticky="e")

        lbl_remitente = tk.Label(
            cont,
            text=remitente,
            bg=BG_CHAT,
            fg=TEXT_SOFT,
            font=("Segoe UI", 10, "bold"),
            anchor="e",
            justify="right"
        )
        lbl_remitente.pack(anchor="e", pady=(0, 4))

        burbuja = tk.Label(
            cont,
            text=mensaje,
            bg=BG_USER,
            fg=TEXT_MAIN,
            font=("Segoe UI", 11),
            wraplength=620,
            justify="left",
            padx=16,
            pady=12
        )
        burbuja.pack(anchor="e")

    else:
        fila.columnconfigure(0, weight=0)
        fila.columnconfigure(1, weight=1)

        cont = tk.Frame(fila, bg=BG_CHAT)
        cont.grid(row=0, column=0, sticky="w")

        lbl_remitente = tk.Label(
            cont,
            text=remitente,
            bg=BG_CHAT,
            fg=TEXT_SOFT,
            font=("Segoe UI", 10, "bold"),
            anchor="w",
            justify="left"
        )
        lbl_remitente.pack(anchor="w", pady=(0, 4))

        burbuja = tk.Label(
            cont,
            text=mensaje,
            bg=BG_AGENT,
            fg=TEXT_MAIN,
            font=("Segoe UI", 11),
            wraplength=620,
            justify="left",
            padx=16,
            pady=12
        )
        burbuja.pack(anchor="w")

    scroll_al_final()


def escribir_usuario(texto: str):
    crear_burbuja("Tú", texto, True)


def escribir_ia(texto: str):
    crear_burbuja("Agente", texto, False)


def escribir_sistema(texto: str):
    crear_burbuja("Sistema", texto, False)


# =========================
# LÓGICA DEL CHAT
# =========================
def procesar_mensaje(mensaje: str):
    mensaje = mensaje.strip()
    if not mensaje:
        return

    escribir_usuario(mensaje)
    entrada.delete(0, tk.END)

    try:
        respuesta = chatbot.responder(mensaje)

        if respuesta:
            escribir_ia(respuesta)
        else:
            escribir_ia("No conozco la respuesta.")
            nueva = simpledialog.askstring(
                "Aprender",
                "¿Cuál debería ser la respuesta?"
            )

            if nueva and nueva.strip():
                chatbot.aprender(chatbot.normalizar(mensaje), nueva.strip())
                escribir_sistema("He aprendido algo nuevo.")

    except Exception as e:
        messagebox.showerror("Error Intenta una nueva pregunta", f"Ocurrió un error:\n{e}")
        escribir_sistema(f"Error: {e}")


def enviar():
    procesar_mensaje(entrada.get())


def importar_documento():
    ruta = filedialog.askopenfilename(
        title="Seleccionar documento",
        filetypes=[
            ("Documentos soportados", "*.pdf *.csv"),
            ("PDF", "*.pdf"),
            ("CSV", "*.csv")
        ]
    )
    if not ruta:
        return

    escribir_sistema(f"Importando documento: {ruta}")

    try:
        ok, mensaje = chatbot.importar_documento(ruta)

        if ok:
            escribir_sistema(mensaje)
            messagebox.showinfo("Importación", mensaje)
        else:
            escribir_sistema(mensaje)
            messagebox.showerror("Importación", mensaje)

    except Exception as e:
        messagebox.showerror("Error", f"No se pudo importar el archivo:\n{e}")
        escribir_sistema(f"Error al importar: {e}")


def voz_ok(texto: str):
    def accion():
        entrada.delete(0, tk.END)
        entrada.insert(0, texto)
        escribir_sistema(f"Voz reconocida -> {texto}")
        enviar()

    ventana.after(0, accion)


def voz_error(mensaje: str):
    def accion():
        escribir_sistema(mensaje)
        messagebox.showwarning("Reconocimiento de voz", mensaje)

    ventana.after(0, accion)


def escuchar_voz():
    escribir_sistema("Escuchando...")
    try:
        chatbot.escuchar_voz_en_hilo(voz_ok, voz_error)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo iniciar el reconocimiento de voz:\n{e}")
        escribir_sistema(f"Error de voz: {e}")


def limpiar_contexto():
    try:
        database.limpiar_memoria()
        escribir_sistema("Contexto conversacional reiniciado.")
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo limpiar el contexto:\n{e}")
        escribir_sistema(f"Error al limpiar contexto: {e}")


# =========================
# PANEL INFERIOR
# =========================
panel_inferior = tk.Frame(contenedor, bg=BG_APP)
panel_inferior.pack(fill="x", pady=(10, 0))


# Caja de entrada
input_frame = tk.Frame(
    panel_inferior,
    bg=BG_INPUT,
    highlightbackground=BORDER,
    highlightthickness=1,
    bd=0
)
input_frame.pack(fill="x", pady=(0, 10))

entrada = tk.Entry(
    input_frame,
    bg=BG_INPUT,
    fg=TEXT_MAIN,
    insertbackground=TEXT_MAIN,
    relief="flat",
    bd=0,
    font=("Segoe UI", 12)
)
entrada.pack(fill="x", padx=16, pady=14)
entrada.bind("<Return>", lambda event: enviar())


# Barra de botones
barra_botones = tk.Frame(panel_inferior, bg=BG_APP)
barra_botones.pack(fill="x")

barra_botones.columnconfigure(0, weight=1)
barra_botones.columnconfigure(1, weight=1)
barra_botones.columnconfigure(2, weight=1)
barra_botones.columnconfigure(3, weight=1)


def crear_boton(parent, texto, comando, bg, activebg, fg=TEXT_MAIN):
    return tk.Button(
        parent,
        text=texto,
        command=comando,
        bg=bg,
        fg=fg,
        activebackground=activebg,
        activeforeground=fg,
        relief="flat",
        bd=0,
        font=("Segoe UI", 11, "bold"),
        padx=10,
        pady=12,
        cursor="hand2"
    )


btn_hablar = crear_boton(
    barra_botones, "🎤 Hablar", escuchar_voz,
    BG_BUTTON, BG_BUTTON_ACTIVE
)
btn_hablar.grid(row=0, column=0, sticky="ew", padx=6)

btn_archivo = crear_boton(
    barra_botones, "📎 Cargar Archivo", importar_documento,
    BG_BUTTON, BG_BUTTON_ACTIVE
)
btn_archivo.grid(row=0, column=1, sticky="ew", padx=6)

btn_enviar = crear_boton(
    barra_botones, "➤ Enviar", enviar,
    BG_SEND, BG_SEND_ACTIVE
)
btn_enviar.grid(row=0, column=2, sticky="ew", padx=6)

btn_limpiar = crear_boton(
    barra_botones, "🧹Limpiar Contexto", limpiar_contexto,
    BG_BUTTON, BG_BUTTON_ACTIVE
)
btn_limpiar.grid(row=0, column=3, sticky="ew", padx=6)


# =========================
# MENSAJE INICIAL
# =========================
escribir_ia("Hola. Estoy listo para ayudarte y aprender. Puedes escribir, usar voz o cargar un archivo.")


# Scroll con rueda del mouse
def _on_mousewheel(event):
    chat_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


chat_canvas.bind_all("<MouseWheel>", _on_mousewheel)


ventana.mainloop()