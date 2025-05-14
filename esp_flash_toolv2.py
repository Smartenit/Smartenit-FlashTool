import os
import json
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog, scrolledtext
import serial.tools.list_ports
import threading
import serial
import re
import csv
import sys
import time

# Default flash parameters as specified
DEFAULT_FLASH_PARAMS = {
    "write_flash_args": ["--flash_mode", "dio",
                        "--flash_size", "10MB",
                        "--flash_freq", "80m"],
    "flash_settings": {
        "flash_mode": "dio",
        "flash_size": "10MB",
        "flash_freq": "80m"
    }
}


class ESPFlashTool:
    def __init__(self, root):
        self.root = root
        self.root.title("ESP Flash Tool")
        self.root.geometry("605x595")

        self.port_var = tk.StringVar()
        self.port_var.trace_add('write', self.update_disconnect_button_state)
        self.baudrate_var = tk.StringVar(value="460800")
        self.flash_args = {}
        self.flash_files = {}
        self.extra_esptool_args = {}
        self.write_flash_args = []
        self.json_data = None  # Initialize json_data
        self.csv_file_path = None  # Path to the CSV file selected by the user
        self.custom_files = []  # Stores tuples of (filepath, offset)
        self.monitoring = False
        self.serial_connection = None  
        self.serial_running = False 
        # Ask the user for the CSV file path at startup
        self.set_csv_file_path()

        self.create_widgets()
        self.refresh_ports()  # Refresh ports on startup


    def create_widgets(self):
        # Configuración general de la ventana
        self.root.title("ESP Flash Tool Version 2.6")
        self.root.geometry("565x645")

        #----------------------------------------------
        # Fila 1: Sección de puertos (ComboBox + Botones)
        #----------------------------------------------
        port_frame = ttk.Frame(self.root)
        port_frame.grid(row=1, column=0, columnspan=2, sticky='w', padx=10, pady=5)

        # Combobox de puertos
        ttk.Label(port_frame, text="Select Port").pack(side=tk.LEFT, padx=(0, 5))
        self.port_combobox = ttk.Combobox(
            port_frame, 
            textvariable=self.port_var, 
            width=25,
            state='readonly'
        )
        self.port_combobox.pack(side=tk.LEFT, padx=(0, 20))

        # Botones verticales (Disconnect y Refresh)
        port_buttons_frame = ttk.Frame(port_frame)
        port_buttons_frame.pack(side=tk.LEFT, anchor='n', padx=(80, 0))

        self.disconnect_button = ttk.Button(
            port_buttons_frame,
            text="Disconnect",
            command=self.close_serial_port,
            width=18,
            state='disabled'  # Estado inicial deshabilitado
        )
        self.disconnect_button.pack(pady=(5, 7))
        ttk.Button(
            port_buttons_frame,
            text="Refresh Ports",
            command=self.refresh_ports,
            width=18
        ).pack(pady=(0, 5))

        #----------------------------------------------
        # Fila 2: Baudrate
        #----------------------------------------------
        baudrate_frame = ttk.Frame(self.root)
        baudrate_frame.grid(row=2, column=0, sticky='w', padx=10, pady=(0, 5))
        
        ttk.Label(baudrate_frame, text="Baudrate:").pack(side=tk.LEFT, padx=(0, 5))
        self.baudrate_combobox = ttk.Combobox(
            baudrate_frame, 
            textvariable=self.baudrate_var, 
            values=["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"], 
            width=8,
            state="readonly"
        )
        self.baudrate_combobox.pack(side=tk.LEFT)
        self.baudrate_combobox.set("460800")

        #----------------------------------------------
        # Separador horizontal
        #----------------------------------------------
        separator = ttk.Separator(self.root, orient='horizontal')
        separator.grid(row=3, column=0, columnspan=3, sticky='ew', padx=10, pady=5)

        #----------------------------------------------
        # Fila 4: Sección de archivos (Label + Botones)
        #----------------------------------------------
        files_frame = ttk.Frame(self.root)
        files_frame.grid(row=4, column=0, columnspan=3, padx=10, pady=5, sticky='w')
        
        ttk.Label(files_frame, text="Selected Files:").pack(side=tk.LEFT, anchor='n', padx=(0, 15))
        
        self.file_listbox = tk.Listbox(
            files_frame, 
            height=5, 
            width=45,
            font=('Courier New', 8),
            bg='#f0f0f0',
            relief='flat'
        )
        self.file_listbox.pack(side=tk.LEFT, padx=(0, 15))

        file_buttons_frame = ttk.Frame(files_frame)
        file_buttons_frame.pack(side=tk.LEFT, anchor='n')
        
        ttk.Button(file_buttons_frame, text="Select Flash Args", width=18, 
                command=self.add_folder).pack(pady=2)
        ttk.Button(file_buttons_frame, text="Clear All", width=18, 
                command=self.clear_files).pack(pady=2)
        ttk.Button(file_buttons_frame, text="Change CSV Path", width=18, 
                command=self.set_csv_file_path).pack(pady=2)

        #----------------------------------------------
        # Fila 5: Botones principales (Ajuste clave)
        #----------------------------------------------
        # Modify the action frame layout
        action_frame = ttk.Frame(self.root)
        action_frame.grid(row=5, column=0, columnspan=3, padx=10, pady=10, sticky='ew')

        ttk.Button(action_frame, text="Flash Device", command=self.flash_device).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Reset Device", command=self.reset_device).pack(side=tk.LEFT, padx=5)  # New button
        self.monitor_button = ttk.Button(action_frame, text="Start Monitoring", command=self.toggle_monitoring)
        self.monitor_button.pack(side=tk.LEFT, padx=5)

        #----------------------------------------------
        # Fila 6: Monitor Output (Ajuste clave)
        #----------------------------------------------
        self.monitor_output = scrolledtext.ScrolledText(
            self.root, 
            wrap=tk.WORD, 
            height=12,
            font=('Consolas', 8)
        )
        self.monitor_output.grid(row=6, column=0, columnspan=3, padx=10, pady=(0, 5), sticky='nsew')  # Eliminado pady superior

        #----------------------------------------------
        # Fila 7: Botones inferiores
        #----------------------------------------------
        bottom_frame = ttk.Frame(self.root)
        bottom_frame.grid(row=7, column=0, columnspan=3, pady=(5, 10))  # Corregida numeración
        
        ttk.Button(bottom_frame, text="Clean Monitor", 
                command=self.clean_monitor).pack(side=tk.LEFT, padx=20)
        ttk.Button(bottom_frame, text="Reset App", 
                command=self.reset_app).pack(side=tk.LEFT, padx=20)

        # Configuración de expansión (Ajuste clave)
        self.root.grid_rowconfigure(6, weight=1)  # Solo la fila del monitor se expande
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_columnconfigure(2, weight=1)

    def update_disconnect_button_state(self, *args):
        if self.port_var.get().strip():
            self.disconnect_button['state'] = 'normal'
        else:
            self.disconnect_button['state'] = 'disabled'
            
    def clean_monitor(self):
        """Limpia completamente el widget de monitor"""
        self.monitor_output.config(state=tk.NORMAL)  # Asegurar que es editable
        self.monitor_output.delete('1.0', tk.END)
        #self.monitor_output.insert(tk.END, "Monitor cleaned - ready for new messages\n")
        self.monitor_output.see(tk.END)
        self.monitor_output.config(state=tk.NORMAL)  # Volver a dejar editable
        
    def reset_app(self):
        """Reinicia la aplicación inmediatamente sin confirmación"""
        try:
            # Cerrar puerto serial si está abierto
            if hasattr(self, 'serial_connection') and self.serial_connection:
                if self.serial_connection.is_open:
                    self.serial_connection.close()
                    self.monitor_output.insert(tk.END, "Serial port closed\n")
                self.monitoring = False
                self.monitor_button.config(text="Monitor Device")
            
            # Limpiar lista de archivos
            self.file_listbox.delete(0, tk.END)
            self.custom_files = []
            self.flash_files = {}
            
            # Resetear configuración
            self.port_var.set('')
            self.baudrate_var.set('460800')
            self.refresh_ports()
            
            # Limpiar monitor
            self.monitor_output.config(state=tk.NORMAL)
            self.monitor_output.delete('1.0', tk.END)
            self.monitor_output.see(tk.END)
            self.monitor_output.config(state=tk.NORMAL)
            
        except Exception as e:
            messagebox.showerror("Reset Error", str(e))

    def refresh_ports(self):
        """Refresh the list of available ports with detailed info."""
        self.port_map = {}  # Diccionario para mapear texto -> nombre real del puerto
        port_info = []
        
        for port in serial.tools.list_ports.comports():
            # Obtener información detallada
            device = port.device
            desc = port.description.split("(")[0].strip() if port.description else "Unknown"
            serial_num = port.serial_number if port.serial_number else ""
            
            # Formato compacto para el Combobox
            display_text = f"{device} - {desc}"
            if serial_num:
                display_text += f" ({serial_num})"
            
            port_info.append(display_text)
            self.port_map[display_text] = device  # Mapeo al nombre real

        self.port_combobox['values'] = port_info
        self.port_combobox.config(width=40)  # Aumentar ancho para mejor visualización
        
        # Solo mostrar advertencia si no hay puertos, no seleccionar automáticamente
        if not port_info:
            messagebox.showwarning("No Ports", "No serial ports detected")
                
    def set_csv_file_path(self):
        """Ask the user for the CSV file path."""
        # Ask the user if they want to select an existing file or create a new one
        response = messagebox.askyesno(
            "Select CSV File",
            "Do you want to select an existing CSV file? (Select 'No' to create a new one)."
        )

        if response:  # If the user wants to select an existing file
            file_path = filedialog.askopenfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                title="Select an existing CSV file"
            )
        else:  # If the user wants to create a new file
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                title="Create or select a CSV file"
            )

        if file_path:
            self.csv_file_path = file_path
            
        else:
            messagebox.showwarning("Warning", "No path selected. Data will not be saved automatically.")

    def update_file_listbox(self):
        """Update the listbox with current flash files and offsets in a formatted way."""
        self.file_listbox.delete(0, tk.END)
        
        if not hasattr(self, 'flash_files') or not self.flash_files:
            self.file_listbox.insert(tk.END, "No files selected - Use 'Add Files' or 'Add Folder' buttons")
            return
        
        # Add header
        # Add files sorted by offset
        for offset, path in sorted(self.flash_files.items()):
            filename = os.path.basename(path)
            dirname = os.path.dirname(path)
            display_text = f"{offset:<10} | {filename:<30}"
            self.file_listbox.insert(tk.END, display_text)
        
        # Add footer with summary
        #self.file_listbox.insert(tk.END, "-" * 80)
        flash_mode = next(
            (self.write_flash_args[i+1] for i, x in enumerate(self.write_flash_args) if x == "--flash_mode"),
            "dio"  # Valor por defecto
        )
        #self.file_listbox.insert(tk.END, f"Total: {len(self.flash_files)} files | Flash Mode: {flash_mode}")

    def ensure_flash_files_initialized(self):
        """Initialize flash parameters if they don't exist."""
        if not hasattr(self, 'flash_files'):
            self.flash_files = {}
        if not hasattr(self, 'write_flash_args'):
            self.write_flash_args = DEFAULT_FLASH_PARAMS["write_flash_args"].copy()  # Use copy to avoid modifying defaults
        if not hasattr(self, 'extra_esptool_args'):
            self.extra_esptool_args = {}

    def clear_files(self, silent=False, keep_geometry=True):
        """
        Clears all selected files and resets the flashing parameters.

        Args:
            silent (bool): If True, does not show the confirmation message.
            keep_geometry (bool): If True, keeps the current window geometry.
        """
        try:
            # Guardar geometría si se solicita
            if keep_geometry:
                current_geometry = self.root.geometry()
            
            # Resetear todos los atributos relacionados con el flasheo
            self.flash_files = {}
            self.flash_args = {}
            self.custom_files = []
            self.json_data = None
            
            # Restablecer parámetros a los valores por defecto
            self.write_flash_args = DEFAULT_FLASH_PARAMS["write_flash_args"].copy()
            self.extra_esptool_args = {}
            
            # Limpiar posibles errores previos
            if hasattr(self, 'last_error'):
                del self.last_error
            
            # Actualizar la interfaz
            self.update_file_listbox()
            
            # Restaurar geometría y foco si se solicitó
            if keep_geometry:
                self.root.geometry(current_geometry)
                self.root.focus_force()
            
        except Exception as e:
            # Handle errors during cleanup
            error_msg = f"Error during cleanup: {str(e)}"
            if not silent:
                messagebox.showerror("Error", error_msg)
            # Save the error for possible diagnostics
            self.last_error = error_msg  # Esta línea estaba mal indentada

    def add_folder(self):
        """Add files using a flasher_args.json file instead of folder selection."""
        file_path = filedialog.askopenfilename(
            title="Select flasher_args.json",
            initialdir=os.getcwd(),
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path and file_path.endswith('flasher_args.json'):
            self.ensure_flash_files_initialized()
            self.process_flasher_args(file_path)
        elif file_path:
            messagebox.showerror(
                "Invalid File",
                "Please select a valid flasher_args.json file"
            )


    def process_flasher_args(self, json_path):
        """Processes flasher_args.json files with a variable structure and robust path handling."""  

        try:
            # 1. Limpieza inicial
            self.clear_files(silent=True)
            config_dir = os.path.dirname(os.path.abspath(json_path))
            
            # 2. Carga y validación básica del JSON
            with open(json_path, 'r') as f:
                try:
                    config_data = json.load(f)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Inavlid JSON File: {str(e)}")
            
            if not isinstance(config_data, dict):
                raise ValueError("JSON File does not have valid parameters")

            # 3. Sistema de resolución de rutas mejorado
            def resolve_file_path(rel_path, config_dir):
                """Resolves file paths using multiple fallback strategies."""  

                if not rel_path or not isinstance(rel_path, str):
                    return None
                
                # Intentar rutas en este orden:
                search_paths = [
                    os.path.abspath(rel_path),  # Ruta absoluta directa
                    os.path.normpath(os.path.join(config_dir, rel_path)),  # Relativa al JSON
                    os.path.join(config_dir, os.path.basename(rel_path)),  # Solo el nombre en dir JSON
                    os.path.abspath(os.path.join('build', rel_path)),  # En directorio build
                    os.path.abspath(os.path.join('build', os.path.basename(rel_path)))  # Nombre en build
                ]
                
                for path in search_paths:
                    if os.path.exists(path):
                        return os.path.normpath(path)
                return None

            # 4. Procesamiento dinámico de flash_files
            processed_files = {}
            
            # Caso 1: Estructura con flash_files directo
            if 'flash_files' in config_data and isinstance(config_data['flash_files'], dict):
                for offset, rel_path in config_data['flash_files'].items():
                    if not isinstance(offset, str) or not offset.startswith('0x'):
                        continue
                    
                    abs_path = resolve_file_path(rel_path, config_dir)
                    if abs_path:
                        processed_files[offset] = abs_path
                    else:
                        self.show_path_warning(rel_path, config_dir, offset)

            # Caso 2: Estructura modular (bootloader, app, partition-table)
            for section in ['bootloader', 'app', 'partition-table', 'ota_data', 'nvs']:
                if section in config_data and isinstance(config_data[section], dict):
                    section_data = config_data[section]
                    offset = section_data.get('offset')
                    rel_path = section_data.get('file')
                    
                    if offset and rel_path and isinstance(offset, str) and offset.startswith('0x'):
                        abs_path = resolve_file_path(rel_path, config_dir)
                        if abs_path:
                            processed_files[offset] = abs_path
                        else:
                            self.show_path_warning(rel_path, config_dir, f"{section} ({offset})")

            # 5. Validación de archivos mínimos requeridos
            if not processed_files:
                raise ValueError("No valid files found for flashing")

            # 6. Actualización de estado de la aplicación
            self.flash_files = processed_files
            
            # 7. Manejo de parámetros de flasheo con valores por defecto
            self.write_flash_args = config_data.get(
                'write_flash_args',
                DEFAULT_FLASH_PARAMS["write_flash_args"].copy()
            )
            
            self.extra_esptool_args = config_data.get(
                'extra_esptool_args',
                {}
            )
            
            # 8. Actualización de interfaz
            self.update_file_listbox()
            
            # 9. Notificación al usuario
            loaded_files = len(self.flash_files)

        except Exception as e:
            messagebox.showerror(
                "Settings Error",
                f"File could not be processed:\n{str(e)}"
            )
            self.clear_files(silent=True)

    def show_path_warning(self, rel_path, config_dir, context):
        """Displays a detailed warning when a file is not found."""  

        search_locations = [
            os.path.normpath(os.path.join(config_dir, rel_path)),
            os.path.join(config_dir, os.path.basename(rel_path)),
            os.path.abspath(os.path.join('build', rel_path)),
            os.path.abspath(os.path.join('build', os.path.basename(rel_path)))
        ]
        
        locations_msg = "\n• ".join(search_locations)
        
        messagebox.showwarning(
            "File not found",
            f"File not found {context}:\n"
            f"Original Path: {rel_path}\n\n"
            f"Path used to searcg:\n• {locations_msg}"
        )
        
    def save_json_to_csv(self):
        """Save JSON data to a CSV file at the specified path."""
        if not hasattr(self, 'json_data') or not self.json_data:
            messagebox.showwarning("Warning", "No JSON data to save.")
            return

        if not self.csv_file_path:
            messagebox.showwarning("Warning", "No CSV file path selected.")
            return

        try:
            # Convert JSON to a format suitable for CSV
            if isinstance(self.json_data, dict):
                data_to_save = [self.json_data]
            elif isinstance(self.json_data, list):
                data_to_save = self.json_data
            else:
                raise ValueError("Unsupported JSON format")

            # Get the keys from the JSON to use as CSV headers
            headers = data_to_save[0].keys()

            # Read the existing CSV file (if it exists)
            existing_data = []
            if os.path.exists(self.csv_file_path):
                with open(self.csv_file_path, mode='r', newline='', encoding='utf-8') as csv_file:
                    reader = csv.DictReader(csv_file)
                    existing_data = list(reader)

            # Search for the hw_id in the existing data
            hw_id = self.json_data.get("hw_id")  # Assume the JSON has an "hw_id" field
            updated = False

            for row in existing_data:
                if row.get("hw_id") == hw_id:
                    # Update the existing row with the new data
                    row.update(self.json_data)
                    updated = True
                    break

            if not updated:
                # If the hw_id was not found, add a new row
                existing_data.append(self.json_data)

            # Write the updated data to the CSV file
            with open(self.csv_file_path, mode='w', newline='', encoding='utf-8') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=headers)
                writer.writeheader()
                writer.writerows(existing_data)

            print(f"Data saved successfully to {self.csv_file_path}")
            gui_msg = (f"Data saved successfully!\n\n"
                   f"File: {os.path.basename(self.csv_file_path)}\n"
                   f"Location: {os.path.dirname(self.csv_file_path)}")
            messagebox.showinfo("Success", gui_msg)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save CSV file: {e}")

    def get_selected_port(self):
        """Obtiene el nombre real del puerto seleccionado o None si es inválido."""
        selected_display = self.port_var.get()
        return self.port_map.get(selected_display, None)

    def flash_device(self):
        """Flash the device with the selected files."""
        port = self.get_selected_port()  # <- Esto es lo importante
        baudrate = self.baudrate_var.get()
        if not port or not baudrate:
            messagebox.showerror("Error", "Please select a port and baudrate.")
            return
        if not self.flash_files:
            messagebox.showerror("Error", "No files selected for flashing.")
            return

        # Obtener la ruta correcta de esptool.py
        if getattr(sys, 'frozen', False):
            # Si la aplicación está empaquetada con PyInstaller
            base_path = sys._MEIPASS
        else:
            # Si la aplicación se ejecuta desde el código fuente
            base_path = os.path.dirname(os.path.abspath(__file__))

        esptool_path = os.path.join(base_path, "esptool_py", "esptool", "esptool.py")

        # Construir el comando base
        cmd = [
            "python",
            esptool_path,
            "-p", port,
            "-b", baudrate,
            "--before", self.extra_esptool_args.get("before", "default_reset"),
            "--after", self.extra_esptool_args.get("after", "hard_reset"),
            "--chip", self.extra_esptool_args.get("chip", "esp32"),
            "write_flash"
        ]

        # Agregar los argumentos de write_flash
        if not self.write_flash_args:
            flash_mode = simpledialog.askstring("Input", "Enter flash mode (e.g., dio):", initialvalue="dio")
            flash_freq = simpledialog.askstring("Input", "Enter flash frequency (e.g., 80m):", initialvalue="80m")
            flash_size = simpledialog.askstring("Input", "Enter flash size (e.g., 2MB):", initialvalue="2MB")
            if flash_mode and flash_freq and flash_size:
                self.write_flash_args = ["--flash_mode", flash_mode, "--flash_freq", flash_freq, "--flash_size", flash_size]
            else:
                messagebox.showerror("Error", "You must enter valid values for flash parameters.")
                return
        cmd.extend(self.write_flash_args)

        # Agregar los archivos de flash con sus offsets
        for offset, file in self.flash_files.items():
            print(f"File to flash: {file} at offset {offset}")
            cmd.extend([offset, file])


        try:
            self.monitor_output.insert(tk.END, "Starting flash process...\n")
            self.monitor_output.insert(tk.END, "Command: " + " ".join(cmd) + "\n\n")
            self.monitor_output.see(tk.END)
            
            # Configurar parámetros para ocultar la ventana en Windows
            startupinfo = None
            if sys.platform.startswith('win'):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            # Ejecutar el comando
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                startupinfo=startupinfo,  # <-- Añadir este parámetro
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0  # <-- Para Windows
            )
            
            # Leer la salida línea por línea
            for line in process.stdout:
                self.monitor_output.insert(tk.END, line)
                self.monitor_output.see(tk.END)
                self.monitor_output.update_idletasks()  # Actualizar la interfaz
            
            # Esperar a que termine el proceso
            return_code = process.wait()
            
            if return_code == 0:
                self.monitor_output.insert(tk.END, "\nDevice flashed successfully!\n")

            else:
                self.monitor_output.insert(tk.END, f"\nFlash process failed with return code {return_code}\n")
                messagebox.showerror("Error", f"Failed to flash device. Return code: {return_code}")
                
            self.monitor_output.see(tk.END)
            
        except Exception as e:
            self.monitor_output.insert(tk.END, f"\nError during flash process: {str(e)}\n")
            self.monitor_output.see(tk.END)
            messagebox.showerror("Error", f"Failed to flash device: {e}")

    def close_serial_port(self):
        """Cierra todas las conexiones seriales y restablece los puertos."""
        try:
            # Detener el monitoreo si está activo
            if hasattr(self, 'monitoring') and self.monitoring:
                self.monitoring = False
                self.monitor_button.config(text="Monitor Device")
                
            # Cerrar conexión serial
            if hasattr(self, 'serial_connection') and self.serial_connection:
                if self.serial_connection.is_open:
                    self.serial_connection.close()
                self.serial_connection = None
                selected = self.port_var.get()

            # Actualizar interfaz
            self.monitor_output.config(state=tk.NORMAL)
            self.monitor_output.insert(tk.END, "\nPorts reset - All connections closed\n")
            self.monitor_output.see(tk.END)
            self.monitor_output.config(state=tk.DISABLED)
            
            # Actualizar lista de puertos y limpiar selección
            self.refresh_ports()
            self.port_var.set('')  # <----- NUEVA LÍNEA AQUÍ
            
        except Exception as e:
            messagebox.showerror("Reset Error", f"Error resetting ports: {str(e)}")
            
    def reset_device(self):
        """Realiza soft reset usando control DTR/RTS y reinicia monitorización"""
        try:
            # 1. Detener monitorización actual si está activa
            if hasattr(self, 'ser') and self.ser.is_open:
                self.ser.close()
                time.sleep(1)  # Esperar cierre completo

            # 2. Obtener puerto seleccionado
            port = self.get_selected_port()
            if not port:
                messagebox.showerror("Error", "Selecciona un puerto")
                return

            # 3. Secuencia de reset (DTR/RTS)
            with serial.Serial(port=port, baudrate=115200) as ser:
                ser.dtr = False
                ser.rts = True
                time.sleep(0.1)
                ser.dtr = True
                ser.rts = False

            # 4. Reiniciar monitorización automáticamente
            self.monitor_device()  # Llama a tu función existente

            # 5. Feedback en consola
            self.monitor_output.insert(tk.END, "\nReset exitoso! Monitorización reiniciada\n")
            self.monitor_output.see(tk.END)

        except Exception as e:
            messagebox.showerror("Error", f"Error en reset: {str(e)}")

    def toggle_monitoring(self):
        """Update button control"""
        if self.monitor_button.cget('text') == 'Start Monitoring':
            self.monitor_device()
            self.monitor_button.config(text="Stop Monitoring")
        else:
            self.stop_monitoring()
            self.monitor_button.config(text="Start Monitoring")
    

    def monitor_device(self):
        """Start monitoring the device."""
        # Detener cualquier instancia previa de manera segura
        if hasattr(self, 'serial_thread') and self.serial_thread.is_alive():
            self.stop_serial = True  # Nueva bandera de control
            self.serial_thread.join()

        if hasattr(self, 'ser') and self.ser.is_open:
            self.ser.close()

        port = self.get_selected_port()  
        if not port:
            messagebox.showerror("Error", "Please select a port.")
            return

        baudrate = 115200  # Default baudrate

        try:
            # Configuración serial con control de flujo
            self.ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=1,
                rtscts=True  # Habilita control de flujo hardware
            )
            self.ser.reset_input_buffer()
            
            self.stop_serial = False  # Reiniciar bandera

            def read_serial():
                """Hilo de lectura con manejo seguro de cierre"""
                while not self.stop_serial and self.ser.is_open:
                    try:
                        data = self.ser.readline().decode("utf-8", errors="ignore").strip()
                        if data:
                            # Actualizar GUI de manera segura
                            self.monitor_output.insert(tk.END, data + "\n")
                            self.monitor_output.see(tk.END)

                            # Procesar datos de manufactura
                            if '{"type":"mfg"' in data:
                                match = re.search(r'(\{.*?"type":"mfg".*?\})', data)
                                if match:
                                    try:
                                        self.json_data = json.loads(match.group(1))
                                        self.save_json_to_csv()
                                    except json.JSONDecodeError:
                                        print("Failed to decode JSON")
                                        
                    except (serial.SerialException, OSError, TypeError, AttributeError) as e:
                        print(f"Serial read error: {e}")
                        break

            # Iniciar hilo con verificación de estado
            self.serial_thread = threading.Thread(target=read_serial, daemon=True)
            self.serial_thread.start()

        except serial.SerialException as e:
            messagebox.showerror("Error", f"Failed to open port {port}: {e}")
            self.stop_serial = True


    def stop_monitoring(self):
        """Safe shutdown procedure"""
        self.stop_serial = True
        if hasattr(self, 'serial_thread') and self.serial_thread.is_alive():
            self.serial_thread.join()
        if hasattr(self, 'ser') and self.ser.is_open:
            self.ser.close()


    def __del__(self):
        """Close the serial port when the instance is destroyed."""
        if hasattr(self, "ser") and self.ser.is_open:
            self.ser.close()



if __name__ == "__main__":
    root = tk.Tk()
    app = ESPFlashTool(root)
    root.mainloop()