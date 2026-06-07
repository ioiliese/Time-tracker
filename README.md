# Time Tracker Application

O aplicație Python cu interfață grafică pentru urmărirea activităților și a timpului alocat.

## Funcționalități

✅ **Adaugă activități** - Apasă butonul "➕ Adauga Activitate" și introdu numele, tag-ul și descrierea activității
✅ **Editare activități** - Modifică detaliile (nume, tag, descriere) pentru activitățile deja create direct din listă
✅ **Gestionare Tag-uri** - Creează, editează și șterge tag-uri personalizate (descrierea tagului este afișată atunci când cursorul este plasat deasupra tagului unei activități)
✅ **Rapoarte Avansate** - Generează rapoarte detaliate pe intervale de date, grupate pe tag-uri, cu timp total calculat
✅ **Timer pe activitate** - Apasă "▶ Start" pentru a porni și "⏹ Stop" pentru a opri cronometrul
✅ **Auto-save** - Salvează automat la fiecare 5 minute
✅ **Salvare la închidere** - La închiderea aplicației, timpul curent este oprit și salvat automat
✅ **Rapoarte zilnice** - Folderul `./report` conține fișier JSON cu timp alocat per activitate per zi
✅ **Selectează ziua de lucru** - La deschidere aplicației, poți alege să continui cu ziua curentă sau să încarci o sesiune din istoric

## Structura Folderelor

```
Time tracker/
├── src/
│   └── main.py              # Aplicația principală
├── tags_for_activities/
│   └── tags.json            # Fișierul cu tag-urile și descrierile acestora
├── report/                   # Rapoarte zilnice în format JSON
├── python/                   # Python 3.12.4 instalat local
├── .venv/                    # Mediul virtual Python
├── run_app.ps1              # Script de pornire aplicație
├── start_app.bat            # Executabil cu dublu-click pentru pornire
└── requirements.txt         # Dependințe Python
```

## Cum Să Pornești Aplicația
```deschide un terminal nou in folderul curent si ruleaza
.\start_app.bat
```

## Format Rapoarte Zilnice

Fișierele sunt salvate în `./report` cu formatul `YYYY-MM-DD.json`:

```json
[
  {
    "name": "Proiect ABC",
    "tag": "Dezvoltare",
    "description": "Implementare feature X",
    "total_time": 3600.5
  }
]
```

## Comenzi Principale

- **➕ Adauga Activitate** - Deschide dialog pentru a adăuga activitate nouă
- **🏷️ Taguri activități** - Deschide managerul de tag-uri (creare, editare, ștergere)
- **📊 Generare Raport** - Generează un raport agregat pe un interval de timp (DD-MM-YYYY)
- **▶ Start / ⏹ Stop** - Pornească/oprește cronometrul pentru o activitate
- **✏️ Edit** - Editează numele, tag-ul și descrierea unei activități
- **🗑 Delete** - Șterge o activitate

## Configurație Mediu

- **Python:** 3.12.4
- **GUI Framework:** tkinter (inclus)
- **Format Date:** YYYY-MM-DD (ISO 8601)
- **Auto-save:** 5 minute

## Notă

- Aplicația folosește firul daemon pentru auto-save, nu va bloca interfața
- Timpurile sunt stocate în secunde cu precizie
- Orice activitate pornită va fi actualizată si afisată in timp real (100ms refresh rate)
