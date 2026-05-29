from flask import Flask, request, jsonify
from groq import Groq
import os
import json
from datetime import datetime

app = Flask(__name__)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SYSTEM_PROMPT = """Du bist Jarvis, ein KI-Assistent der einen Windows PC steuert.
Der Benutzer spricht Deutsch. Antworte immer auf Deutsch.

Antworte IMMER mit einem JSON-Objekt in diesem Format:
{
  "antwort": "Was du dem Benutzer sagst (kurz und präzise)",
  "befehl": "BEFEHL_TYP",
  "parameter": "parameter",
  "speichern": true/false
}

Mögliche Befehle:
- befehl: "APP_OEFFNEN", parameter: "chrome" / "minecraft" / "discord" / "steam" / "spotify" / "notepad" / "explorer"
- befehl: "APP_SCHLIESSEN", parameter: "chrome" / "discord" / "spotify" / "steam" / "minecraft"
- befehl: "WEBSEITE", parameter: "vollständige URL"
- befehl: "SUCHEN", parameter: "Suchbegriff"
- befehl: "PC_AKTION", parameter: "shutdown" / "lock" / "restart" / "logout"
- befehl: "TERMIN", parameter: "Datum|Uhrzeit|Beschreibung" z.B. "2026-05-25|14:00|Zahnarzt"
- befehl: "WOCHENPLAN", parameter: ""
- befehl: "DOKUMENT_SCHREIBEN", parameter: "pdf|Titel|VOLLSTAENDIGER TEXT MIT ABSAETZEN"
- befehl: "DOKUMENT_SCHREIBEN", parameter: "word|Titel|VOLLSTAENDIGER TEXT MIT ABSAETZEN"
- befehl: "DOKUMENT_SCHREIBEN", parameter: "excel|Titel|Zeile1;Zeile2;Zeile3"
- befehl: "SELF_UPGRADE", parameter: "Wunsch des Benutzers z.B. Timer einbauen"
- befehl: "ANTWORT", parameter: ""

Webseiten (immer echte URL zurückgeben):
- "youtube" → "https://www.youtube.com"
- "google" → "https://www.google.de"
- "netflix" → "https://www.netflix.com"
- "tiktok" → "https://www.tiktok.com"
- "twitter" / "x" → "https://www.x.com"
- "instagram" → "https://www.instagram.com"
- "reddit" → "https://www.reddit.com"
- "github" → "https://www.github.com"
- "twitch" → "https://www.twitch.tv"
- "amazon" → "https://www.amazon.de"
- "spotify" (Webseite) → "https://www.spotify.com"
- Unbekannte Seiten → "https://www.google.de/search?q=SEITENNAME"

PC-Aktionen:
- "herunterfahren" / "ausschalten" → PC_AKTION, shutdown
- "sperren" → PC_AKTION, lock
- "neu starten" → PC_AKTION, restart
- "abmelden" → PC_AKTION, logout

Dokumente erstellen (WICHTIG):
- Wenn der Benutzer ein Dokument will, schreibe den VOLLSTÄNDIGEN TEXT selbst
- Mindestens 100-200 Wörter wenn gewünscht
- Verwende \\n für Absätze
- Beispiel parameter: "pdf|Schule|Die Schule ist ein wichtiger Ort...\\n\\nAbsatz 2..."
- Bei Excel: Zeilen mit Semikolon trennen z.B. "excel|Budget|Name;Betrag\\nEssen;200\\nMiete;500"

Self-Upgrade:
- Wenn der Benutzer sagt "verbessere dich", "upgrade", "entwickle dich weiter", "update dich" → SELF_UPGRADE
- parameter = der konkrete Wunsch des Benutzers (z.B. "Timer einbauen", "Lautstärke fixen")
- Falls kein konkreter Wunsch: parameter = ""

Speichern (speichern: true nur wenn wichtig):
- Termine, Projekte, Namen → speichern: true
- Kleine Fragen, Apps öffnen → speichern: false

Antworte NUR mit dem JSON Objekt, niemals mit Text davor oder danach."""

conversation_history = []
custom_shortcuts = {}
memory = []
termine = []

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '').strip()
    extra_termine = data.get('termine', [])

    if extra_termine:
        termine.clear()
        termine.extend(extra_termine)

    if not user_message:
        return jsonify({"antwort": "Ich habe nichts gehört.", "befehl": "ANTWORT", "parameter": "", "speichern": False})

    # Abkürzung speichern
    if 'merke dir:' in user_message.lower() or 'speichere:' in user_message.lower():
        parts = user_message.split('=')
        if len(parts) == 2:
            key = parts[0].replace('merke dir:', '').replace('speichere:', '').strip().lower()
            value = parts[1].strip()
            custom_shortcuts[key] = value
            return jsonify({
                "antwort": f"Verstanden! {key} = {value}",
                "befehl": "ANTWORT",
                "parameter": "",
                "speichern": False
            })

    # Abkürzung prüfen
    for key, value in custom_shortcuts.items():
        if key in user_message.lower():
            user_message = value
            break

    # Memory + Termine in Kontext
    extra_context = ""
    if memory:
        extra_context += "\n\nWichtige gespeicherte Infos:\n" + "\n".join(memory[-10:])
    if termine:
        extra_context += "\n\nGespeicherte Termine:\n" + "\n".join(
            [f"- {t['datum']} {t['uhrzeit']}: {t['beschreibung']}" for t in termine]
        )

    conversation_history.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT + extra_context},
            *conversation_history
        ],
        max_tokens=1500
    )

    assistant_message = response.choices[0].message.content.strip()
    conversation_history.append({"role": "assistant", "content": assistant_message})

    if len(conversation_history) > 20:
        conversation_history.pop(0)
        conversation_history.pop(0)

    try:
        clean = assistant_message.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean)
    except:
        result = {"antwort": assistant_message, "befehl": "ANTWORT", "parameter": "", "speichern": False}

    if result.get("speichern"):
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
        memory.append(f"[{timestamp}] {user_message}")

    return jsonify(result)


UPGRADE_SYSTEM_PROMPT = """Du bist ein Python-Experte und verbesserst Jarvis, einen lokalen KI-Assistenten für Windows.

Du bekommst den aktuellen Python-Code von jarvis.py und einen optionalen Wunsch.

Antworte AUSSCHLIESSLICH mit einem JSON-Objekt (kein Text davor/danach, keine Backticks):
{
  "patches": [
    {
      "suchen": "EXAKTER TEXT DER IM CODE STEHT (mehrzeilig erlaubt)",
      "ersetzen": "NEUER TEXT DER EINGESETZT WIRD",
      "beschreibung": "Was diese Änderung macht"
    }
  ],
  "beschreibung": "Gesamtzusammenfassung in 2 Sätzen",
  "aenderungen": ["Änderung 1", "Änderung 2"]
}

REGELN:
- Maximal 5 Patches pro Aufruf
- "suchen" muss EXAKT im Code vorkommen (copy-paste aus dem Code)
- "suchen" muss eindeutig sein (nicht zu kurz)
- Keine kompletten Funktionen ersetzen wenn nur kleine Änderung nötig
- Kommentare auf Deutsch
- Bei Version-String: v2.0 → v2.1 etc.

Bekannte Bugs (Priorität wenn kein konkreter Wunsch):
1. TIMER fehlt komplett → füge Timer-Befehl in befehl_ausfuehren() ein
2. APP_OEFFNEN: Chrome nicht im PATH → füge echte Pfade als Fallback hinzu:
   C:/Program Files/Google/Chrome/Application/chrome.exe
   C:/Program Files (x86)/Google/Chrome/Application/chrome.exe
3. LAUTSTAERKE fehlt → nutze PowerShell als Fallback"""


@app.route('/upgrade', methods=['POST'])
def upgrade():
    """Empfängt aktuellen jarvis.py Code, gibt Patches zurück die lokal angewendet werden."""
    data = request.json
    aktueller_code = data.get('code', '')
    wunsch         = data.get('wunsch', '')
    version        = data.get('version', '?')

    if not aktueller_code:
        return jsonify({"error": "Kein Code empfangen"}), 400

    wunsch_text = ""
    if wunsch:
        wunsch_text = f"\n\nKONKRETER WUNSCH (Priorität):\n{wunsch}"

    # Nur die relevanten Teile des Codes schicken um Tokens zu sparen
    # Wir schicken Funktionsnamen + ersten 8000 Zeichen als Überblick
    code_preview = aktueller_code[:6000] + "\n\n[... weiterer Code ...]\n\n" + aktueller_code[-2000:]

    user_message = f"jarvis.py (Version {version}):\n\n{code_preview}{wunsch_text}"

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": UPGRADE_SYSTEM_PROMPT},
                {"role": "user",   "content": user_message}
            ],
            max_tokens=4000,
            temperature=0.2
        )

        antwort = response.choices[0].message.content.strip()
        clean = antwort.replace("```json", "").replace("```", "").strip()

        # JSON-Start finden falls LLM Text davor schreibt
        start = clean.find("{")
        if start > 0:
            clean = clean[start:]

        result = json.loads(clean)

        # Patches auf den Code anwenden
        patches     = result.get("patches", [])
        code        = aktueller_code
        angewendet  = []
        fehlgeschlagen = []

        for patch in patches:
            suchen   = patch.get("suchen", "")
            ersetzen = patch.get("ersetzen", "")
            beschr   = patch.get("beschreibung", "")

            if suchen and suchen in code:
                code = code.replace(suchen, ersetzen, 1)
                angewendet.append(beschr)
            else:
                fehlgeschlagen.append(beschr)

        if fehlgeschlagen:
            result["fehlgeschlagen"] = fehlgeschlagen

        result["code"]       = code
        result["angewendet"] = angewendet
        return jsonify(result)

    except json.JSONDecodeError:
        return jsonify({"error": f"JSON-Parse-Fehler: {antwort[:300]}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "endpoints": ["/chat", "/upgrade", "/health"]})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
