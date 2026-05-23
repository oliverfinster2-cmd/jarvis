from flask import Flask, request, jsonify
from groq import Groq
import os
import json

app = Flask(__name__)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SYSTEM_PROMPT = """Du bist Jarvis, ein KI-Assistent der einen Windows PC steuert.
Der Benutzer spricht Deutsch. Antworte immer auf Deutsch.

Wenn der Benutzer etwas tun möchte, antworte mit einem JSON-Objekt in diesem Format:
{
  "antwort": "Was du dem Benutzer sagst",
  "befehl": "BEFEHL_TYP",
  "parameter": "parameter"
}

Mögliche Befehle:
- befehl: "APP_OEFFNEN", parameter: "chrome" / "minecraft" / "discord" / "steam" / "spotify" / "notepad" / "explorer"
- befehl: "WEBSEITE", parameter: "https://youtube.com"
- befehl: "SUCHEN", parameter: "Suchbegriff"
- befehl: "ORDNER_ERSTELLEN", parameter: "C:/Users/Pfad/Ordnername"
- befehl: "NICHTS", parameter: ""

Wenn der Benutzer sagt "ich will einen Film schauen" → öffne Netflix
Wenn der Benutzer sagt "ich will zocken" → öffne Steam
Wenn der Benutzer sagt "musik" → öffne Spotify
Wenn der Benutzer sagt "youtube" → öffne YouTube

Merke dir auch eigene Abkürzungen die der Benutzer dir beibringt.
Antworte NUR mit dem JSON, nichts anderes."""

conversation_history = []
custom_shortcuts = {}

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    
    # Abkürzung speichern
    if 'merke dir:' in user_message.lower() or 'speichere:' in user_message.lower():
        parts = user_message.split('=')
        if len(parts) == 2:
            key = parts[0].replace('merke dir:', '').replace('speichere:', '').strip().lower()
            value = parts[1].strip()
            custom_shortcuts[key] = value
            return jsonify({
                "antwort": f"Verstanden! Ich merke mir: {key} = {value}",
                "befehl": "NICHTS",
                "parameter": ""
            })
    
    # Abkürzung prüfen
    for key, value in custom_shortcuts.items():
        if key in user_message.lower():
            user_message = value
    
    conversation_history.append({
        "role": "user",
        "content": user_message
    })
    
    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *conversation_history
        ],
        max_tokens=500
    )
    
    assistant_message = response.choices[0].message.content
    conversation_history.append({
        "role": "assistant", 
        "content": assistant_message
    })
    
    # Nur letzte 20 Nachrichten behalten
    if len(conversation_history) > 20:
        conversation_history.pop(0)
        conversation_history.pop(0)
    
    try:
        result = json.loads(assistant_message)
    except:
        result = {
            "antwort": assistant_message,
            "befehl": "NICHTS",
            "parameter": ""
        }
    
    return jsonify(result)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
