import tkinter as tk
from tkinter import ttk, messagebox
import serial
import threading
import json
import time
import csv
from datetime import datetime

class SeniorDesignGUI:
    # --- HiDPI SETTINGS ---
    SCALE_FACTOR = 1.5 

    def __init__(self, root):
        self.root = root
        self.root.title("Senior Design Dashboard")
        
        width = int(900 * self.SCALE_FACTOR)
        height = int(700 * self.SCALE_FACTOR)
        self.root.geometry(f"{width}x{height}")
        self.root.tk.call('tk', 'scaling', self.SCALE_FACTOR)

        # Serial settings
        self.serial_port = None
        self.serial_thread = None
        self.running = False

        # --- LOGGING STATE ---
        self.is_recording = False
        self.log_file = None
        self.log_writer = None

        # Data for the informational frames
        # MODULAR: Adding a key here automatically adds a column to the Excel export and a box to the UI
        self.frame_info = {
            "Inlet temp": {"value": None, "range": (20, 30), "unit": "°C"},
                        "Humidity": {"value": None, "range": (20, 100), "unit": "%"},
                           "PM 1.0": {"value": None, "range": (0, 100), "unit": "ug/m^3"},         
"Measured Velocity": {"value": None, "range": (0, 10), "unit": "m/s"},
            "Outlet temp 1": {"value": None, "range": (30, 60), "unit": "°C"},
            "Outlet temp 2": {"value": None, "range": (1000, 1020), "unit": "°C"},
            "Room pressure": {"value": None, "range": (11.5, 12.5), "unit": "Pa"},
            "Inlet air velocity": {"value": None, "range": (1.0, 2.0), "unit": "ft/s"},
            "Outlet air velocity 1": {"value": None, "range": (100, 500), "unit": "ft/s"},
            "Outlet air velocity 2": {"value": None, "range": (350, 450), "unit": "ft/s"}
             # NEW BOX
        }
        
        self.log_headers = ["Date", "Time"] + list(self.frame_info.keys())

        self.ui_elements = {}
        self.setup_ui()

    def s_int(self, value):
        return int(value * self.SCALE_FACTOR)

    def s_font(self, size):
        return int(size * self.SCALE_FACTOR)

    def setup_ui(self):
        control_bar = ttk.Frame(self.root, padding=self.s_int(5))
        control_bar.pack(fill=tk.X)

        ttk.Label(control_bar, text="Serial Port:").pack(side=tk.LEFT, padx=self.s_int(5))
        self.port_entry = ttk.Entry(control_bar, width=self.s_int(15))
        self.port_entry.insert(0, "/dev/ttyUSB0")
        self.port_entry.pack(side=tk.LEFT, padx=self.s_int(5))

        self.connect_btn = ttk.Button(control_bar, text="Connect", command=self.toggle_connection)
        self.connect_btn.pack(side=tk.LEFT, padx=self.s_int(5))

        self.record_btn = ttk.Button(control_bar, text="Start Recording", command=self.toggle_recording, state="disabled")
        self.record_btn.pack(side=tk.LEFT, padx=self.s_int(5))

        self.status_label = ttk.Label(control_bar, text="Disconnected", foreground="red")
        self.status_label.pack(side=tk.LEFT, padx=self.s_int(10))

        self.main_container = ttk.Frame(self.root, padding=self.s_int(20))
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # Grid Layout: 3 columns
        for i in range(3):
            self.main_container.columnconfigure(i, weight=1)
        # We have 10 items now, so we need 4 rows
        for i in range(4):
            self.main_container.rowconfigure(i, weight=1)

        for index, (title, info) in enumerate(self.frame_info.items()):
            row = index // 3
            col = index % 3
            bg_color = "#eeeeee"
            display_text = "--"

            frame = tk.Frame(
                self.main_container, 
                bg=bg_color, 
                highlightbackground="black", 
                highlightthickness=1,
                padx=self.s_int(15), 
                pady=self.s_int(15)
            )
            frame.grid(row=row, column=col, sticky="nsew", padx=self.s_int(10), pady=self.s_int(10))

            title_label = tk.Label(frame, text=title, font=("Helvetica", self.s_font(12), "bold"), bg=bg_color)
            title_label.pack(anchor="w")

            value_label = tk.Label(frame, text=display_text, font=("Helvetica", self.s_font(20)), bg=bg_color)
            value_label.pack(anchor="center", pady=(self.s_int(10), 0))

            self.ui_elements[title] = {
                "frame": frame,
                "value_label": value_label,
                "title_label": title_label
            }

    def toggle_connection(self):
        if not self.running:
            port = self.port_entry.get()
            try:
                self.serial_port = serial.Serial(port, 115200, timeout=1)
                self.running = True
                self.connect_btn.config(text="Disconnect")
                self.status_label.config(text=f"Connected to {port}", foreground="green")
                self.record_btn.config(state="normal") 
                
                self.serial_thread = threading.Thread(target=self.read_serial, daemon=True)
                self.serial_thread.start()
            except Exception as e:
                messagebox.showerror("Connection Error", str(e))
        else:
            self.stop_connection()

    def stop_connection(self):
        self.running = False
        if self.is_recording:
            self.toggle_recording()
        if self.serial_port:
            self.serial_port.close()
        self.connect_btn.config(text="Connect")
        self.status_label.config(text="Disconnected", foreground="red")
        self.record_btn.config(state="disabled")

    def toggle_recording(self):
        if not self.is_recording:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sensor_data_{timestamp_str}.csv"
            try:
                self.log_file = open(filename, mode='w', newline='')
                self.log_writer = csv.DictWriter(self.log_file, fieldnames=self.log_headers)
                self.log_writer.writeheader()
                self.is_recording = True
                self.record_btn.config(text="Stop Recording")
                self.status_label.config(text=f"Recording: {filename}", foreground="blue")
            except Exception as e:
                messagebox.showerror("Logging Error", f"Could not create file: {e}")
        else:
            self.is_recording = False
            if self.log_file:
                self.log_file.close()
                self.log_file = None
                self.log_writer = None
            self.record_btn.config(text="Start Recording")
            self.status_label.config(text="Stopped Recording", foreground="green")

    def read_serial(self):
        while self.running:
            if self.serial_port and self.serial_port.in_waiting > 0:
                try:
                    line = self.serial_port.readline().decode('utf-8').strip()
                    if line:
                        data = json.loads(line)
                        self.root.after(0, self.update_ui_from_data, data)
                except json.JSONDecodeError:
                    pass 
                except Exception as e:
                    print(f"Error reading serial: {e}")
            time.sleep(0.01)

    def update_ui_from_data(self, data):
        for key, new_val in data.items():
            if key in self.frame_info and key in self.ui_elements:
                info = self.frame_info[key]
                ui = self.ui_elements[key]
                info["value"] = new_val
                ui["value_label"].config(text=f"{new_val} {info['unit']}")
                in_range = info["range"][0] <= new_val <= info["range"][1]
                bg_color = "#caffbf" if in_range else "#ffadad"
                ui["frame"].config(bg=bg_color)
                ui["title_label"].config(bg=bg_color)
                ui["value_label"].config(bg=bg_color)

        if self.is_recording and self.log_writer:
            try:
                now = datetime.now()
                row = {
                    "Date": now.strftime("%Y-%m-%d"),
                    "Time": now.strftime("%H:%M:%S")
                }
                for key in self.frame_info.keys():
                    row[key] = data.get(key, "") 
                self.log_writer.writerow(row)
                self.log_file.flush() 
            except Exception as e:
                print(f"Logging error: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = SeniorDesignGUI(root)
    root.mainloop()
