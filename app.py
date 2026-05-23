from flask import Flask, request, jsonify
from groq import Groq
import os
import json

app = Flask(__name__)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SYSTEM_PROMPT = """Du bist Jarvis, ein KI-Assistent der einen Windows PC steuert.
Der Benutzer spricht Deutsch. Antworte immer auf Deutsch.

Antworte IMMER mit einem JSON-Objekt in diesem Format:
{
  "antwort": "Was du dem Benutzer sagst (kurz und präzise)",
  "befehl": "BEFEHL_TYP",
  "parameter": "parameter"
}

Mögliche Befehle:
- befehl: "APP_OEFFNEN", parameter: "chrome" / "minecraft" / "discord" / "steam" / "spotify" / "notepad" / "explorer"
- befehl: "WEBSEITE", parameter: "https://youtube.com"
- befehl: "SUCHEN", parameter: "Suchbegriff"
- befehl: "ORDNER_ERSTELLEN", parameter: "C:/Users/Pfad/Ordnername"
- befehl: "ANTWORT", parameter: "" (nur für Fragen ohne PC-Aktion)

Wichtige Zuordnungen:
- "youtube" / "YouTube" → befehl: "WEBSEITE", parameter: "https://www.youtube.com"
- "google" / "Google" → befehl: "WEBSEITE", parameter: "https://www.google.de"
- "netflix" / "Film schauen" → befehl: "WEBSEITE", parameter: "https://www.netflix.com"
- "minecraft" → befehl: "APP_OEFFNEN", parameter: "minecraft"
- "discord" → befehl: "APP_OEFFNEN", parameter: "discord"
- "steam" / "zocken" → befehl: "APP_OEFFNEN", parameter: "steam"
- "spotify" / "musik" → befehl: "APP_OEFFNEN", parameter: "spotify"
- Wissensfragen (wie lange leben Elefanten etc.) → befehl: "ANTWORT", parameter: ""

Antworte NUR mit dem JSON Objekt, niemals mit normalem Text davor oder danach."""

conversation_history = []
custom_shortcuts = {}

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return jsonify({"antwort": "Ich habe nichts gehört.", "befehl": "ANTWORT", "parameter": ""})

    # Abkürzung speichern
    if 'merke dir:' in user_message.lower() or 'speichere:' in user_message.lower():
        parts = user_message.split('=')
        if len(parts) == 2:
            key = parts[0].replace('merke dir:', '').replace('speichere:', '').strip().lower()
            value = parts[1].strip()
            custom_shortcuts[key] = value
            return jsonify({
                "antwort": f"Verstanden! Ich merke mir: {key} bedeutet {value}",
                "befehl": "ANTWORT",
                "parameter": ""
            })
    
    # Abkürzung prüfen
    for key, value in custom_shortcuts.items():
        if key in user_message.lower():
            user_message = value
            break

    conversation_history.append({
        "role": "user",
        "content": user_message
    })
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *conversation_history
        ],
        max_tokens=300
    )
    
    assistant_message = response.choices[0].message.content.strip()
    
    conversation_history.append({
        "role": "assistant",
        "content": assistant_message
    })
    
    if len(conversation_history) > 20:
        conversation_history.pop(0)
        conversation_history.pop(0)
    
    # JSON aus Antwort extrahieren
    try:
        # Falls Markdown-Backticks dabei sind
        clean = assistant_message.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean)
    except:
        result = {
            "antwort": assistant_message,
            "befehl": "ANTWORT",
            "parameter": ""
        }
    
    return jsonify(result)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
