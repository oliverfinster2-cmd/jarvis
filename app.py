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
- befehl: "WEBSEITE", parameter: "Suchbegriff oder URL" (du gibst immer die beste URL zurück)
- befehl: "SUCHEN", parameter: "Suchbegriff"
- befehl: "PC_AKTION", parameter: "shutdown" / "lock" / "restart" / "logout"
- befehl: "TERMIN", parameter: "Datum|Uhrzeit|Beschreibung" z.B. "2026-05-25|14:00|Zahnarzt"
- befehl: "WOCHENPLAN", parameter: ""
- befehl: "DOKUMENT", parameter: "pdf|Titel|Inhalt" oder "word|Titel|Inhalt" oder "excel|Titel|Inhalt"
- befehl: "ANTWORT", parameter: ""

Webseiten-Regeln (bei WEBSEITE immer die echte URL zurückgeben):
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
- Unbekannte Seiten → "https://www.google.de/search?q=SEITENNAME"

PC-Aktionen:
- "herunterfahren" / "ausschalten" → PC_AKTION, shutdown
- "sperren" / "bildschirm sperren" → PC_AKTION, lock
- "neu starten" → PC_AKTION, restart
- "abmelden" → PC_AKTION, logout

Speichern-Regeln (speichern: true nur wenn wichtig):
- Termine, Projekte, To-Dos, Namen, wichtige Infos → speichern: true
- "öffne google", "wie alt ist die Erde", kleine Fragen → speichern: false

Apps:
- "minecraft" → APP_OEFFNEN, minecraft
- "discord" → APP_OEFFNEN, discord
- "steam" / "zocken" → APP_OEFFNEN, steam
- "spotify" / "musik" → APP_OEFFNEN, spotify

Antworte NUR mit dem JSON Objekt, niemals mit Text davor oder danach."""

conversation_history = []
custom_shortcuts = {}
memory = []

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '').strip()

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

    # Memory in Kontext einbauen
    memory_context = ""
    if memory:
        memory_context = f"\n\nGespeicherte wichtige Infos:\n" + "\n".join(memory[-10:])

    conversation_history.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT + memory_context},
            *conversation_history
        ],
        max_tokens=500
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

    # Wichtiges speichern
    if result.get("speichern"):
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
        memory.append(f"[{timestamp}] {user_message}")

    return jsonify(result)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
