import tkinter as tk
from tkinter import simpledialog, messagebox, ttk
import json
import os
import threading
import time
import sys
import ctypes
from datetime import datetime, timedelta
from pathlib import Path

class Activity:
    """Reprezentare a unei activitati cu timer"""
    def __init__(self, name, tag="", description=""):
        self.name = name
        self.tag = tag
        self.description = description
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
            "tag": getattr(self, 'tag', ""),
            "description": getattr(self, 'description', ""),
            "total_time": self.total_time
        }
    
    @staticmethod
    def from_dict(data):
        """Creeaza o activitate din dictionar"""
        act = Activity(
            name=data["name"],
            tag=data.get("tag", ""),
            description=data.get("description", "")
        )
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

class ToolTip:
    """Creează un tooltip plutitor pentru un widget (la hover)."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True) # Elimină marginile ferestrei
        tw.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(tw, text=self.text, justify=tk.LEFT, background="#ffffe0", relief=tk.SOLID, borderwidth=1, font=("Arial", 9), padx=5, pady=3)
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

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
        
        
        self.root.resizable(True, True)
        
        self.activities = []
        self.activity_widgets = {}
        
        # Determinam folderul de baza (compatibilitate atat pentru .py cat si pentru .exe)
        if getattr(sys, 'frozen', False):
            self.base_dir = Path(sys.executable).parent
        else:
            self.base_dir = Path(__file__).parent.parent
            
        self.report_dir = self.base_dir / "report"
        self.report_dir.mkdir(exist_ok=True)
        self.report_file = self.get_report_file_for_date(self.current_date)
        
        # Initializeaza directorul si fisierul pentru tag-uri
        self.tags_dir = self.base_dir / "tags_for_activities"
        self.tags_dir.mkdir(exist_ok=True)
        self.tags_file = self.tags_dir / "tags.json"
        
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

        # Incepe salvarea automata a activitatilor
        self.auto_save_activities()
        
        # Ajusteaza la final dimensiunea ferestrei in functie de activitatile incarcate
        self.adjust_window_size()

    def auto_save_activities(self):
        """"Salveaza automat timpul petrecut pentru fiecare activitate"""
        self.save_activities()
        self.root.after(self.auto_save_interval, self.auto_save_activities)

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
        self.header_frame = ttk.Frame(self.root)
        self.header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Buton adauga activitate
        self.add_btn = ttk.Button(self.header_frame, text="➕ Adauga Activitate", command=self.add_activity)
        self.add_btn.pack(side=tk.LEFT, padx=5)
        
        # Buton gestionare Tags
        self.tags_btn = ttk.Button(self.header_frame, text="🏷️ Taguri activități", command=self.open_tags_dialog)
        self.tags_btn.pack(side=tk.LEFT, padx=5)
        
        # Buton generare raport
        self.report_btn = ttk.Button(self.header_frame, text="📊 Generare Raport", command=self.open_report_dialog)
        self.report_btn.pack(side=tk.LEFT, padx=5)
        
        # Label total timp pe zi
        self.total_day_time_label = ttk.Label(self.header_frame, text="Suma totala a activitatiilor: 00:00:00", font=("Arial", 12, "bold"))
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
        
    def adjust_window_size(self):
        """Ajusteaza latimea si inaltimea UI-ului pentru a incadra perfect activitatile existente la lansare"""
        self.root.update_idletasks() # Actualizam layout-ul curent pentru a citi inaltimi/latimi reale
        
        header_height = self.header_frame.winfo_reqheight()
        content_height = self.scrollable_frame.winfo_reqheight()
        
        # Inaltimea elementelor plus padding general
        desired_height = header_height + content_height + 50
        
        # Verificam necesarul de latime
        content_width = self.scrollable_frame.winfo_reqwidth()
        header_width = self.header_frame.winfo_reqwidth()
        desired_width = max(700, max(content_width, header_width) + 60)
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Limitam dimensiunea la inaltimea/latimea ecranului ca sa nu il depaseasca
        window_width = min(desired_width, screen_width - 100)
        window_height = max(250, min(desired_height, screen_height - 150))
        
        center_x = int(screen_width / 2 - window_width / 2)
        center_y = int(screen_height / 2 - window_height / 2)
        
        self.root.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
    
    def add_activity(self):
        """Adauga o noua activitate"""
        dialog = tk.Toplevel(self.root)
        dialog.withdraw() # Ascunde fereastra inainte de a o configura
        dialog.title("Adauga Activitate")
        dialog.resizable(True, True)
        dialog.transient(self.root)
        
        frame = ttk.Frame(dialog, padding="15")
        frame.pack(fill="both", expand=True)
        
        # Nume
        ttk.Label(frame, text="Nume activitate:").pack(anchor=tk.W, pady=(0, 5))
        name_entry = ttk.Entry(frame, width=40)
        name_entry.pack(fill=tk.X, pady=(0, 10), ipadx=5, ipady=4)
        
        # Tag (Combobox/Dropdown)
        ttk.Label(frame, text="Tag:").pack(anchor=tk.W, pady=(0, 5))
        tags_data = {}
        if self.tags_file.exists():
            try:
                with open(self.tags_file, 'r', encoding='utf-8') as f:
                    tags_data = json.load(f)
            except Exception:
                tags_data = {}
                
        display_to_tag = {}
        for k, v in tags_data.items():
            display_str = f"{k} - {v}" if v else k
            display_to_tag[display_str] = k
            
        tag_combo = ttk.Combobox(frame, values=list(display_to_tag.keys()), state="readonly")
        tag_combo.pack(fill=tk.X, pady=(0, 10), ipady=2)

        # Descriere (Text area multi-line)
        ttk.Label(frame, text="Descriere:").pack(anchor=tk.W, pady=(0, 5))
        desc_text = tk.Text(frame, width=40, height=6, font=("Arial", 10))
        desc_text.pack(fill=tk.X, pady=(0, 15))
        
        def save():
            name = name_entry.get().strip()
            display_tag = tag_combo.get().strip()
            tag = display_to_tag.get(display_tag, display_tag)
            desc = desc_text.get("1.0", tk.END).strip()
            
            if not name or not tag or not desc:
                messagebox.showwarning("Atenție", "Te rog introdu numele, tag-ul și descrierea activității.", parent=dialog)
                return
                
            act = Activity(name, tag=tag, description=desc)
            self.activities.append(act)
            self.save_activities()
            self.refresh_activities_ui()
            dialog.destroy()
        # Buton salveaza
        save_btn = ttk.Button(frame, text="Salvează", command=save)
        save_btn.pack(pady=5)
        
        # Bind Enter key
        name_entry.bind("<Return>", lambda e: save())

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
        name_entry.focus()
        dialog.grab_set()
        
    def open_tags_dialog(self):
        """Deschide dialogul pentru salvarea si gestionarea tag-urilor"""
        if hasattr(self, 'tags_dialog') and self.tags_dialog.winfo_exists():
            self.tags_dialog.focus()
            return
            
        self.tags_dialog = tk.Toplevel(self.root)
        self.tags_dialog.title("Gestionare Tags")
        self.tags_dialog.geometry("450x400")
        self.tags_dialog.transient(self.root)
        
        # Frame-ul superior cu butonul de adaugare
        top_frame = ttk.Frame(self.tags_dialog, padding="10")
        top_frame.pack(fill=tk.X)
        
        add_btn = ttk.Button(top_frame, text="➕ Adaugă Tag", command=self.open_tag_editor)
        add_btn.pack(side=tk.LEFT)
        
        # Zona cu lista de tag-uri (canvas + scrollbar)
        self.tags_canvas = tk.Canvas(self.tags_dialog, bg="#f0f0f0", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.tags_dialog, orient="vertical", command=self.tags_canvas.yview)
        self.tags_scrollable_frame = ttk.Frame(self.tags_canvas)
        
        self.tags_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.tags_canvas.configure(scrollregion=self.tags_canvas.bbox("all"))
        )
        
        self.tags_canvas_window = self.tags_canvas.create_window((0, 0), window=self.tags_scrollable_frame, anchor="nw")
        self.tags_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.tags_canvas.pack(side="left", fill="both", expand=True, padx=10, pady=(0, 10))
        scrollbar.pack(side="right", fill="y", pady=(0, 10))
        
        self.tags_canvas.bind("<Configure>", lambda e: self.tags_canvas.itemconfig(self.tags_canvas_window, width=e.width))
        
        # Centram dialogul si populam lista
        self.tags_dialog.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() // 2) - (self.tags_dialog.winfo_width() // 2)
        y = self.root.winfo_rooty() + (self.root.winfo_height() // 2) - (self.tags_dialog.winfo_height() // 2)
        self.tags_dialog.geometry(f"+{x}+{y}")
        
        self.refresh_tags_ui()

    def refresh_tags_ui(self):
        """Reincarca lista de tag-uri afisata in dialog"""
        if not hasattr(self, 'tags_scrollable_frame') or not self.tags_scrollable_frame.winfo_exists():
            return
            
        for widget in self.tags_scrollable_frame.winfo_children():
            widget.destroy()
            
        tags = {}
        if self.tags_file.exists():
            try:
                with open(self.tags_file, 'r', encoding='utf-8') as f:
                    tags = json.load(f)
            except Exception:
                pass
                
        if not tags:
            ttk.Label(self.tags_scrollable_frame, text="Nu există tag-uri salvate.", foreground="gray").pack(pady=20)
            return
            
        for name, desc in tags.items():
            frame = tk.Frame(self.tags_scrollable_frame, highlightbackground="#cccccc", highlightthickness=1)
            frame.pack(fill=tk.X, pady=3, padx=2)
            
            info_frame = ttk.Frame(frame)
            info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
            
            ttk.Label(info_frame, text=name, font=("Arial", 10, "bold")).pack(anchor="w")
            ttk.Label(info_frame, text=desc, font=("Arial", 9), foreground="#555555").pack(anchor="w")
            
            btn_frame = ttk.Frame(frame)
            btn_frame.pack(side=tk.RIGHT, padx=5)
            
            ttk.Button(btn_frame, text="✏️ Edit", command=lambda n=name, d=desc: self.open_tag_editor(n, d)).pack(side=tk.LEFT, padx=2)
            ttk.Button(btn_frame, text="🗑️ Delete", command=lambda n=name: self.delete_tag(n)).pack(side=tk.LEFT, padx=2)

    def open_tag_editor(self, old_name=None, old_desc=None):
        """Deschide fereastra pentru adaugarea sau editarea unui tag"""
        parent_win = self.tags_dialog if hasattr(self, 'tags_dialog') and self.tags_dialog.winfo_exists() else self.root
        editor = tk.Toplevel(parent_win)
        editor.title("Editează Tag" if old_name else "Adaugă Tag")
        editor.resizable(True, True)
        editor.transient(parent_win)
        
        frame = ttk.Frame(editor, padding="15")
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Nume Tag:").grid(row=0, column=0, sticky=tk.W, pady=5)
        name_entry = ttk.Entry(frame, width=30)
        name_entry.grid(row=0, column=1, pady=5, padx=5)
        if old_name:
            name_entry.insert(0, old_name)
        
        ttk.Label(frame, text="Descriere:").grid(row=1, column=0, sticky=tk.W, pady=5)
        desc_entry = ttk.Entry(frame, width=30)
        desc_entry.grid(row=1, column=1, pady=5, padx=5)
        if old_desc:
            desc_entry.insert(0, old_desc)

        def save_tag():
            new_name = name_entry.get().strip()
            new_desc = desc_entry.get().strip()
            
            if not new_name or not new_desc:
                messagebox.showwarning("Atenție", "Te rog introdu atât numele cât și descrierea tag-ului.", parent=editor)
                return
        
            tags = {}
            if self.tags_file.exists():
                try:
                    with open(self.tags_file, 'r', encoding='utf-8') as f:
                        tags = json.load(f)
                except Exception:
                    pass
                    
            # Verificare duplicate cu lowercase
            lower_new_name = new_name.lower()
            for existing_name in tags.keys():
                if lower_new_name == existing_name.lower():
                    # Daca editam fix acelasi tag (posibil sa fi schimbat doar majusculele/descrierea), permitem trecerea
                    if old_name and existing_name.lower() == old_name.lower():
                        continue
                    messagebox.showwarning("Atenție", f"Tag-ul cu numele '{new_name}' (sau similar) există deja!", parent=editor)
                    return
            
            try:
                # Daca este editare si numele s-a schimbat, il stergem pe cel vechi mai intai
                if old_name and old_name in tags and old_name != new_name:
                    del tags[old_name]
                    
                tags[new_name] = new_desc
                
                temp_file = self.tags_file.with_suffix('.json.tmp')
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(tags, f, ensure_ascii=False, indent=2)
                os.replace(temp_file, self.tags_file)
                
                self.refresh_tags_ui()
                editor.destroy()
            except Exception as e:
                messagebox.showerror("Eroare la Salvare", f"Nu am putut salva tag-ul:\n{e}", parent=editor)

        ttk.Button(frame, text="Salvează", command=save_tag).grid(row=2, column=0, columnspan=2, pady=15)
        
        # Centram editorul fata de fereastra parinte
        editor.update_idletasks()
        x = parent_win.winfo_rootx() + (parent_win.winfo_width() // 2) - (editor.winfo_width() // 2)
        y = parent_win.winfo_rooty() + (parent_win.winfo_height() // 2) - (editor.winfo_height() // 2)
        editor.geometry(f"+{x}+{y}")
        
        editor.grab_set()
        name_entry.focus()

    def delete_tag(self, name):
        """Sterge un tag din fisier si din interfata"""
        parent_win = self.tags_dialog if hasattr(self, 'tags_dialog') and self.tags_dialog.winfo_exists() else self.root
        if not messagebox.askyesno("Confirmare", f"Sigur vrei să ștergi tag-ul '{name}'?", parent=parent_win):
            return
            
        tags = {}
        if self.tags_file.exists():
            try:
                with open(self.tags_file, 'r', encoding='utf-8') as f:
                    tags = json.load(f)
            except Exception:
                pass
                
        if name in tags:
            del tags[name]
            try:
                temp_file = self.tags_file.with_suffix('.json.tmp')
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(tags, f, ensure_ascii=False, indent=2)
                os.replace(temp_file, self.tags_file)
                self.refresh_tags_ui()
            except Exception as e:
                messagebox.showerror("Eroare", f"Eroare la ștergerea tag-ului:\n{e}", parent=parent_win)
                
    def open_report_dialog(self):
        """Deschide dialogul pentru generarea unui raport"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Generare raport")
        dialog.geometry("650x500")
        dialog.transient(self.root)
        
        # Calculeaza datele implicite
        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday())
        
        top_frame = ttk.Frame(dialog, padding="10")
        top_frame.pack(fill=tk.X)
        
        ttk.Label(top_frame, text="Dată început (zi-lună-an):").grid(row=0, column=0, padx=5, pady=5)
        start_entry = ttk.Entry(top_frame, width=12)
        start_entry.grid(row=0, column=1, padx=5, pady=5)
        start_entry.insert(0, start_of_week.strftime("%d-%m-%Y"))
        
        ttk.Label(top_frame, text="Dată sfârșit (zi-lună-an):").grid(row=0, column=2, padx=5, pady=5)
        end_entry = ttk.Entry(top_frame, width=12)
        end_entry.grid(row=0, column=3, padx=5, pady=5)
        end_entry.insert(0, today.strftime("%d-%m-%Y"))
        
        text_frame = ttk.Frame(dialog)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        text_area = tk.Text(text_frame, wrap=tk.WORD, font=("Arial", 10))
        scroll = ttk.Scrollbar(text_frame, command=text_area.yview)
        text_area.configure(yscrollcommand=scroll.set)
        
        text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        def generate():
            start_str = start_entry.get().strip()
            end_str = end_entry.get().strip()
            
            try:
                start_date = datetime.strptime(start_str, "%d-%m-%Y")
                end_date = datetime.strptime(end_str, "%d-%m-%Y")
            except ValueError:
                messagebox.showerror("Eroare", "Formatul datelor trebuie să fie zi-lună-an", parent=dialog)
                return
                
            if start_date > end_date:
                messagebox.showerror("Eroare", "Data de start trebuie să fie mai mică sau egală cu data de final.", parent=dialog)
                return
                
            report_data = {}
            
            if self.report_dir.exists():
                for file in self.report_dir.glob("*.json"):
                    file_date_str = file.stem
                    try:
                        file_date = datetime.strptime(file_date_str, "%Y-%m-%d")
                        if start_date <= file_date <= end_date:
                            with open(file, 'r', encoding='utf-8') as f:
                                activities = json.load(f)
                                for act in activities:
                                    tag = act.get("tag", "").strip()
                                    if not tag:
                                        tag = "Fără tag"
                                    
                                    if tag not in report_data:
                                        report_data[tag] = {"total_time": 0, "activities": []}
                                        
                                    report_data[tag]["total_time"] += act.get("total_time", 0)
                                    
                                    day = file_date.day
                                    month_name = ROMANIAN_MONTHS[file_date.month - 1]
                                    year = file_date.year
                                    formatted_date = f"{day} {month_name} {year}"
                                    
                                    report_data[tag]["activities"].append({
                                        "date": formatted_date,
                                        "name": act.get("name", ""),
                                        "time": act.get("total_time", 0),
                                        "desc": act.get("description", "")
                                    })
                    except Exception:
                        continue
            
            text_area.delete("1.0", tk.END)
            
            if not report_data:
                text_area.insert(tk.END, "Nu s-au găsit activități pentru perioada selectată.\n")
                return
            
            def format_dhm(seconds):
                d = int(seconds // 86400)
                h = int((seconds % 86400) // 3600)
                m = int((seconds % 3600) // 60)
                parts = []
                if d == 1: parts.append(f"{d} zi")
                elif d > 1: parts.append(f"{d} zile")
                if h == 1: parts.append(f"{h} oră")
                elif h > 1: parts.append(f"{h} ore")
                if m == 1: parts.append(f"{m} minut")
                elif m > 1 or (d == 0 and h == 0): parts.append(f"{m} minute")
                return " ".join(parts)
            
            # Incarcam descrierile tag-urilor
            tags_descriptions = {}
            if self.tags_file.exists():
                try:
                    with open(self.tags_file, 'r', encoding='utf-8') as f:
                        tags_descriptions = json.load(f)
                except Exception:
                    pass # Ignora daca fisierul e corupt
            
            for tag, data in report_data.items():
                total_str = format_dhm(data["total_time"])
                tag_desc = tags_descriptions.get(tag, "Tag fără descriere")
                text_area.insert(tk.END, f"🏷️ [{tag}] {tag_desc} (Timp total: {total_str})\n", "header")
                for act in data["activities"]:
                    time_str = format_dhm(act["time"])
                    desc = act["desc"] if act["desc"] else "Fără descriere"
                    text_area.insert(tk.END, f"  📅 Ziua: {act['date']} | ⏱️ {time_str}\n")
                    text_area.insert(tk.END, f"  📌 Nume activitate: {act['name']}\n")
                    text_area.insert(tk.END, f"  📝 Descriere activitate: {desc}\n\n")
                text_area.insert(tk.END, "-" * 60 + "\n\n")
                
            text_area.tag_config("header", font=("Arial", 11, "bold"), foreground="#0277bd") # specifica caracteristicile tag-ului header
            text_area.tag_raise("sel") # textul selectat are culoarea alba si fundal albastru
            
        gen_btn = ttk.Button(top_frame, text="Generează", command=generate)
        gen_btn.grid(row=0, column=4, padx=10)
        
        # Centram fereastra
        dialog.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_rooty() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
    
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
        frame = tk.Frame(self.scrollable_frame, highlightbackground=border_color, highlightcolor=border_color, highlightthickness=2)
        frame.pack(fill=tk.X, pady=5, padx=5)
        
        top_frame = ttk.Frame(frame)
        top_frame.pack(fill=tk.X)
        
        # Nume activitate
        name_label = ttk.Label(top_frame, text=f"📌 {activity.name}", font=("Arial", 13, "bold"), foreground="#1565c0")
        name_label.pack(side=tk.LEFT, padx=(10, 5), pady=5)
        
        # Tag activitate (stilizat ca un badge)
        if getattr(activity, 'tag', ""):
            tag_label = tk.Label(top_frame, text=f"🏷️ {activity.tag}", font=("Arial", 9, "bold"), bg="#e0e7ff", fg="#3730a3", padx=8, pady=3)
            tag_label.pack(side=tk.LEFT, padx=(0, 10))
            
            # Caută descrierea tag-ului pentru tooltip
            tag_desc = "Fără descriere"
            if hasattr(self, 'tags_file') and self.tags_file.exists():
                try:
                    with open(self.tags_file, 'r', encoding='utf-8') as f:
                        tags_data = json.load(f)
                        tag_desc = tags_data.get(activity.tag, tag_desc)
                except Exception:
                    pass
            ToolTip(tag_label, f"{tag_desc}")
        
        # Timp curent
        self.activity_widgets[idx] = {
            "activity": activity,
            "frame": frame,
            "time_label": ttk.Label(top_frame, text=f"Total: {format_time(activity.get_current_time())}", font=("Arial", 10))
        }
        self.activity_widgets[idx]["time_label"].pack(side=tk.LEFT, padx=5)
        
        total_text = f"Salvat in raport: {format_time(activity.total_time)}"
        total_label = ttk.Label(top_frame, text=total_text, foreground="blue")
        total_label.pack(side=tk.LEFT, padx=5)
        self.activity_widgets[idx]["total_label"] = total_label
        
        # Buton Start/Stop
        btn_text = "⏹ Stop" if activity.is_running else "▶ Start"
        self.activity_widgets[idx]["timer_btn"] = ttk.Button(
            top_frame,
            text=btn_text,
            command=lambda: self.toggle_timer(idx)
        )
        self.activity_widgets[idx]["timer_btn"].pack(side=tk.LEFT, padx=5, pady=5)
        
        # Buton Edit
        edit_btn = ttk.Button(
            top_frame,
            text="✏️ Editare",
            command=lambda: self.edit_activity(idx)
        )
        edit_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Buton Delete
        delete_btn = ttk.Button(
            top_frame,
            text="🗑 Ștergere",
            command=lambda: self.delete_activity(idx)
        )
        delete_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Descriere (daca exista, impachetata sub restul informatiilor)
        desc_text = getattr(activity, 'description', "").strip()
        if desc_text:
            desc_inner_frame = tk.Frame(frame, bg="#fafafa", padx=10, pady=8, highlightbackground="#e0e0e0", highlightthickness=1)
            desc_inner_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
            
            desc_header = tk.Label(desc_inner_frame, text="📝 Descriere:", font=("Arial", 9, "bold"), bg="#fafafa", fg="#333333", anchor="w")
            desc_header.pack(fill=tk.X, pady=(0, 4))
            
            desc_label = tk.Label(desc_inner_frame, text=desc_text, justify=tk.LEFT, font=("Arial", 9), bg="#fafafa", fg="#555555", anchor="w")
            desc_label.pack(fill=tk.X)
            
            # Modificam wraplength la latimea disponibila in cardul activitatii
            desc_label.bind("<Configure>", lambda e, lbl=desc_label: lbl.configure(wraplength=max(100, e.width - 5)))
    
    def toggle_timer(self, idx):
        """Porneste/opreste timerul pentru o activitate"""
        act = self.activity_widgets[idx]["activity"]
        btn = self.activity_widgets[idx]["timer_btn"]
        frame = self.activity_widgets[idx]["frame"]
        
        if not act.is_running:
            act.start()
            btn.config(text="⏹ Stop")
            frame.config(highlightbackground="#4CAF50", highlightcolor="#4CAF50")
        else:
            act.stop()
            btn.config(text="▶ Start")
            frame.config(highlightbackground="#cccccc", highlightcolor="#cccccc")
            self.save_activities()
    
    def edit_activity(self, idx):
        """Editeaza o activitate existenta"""
        act = self.activities[idx]
        
        dialog = tk.Toplevel(self.root)
        dialog.withdraw() # Ascunde fereastra inainte de a o configura
        dialog.title("Editeaza Activitate")
        dialog.resizable(True, True)
        dialog.transient(self.root)
        
        frame = ttk.Frame(dialog, padding="15")
        frame.pack(fill="both", expand=True)
        
        # Nume
        ttk.Label(frame, text="Nume activitate:").pack(anchor=tk.W, pady=(0, 5))
        name_entry = ttk.Entry(frame, width=40)
        name_entry.pack(fill=tk.X, pady=(0, 10), ipadx=5, ipady=4)
        name_entry.insert(0, act.name)
        
        # Tag (Combobox/Dropdown)
        ttk.Label(frame, text="Tag:").pack(anchor=tk.W, pady=(0, 5))
        tags_data = {}
        if self.tags_file.exists():
            try:
                with open(self.tags_file, 'r', encoding='utf-8') as f:
                    tags_data = json.load(f)
            except Exception:
                tags_data = {}
                
        combo_option_to_tag = {}
        preselect_val = ""
        act_tag = getattr(act, 'tag', "")
        for k, v in tags_data.items():
            combo_option = f"[{k}] {v}" if v else k
            combo_option_to_tag[combo_option] = k
            if k == act_tag:
                preselect_val = combo_option
                
        tag_combo = ttk.Combobox(frame, values=list(combo_option_to_tag.keys()), state="readonly")
        tag_combo.pack(fill=tk.X, pady=(0, 10), ipady=2)
        
        if preselect_val:
            tag_combo.set(preselect_val)
        elif act_tag:
            tag_combo.set(act_tag) # Daca tag-ul a fost sters din tags.json intre timp, tot il afisam

        # Timp total
        ttk.Label(frame, text="Timp total (HH:MM:SS):").pack(anchor=tk.W, pady=(0, 5))
        time_entry = ttk.Entry(frame, width=40)
        time_entry.pack(fill=tk.X, pady=(0, 10), ipadx=5, ipady=4)
        time_entry.insert(0, format_time(act.get_current_time()))

        # Descriere (Text area multi-line)
        ttk.Label(frame, text="Descriere:").pack(anchor=tk.W, pady=(0, 5))
        desc_text = tk.Text(frame, width=40, height=6, font=("Arial", 10))
        desc_text.pack(fill=tk.X, pady=(0, 15))
        desc_text.insert("1.0", getattr(act, 'description', ""))
        
        def save():
            new_name = name_entry.get().strip()
            display_tag = tag_combo.get().strip()
            new_tag = combo_option_to_tag.get(display_tag, display_tag)
            new_time_str = time_entry.get().strip()
            new_desc = desc_text.get("1.0", tk.END).strip()
            
            if not new_name or not new_tag or not new_desc or not new_time_str:
                messagebox.showwarning("Atenție", "Te rog introdu numele, tag-ul, timpul și descrierea activității.", parent=dialog)
                return
                
            try:
                parts = new_time_str.split(':')
                if len(parts) != 3:
                    raise ValueError
                h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
                new_seconds = h * 3600 + m * 60 + s
            except ValueError:
                messagebox.showwarning("Atenție", "Formatul timpului trebuie să fie HH:MM:SS (ex: 01:30:00).", parent=dialog)
                return
                
            # Actualizam datele activitatii in sine
            act.name = new_name
            act.tag = new_tag
            act.description = new_desc
            if act.is_running:
                act.total_time = new_seconds - (time.time() - act.start_time)
            else:
                act.total_time = new_seconds
            
            self.save_activities()
            self.refresh_activities_ui()
            dialog.destroy()
        
        # Buton salveaza
        save_btn = ttk.Button(frame, text="Salvează", command=save)
        save_btn.pack(pady=5)
        
        # Bind Enter key pe entry-ul de nume
        name_entry.bind("<Return>", lambda e: save())

        # --- Logica de centrare ---
        dialog.update_idletasks()
        parent_x = self.root.winfo_rootx()
        parent_y = self.root.winfo_rooty()
        parent_width = self.root.winfo_width()
        parent_height = self.root.winfo_height()

        dialog_width = dialog.winfo_width()
        dialog_height = dialog.winfo_height()

        x = parent_x + (parent_width // 2) - (dialog_width // 2)
        y = parent_y + (parent_height // 2) - (dialog_height // 2)
        dialog.geometry(f"+{x}+{y}")

        dialog.deiconify()
        name_entry.focus()
        dialog.grab_set()

    def delete_activity(self, idx):
        """Sterge o activitate"""
        if messagebox.askyesno("Confirma", "Esti sigur ca doresti sa stergi aceasta activitate?"):
            del self.activities[idx]
            self.save_activities()
            self.refresh_activities_ui()
    
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
        self.resizable(True, True)
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
    # Separăm aplicația de procesul Python standard pentru ca Windows
    # să afișeze iconița nativă Tkinter (sau custom) în taskbar
    try:
        app_id = 'timetracker.app.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass

    root = tk.Tk()
    root.withdraw()  # Ascunde fereastra principala initial
    if getattr(sys, 'frozen', False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).parent.parent
        
    report_dir = base_dir / "report"
    report_dates = get_report_dates(report_dir)

    dialog = StartupDialog(root, report_dates)
    selected_date = dialog.result

    if selected_date:
        app = TimeTrackerApp(root, selected_date=selected_date)
        root.deiconify()  # Arata fereastra principala
        root.mainloop()
    else:
        root.destroy()