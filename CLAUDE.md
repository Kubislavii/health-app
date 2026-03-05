# Krevní testy

## Project Overview
Lokální webová aplikace v češtině pro sledování výsledků krevních odběrů.
Tech stack: Python Flask + SQLite + Chart.js (v4, CDN).

## Structure
- `app.py` — Flask backend, SQLite inicializace, API routes
- `templates/base.html` — layout, navigace (Přehled / Přidat / Graf)
- `templates/index.html` — přehled výsledků, tlačítko "Nový odběr", inline editace hodnot, odkaz na graf u parametrů
- `templates/add.html` — formulář pro přidání odběru (nový den i přidání k existujícímu datu)
- `templates/graph.html` — graf parametru v čase, auto-select přes URL hash
- `static/style.css` — styly
- `static/script.js` — Chart.js logika pro graf, referenční pásmo (fill target "+1"), auto-select z URL hash
- `data/` — SQLite databáze (vytvoří se automaticky)

## Key UX details
- Přehled: zelené tlačítko "+ Nový odběr" nahoře, u každého parametru ikonka grafu (odkaz na `/graph#Parametr`)
- Graf: referenční pásmo vykresleno jako šedá výplň mezi ref_min a ref_max (Chart.js fill object syntax)
- Graf: při navigaci z přehledu se parametr automaticky vybere podle URL hash

## How to run
```bash
pip install -r requirements.txt
python app.py
```
Runs on http://localhost:5000
