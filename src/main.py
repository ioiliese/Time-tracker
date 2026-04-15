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
            self.start_time = None
            return elapsed
        return 0
        
    def prepare_for_auto_save(self):
        """Notificam activitatea ca urmeaza o salvare automata a timpului scurs pana in prezent"""
        if self.is_running:
            now = time.time()
            self.total_time += (now - self.start_time)
            self.start_time = now
    
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

ROMANIAN_MONTHS = [
    "Ianuarie", "Februarie", "Martie", "Aprilie", "Mai", "Iunie",
    "Iulie", "August", "Septembrie", "Octombrie", "Noiembrie", "Decembrie"
]

class TimeTrackerApp:
    def __init__(self, root, selected_date):
        self.auto_save_interval = 300000  # 5 minute in milisecunde
        self.root = root
        self.current_date = selected_date

        # Formateaza data pentru titlu
        try:
            date_obj = datetime.strptime(self.current_date, "%Y-%m-%d")
            day = date_obj.day
            month_name = ROMANIAN_MONTHS[date_obj.month - 1] # list is 0-indexed
            year = date_obj.year
            title_date = f"{day} {month_name} {year}"
        except (ValueError, IndexError):
            title_date = self.current_date # Fallback la data originala

        self.root.title(f"Time Tracker - {title_date}")
        
        # Centreaza fereastra principala pe ecran
        window_width = 600
        window_height = 700
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        center_x = int(screen_width / 2 - window_width / 2)
        center_y = int(screen_height / 2 - window_height / 2)
        self.root.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
        
        self.root.resizable(True, True)
        
        self.activities = []
        self.activity_widgets = {}
        self.report_dir = Path(__file__).parent.parent / "report"
        self.report_dir.mkdir(exist_ok=True)
        self.report_file = self.get_report_file_for_date(self.current_date)
        
        # Incarc activitati din fisier daca exista
        self.load_activities()
        
        # Creez interfata
        self.create_ui()
        
        # Setez inchiderea ferestrei pentru a salva datele
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Setez evenimentul pentru recapatarea focusului
        self.root.bind("<FocusIn>", self.on_focus_in)
        self.root.bind("<FocusOut>", self.on_focus_out)
        self.timer_after_id = None

        # Incepe actualizarea timerelor
        self.update_timers_loop() 
    
    def get_report_file_for_date(self, date_str):
        """Returneaza calea fisierului de raport pentru data specificata"""
        return self.report_dir / f"{date_str}.json"
    
    def load_activities(self):
        """Incarca activitati din fisierul de astazi daca exista"""
        if self.report_file.exists():
            try:
                with open(self.report_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.activities = [Activity.from_dict(act) for act in data]
                    
                    msg_text = f"Am incarcat {len(self.activities)} activitati din {self.report_file.name}"
                    
                    def show_popup():
                        # Fereastra custom pentru mesaj cu font marit
                        msg_win = tk.Toplevel(self.root)
                        msg_win.title("Info")
                        msg_win.resizable(False, False)
                        
                        ttk.Label(msg_win, text=msg_text, font=("Arial", 14)).pack(padx=30, pady=20)
                        ttk.Button(msg_win, text="OK", command=msg_win.destroy).pack(pady=(0, 20))
                        
                        # Centram fereastra pe ecran
                        msg_win.update_idletasks()
                        x = (msg_win.winfo_screenwidth() // 2) - (msg_win.winfo_width() // 2)
                        y = (msg_win.winfo_screenheight() // 2) - (msg_win.winfo_height() // 2)
                        msg_win.geometry(f"+{x}+{y}")
                        
                        msg_win.transient(self.root)
                        msg_win.grab_set()
                        
                    self.root.after(100, show_popup)
            except Exception as e:
                messagebox.showerror("Eroare", f"Eroare la incarcare: {e}")
    
    def save_activities(self):
        """Salveaza activitati in fisierul zilei folosind o scriere atomica."""
        for act in self.activities:
            act.prepare_for_auto_save()
            
        try:
            data = [act.to_dict() for act in self.activities]
            
            # Scrie intr-un fisier temporar in acelasi director
            temp_file = self.report_file.with_suffix('.json.tmp')
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            # Inlocuieste fisierul original cu cel temporar (operatie atomica pe majoritatea OS-urilor)
            os.replace(temp_file, self.report_file)
            
        except (IOError, OSError, Exception) as e:
            messagebox.showerror("Eroare la Salvare", f"Nu am putut salva fisierul de raport:\n{e}")
    
    def create_ui(self):
        """Creeaza interfata"""
        # Header frame
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Buton adauga activitate
        self.add_btn = ttk.Button(header_frame, text="➕ Adauga Activitate", command=self.add_activity)
        self.add_btn.pack(side=tk.LEFT, padx=5)
        
        # Label total timp pe zi
        self.total_day_time_label = ttk.Label(header_frame, text="Suma totala a activitatiilor: 00:00:00", font=("Arial", 12, "bold"))
        self.total_day_time_label.pack(side=tk.RIGHT, padx=5)
        
        # Container pentru activitati
        self.canvas = tk.Canvas(self.root, bg="#f0f0f0", highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")
        
        # Bind canvas configure event to resize the scrollable frame
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        
        # Refresh activitati
        self.refresh_activities_ui()
    
    def on_canvas_configure(self, event):
        """Ajusteaza latimea frame-ului scrollabil la latimea canvas-ului"""
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)
    
    def add_activity(self):
        """Adauga o noua activitate"""
        dialog = tk.Toplevel(self.root)
        dialog.withdraw() # Ascunde fereastra inainte de a o configura
        dialog.title("Adauga Activitate")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        
        # Label
        label = ttk.Label(dialog, text="Nume activitate:")
        label.pack(pady=10)
        
        # Entry
        entry = ttk.Entry(dialog, width=30)
        entry.pack(padx=20, pady=10, ipadx=5, ipady=4)
        
        def save():
            name = entry.get().strip()
            if name:
                act = Activity(name)
                self.activities.append(act)
                self.refresh_activities_ui()
                self.save_activities()
                dialog.destroy()
            else:
                messagebox.showwarning("Atentie", "Introdu un nume pentru activitate", parent=dialog)
        
        # Buton salveaza
        save_btn = ttk.Button(dialog, text="Salveaza", command=save)
        save_btn.pack(pady=10)
        
        # Bind Enter key
        entry.bind("<Return>", lambda e: save())

        # --- Logica de centrare ---
        # Forteaza actualizarea dialogului pentru a-i calcula dimensiunile reale
        dialog.update_idletasks()

        # Preia dimensiunile si pozitia ferestrei parinte
        parent_x = self.root.winfo_rootx()
        parent_y = self.root.winfo_rooty()
        parent_width = self.root.winfo_width()
        parent_height = self.root.winfo_height()

        # Preia dimensiunile reale ale dialogului (calculate automat)
        dialog_width = dialog.winfo_width()
        dialog_height = dialog.winfo_height()

        # Calculeaza pozitia si seteaza geometria
        x = parent_x + (parent_width // 2) - (dialog_width // 2)
        y = parent_y + (parent_height // 2) - (dialog_height // 2)
        dialog.geometry(f"+{x}+{y}")

        dialog.deiconify() # Afiseaza fereastra, acum ca este pozitionata corect
        entry.focus()
        dialog.grab_set()
    
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
        border_color = "#4CAF50" if activity.is_running else "#cccccc"
        frame = tk.Frame(self.scrollable_frame, highlightbackground=border_color, highlightthickness=2)
        frame.pack(fill=tk.X, pady=5, padx=5)
        
        # Nume activitate
        name_label = ttk.Label(frame, text=activity.name, font=("Arial", 12, "bold"))
        name_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Timp curent
        self.activity_widgets[idx] = {
            "activity": activity,
            "frame": frame,
            "time_label": ttk.Label(frame, text=f"Total: {format_time(activity.get_current_time())}", font=("Arial", 10))
        }
        self.activity_widgets[idx]["time_label"].pack(side=tk.LEFT, padx=5)
        
        total_text = f"Salvat in raport: {format_time(activity.total_time)}"
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
        frame = self.activity_widgets[idx]["frame"]
        
        if not act.is_running:
            act.start()
            btn.config(text="⏹ Stop")
            frame.config(highlightbackground="#4CAF50")
        else:
            act.stop()
            btn.config(text="▶ Start")
            frame.config(highlightbackground="#cccccc")
            self.save_activities()
    
    def delete_activity(self, idx):
        """Sterge o activitate"""
        if messagebox.askyesno("Confirma", "Esti sigur ca doresti sa stergi aceasta activitate?"):
            del self.activities[idx]
            self.refresh_activities_ui()
            self.save_activities()
    
    def update_timers_loop(self):
        """Bucla care ruleaza la fiecare secunda cat timp fereastra are focus."""
        self.refresh_timer_labels()
        self.timer_after_id = self.root.after(1000, self.update_timers_loop)

    def refresh_timer_labels(self):
        """Actualizeaza vizual textele de timp pentru toate activitatile."""
        for idx in self.activity_widgets:
            act = self.activity_widgets[idx]["activity"]
            current_time = act.get_current_time()
            formatted = f"Total: {format_time(current_time)}"
            self.activity_widgets[idx]["time_label"].config(text=formatted)
            
            total_text = f"Salvat in raport: {format_time(act.total_time)}"
            self.activity_widgets[idx]["total_label"].config(text=total_text)
            
        # Actualizeaza timpul total al zilei
        total_day_time = sum(act.total_time for act in self.activities)
        self.total_day_time_label.config(text=f"Suma totala a activitatiilor: {format_time(total_day_time)}")

    def on_focus_out(self, event):
        """Declansat cand fereastra principala pierde focusul."""
        if event.widget == self.root:
            if self.timer_after_id is not None:
                self.root.after_cancel(self.timer_after_id)
                self.timer_after_id = None

    def on_focus_in(self, event):
        """Declansat instantaneu cand fereastra principala primeste focus."""
        # Conditia previne rularea daca focusul pica pe un widget interior (ex: un buton)
        if event.widget == self.root:
            self.refresh_timer_labels()
            # Repornim bucla daca a fost oprita
            if self.timer_after_id is None:
                self.update_timers_loop()

    def on_close(self):
        """Salveaza activitatile la inchidere si opreste timer-ele active"""
        for act in self.activities:
            if act.is_running:
                act.stop()
        self.save_activities()
        self.root.destroy()

class StartupDialog(tk.Toplevel):
    def __init__(self, parent, report_dates):
        super().__init__(parent)
        self.title("Selectează Sesiunea")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.grab_set()

        self.result = None  # Va contine data selectata

        self.choice = tk.StringVar(value="today")

        ttk.Label(self, text="Alege sesiunea de lucru:").pack(pady=10)

        today_rb = ttk.Radiobutton(self, text="Ziua curentă", variable=self.choice, value="today", command=self.toggle_combobox)
        today_rb.pack(anchor=tk.W, padx=20)

        other_day_rb = ttk.Radiobutton(self, text="Altă zi:", variable=self.choice, value="other", command=self.toggle_combobox)
        other_day_rb.pack(anchor=tk.W, padx=20)

        self.dates_combo = ttk.Combobox(self, state="disabled", values=report_dates)
        if report_dates:
            self.dates_combo.set(report_dates[0])
        self.dates_combo.pack(padx=40, fill=tk.X, expand=True)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=15)

        ok_btn = ttk.Button(btn_frame, text="Start", command=self.on_ok)
        ok_btn.pack(side=tk.LEFT, padx=10)
        cancel_btn = ttk.Button(btn_frame, text="Anulează", command=self.on_cancel)
        cancel_btn.pack(side=tk.LEFT, padx=10)

        # Centreaza fereastra
        self.update_idletasks()
        width = 350
        height = 200
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

        self.focus_force()
        self.wait_window(self)

    def toggle_combobox(self):
        if self.choice.get() == "other":
            self.dates_combo.config(state="readonly")
        else:
            self.dates_combo.config(state="disabled")

    def on_ok(self):
        if self.choice.get() == "today":
            self.result = datetime.now().strftime("%Y-%m-%d")
        else:
            selected = self.dates_combo.get()
            if not selected:
                messagebox.showwarning("Atenție", "Te rog selectează o dată.", parent=self)
                return
            self.result = selected
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()

def get_report_dates(report_dir):
    if not report_dir.exists():
        return []
    dates = []
    for f in report_dir.glob("*.json"):
        date_str = f.stem
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            dates.append(date_str)
        except ValueError:
            continue  # Ignora fisierele care nu au formatul corect
    return sorted(dates, reverse=True)

if __name__ == "__main__":

    root = tk.Tk()
    root.withdraw()  # Ascunde fereastra principala initial

    report_dir = Path(__file__).parent.parent / "report"
    report_dates = get_report_dates(report_dir)

    dialog = StartupDialog(root, report_dates)
    selected_date = dialog.result

    if selected_date:
        app = TimeTrackerApp(root, selected_date=selected_date)
        root.deiconify()  # Arata fereastra principala
        root.mainloop()
    else:
        root.destroy()