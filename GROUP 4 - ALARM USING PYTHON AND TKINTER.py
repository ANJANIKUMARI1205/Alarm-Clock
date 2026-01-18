import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import sqlite3
import threading
import time
import os
import pygame

pygame.mixer.init()
temp_snooze = {}
triggered_today = {}

class AlarmClock :
    def __init__(self, root):
        self.root = root
        self.root.title("Alarm Clock")
        self.root.geometry("600x500")
        self.root.configure(bg="#1e1e2f")  

        self.conn = sqlite3.connect("alarms.db", check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS alarms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT NOT NULL,
                event TEXT,
                status TEXT,
                repeat TEXT,
                days TEXT
            )
        ''')
        self.conn.commit()

        self.event_var = tk.StringVar()
        self.repeat_var = tk.StringVar(value="No")
        self.status_var = tk.StringVar(value="ON")
        self.time_format_var = tk.StringVar(value="12")
        self.ampm_var = tk.StringVar(value="AM")
        self.days_vars = {day: tk.BooleanVar() for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]}

        self.time_24_var = tk.StringVar()
        self.hour_12_var = tk.StringVar()
        self.min_12_var = tk.StringVar()

        self.popup_window = None

        self.build_gui()
        self.load_alarms()
        threading.Thread(target=self.check_alarms, daemon=True).start()

    def build_gui(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#2e2e3e", foreground="white", fieldbackground="#2e2e3e", rowheight=25)
        style.configure("Treeview.Heading", background="#3a3a4f", foreground="white", font=('Helvetica', 10, 'bold'))
        style.map("Treeview", background=[('selected', '#5c5cff')])

        entry_frame = tk.Frame(self.root, bg="#1e1e2f")
        entry_frame.pack(pady=10)

        tk.Label(entry_frame, text="Choose Time Format", bg="#1e1e2f", fg="white").grid(row=0, column=0, sticky='w')
        format_frame = tk.Frame(entry_frame, bg="#1e1e2f")
        format_frame.grid(row=0, column=1, sticky='w')
        tk.Radiobutton(format_frame, text="12-hour (AM/PM)", variable=self.time_format_var, value="12", command=self.update_time_input, bg="#1e1e2f", fg="white", selectcolor="#444").pack(side=tk.LEFT)
        tk.Radiobutton(format_frame, text="24-hour", variable=self.time_format_var, value="24", command=self.update_time_input, bg="#1e1e2f", fg="white", selectcolor="#444").pack(side=tk.LEFT)

        self.time_input_frame = tk.Frame(entry_frame, bg="#1e1e2f")
        self.time_input_frame.grid(row=1, column=1)
        self.update_time_input()

        tk.Label(entry_frame, text="Time", bg="#1e1e2f", fg="white").grid(row=1, column=0)
        tk.Label(entry_frame, text="Event", bg="#1e1e2f", fg="white").grid(row=2, column=0)
        tk.Entry(entry_frame, textvariable=self.event_var, width=20, bg="#2e2e3e", fg="white", insertbackground="white").grid(row=2, column=1)

        tk.Label(entry_frame, text="Repeat", bg="#1e1e2f", fg="white").grid(row=3, column=0)
        self.repeat_box = ttk.Combobox(entry_frame, textvariable=self.repeat_var, values=["No", "Daily", "Weekly"])
        self.repeat_box.grid(row=3, column=1)
        self.repeat_box.current(0)

        tk.Label(entry_frame, text="Days (for Weekly)", bg="#1e1e2f", fg="white").grid(row=4, column=0)
        days_frame = tk.Frame(entry_frame, bg="#1e1e2f")
        days_frame.grid(row=4, column=1)
        for i, (day, var) in enumerate(self.days_vars.items()):
            tk.Checkbutton(days_frame, text=day, variable=var, bg="#1e1e2f", fg="white", selectcolor="#444").grid(row=0, column=i)

        tk.Button(entry_frame, text="Set Alarm", command=self.set_alarm, bg="#444", fg="white", activebackground="#666").grid(row=5, columnspan=2, pady=5)

        self.tree = ttk.Treeview(self.root, columns=("time", "event", "status", "repeat", "days"), show='headings')
        for col in ("time", "event", "status", "repeat", "days"):
            self.tree.heading(col, text=col.capitalize())
        self.tree.pack(expand=True, fill='both', padx=10, pady=10)

        btn_frame = tk.Frame(self.root, bg="#1e1e2f")
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Delete", command=self.delete_alarm, bg="red", fg="white", activebackground="#aa0000").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Toggle ON/OFF", command=self.toggle_alarm, bg="#005f5f", fg="white", activebackground="#007f7f").pack(side=tk.LEFT, padx=5)

        self.status_label = tk.Label(self.root, text="", fg="lightgreen", bg="#1e1e2f")
        self.status_label.pack()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def update_time_input(self):
        for widget in self.time_input_frame.winfo_children():
            widget.destroy()
        if self.time_format_var.get() == "12":
            tk.Entry(self.time_input_frame, textvariable=self.hour_12_var, width=5, bg="#2e2e3e", fg="white", insertbackground="white").pack(side=tk.LEFT)
            tk.Label(self.time_input_frame, text=":", bg="#1e1e2f", fg="white").pack(side=tk.LEFT)
            tk.Entry(self.time_input_frame, textvariable=self.min_12_var, width=5, bg="#2e2e3e", fg="white", insertbackground="white").pack(side=tk.LEFT)
            ampm_menu = ttk.Combobox(self.time_input_frame, textvariable=self.ampm_var, values=["AM", "PM"], width=5, state="readonly")
            ampm_menu.pack(side=tk.LEFT)
            ampm_menu.current(0)
        else:
            tk.Entry(self.time_input_frame, textvariable=self.time_24_var, width=10, bg="#2e2e3e", fg="white", insertbackground="white").pack(side=tk.LEFT)
            tk.Label(self.time_input_frame, text="(HH:MM)", bg="#1e1e2f", fg="white").pack(side=tk.LEFT)

    def set_alarm(self):
        event = self.event_var.get().strip()
        repeat = self.repeat_var.get().strip()
        status = self.status_var.get().strip()
        days_selected = ",".join([d for d, v in self.days_vars.items() if v.get()])
        format_selected = self.time_format_var.get()

        if format_selected == "12":
            hour = self.hour_12_var.get().zfill(2)
            minute = self.min_12_var.get().zfill(2)
            ampm = self.ampm_var.get()
            time_input = f"{hour}:{minute} {ampm}"
            try:
                parsed_time = datetime.strptime(time_input, "%I:%M %p")
            except ValueError:
                messagebox.showerror("Error", "Invalid 12-hour format. Use HH MM and AM/PM.")
                return
        else:
            time_input = self.time_24_var.get()
            try:
                parsed_time = datetime.strptime(time_input, "%H:%M")
            except ValueError:
                messagebox.showerror("Error", "Invalid 24-hour format. Use HH:MM.")
                return

        formatted_time = parsed_time.strftime("%I:%M %p")

        self.cursor.execute("SELECT * FROM alarms WHERE time=? AND event=?", (formatted_time, event))
        if self.cursor.fetchone():
            messagebox.showerror("Error", "Duplicate alarm")
            return

        self.cursor.execute("INSERT INTO alarms (time, event, status, repeat, days) VALUES (?, ?, ?, ?, ?)",
                            (formatted_time, event, status, repeat, days_selected))
        self.conn.commit()
        self.load_alarms()

        self.event_var.set("")
        self.hour_12_var.set("")
        self.min_12_var.set("")
        self.ampm_var.set("AM")
        self.time_24_var.set("")
        for v in self.days_vars.values():
            v.set(False)

    def load_alarms(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.cursor.execute("SELECT * FROM alarms ORDER BY time")
        for row in self.cursor.fetchall():
            self.tree.insert('', 'end', iid=row[0], values=row[1:])

    def delete_alarm(self):
        selected = self.tree.selection()
        for i in selected:
            self.cursor.execute("DELETE FROM alarms WHERE id=?", (i,))
        self.conn.commit()
        self.load_alarms()

    def toggle_alarm(self):
        selected = self.tree.selection()
        for i in selected:
            current = self.tree.item(i)['values']
            new_status = "OFF" if current[2] == "ON" else "ON"
            self.cursor.execute("UPDATE alarms SET status=? WHERE id=?", (new_status, i))
        self.conn.commit()
        self.load_alarms()

    def check_alarms(self):
        thread_conn = sqlite3.connect("alarms.db", check_same_thread=False)
        thread_cursor = thread_conn.cursor()

        while True:
            now = datetime.now()
            current_time = now.strftime("%I:%M %p")
            weekday = now.strftime("%a")[:3]
            key_time = now.strftime("%Y-%m-%d %I:%M %p")

            thread_cursor.execute("SELECT * FROM alarms WHERE status='ON'")
            for row in thread_cursor.fetchall():
                alarm_id, time_str, event, status, repeat, days = row

                if temp_snooze.get(alarm_id) and time.time() < temp_snooze[alarm_id]:
                    continue

                if time_str == current_time:
                    if repeat == "No" or repeat == "Daily" or (repeat == "Weekly" and weekday in days.split(",")):
                        if triggered_today.get(alarm_id) != key_time:
                            triggered_today[alarm_id] = key_time
                            self.status_label.config(text=f"Triggered: {event} at {current_time}")
                            if repeat == "No":
                                thread_cursor.execute("UPDATE alarms SET status='OFF' WHERE id=?", (alarm_id,))
                                thread_conn.commit()
                            self.trigger_alarm(alarm_id, event)
            time.sleep(1)

    def trigger_alarm(self, alarm_id, event):
        if self.popup_window and self.popup_window.winfo_exists():
            return

        def alarm_popup():
            self.popup_window = tk.Toplevel(self.root)
            self.popup_window.title("Alarm")
            self.popup_window.geometry("250x150")
            tk.Label(self.popup_window, text=f"Event: {event}").pack(pady=10)
            tk.Button(self.popup_window, text="Snooze 5 Min", command=lambda: self.snooze_alarm(alarm_id)).pack()
            tk.Button(self.popup_window, text="Stop", command=self.stop_sound).pack()

            mp3_path = os.path.join(os.getcwd(), "alarm.mp3")
            if os.path.exists(mp3_path):
                pygame.mixer.music.load(mp3_path)
                pygame.mixer.music.play(-1)
            else:
                print("Alarm sound not found:", mp3_path)

        self.root.after(0, alarm_popup)

    def stop_sound(self):
        pygame.mixer.music.stop()
        if self.popup_window:
            self.popup_window.destroy()

    def snooze_alarm(self, alarm_id):
        temp_snooze[alarm_id] = time.time() + 300
        self.stop_sound()

    def on_close(self):
        pygame.mixer.music.stop()
        self.conn.close()
        self.root.destroy()

if __name__ == '__main__' :
    root = tk.Tk()
    app = AlarmClock(root)
    root.mainloop()
