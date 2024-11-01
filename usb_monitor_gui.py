import os #permite interactuar con el sistema operativo , manejo de archivos ,carpetas etc
import time #obtiene fecha y hora con consultoria al mismo pc
import psutil #permite obtener informacion del sistema como uso de CPU , ip ,mac y controlar procesos 
import socket #permite conexiones de bajo nivel como para servidores o cliente
import tkinter as tk #biblioteca estandar de python para entornos graficos basicos
from tkinter import messagebox # se utiliza para mostrar mensajes emergentes
import pandas as pd #permite manipulacion y analisis de datos
from datetime import datetime #utiliza fecha y hora de manera actualizada
import uuid  #se utiliza para identificaciones unicas

# Lista para almacenar logs y dispositivos ya analizados
log_data = []
dispositivos_analizados = {}
dispositivos_maliciosos = []

# Función para obtener información del computador
def obtener_info_computador():
    nombre_usuario = os.getlogin()
    nombre_computador = os.getenv('COMPUTERNAME')
    ip = socket.gethostbyname(socket.gethostname())
    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0, 2 * 6, 2)][::-1])
    return nombre_usuario, nombre_computador, ip, mac

# Función para detectar dispositivos USB conectados
def detectar_dispositivos_usb():
    dispositivos = []
    for part in psutil.disk_partitions(all=False):
        if 'removable' in part.opts:
            dispositivos.append(part.device)
    return dispositivos

# Función para verificar archivos maliciosos
def es_archivo_malicioso(ruta_archivo):
    extensiones_maliciosas = ['.exe', '.bat', '.cmd', '.vbs', '.msi']
    return any(ruta_archivo.endswith(ext) for ext in extensiones_maliciosas)

# Función para registrar eventos en la pantalla
def registrar_evento(evento, ruta, dispositivo, malicioso=False, desconectado=False):
    fecha_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    texto_evento = f"Evento: {evento} - Ruta: {ruta} - Dispositivo: {dispositivo} - Fecha y Hora: {fecha_hora}"

    if malicioso:
        texto_evento += f"\nArchivo malicioso detectado: {ruta}"
        log_text.insert(tk.END, texto_evento + "\n", "malicioso")
        dispositivos_maliciosos.append(dispositivo)
    else:
        log_text.insert(tk.END, texto_evento + "\n", "seguro")

    # Agregar registro a los logs
    log_data.append({
        "Dispositivo": dispositivo,
        "Ruta": ruta,
        "Accion": evento,
        "Fecha_Hora": fecha_hora,
        "Detalles": ruta,
        "Malicioso": malicioso,
        "Desconectado": desconectado
    })

# Función para analizar un dispositivo USB
def analizar_dispositivo(dispositivo):
    registrar_evento("Conectado", dispositivo, dispositivo)
    try:
        archivos_iniciales = set(os.listdir(dispositivo))
        dispositivos_analizados[dispositivo] = archivos_iniciales

        for archivo in archivos_iniciales:
            ruta_archivo = os.path.join(dispositivo, archivo)
            if es_archivo_malicioso(ruta_archivo):
                registrar_evento("Detectado archivo malicioso", ruta_archivo, dispositivo, malicioso=True)
            else:
                registrar_evento("Archivo existente", ruta_archivo, dispositivo)
    except Exception as e:
        log_text.insert(tk.END, f"Error al analizar {dispositivo}: {str(e)}\n", "malicioso")

# Función para comenzar el análisis inicial y luego el análisis en tiempo real
def comenzar_analisis():
    log_text.config(fg="purple")
    log_text.insert(tk.END, "Esperando dispositivos...\n")
    root.update()

    while True:
        dispositivos_actuales = detectar_dispositivos_usb()
        dispositivos_actuales_set = set(dispositivos_actuales)

        # Analizar dispositivos nuevos
        for dispositivo in dispositivos_actuales_set:
            if dispositivo not in dispositivos_analizados:
                analizar_dispositivo(dispositivo)

        # Comprobar cambios en dispositivos analizados
        for dispositivo in list(dispositivos_analizados.keys()):
            if dispositivo in dispositivos_actuales_set:
                try:
                    archivos_actuales = set(os.listdir(dispositivo))

                    # Verificar si se añadieron archivos nuevos
                    archivos_nuevos = archivos_actuales - dispositivos_analizados[dispositivo]
                    for archivo in archivos_nuevos:
                        ruta_archivo = os.path.join(dispositivo, archivo)
                        if es_archivo_malicioso(ruta_archivo):
                            registrar_evento("Detectado archivo malicioso", ruta_archivo, dispositivo, malicioso=True)
                        else:
                            registrar_evento("Archivo creado", ruta_archivo, dispositivo)

                    # Verificar si se eliminaron archivos
                    archivos_eliminados = dispositivos_analizados[dispositivo] - archivos_actuales
                    for archivo in archivos_eliminados:
                        ruta_archivo = os.path.join(dispositivo, archivo)
                        registrar_evento("Archivo eliminado", ruta_archivo, dispositivo)

                    # Actualizar los archivos analizados para el siguiente ciclo
                    dispositivos_analizados[dispositivo] = archivos_actuales

                except Exception as e:
                    log_text.insert(tk.END, f"Error al analizar {dispositivo}: {str(e)}\n", "malicioso")
            else:
                registrar_evento("Desconectado", dispositivo, dispositivo, desconectado=True)
                del dispositivos_analizados[dispositivo]

        root.update()
        time.sleep(2)  # Esperar 2 segundos antes de la próxima revisión

# Función para detener el análisis
def detener_analisis():
    log_text.config(fg="yellow")
    log_text.insert(tk.END, "Análisis detenido.\n")

# Función para eliminar archivos maliciosos
def eliminar_archivos_no_deseados():
    for log in log_data:
        if log["Malicioso"] and not log.get("Archivo Eliminado", False):
            try:
                os.remove(log["Ruta"])
                registrar_evento("Eliminado", log["Ruta"], log["Dispositivo"])
                log["Archivo Eliminado"] = True  # Marcar como eliminado
            except Exception as e:
                log_text.config(fg="red")
                log_text.insert(tk.END, f"Error eliminando archivo {log['Ruta']}: {str(e)}\n")

# Función para desconectar dispositivos con archivos maliciosos
def desconectar_dispositivos_maliciosos():
    for dispositivo in dispositivos_maliciosos:
        os.system(f"mountvol {dispositivo} /p")
        registrar_evento("Desconectado", dispositivo, dispositivo, desconectado=True)  # Registrar la desconexión en logs
        log_text.insert(tk.END, f"Dispositivo {dispositivo} desmontado.\n")
    if dispositivos_maliciosos:
        messagebox.showinfo("Éxito", "Dispositivos con archivos maliciosos desconectados.")
    else:
        messagebox.showwarning("Advertencia", "No hay dispositivos maliciosos para desconectar.")

# Función para mostrar los logs en la pantalla
def mostrar_logs():
    log_text.config(fg="blue")
    log_text.insert(tk.END, "=== Mostrando Logs ===\n")
    for log in log_data:
        log_text.insert(tk.END, f"{log}\n")
    log_text.insert(tk.END, "=== Fin de Logs ===\n")

# Función para limpiar la pantalla
def limpiar_pantalla():
    log_text.delete(1.0, tk.END)

# Función para guardar los logs en un archivo Excel
def guardar_logs_excel():
    if not log_data:
        messagebox.showerror("Error", "No hay datos para exportar")
        return

    nombre_usuario, nombre_computador, ip, mac = obtener_info_computador()
    for log in log_data:
        log["Nombre_Usuario"] = nombre_usuario
        log["IP"] = ip
        log["MAC"] = mac

    df_logs = pd.DataFrame(log_data)
    try:
        df_logs = df_logs[["Fecha_Hora", "Nombre_Usuario", "IP", "MAC", "Dispositivo", "Accion", "Ruta", "Malicioso", "Desconectado"]]
        df_logs.to_excel('logs_usb_monitor.xlsx', index=False)
        messagebox.showinfo("Éxito", "Logs guardados en logs_usb_monitor.xlsx")
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo exportar el archivo de Excel: {str(e)}")

# Creación de la interfaz gráfica
root = tk.Tk()
root.title("Monitor de Dispositivos USB")
root.geometry("1366x768")

# Texto de bienvenida
nombre_usuario, nombre_computador, ip, mac = obtener_info_computador()
bienvenida_texto = f"Bienvenido a la aplicación de Monitoreo USB\nUsuario: {nombre_usuario}\nComputador: {nombre_computador}\nIP: {ip}\nMAC: {mac}\n"
log_text = tk.Text(root, bg="black", fg="white", font=("Courier", 10), wrap=tk.WORD)
log_text.insert(tk.END, bienvenida_texto)

# Estilos para el área de logs
log_text.tag_configure("malicioso", foreground="red")
log_text.tag_configure("seguro", foreground="green")
log_text.tag_configure("advertencia", foreground="orange")

# Ajuste para que el log_text sea ajustable al tamaño de la ventana
log_text.pack(fill=tk.BOTH, expand=True)

# Frame para los botones
boton_frame = tk.Frame(root)
boton_frame.pack(pady=20)

# Botones
boton_iniciar = tk.Button(boton_frame, text="Iniciar Análisis", command=comenzar_analisis, bg="green", fg="white")
boton_iniciar.pack(side=tk.LEFT, padx=10, pady=10)

boton_detener = tk.Button(boton_frame, text="Detener Análisis", command=detener_analisis, bg="yellow", fg="black")
boton_detener.pack(side=tk.LEFT, padx=10, pady=10)

boton_eliminar = tk.Button(boton_frame, text="Eliminar Archivos No Deseados", command=eliminar_archivos_no_deseados, bg="red", fg="white")
boton_eliminar.pack(side=tk.LEFT, padx=10, pady=10)

boton_desconectar = tk.Button(boton_frame, text="Desconectar Dispositivos Maliciosos", command=desconectar_dispositivos_maliciosos, bg="orange", fg="black")
boton_desconectar.pack(side=tk.LEFT, padx=10, pady=10)

boton_logs = tk.Button(boton_frame, text="Mostrar Logs", command=mostrar_logs, bg="blue", fg="white")
boton_logs.pack(side=tk.LEFT, padx=10, pady=10)

boton_guardar_logs = tk.Button(boton_frame, text="Guardar Logs en Excel", command=guardar_logs_excel, bg="purple", fg="white")
boton_guardar_logs.pack(side=tk.LEFT, padx=10, pady=10)

boton_limpiar = tk.Button(boton_frame, text="Limpiar Pantalla", command=limpiar_pantalla, bg="gray", fg="white")
boton_limpiar.pack(side=tk.LEFT, padx=10, pady=10)

# Iniciar la interfaz
root.mainloop()
