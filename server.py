from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static')
CORS(app)

# Configuration
API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not API_KEY:
    raise ValueError("Missing DEEPSEEK_API_KEY in .env file")

API_URL = "https://api.deepseek.com/v1/chat/completions"

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        if not data or "prompt" not in data:
            return jsonify({"error": "Missing prompt"}), 400
            
        prompt = data["prompt"].strip()
        if not prompt:
            return jsonify({"error": "Empty prompt"}), 400

        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [{
                "role": "user", 
                "content": f"Complete these song lyrics dont tell the user what ur doing just do it dont use emojis dont show verse 1 or anything like that just 1-2 min rap song: {prompt}"
            }],
            "temperature": 0.7,
            "max_tokens": 200
        }

        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        return jsonify({"lyrics": result["choices"][0]["message"]["content"]})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8888, debug=True)
