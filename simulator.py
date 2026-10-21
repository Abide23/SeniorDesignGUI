import tkinter as tk
from tkinter import ttk, messagebox
import serial
import json
import sys

class SerialSimulator:
    def __init__(self, root):
        self.root = root
        self.root.title("Serial Data Simulator")
        self.root.geometry("400x300")

        self.serial_port = None
        self.running = False

        self.setup_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Port Selection
        ttk.Label(main_frame, text="Serial Port:").grid(row=0, column=0, sticky="w", pady=5)
        self.port_entry = ttk.Entry(main_frame)
        self.port_entry.insert(0, "/dev/pts/2") # Default to common socat port
        self.port_entry.grid(row=0, column=1, sticky="ew", pady=5)

        # Connect/Disconnect
        self.connect_btn = ttk.Button(main_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.grid(row=1, column=0, columnspan=2, pady=10, sticky="ew")

        # Data Input
        ttk.Label(main_frame, text="Send JSON Data:").grid(row=2, column=0, sticky="w", pady=5)
        self.data_entry = ttk.Entry(main_frame)
        self.data_entry.grid(row=3, column=0, columnspan=2, sticky="ew", pady=5)
        self.data_entry.insert(0, '{"Temperature": 25.0}')
        
        # Hint/Template
        hint_text = "Example: {\"Temperature\": 35.0}\nor multiple:\n{\"Voltage\": 10.0, \"Battery\": 5}"
        ttk.Label(main_frame, text=hint_text, font=("Courier", 8), foreground="gray").grid(row=4, column=0, columnspan=2, sticky="w", pady=5)

        # Send Button
        self.send_btn = ttk.Button(main_frame, text="Send", command=self.send_data, state=tk.DISABLED)
        self.send_btn.grid(row=5, column=0, columnspan=2, pady=10, sticky="ew")

        # Status
        self.status_label = ttk.Label(main_frame, text="Disconnected", foreground="red")
        self.status_label.grid(row=6, column=0, columnspan=2, pady=5)

        main_frame.columnconfigure(1, weight=1)

    def toggle_connection(self):
        if not self.running:
            port = self.port_entry.get()
            try:
                self.serial_port = serial.Serial(port, 9600, timeout=1)
                self.running = True
                self.connect_btn.config(text="Disconnect")
                self.send_btn.config(state=tk.NORMAL)
                self.status_label.config(text=f"Connected to {port}", foreground="green")
            except Exception as e:
                messagebox.showerror("Connection Error", str(e))
        else:
            self.running = False
            if self.serial_port:
                self.serial_port.close()
            self.connect_btn.config(text="Connect")
            self.send_btn.config(state=tk.DISABLED)
            self.status_label.config(text="Disconnected", foreground="red")

    def send_data(self):
        if not self.running or not self.serial_port:
            return
        
        raw_data = self.data_entry.get().strip()
        
        # Validate JSON before sending
        try:
            json.loads(raw_data)
        except json.JSONDecodeError:
            messagebox.showerror("Invalid JSON", "The data entered is not valid JSON.")
            return

        try:
            self.serial_port.write((raw_data + "\n").encode('utf-8'))
        except Exception as e:
            messagebox.showerror("Send Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = SerialSimulator(root)
    root.mainloop()
