import tkinter as tk
import chatbot
from tkinter import simpledialog

def enviar():

    mensaje = entrada.get()

    chat.insert(tk.END,"Tú: "+mensaje+"\n")

    respuesta = chatbot.responder(mensaje)

    if respuesta:
        chat.insert(tk.END,"IA: "+respuesta+"\n")

    else:
        chat.insert(tk.END,"IA: No conozco la respuesta.\n")

        nueva = simpledialog.askstring(
            "Aprender",
            "¿Cuál debería ser la respuesta?"
        )

        if nueva:
            chatbot.aprender(mensaje,nueva)

            chat.insert(tk.END,"IA: He aprendido algo nuevo.\n")

    entrada.delete(0,tk.END)


ventana = tk.Tk()
ventana.title("Chatbot IA")

chat = tk.Text(ventana,height=20,width=60)
chat.pack()

entrada = tk.Entry(ventana,width=50)
entrada.pack(side=tk.LEFT)

boton = tk.Button(ventana,text="Enviar",command=enviar)
boton.pack(side=tk.RIGHT)

ventana.mainloop()