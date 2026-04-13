import tkinter as tk
from tkinter import simpledialog, messagebox, ttk
import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path

class Activity:
    """Reprezentare a unei activitati cu timer"""
    def __init__(self, name):
        self.name = name
        self.total_time = 0  # in secunde
        self.is_running = False
        self.start_time = None
        self.last_save_time = 0
        
    def start(self):
        """Porneste timerul"""
        if not self.is_running:
            self.is_running = True
            self.start_time = time.time()
            
    def stop(self):
        """Opreste timerul si adauga timpul la totalul activitatii"""
        if self.is_running:
            self.is_running = False
            elapsed = time.time() - self.start_time
            self.total_time += elapsed
            self.last_save_time = self.total_time
            self.start_time = None
            return elapsed
        return 0
    
    def get_current_time(self):
        """Returneaza timpul curent pentru activitate (total + timp curent daca e pornit)"""
        if self.is_running:
            return self.total_time + (time.time() - self.start_time)
        return self.total_time
    
    def to_dict(self):
        """Converteste activitatea in dictionar pentru salvare"""
        return {
            "name": self.name,
            "total_time": self.total_time
        }
    
    @staticmethod
    def from_dict(data):
        """Creeaza o activitate din dictionar"""
        act = Activity(data["name"])
        act.total_time = data["total_time"]
        return act


def format_time(seconds):
    """Formateaza timp in format HH:MM:SS"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


class TimeTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Time Tracker")
        self.root.geometry("600x700")
        self.root.resizable(False, False)
        
        self.activities = []
        self.activity_widgets = {}
        self.show_totals = True
        self.report_dir = Path("./report")
        self.report_dir.mkdir(exist_ok=True)
        self.report_file = self.get_today_report_file()
        
        # Incarc activitati din fisier daca exista
        self.load_activities()
        
        # Creez interfata
        self.create_ui()
        
        # Setez inchiderea ferestrei pentru a salva datele
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Incerc auto-save
        self.auto_save_thread = threading.Thread(target=self.auto_save_worker, daemon=True)
        self.auto_save_thread.start()
        
        # Update timer afisaj
        self.update_timers()
    
    def get_today_report_file(self):
        """Returneaza calea fisierului de raport pentru astazi"""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.report_dir / f"{today}.json"
    
    def load_activities(self):
        """Incarca activitati din fisierul de astazi daca exista"""
        if self.report_file.exists():
            try:
                with open(self.report_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.activities = [Activity.from_dict(act) for act in data]
                    messagebox.showinfo("Info", f"Am incarcat {len(self.activities)} activitati din {self.report_file.name}")
            except Exception as e:
                messagebox.showerror("Eroare", f"Eroare la incarcare: {e}")
    
    def save_activities(self):
        """Salveaza activitati in fisierul zilei"""
        try:
            data = [act.to_dict() for act in self.activities]
            with open(self.report_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("Eroare", f"Eroare la salvare: {e}")
    
    def auto_save_worker(self):
        """Thread worker pentru auto-save la fiecare 5 minute"""
        while True:
            time.sleep(300)  # 5 minute
            self.root.after(0, self.save_activities)
    
    def create_ui(self):
        """Creeaza interfata"""
        # Header frame
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Buton adauga activitate
        self.add_btn = ttk.Button(header_frame, text="➕ Adauga Activitate", command=self.add_activity)
        self.add_btn.pack(side=tk.LEFT, padx=5)
        
        # Buton show/hide totals
        self.toggle_totals_btn = ttk.Button(header_frame, text="👁 Ascunde Total", command=self.toggle_totals)
        self.toggle_totals_btn.pack(side=tk.LEFT, padx=5)
        
        # Buton salveaza manual
        save_btn = ttk.Button(header_frame, text="💾 Salveaza", command=self.save_activities)
        save_btn.pack(side=tk.LEFT, padx=5)
        
        # Container pentru activitati
        self.canvas = tk.Canvas(self.root, bg="#f0f0f0")
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")
        
        # Refresh activitati
        self.refresh_activities_ui()
    
    def add_activity(self):
        """Adauga o noua activitate"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Adauga Activitate")
        dialog.geometry("300x150")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Label
        label = ttk.Label(dialog, text="Nume activitate:")
        label.pack(pady=10)
        
        # Entry
        entry = ttk.Entry(dialog, width=30)
        entry.pack(pady=5)
        entry.focus()
        
        def save():
            name = entry.get().strip()
            if name:
                act = Activity(name)
                self.activities.append(act)
                self.refresh_activities_ui()
                self.save_activities()
                dialog.destroy()
            else:
                messagebox.showwarning("Atentie", "Introdu un nume pentru activitate")
        
        # Buton salveaza
        save_btn = ttk.Button(dialog, text="Salveaza", command=save)
        save_btn.pack(pady=10)
        
        # Bind Enter key
        entry.bind("<Return>", lambda e: save())
    
    def toggle_totals(self):
        """Afiseaza/ascunde timpurile totale"""
        self.show_totals = not self.show_totals
        btn_text = "👁 Ascunde Total" if self.show_totals else "👁 Arata Total"
        self.toggle_totals_btn.config(text=btn_text)
        self.refresh_activities_ui()
    
    def refresh_activities_ui(self):
        """Reincarca afisajul activitatilor"""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        self.activity_widgets = {}
        
        if not self.activities:
            label = ttk.Label(self.scrollable_frame, text="Nu ai nicio activitate. Adauga una!", foreground="gray")
            label.pack(pady=20)
        
        for idx, act in enumerate(self.activities):
            self.create_activity_widget(idx, act)
    
    def create_activity_widget(self, idx, activity):
        """Creeaza widget-ul pentru o activitate"""
        frame = ttk.Frame(self.scrollable_frame, relief=tk.RIDGE, borderwidth=1)
        frame.pack(fill=tk.X, pady=5, padx=5)
        
        # Nume activitate
        name_label = ttk.Label(frame, text=activity.name, font=("Arial", 12, "bold"))
        name_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Timp curent
        self.activity_widgets[idx] = {
            "activity": activity,
            "frame": frame,
            "time_label": ttk.Label(frame, text="00:00:00", font=("Arial", 10))
        }
        self.activity_widgets[idx]["time_label"].pack(side=tk.LEFT, padx=5)
        
        # Total timp daca show_totals
        if self.show_totals:
            total_text = f"Total: {format_time(activity.total_time)}"
            total_label = ttk.Label(frame, text=total_text, foreground="blue")
            total_label.pack(side=tk.LEFT, padx=5)
            self.activity_widgets[idx]["total_label"] = total_label
        
        # Buton Start/Stop
        btn_text = "⏹ Stop" if activity.is_running else "▶ Start"
        self.activity_widgets[idx]["timer_btn"] = ttk.Button(
            frame,
            text=btn_text,
            command=lambda: self.toggle_timer(idx)
        )
        self.activity_widgets[idx]["timer_btn"].pack(side=tk.LEFT, padx=5, pady=5)
        
        # Buton Delete
        delete_btn = ttk.Button(
            frame,
            text="🗑 Delete",
            command=lambda: self.delete_activity(idx)
        )
        delete_btn.pack(side=tk.LEFT, padx=5, pady=5)
    
    def toggle_timer(self, idx):
        """Porneste/opreste timerul pentru o activitate"""
        act = self.activity_widgets[idx]["activity"]
        btn = self.activity_widgets[idx]["timer_btn"]
        
        if not act.is_running:
            act.start()
            btn.config(text="⏹ Stop")
        else:
            act.stop()
            btn.config(text="▶ Start")
            self.save_activities()
    
    def delete_activity(self, idx):
        """Sterge o activitate"""
        if messagebox.askyesno("Confirma", "Esti sigur ca doresti sa stergi aceasta activitate?"):
            del self.activities[idx]
            self.refresh_activities_ui()
            self.save_activities()
    
    def update_timers(self):
        """Actualizeaza afisajul timpilor in timp real"""
        for idx in self.activity_widgets:
            act = self.activity_widgets[idx]["activity"]
            current_time = act.get_current_time()
            formatted = format_time(current_time)
            self.activity_widgets[idx]["time_label"].config(text=formatted)
            
            if self.show_totals and "total_label" in self.activity_widgets[idx]:
                total_text = f"Total: {format_time(act.total_time)}"
                self.activity_widgets[idx]["total_label"].config(text=total_text)
        
        self.root.after(100, self.update_timers)

    def on_close(self):
        """Salveaza activitatile la inchidere si opreste timer-ele active"""
        for act in self.activities:
            if act.is_running:
                act.stop()
        self.save_activities()
        self.root.destroy()


if __name__ == "__main__":

    root = tk.Tk()
    app = TimeTrackerApp(root)
    root.mainloop()