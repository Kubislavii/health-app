# Krevní testy

Jednoduchá lokální webová aplikace pro sledování výsledků krevních odběrů.

## Spuštění

```bash
pip install -r requirements.txt
python app.py
```

Aplikace poběží na **http://localhost:5000**

## Funkce

- **Přehled** — tabulka všech výsledků, hodnoty mimo normu zvýrazněny červeně
- **Přidat** — formulář pro zadání nového výsledku odběru
- **Graf** — vývoj vybraného parametru v čase s vyznačeným referenčním rozmezím

## Přístup z telefonu

Aplikace naslouchá na `0.0.0.0`, takže je dostupná z jakéhokoli zařízení na stejné síti. Otevřete `http://<IP-adresa-počítače>:5000` v prohlížeči na telefonu.
