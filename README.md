# Time Tracker Application

O aplicație Python cu interfață grafică pentru urmărirea activităților și a timpului alocat.

## Funcționalități

✅ **Adauga activități** - Apasă butonul "➕ Adauga Activitate" și introdu numele activității
✅ **Timer pe activitate** - Apasă "▶ Start" pentru a porni și "⏹ Stop" pentru a opri cronometrul
✅ **Auto-save** - Salvează automat la fiecare 5 minute
✅ **Salvare la închidere** - La închiderea aplicației, timpul curent este oprit și salvat automat
✅ **Rapoarte zilnice** - Folderul `./report` conține fișier JSON cu timp alocat per activitate per zi
✅ **Reîncărcare la pornire** - Dacă exista raport pentru astazi, activitățile sunt reîncărcate

## Structura Folderelor

```
Time tracker/
├── src/
│   └── main.py              # Aplicația principală
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
    "total_time": 3600.5
  },
  {
    "name": "Intalniri",
    "total_time": 1800.25
  }
]
```

## Comenzi Principale

- **➕ Adauga Activitate** - Deschide dialog pentru a adăuga activitate nouă
- **▶ Start / ⏹ Stop** - Pornească/oprește cronometrul pentru o activitate
- **👁 Ascunde/Arata Total** - Comută vizibilitatea timpului total
- **💾 Salveaza** - Salvează manual raportul
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
