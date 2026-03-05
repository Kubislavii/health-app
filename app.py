import os
import io
import base64
import json
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, jsonify
from dotenv import load_dotenv

load_dotenv()

import anthropic
import fitz  # pymupdf
from PIL import Image

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "krevni_testy.db")

ANTHROPIC_CLIENT = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Předdefinované parametry s referenčními hodnotami
PREDEFINED_PARAMS = [
    # Krevní obraz
    {"name": "Leukocyty (WBC)", "unit": "×10⁹/l", "ref_min": 4.0, "ref_max": 10.0, "category": "Krevní obraz"},
    {"name": "Erytrocyty (RBC)", "unit": "×10¹²/l", "ref_min": 4.0, "ref_max": 5.8, "category": "Krevní obraz"},
    {"name": "Hemoglobin (HGB)", "unit": "g/l", "ref_min": 135, "ref_max": 175, "category": "Krevní obraz"},
    {"name": "Hematokrit (HCT)", "unit": "", "ref_min": 0.40, "ref_max": 0.54, "category": "Krevní obraz"},
    {"name": "Trombocyty (PLT)", "unit": "×10⁹/l", "ref_min": 150, "ref_max": 400, "category": "Krevní obraz"},
    {"name": "MCV", "unit": "fl", "ref_min": 82, "ref_max": 98, "category": "Krevní obraz"},
    {"name": "MCH", "unit": "pg", "ref_min": 28, "ref_max": 34, "category": "Krevní obraz"},
    {"name": "MCHC", "unit": "g/l", "ref_min": 320, "ref_max": 360, "category": "Krevní obraz"},
    # Biochemie – játra
    {"name": "ALT", "unit": "µkat/l", "ref_min": 0.1, "ref_max": 0.78, "category": "Jaterní testy"},
    {"name": "AST", "unit": "µkat/l", "ref_min": 0.05, "ref_max": 0.72, "category": "Jaterní testy"},
    {"name": "GGT", "unit": "µkat/l", "ref_min": 0.14, "ref_max": 0.84, "category": "Jaterní testy"},
    {"name": "ALP", "unit": "µkat/l", "ref_min": 0.66, "ref_max": 2.20, "category": "Jaterní testy"},
    {"name": "Bilirubin celkový", "unit": "µmol/l", "ref_min": 2, "ref_max": 17, "category": "Jaterní testy"},
    # Biochemie – ledviny
    {"name": "Kreatinin", "unit": "µmol/l", "ref_min": 62, "ref_max": 106, "category": "Ledviny"},
    {"name": "Urea", "unit": "mmol/l", "ref_min": 2.8, "ref_max": 8.0, "category": "Ledviny"},
    {"name": "Kyselina močová", "unit": "µmol/l", "ref_min": 200, "ref_max": 420, "category": "Ledviny"},
    # Biochemie – metabolismus
    {"name": "Glykémie (GLU)", "unit": "mmol/l", "ref_min": 3.33, "ref_max": 5.59, "category": "Metabolismus"},
    {"name": "Celkový cholesterol", "unit": "mmol/l", "ref_min": 2.9, "ref_max": 5.0, "category": "Lipidy"},
    {"name": "HDL cholesterol", "unit": "mmol/l", "ref_min": 1.0, "ref_max": 2.1, "category": "Lipidy"},
    {"name": "LDL cholesterol", "unit": "mmol/l", "ref_min": 0, "ref_max": 3.0, "category": "Lipidy"},
    {"name": "Triglyceridy", "unit": "mmol/l", "ref_min": 0.45, "ref_max": 1.7, "category": "Lipidy"},
    # Minerály
    {"name": "Sodík (Na)", "unit": "mmol/l", "ref_min": 136, "ref_max": 145, "category": "Minerály"},
    {"name": "Draslík (K)", "unit": "mmol/l", "ref_min": 3.5, "ref_max": 5.1, "category": "Minerály"},
    {"name": "Chloridy (Cl)", "unit": "mmol/l", "ref_min": 98, "ref_max": 107, "category": "Minerály"},
    {"name": "Vápník (Ca)", "unit": "mmol/l", "ref_min": 2.15, "ref_max": 2.55, "category": "Minerály"},
    {"name": "Železo (Fe)", "unit": "µmol/l", "ref_min": 11.6, "ref_max": 31.3, "category": "Minerály"},
    # Záněty
    {"name": "CRP", "unit": "mg/l", "ref_min": 0, "ref_max": 5, "category": "Zánětlivé markery"},
    # Štítná žláza
    {"name": "TSH", "unit": "mIU/l", "ref_min": 0.27, "ref_max": 4.20, "category": "Štítná žláza"},
    {"name": "fT4", "unit": "pmol/l", "ref_min": 12, "ref_max": 22, "category": "Štítná žláza"},
    {"name": "fT3", "unit": "pmol/l", "ref_min": 3.1, "ref_max": 6.8, "category": "Štítná žláza"},
]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS blood_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            parameter TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT NOT NULL,
            ref_min REAL,
            ref_max REAL,
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


@app.route("/")
def index():
    conn = get_db()
    results = conn.execute(
        "SELECT * FROM blood_tests ORDER BY date DESC, parameter"
    ).fetchall()
    conn.close()

    # Group results by date
    grouped = {}
    for r in results:
        d = r["date"]
        if d not in grouped:
            grouped[d] = []
        grouped[d].append(dict(r))

    return render_template("index.html", grouped=grouped)


@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        date = request.form["date"]
        note = request.form.get("note", "").strip() or None
        conn = get_db()

        # Process predefined parameters
        for i, param in enumerate(PREDEFINED_PARAMS):
            value_key = f"value_{i}"
            if value_key in request.form and request.form[value_key].strip():
                conn.execute(
                    """INSERT INTO blood_tests (date, parameter, value, unit, ref_min, ref_max, note)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        date,
                        param["name"],
                        float(request.form[value_key]),
                        param["unit"],
                        param["ref_min"],
                        param["ref_max"],
                        note,
                    ),
                )

        # Process custom parameters
        custom_names = request.form.getlist("custom_name[]")
        custom_values = request.form.getlist("custom_value[]")
        custom_units = request.form.getlist("custom_unit[]")
        custom_ref_mins = request.form.getlist("custom_ref_min[]")
        custom_ref_maxs = request.form.getlist("custom_ref_max[]")

        for j in range(len(custom_names)):
            if custom_names[j].strip() and custom_values[j].strip():
                conn.execute(
                    """INSERT INTO blood_tests (date, parameter, value, unit, ref_min, ref_max, note)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        date,
                        custom_names[j].strip(),
                        float(custom_values[j]),
                        custom_units[j].strip() if custom_units[j].strip() else "",
                        float(custom_ref_mins[j]) if custom_ref_mins[j].strip() else None,
                        float(custom_ref_maxs[j]) if custom_ref_maxs[j].strip() else None,
                        note,
                    ),
                )

        conn.commit()
        conn.close()
        return redirect(url_for("index"))

    # Group params by category
    categories = {}
    for i, p in enumerate(PREDEFINED_PARAMS):
        cat = p["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append({"index": i, **p})

    return render_template("add.html", categories=categories)


@app.route("/add-to-date/<date>")
def add_to_date(date):
    """Show add form pre-filled with a specific date for adding more values."""
    conn = get_db()
    existing = conn.execute(
        "SELECT parameter FROM blood_tests WHERE date = ?", (date,)
    ).fetchall()
    conn.close()
    existing_params = {r["parameter"] for r in existing}

    categories = {}
    for i, p in enumerate(PREDEFINED_PARAMS):
        cat = p["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append({"index": i, "existing": p["name"] in existing_params, **p})

    return render_template("add.html", categories=categories, prefill_date=date)


@app.route("/graph")
def graph():
    return render_template("graph.html")


@app.route("/api/results")
def api_results():
    conn = get_db()
    results = conn.execute(
        "SELECT * FROM blood_tests ORDER BY date DESC, parameter"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in results])


@app.route("/api/parameters")
def api_parameters():
    conn = get_db()
    rows = conn.execute(
        "SELECT DISTINCT parameter FROM blood_tests ORDER BY parameter"
    ).fetchall()
    conn.close()
    return jsonify([r["parameter"] for r in rows])


@app.route("/api/results/<parameter>")
def api_results_by_parameter(parameter):
    conn = get_db()
    results = conn.execute(
        "SELECT * FROM blood_tests WHERE parameter = ? ORDER BY date",
        (parameter,),
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in results])


@app.route("/upload", methods=["GET"])
def upload():
    return render_template("upload.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    """Přijme soubor, pošle do Claude, vrátí extrahovaná data jako JSON."""
    if "file" not in request.files or request.files["file"].filename == "":
        return jsonify({"error": "Nebyl vybrán žádný soubor."}), 400

    file = request.files["file"]
    filename = file.filename.lower()

    try:
        images_b64 = []  # seznam (base64, media_type)

        if filename.endswith(".pdf"):
            # Konverze každé stránky PDF na PNG
            pdf_bytes = file.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page in doc:
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("png")
                images_b64.append((base64.b64encode(img_bytes).decode(), "image/png"))
            doc.close()
        else:
            # Obrázek – resize na max 2000px po delší straně
            img = Image.open(file.stream)
            img.thumbnail((2000, 2000), Image.LANCZOS)
            buf = io.BytesIO()
            fmt = "PNG" if filename.endswith(".png") else "JPEG"
            media_type = "image/png" if fmt == "PNG" else "image/jpeg"
            img.save(buf, format=fmt)
            images_b64.append((base64.b64encode(buf.getvalue()).decode(), media_type))

        extracted = extract_blood_test_from_images(images_b64)
        return jsonify(extracted)

    except Exception as e:
        return jsonify({"error": f"Chyba při zpracování souboru: {str(e)}"}), 500


def extract_blood_test_from_images(images_b64):
    """Odešle obrázky do Claude a vrátí strukturovaný JSON s výsledky."""
    prompt = """Jsi asistent pro analýzu výsledků krevních odběrů.
Analyzuj přiložený obrázek (nebo obrázky) a extrahuj všechny laboratorní parametry.

Vrať POUZE validní JSON v tomto formátu (bez markdown backticks, bez komentářů):
{
  "date": "YYYY-MM-DD nebo null pokud datum není viditelné",
  "results": [
    {
      "parameter": "název parametru",
      "value": číslo,
      "unit": "jednotka",
      "ref_min": číslo nebo null,
      "ref_max": číslo nebo null
    }
  ]
}

Pravidla:
- Hodnoty musí být čísla (float), ne řetězce
- Pokud je referenční rozsah ve formátu "2.5 - 5.0", extrahuj ref_min=2.5 a ref_max=5.0
- Pokud referenční rozsah chybí, nastav ref_min a ref_max na null
- Zahrni VŠECHNY parametry z odběru, i méně běžné
- Datum formátuj jako YYYY-MM-DD"""

    # Sestavení zprávy s jedním nebo více obrázky
    content = []
    for b64_data, media_type in images_b64:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": b64_data,
            }
        })
    content.append({"type": "text", "text": prompt})

    response = ANTHROPIC_CLIENT.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": content}]
    )

    raw_text = response.content[0].text.strip()
    # Odstraň případné markdown fences
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
    return json.loads(raw_text)


@app.route("/api/save-extracted", methods=["POST"])
def api_save_extracted():
    """Uloží ověřená extrahovaná data z review screen do DB."""
    data = request.get_json()
    date = data.get("date")
    results = data.get("results", [])

    if not date:
        return jsonify({"error": "Chybí datum odběru."}), 400

    conn = get_db()
    saved = 0
    for r in results:
        if not r.get("parameter") or r.get("value") is None:
            continue
        try:
            conn.execute(
                """INSERT INTO blood_tests (date, parameter, value, unit, ref_min, ref_max)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    date,
                    r["parameter"],
                    float(r["value"]),
                    r.get("unit", ""),
                    float(r["ref_min"]) if r.get("ref_min") is not None else None,
                    float(r["ref_max"]) if r.get("ref_max") is not None else None,
                ),
            )
            saved += 1
        except (ValueError, TypeError):
            continue
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "saved": saved})


@app.route("/api/delete/<int:result_id>", methods=["POST"])
def api_delete(result_id):
    conn = get_db()
    conn.execute("DELETE FROM blood_tests WHERE id = ?", (result_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/update/<int:result_id>", methods=["POST"])
def api_update(result_id):
    data = request.get_json()
    conn = get_db()
    conn.execute(
        "UPDATE blood_tests SET value = ? WHERE id = ?",
        (float(data["value"]), result_id),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5001, debug=True)
