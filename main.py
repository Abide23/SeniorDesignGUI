import tkinter as tk
from tkinter import ttk, messagebox
from collections import deque
import socket
import threading
import json
import time
import csv
from datetime import datetime


class SeniorDesignGUI:
    SCALE_FACTOR = 1.5

    def __init__(self, root):
        self.root = root
        self.root.title("Senior Design Dashboard")

        width = int(900 * self.SCALE_FACTOR)
        height = int(700 * self.SCALE_FACTOR)
        self.root.geometry(f"{width}x{height}")
        self.root.tk.call("tk", "scaling", self.SCALE_FACTOR)

        # TCP server state. The computer listens for the UNO boards.
        self.server_socket = None
        self.server_thread = None
        self.client_sockets = set()
        self.client_lock = threading.Lock()
        self.server_port = None
        self.running = False

        # Logging state
        self.is_recording = False
        self.log_file = None
        self.log_writer = None

        # Keep a separate ten-reading velocity window for each board.
        self.velocity_samples = {}
        self.latest_velocity_average = {}

        self.frame_info = {
            "Inlet temp": {"value": None, "range": (20, 30), "unit": "°C"},
            "Humidity": {"value": None, "range": (20, 100), "unit": "%"},
            "PM 1.0": {"value": None, "range": (0, 100), "unit": "ug/m^3"},
            "Measured Velocity": {
                "value": None,
                "range": (0, 10),
                "unit": "m/s",
            },
            "Outlet temp 1": {"value": None, "range": (20, 30), "unit": "°C"},
            "Outlet temp 2": {"value": None, "range": (20, 30), "unit": "°C"},
            "Humidity 1": {"value": None, "range": (20, 100), "unit": "%"},
            "Humidity 2": {
                "value": None,
                "range": (20, 100),
                "unit": "%",
            },
            "Outlet air velocity 1": {
                "value": None,
                "range": (100, 500),
                "unit": "ft/s",
            },
            "Outlet air velocity 2": {
                "value": None,
                "range": (350, 450),
                "unit": "ft/s",
            },
        }

        self.log_headers = ["Date", "Time", "Device"] + list(self.frame_info.keys())
        self.ui_elements = {}
        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def s_int(self, value):
        return int(value * self.SCALE_FACTOR)

    def s_font(self, size):
        return int(size * self.SCALE_FACTOR)

    def setup_ui(self):
        control_bar = ttk.Frame(self.root, padding=self.s_int(5))
        control_bar.pack(fill=tk.X)

        ttk.Label(control_bar, text="TCP Port:").pack(
            side=tk.LEFT, padx=self.s_int(5)
        )

        self.port_entry = ttk.Entry(control_bar, width=self.s_int(8))
        self.port_entry.insert(0, "5000")
        self.port_entry.pack(side=tk.LEFT, padx=self.s_int(5))

        self.connect_btn = ttk.Button(
            control_bar,
            text="Start Listening",
            command=self.toggle_connection,
        )
        self.connect_btn.pack(side=tk.LEFT, padx=self.s_int(5))

        self.record_btn = ttk.Button(
            control_bar,
            text="Start Recording",
            command=self.toggle_recording,
            state="disabled",
        )
        self.record_btn.pack(side=tk.LEFT, padx=self.s_int(5))

        self.status_label = ttk.Label(
            control_bar,
            text="Not listening",
            foreground="red",
        )
        self.status_label.pack(side=tk.LEFT, padx=self.s_int(10))

        self.main_container = ttk.Frame(self.root, padding=self.s_int(20))
        self.main_container.pack(fill=tk.BOTH, expand=True)

        for i in range(3):
            self.main_container.columnconfigure(i, weight=1)
        for i in range(4):
            self.main_container.rowconfigure(i, weight=1)

        for index, (title, info) in enumerate(self.frame_info.items()):
            row = index // 3
            col = index % 3
            bg_color = "#eeeeee"

            frame = tk.Frame(
                self.main_container,
                bg=bg_color,
                highlightbackground="black",
                highlightthickness=1,
                padx=self.s_int(15),
                pady=self.s_int(15),
            )
            frame.grid(
                row=row,
                column=col,
                sticky="nsew",
                padx=self.s_int(10),
                pady=self.s_int(10),
            )

            title_label = tk.Label(
                frame,
                text=title,
                font=("Helvetica", self.s_font(12), "bold"),
                bg=bg_color,
            )
            title_label.pack(anchor="w")

            value_label = tk.Label(
                frame,
                text="--",
                font=("Helvetica", self.s_font(20)),
                bg=bg_color,
            )
            value_label.pack(anchor="center", pady=(self.s_int(10), 0))

            self.ui_elements[title] = {
                "frame": frame,
                "value_label": value_label,
                "title_label": title_label,
            }

    def toggle_connection(self):
        if not self.running:
            listener = None
            try:
                port = int(self.port_entry.get().strip())
                if not 1 <= port <= 65535:
                    raise ValueError("TCP port must be between 1 and 65535.")

                listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                listener.bind(("0.0.0.0", port))
                listener.listen(8)
                listener.settimeout(0.5)

                self.server_socket = listener
                self.server_port = port
                self.running = True
                self.velocity_samples.clear()
                self.latest_velocity_average.clear()

                self.connect_btn.config(text="Stop Listening")
                self.status_label.config(
                    text=f"Listening on TCP port {port}",
                    foreground="green",
                )
                self.record_btn.config(state="normal")

                self.server_thread = threading.Thread(
                    target=self.accept_clients,
                    daemon=True,
                )
                self.server_thread.start()

            except Exception as e:
                if listener:
                    listener.close()
                self.server_socket = None
                messagebox.showerror("Server Error", str(e))
        else:
            self.stop_connection()

    def accept_clients(self):
        listener = self.server_socket
        while self.running and listener:
            try:
                client_socket, address = listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            client_socket.settimeout(1.0)
            with self.client_lock:
                self.client_sockets.add(client_socket)

            self.root.after(0, self.refresh_connection_status)
            threading.Thread(
                target=self.read_client,
                args=(client_socket, address),
                daemon=True,
            ).start()

    def read_client(self, client_socket, address):
        buffer = ""
        try:
            while self.running:
                try:
                    chunk = client_socket.recv(1024)
                except socket.timeout:
                    continue

                if not chunk:
                    break

                buffer += chunk.decode("utf-8", errors="replace")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        if isinstance(data, dict):
                            self.root.after(0, self.update_ui_from_data, data)
                    except json.JSONDecodeError:
                        print(f"Invalid JSON received from {address}: {line}")

        except OSError as e:
            if self.running:
                print(f"Connection error from {address}: {e}")
        finally:
            try:
                client_socket.close()
            except OSError:
                pass
            with self.client_lock:
                self.client_sockets.discard(client_socket)
            if self.running:
                self.root.after(0, self.refresh_connection_status)

    def refresh_connection_status(self):
        with self.client_lock:
            count = len(self.client_sockets)

        if self.running:
            self.status_label.config(
                text=f"Listening on TCP {self.server_port} | {count} board(s)",
                foreground="green",
            )

    def stop_connection(self):
        self.running = False

        if self.is_recording:
            self.toggle_recording()

        listener = self.server_socket
        self.server_socket = None
        if listener:
            try:
                listener.close()
            except OSError:
                pass

        with self.client_lock:
            clients = list(self.client_sockets)
            self.client_sockets.clear()

        for client_socket in clients:
            try:
                client_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                client_socket.close()
            except OSError:
                pass

        self.connect_btn.config(text="Start Listening")
        self.status_label.config(text="Not listening", foreground="red")
        self.record_btn.config(state="disabled")

    def on_close(self):
        if self.running:
            self.stop_connection()
        elif self.is_recording:
            self.toggle_recording()
        self.root.destroy()

    def toggle_recording(self):
        if not self.is_recording:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sensor_data_{timestamp_str}.csv"

            try:
                self.log_file = open(filename, mode="w", newline="")
                self.log_writer = csv.DictWriter(
                    self.log_file,
                    fieldnames=self.log_headers,
                )
                self.log_writer.writeheader()

                self.is_recording = True
                self.record_btn.config(text="Stop Recording")

            except Exception as e:
                messagebox.showerror(
                    "Logging Error",
                    f"Could not create file: {e}",
                )
        else:
            self.is_recording = False

            if self.log_file:
                self.log_file.close()
                self.log_file = None
                self.log_writer = None

            self.record_btn.config(text="Start Recording")

    def update_ui_from_data(self, data):
        device_id = str(data.get("Device", "Unknown"))

        # Keep a separate moving average for each board.
        velocity = data.get("Measured Velocity")
        if velocity is not None:
            try:
                samples = self.velocity_samples.setdefault(
                    device_id, deque(maxlen=10)
                )
                samples.append(float(velocity))

                if len(samples) == 10:
                    average = sum(samples) / len(samples)
                    self.latest_velocity_average[device_id] = average
                    self.update_value_display("Measured Velocity", average)
            except (TypeError, ValueError):
                pass

        # The existing dashboard has one set of display panels, so it shows
        # the latest value received for each field, regardless of board.
        for key, new_val in data.items():
            if key in ("Device", "Measured Velocity"):
                continue

            if key in self.frame_info and key in self.ui_elements:
                try:
                    self.update_value_display(key, float(new_val))
                except (TypeError, ValueError):
                    pass

        if self.is_recording and self.log_writer:
            try:
                now = datetime.now()
                row = {
                    "Date": now.strftime("%Y-%m-%d"),
                    "Time": now.strftime("%H:%M:%S"),
                    "Device": device_id,
                }

                for key in self.frame_info:
                    if key == "Measured Velocity":
                        row[key] = self.latest_velocity_average.get(device_id, "")
                    else:
                        row[key] = data.get(key, "")

                self.log_writer.writerow(row)
                self.log_file.flush()

            except Exception as e:
                print(f"Logging error: {e}")

    def update_value_display(self, key, value):
        info = self.frame_info[key]
        ui = self.ui_elements[key]

        info["value"] = value
        ui["value_label"].config(text=f"{value:.2f} {info['unit']}")

        in_range = info["range"][0] <= value <= info["range"][1]
        bg_color = "#caffbf" if in_range else "#ffadad"

        ui["frame"].config(bg=bg_color)
        ui["title_label"].config(bg=bg_color)
        ui["value_label"].config(bg=bg_color)


if __name__ == "__main__":
    root = tk.Tk()
    app = SeniorDesignGUI(root)
    root.mainloop()
