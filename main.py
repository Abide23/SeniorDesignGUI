import tkinter as tk
from tkinter import ttk, messagebox
import serial
import threading
import json
import time

class SeniorDesignGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Senior Design Dashboard")
        self.root.geometry("800x600")

        # Serial settings
        self.serial_port = None
        self.serial_thread = None
        self.running = False

        # Data for the eight informational frames
        # Keys must match the JSON sent via serial
        # value is set to None initially to indicate "no data received yet"
        self.frame_info = {
            "Inlet temp": {"value": None, "range": (20, 30), "unit": "°C"},
            "Outlet temp 1": {"value": None, "range": (30, 60), "unit": "°C"},
            "Outlet temp 2": {"value": None, "range": (1000, 1020), "unit": "°C"},
            "Room pressure": {"value": None, "range": (11.5, 12.5), "unit": "Pa"},
            "Inlet air velocity": {"value": None, "range": (1.0, 2.0), "unit": "ft/s"},
            "Outlet air velocity 1": {"value": None, "range": (100, 500), "unit": "ft/s"},
            "Outlet air velocity 2": {"value": None, "range": (350, 450), "unit": "ft/s"},
            "Humidity": {"value": None, "range": (20, 100), "unit": "%"},
        }

        # References to UI elements
        self.ui_elements = {}

        self.setup_ui()

    def setup_ui(self):
        # Top control bar
        control_bar = ttk.Frame(self.root, padding="5")
        control_bar.pack(fill=tk.X)

        ttk.Label(control_bar, text="Serial Port:").pack(side=tk.LEFT, padx=5)
        self.port_entry = ttk.Entry(control_bar, width=15)
        self.port_entry.insert(0, "/dev/ttyUSB0")
        self.port_entry.pack(side=tk.LEFT, padx=5)

        self.connect_btn = ttk.Button(control_bar, text="Connect", command=self.toggle_connection)
        self.connect_btn.pack(side=tk.LEFT, padx=5)

        self.status_label = ttk.Label(control_bar, text="Disconnected", foreground="red")
        self.status_label.pack(side=tk.LEFT, padx=10)

        # Main container with padding
        self.main_container = ttk.Frame(self.root, padding="20")
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # Configure grid weights
        for i in range(2):
            self.main_container.columnconfigure(i, weight=1)
        for i in range(4):
            self.main_container.rowconfigure(i, weight=1)

        # Create the frames
        for index, (title, info) in enumerate(self.frame_info.items()):
            row = index // 2
            col = index % 2

            # Initial state: if value is None, use neutral color and "--" text
            if info["value"] is None:
                bg_color = "#eeeeee"  # Light neutral gray
                display_text = "--"
            else:
                in_range = info["range"][0] <= info["value"] <= info["range"][1]
                bg_color = "#caffbf" if in_range else "#ffadad"
                display_text = f"{info['value']} {info['unit']}"

            frame = tk.Frame(
                self.main_container, 
                bg=bg_color, 
                highlightbackground="black", 
                highlightthickness=1,
                padx=15, 
                pady=15
            )
            frame.grid(row=row, column=col, sticky="nsew", padx=10, pady=10)

            # Title Label
            title_label = tk.Label(
                frame, 
                text=title, 
                font=("Helvetica", 14, "bold"), 
                bg=bg_color
            )
            title_label.pack(anchor="w")

            # Value Label
            value_label = tk.Label(
                frame, 
                text=display_text, 
                font=("Helvetica", 24), 
                bg=bg_color
            )
            value_label.pack(anchor="center", pady=(10, 0))

            # Store references for updating
            self.ui_elements[title] = {
                "frame": frame,
                "value_label": value_label,
                "title_label": title_label
            }

    def toggle_connection(self):
        if not self.running:
            port = self.port_entry.get()
            try:
                self.serial_port = serial.Serial(port, 9600, timeout=1)
                self.running = True
                self.connect_btn.config(text="Disconnect")
                self.status_label.config(text=f"Connected to {port}", foreground="green")
                
                self.serial_thread = threading.Thread(target=self.read_serial, daemon=True)
                self.serial_thread.start()
            except Exception as e:
                messagebox.showerror("Connection Error", str(e))
        else:
            self.running = False
            if self.serial_port:
                self.serial_port.close()
            self.connect_btn.config(text="Connect")
            self.status_label.config(text="Disconnected", foreground="red")

    def read_serial(self):
        while self.running:
            if self.serial_port and self.serial_port.in_waiting > 0:
                try:
                    line = self.serial_port.readline().decode('utf-8').strip()
                    if line:
                        data = json.loads(line)
                        self.root.after(0, self.update_ui_from_data, data)
                except json.JSONDecodeError:
                    pass # Ignore malformed JSON
                except Exception as e:
                    print(f"Error reading serial: {e}")
            time.sleep(0.01)

    def update_ui_from_data(self, data):
        # data is expected to be a dict like {"Temperature": 25.5, "Humidity": 50}
        for key, new_val in data.items():
            if key in self.frame_info and key in self.ui_elements:
                info = self.frame_info[key]
                ui = self.ui_elements[key]

                # Update value
                info["value"] = new_val
                ui["value_label"].config(text=f"{new_val} {info['unit']}")

                # Update color based on new range check
                in_range = info["range"][0] <= new_val <= info["range"][1]
                bg_color = "#caffbf" if in_range else "#ffadad"
                
                ui["frame"].config(bg=bg_color)
                ui["title_label"].config(bg=bg_color)
                ui["value_label"].config(bg=bg_color)

if __name__ == "__main__":
    root = tk.Tk()
    app = SeniorDesignGUI(root)
    root.mainloop()
