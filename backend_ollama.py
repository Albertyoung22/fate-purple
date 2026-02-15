import os
import json
import requests
from flask import Flask, request, jsonify, make_response, send_file

app = Flask(__name__)

# Ollama Configuration
OLLAMA_API_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "gemma2:2b"

def _build_cors_preflight_response():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "*")
    response.headers.add("Access-Control-Allow-Methods", "*")
    return response

def _corsify_actual_response(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

@app.route('/')
def index():
    return send_file('fate.html')

from datetime import datetime

@app.route('/api/save_record', methods=['POST', 'OPTIONS'])
def save_record():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()

    data = request.json or {}
    record = {
        "timestamp": datetime.now().isoformat(),
        "name": data.get("name", "Unknown"),
        "gender": data.get("gender"),
        "birth_date": data.get("birth_date"),
        "birth_hour": data.get("birth_hour"),
        "lunar_date": data.get("lunar_date")
    }

    records_file = 'user_records.json'
    records = []
    if os.path.exists(records_file):
        try:
            with open(records_file, 'r', encoding='utf-8') as f:
                records = json.load(f)
        except:
            pass
    
    records.append(record)
    
    # Save to JSON
    with open(records_file, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    # Save to Excel
    try:
        import pandas as pd
        df = pd.DataFrame(records)
        # Rename columns for better readability in Excel
        df.rename(columns={
            "timestamp": "紀錄時間",
            "name": "姓名",
            "gender": "性別",
            "birth_date": "國曆生日",
            "birth_hour": "時辰(支)",
            "lunar_date": "農曆日期"
        }, inplace=True)
        df.to_excel('user_records.xlsx', index=False, engine='openpyxl')
    except Exception as e:
        print(f"Failed to save Excel: {e}")
        
    return _corsify_actual_response(jsonify({"success": True}))

from master_book import MASTER_BOOK

@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()

    data = request.json or {}
    user_prompt = data.get('prompt', '')
    client_system_prompt = data.get('system_prompt', '')
    model = data.get('model', DEFAULT_MODEL)

    if not user_prompt:
        return _corsify_actual_response(jsonify({"error": "No prompt provided"})), 400

    # Inject MASTER_BOOK into the system prompt securely on the server side
    full_system_prompt = f"IMPORTANT: You must respond in Traditional Chinese (繁體中文). Do NOT use Simplified Chinese or English.\n\n{client_system_prompt}\n\n【紫微心法秘卷】\n{MASTER_BOOK}\n\nIMPORTANT: You must respond in Traditional Chinese (繁體中文). Do NOT use Simplified Chinese or English."

    payload = {
        "model": model,
        "prompt": user_prompt + "\n\n(請務必使用繁體中文 Traditional Chinese 回答)",
        "system": full_system_prompt,
        "stream": False
    }

    try:
        print(f"Sending request to Ollama: {model}")
        response = requests.post(OLLAMA_API_URL, json=payload)
        response.raise_for_status()
        result = response.json()
        ai_text = result.get('response', '')
        
        return _corsify_actual_response(jsonify({"success": True, "text": ai_text}))

    except requests.exceptions.RequestException as e:
        print(f"Ollama Connection Error: {e}")
        return _corsify_actual_response(jsonify({"error": "Failed to connect to Ollama", "details": str(e)})), 503
    except Exception as e:
        print(f"Error: {e}")
        return _corsify_actual_response(jsonify({"error": "Internal Server Error", "details": str(e)})), 500

if __name__ == '__main__':
    print("Starting FatePurple Ollama Backend (CORS fixes applied)...")
    app.run(host='0.0.0.0', port=5000, debug=True)
