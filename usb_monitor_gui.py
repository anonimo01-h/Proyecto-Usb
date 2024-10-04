import os
import time
import logging
import psutil
import platform
import getpass
import threading
from datetime import datetime
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler
import tkinter as tk
from tkinter import scrolledtext, messagebox
from tkinter import filedialog

# Configuración de logging
logging.basicConfig(filename='usb_monitor.log', level=logging.INFO,
                    format='%(asctime)s - %(message)s')

class USBMonitorHandler(FileSystemEventHandler):
    def __init__(self, drive_letter, volume_label, output_widget):
        self.drive_letter = drive_letter
        self.volume_label = volume_label
        self.output_widget = output_widget
        self.unwanted_files = []
        self.safe_device_message_shown = False
        self.unwanted_file_message_shown = False
        super().__init__()

    def on_modified(self, event):
        self.process_event(event)

    def on_created(self, event):
        self.process_event(event)

    def on_deleted(self, event):
        message = f'Evento: Eliminado - Ruta: {event.src_path} - Dispositivo: {self.volume_label}'
        logging.info(message)
        self.output_widget.insert(tk.END, message + "\n")
        self.output_widget.see(tk.END)

    def on_moved(self, event):
        message = f'Evento: Movido/Renombrado - De: {event.src_path} A: {event.dest_path} - Dispositivo: {self.volume_label}'
        logging.info(message)
        self.output_widget.insert(tk.END, message + "\n")
        self.output_widget.see(tk.END)

    def process_event(self, event):
        message = f'Evento: Detectado - Ruta: {event.src_path} - Dispositivo: {self.volume_label}'
        logging.info(message)
        self.output_widget.insert(tk.END, message + "\n")
        self.output_widget.see(tk.END)
        self.detect_unwanted_files(event.src_path)

    def detect_unwanted_files(self, file_path):
        unwanted_extensions = ['.exe', '.bat', '.js']
        if any(file_path.endswith(ext) for ext in unwanted_extensions):
            if file_path not in self.unwanted_files:
                self.unwanted_files.append(file_path)

def scan_entire_drive(drive_letter, handler):
    for root, dirs, files in os.walk(drive_letter):
        for file in files:
            file_path = os.path.join(root, file)
            handler.detect_unwanted_files(file_path)

def get_volume_label(drive_letter):
    """Obtener la etiqueta del volumen usando win32api"""
    try:
        import win32api
        return win32api.GetVolumeInformation(drive_letter)[0]
    except Exception as e:
        logging.error(f'Error al obtener la etiqueta del volumen: {e}')
        return "Desconocido"

def get_system_info():
    """Obtener información detallada del sistema"""
    try:
        system_info = {
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "usuario": getpass.getuser(),
            "nombre_del_pc": platform.node(),
            "sistema_operativo": platform.system(),
            "version_os": platform.version(),
            "arquitectura": platform.architecture()[0],
            "nombre_sesion": os.getlogin()
        }
        return system_info
    except Exception as e:
        logging.error(f'Error al obtener la información del sistema: {e}')
        return {}

def start_monitoring(path, volume_label, monitored_drives_status, output_widget, stop_event):
    message = f'Iniciando monitoreo en: {path} - Nombre del USB: {volume_label} - Fecha y Hora: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
    logging.info(message)
    output_widget.insert(tk.END, message + "\n")
    output_widget.see(tk.END)

    event_handler = USBMonitorHandler(path, volume_label, output_widget)
    observer = PollingObserver()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()

    try:
        while not stop_event.is_set():
            scan_entire_drive(path, event_handler)

            if event_handler.unwanted_files:
                if not event_handler.unwanted_file_message_shown:
                    output_widget.insert(tk.END, f'\n')
                    output_widget.tag_config("unwanted", foreground="red")
                    output_widget.insert(tk.END, f'Archivos no deseados detectados en el dispositivo {volume_label}:\n', "unwanted")
                    for uf in event_handler.unwanted_files:
                        output_widget.insert(tk.END, f'{uf}\n', "unwanted")
                    output_widget.insert(tk.END, f"Por favor, no utilice este dispositivo {volume_label}.\n", "unwanted")
                    monitored_drives_status[volume_label] = False
                    event_handler.unwanted_file_message_shown = True
                event_handler.safe_device_message_shown = False
            else:
                if not event_handler.safe_device_message_shown:
                    output_widget.insert(tk.END, f'\n')
                    output_widget.tag_config("safe", foreground="green")
                    output_widget.insert(tk.END, f'El dispositivo {volume_label} es seguro para usar.\n', "safe")
                    monitored_drives_status[volume_label] = True
                    event_handler.safe_device_message_shown = True

            time.sleep(30)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def detect_usb_windows(output_widget, stop_event):
    monitored_drives = set()
    monitored_drives_status = {}
    last_usb_state = False

    while not stop_event.is_set():
        try:
            drives = psutil.disk_partitions()
            usb_connected = any('removable' in drive.opts for drive in drives)
            current_drives = {drive.device: get_volume_label(drive.device) for drive in drives if 'removable' in drive.opts}

            # Detectar dispositivos desconectados
            if not usb_connected and last_usb_state:
                for drive in monitored_drives:
                    if drive not in current_drives:
                        logging.info(f'Dispositivo USB desconectado: {drive}')
                        output_widget.insert(tk.END, f'Dispositivo USB desconectado: {drive}\n')
                monitored_drives.clear()  # Limpiar la lista de dispositivos monitoreados
                output_widget.insert(tk.END, "\n")
                output_widget.tag_config("no_device", foreground="purple")
                output_widget.insert(tk.END, "Ningún dispositivo detectado, esperando dispositivos...\n", "no_device")

            # Detectar dispositivos conectados
            if usb_connected:
                for drive in current_drives:
                    if drive not in monitored_drives:
                        monitored_drives.add(drive)
                        drive_label = current_drives[drive]
                        logging.info(f'Dispositivo USB conectado: {drive_label} - {drive}')
                        output_widget.insert(tk.END, f'Dispositivo USB detectado: {drive_label} - {drive} - Fecha y Hora: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
                        threading.Thread(target=start_monitoring, args=(drive, drive_label, monitored_drives_status, output_widget, stop_event)).start()

            last_usb_state = usb_connected
            
            time.sleep(1)
        except Exception as e:
            logging.error(f'Error al detectar USB: {e}')

def stop_analysis(stop_event, output_widget):
    stop_event.set()
    output_widget.insert(tk.END, "\nAnálisis detenido.\n")

def show_logs():
    try:
        with open('usb_monitor.log', 'r') as log_file:
            logs = log_file.read()
            log_window = tk.Toplevel()
            log_window.title("Logs del Monitoreo de USB")
            log_text = scrolledtext.ScrolledText(log_window, wrap=tk.WORD, bg="black", fg="white", font=("Arial", 12))
            log_text.pack(expand=True, fill='both')
            log_text.insert(tk.END, logs)
            log_text.config(state=tk.DISABLED)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo abrir el archivo de log: {e}")

def print_logs():
    try:
        with open('usb_monitor.log', 'r') as log_file:
            logs = log_file.read()
        save_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if save_path:
            with open(save_path, 'w') as f:
                f.write(logs)
            messagebox.showinfo("Éxito", "Logs impresos y guardados correctamente.")
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo imprimir los logs: {e}")

def clear_output(output_widget):
    """Limpiar la salida y mostrar el mensaje de bienvenida"""
    output_widget.delete(1.0, tk.END)
    
    # Mostrar mensaje de bienvenida y detalles del sistema
    system_info = get_system_info()
    output_widget.insert(tk.END, f"Bienvenido al sistema de monitoreo USB.\n")
    output_widget.insert(tk.END, f"Fecha y Hora: {system_info['fecha']}\n")
    output_widget.insert(tk.END, f"Usuario: {system_info['usuario']}\n")
    output_widget.insert(tk.END, f"Nombre del PC: {system_info['nombre_del_pc']}\n")
    output_widget.insert(tk.END, f"Sistema Operativo: {system_info['sistema_operativo']}\n")
    output_widget.insert(tk.END, f"Versión: {system_info['version_os']}\n")
    output_widget.insert(tk.END, f"Arquitectura: {system_info['arquitectura']}\n")
    output_widget.insert(tk.END, "\n")
    output_widget.tag_config("welcome", foreground="green")
    output_widget.insert(tk.END, "Ningún dispositivo detectado, esperando dispositivos...\n", "welcome")
    output_widget.see(tk.END)

def create_gui():
    window = tk.Tk()
    window.title("Monitoreo de USB")
    window.geometry("800x600")
    window.configure(bg="gray20")

    stop_event = threading.Event()

    # Área de texto para mostrar información
    output_widget = scrolledtext.ScrolledText(window, wrap=tk.WORD, bg="black", fg="white", font=("Arial", 12))
    output_widget.pack(padx=10, pady=10, expand=True, fill='both')

    # Mostrar mensaje inicial de bienvenida
    clear_output(output_widget)

    # Frame de botones
    button_frame = tk.Frame(window, bg="gray20")
    button_frame.pack(fill=tk.X, padx=10, pady=10)

    # Botón para iniciar el análisis
    analyze_button = tk.Button(button_frame, text="Analizar", font=("Arial", 12), bg="green", fg="white",
                               command=lambda: threading.Thread(target=detect_usb_windows, args=(output_widget, stop_event)).start())
    analyze_button.pack(side=tk.LEFT, padx=10, pady=10)

    # Botón para detener el análisis
    stop_button = tk.Button(button_frame, text="Detener", font=("Arial", 12), bg="red", fg="white",
                            command=lambda: stop_analysis(stop_event, output_widget))
    stop_button.pack(side=tk.LEFT, padx=10, pady=10)

    # Botón para mostrar logs
    log_button = tk.Button(button_frame, text="Mostrar Log", font=("Arial", 12), bg="blue", fg="white", command=show_logs)
    log_button.pack(side=tk.LEFT, padx=10, pady=10)

    # Botón para imprimir logs
    print_button = tk.Button(button_frame, text="Imprimir Log", font=("Arial", 12), bg="purple", fg="white", command=print_logs)
    print_button.pack(side=tk.LEFT, padx=10, pady=10)

    # Botón para limpiar pantalla
    clear_button = tk.Button(button_frame, text="Limpiar Pantalla", font=("Arial", 12), bg="orange", fg="white",
                             command=lambda: clear_output(output_widget))
    clear_button.pack(side=tk.LEFT, padx=10, pady=10)

    # Botón para cerrar el programa
    close_button = tk.Button(button_frame, text="Cerrar Programa", font=("Arial", 12), bg="gray", fg="white",
                             command=window.quit)
    close_button.pack(side=tk.LEFT, padx=10, pady=10)

    window.mainloop()

if __name__ == "__main__":
    create_gui()