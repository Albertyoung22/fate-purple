
import os
import json
import requests
import sys
import logging
import time
from datetime import datetime
from flask import Flask, request, jsonify, make_response, send_file, Response, stream_with_context, send_from_directory
from flask_cors import CORS
import lunar_python
from lunar_python import Lunar, Solar
try:
    import google.generativeai as genai
except ImportError:
    genai = None

from master_book import MASTER_BOOK
from rule_engine import create_chart_from_dict, evaluate_rules, PALACE_NAMES

# --- Configuration & Constants Loading ---
def load_config():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, 'config.json')
    defaults = {
        "server": {"host": "0.0.0.0", "port": 5000, "debug": False},
        "gemini": {"provider": "groq", "api_key": "", "model": "llama-3.3-70b-versatile", "temperature": 0.7, "max_output_tokens": 1024}
    }
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                for k, v in user_config.items():
                    if k in defaults and isinstance(v, dict): defaults[k].update(v)
                    else: defaults[k] = v
        except Exception as e:
            print(f"Error loading config.json: {e}")
    return defaults

def load_constants():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    const_path = os.path.join(base_dir, 'ziwei_constants.json')
    defaults = {
        "STEMS": ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"],
        "BRANCHES": ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"],
        "SI_HUA_TABLE": {}
    }
    if os.path.exists(const_path):
        try:
            with open(const_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                defaults.update(data)
        except Exception as e:
            print(f"Error loading ziwei_constants.json: {e}")
    return defaults

CONFIG = load_config()
CONSTANTS = load_constants()
STEMS = CONSTANTS['STEMS']
BRANCHES = CONSTANTS['BRANCHES']
SI_HUA_TABLE = CONSTANTS['SI_HUA_TABLE']

# --- App Initialization ---
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# Use Environment Variables primarily for Render deployment
AI_PROVIDER = os.environ.get("AI_PROVIDER") or CONFIG['gemini'].get('provider', 'groq')
AI_API_KEY = os.environ.get("AI_API_KEY") or CONFIG['gemini'].get('api_key', "")
AI_MODEL = os.environ.get("AI_MODEL") or CONFIG['gemini'].get('model', "llama-3.3-70b-versatile")

RECORD_FILE = 'user_records.json'

# --- AI Engine Callers ---
def call_groq_api(prompt, system_prompt="", stream=False):
    try:
        from groq import Groq
        client = Groq(api_key=AI_API_KEY)
        completion = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=CONFIG['gemini'].get('temperature', 0.7),
            max_completion_tokens=CONFIG['gemini'].get('max_output_tokens', 1024),
            stream=stream
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Groq API Error: {e}")
        return None

def call_gemini_api(prompt, system_prompt="", stream=False):
    if not genai: return "Error: Gemini SDK not installed"
    try:
        genai.configure(api_key=AI_API_KEY)
        model = genai.GenerativeModel(AI_MODEL)
        full_prompt = f"{system_prompt}\n\n{prompt}"
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return None

# --- Routes ---
@app.route('/')
def index():
    return send_file('fate.html')

@app.route('/<path:filename>')
def serve_static(filename):
    if filename.lower().endswith(('.png', '.ico', '.jpg', '.jpeg', '.html', '.css', '.js', '.json')):
        if os.path.exists(filename):
            return send_file(filename)
    return "Not Found", 404

@app.route('/api/save_record', methods=['POST', 'OPTIONS'])
def save_record():
    if request.method == 'OPTIONS': return _corsify_actual_response(make_response())
    data = request.json or {}
    record = {
        "timestamp": datetime.now().isoformat(),
        "name": data.get("name", "Unknown"),
        "gender": data.get("gender"),
        "birth_date": data.get("birth_date"),
        "birth_hour": data.get("birth_hour"),
        "lunar_date": data.get("lunar_date")
    }
    records = []
    if os.path.exists(RECORD_FILE):
        try:
            with open(RECORD_FILE, 'r', encoding='utf-8') as f: records = json.load(f)
        except: pass
    records.append(record)
    with open(RECORD_FILE, 'w', encoding='utf-8') as f: json.dump(records, f, ensure_ascii=False, indent=2)
    return _cors_resp({"success": True})

def _corsify_actual_response(resp):
    resp.headers.add("Access-Control-Allow-Origin", "*")
    return resp

def _cors_resp(data):
    return _corsify_actual_response(jsonify(data))

@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS': return _corsify_actual_response(make_response())
    
    data = request.json or {}
    user_prompt = data.get('prompt', '')
    client_system_prompt = data.get('system_prompt', '')
    gender = data.get('gender', 'M')
    chart_data = data.get('chart_data')

    matched_results = []
    if chart_data:
        try:
            chart = create_chart_from_dict(chart_data, gender=gender)
            rule_file = "ziwei_rules.json"
            if os.path.exists(rule_file):
                with open(rule_file, 'r', encoding='utf-8') as f:
                    rules = json.load(f)
                    matched_results = evaluate_rules(chart, rules)
        except Exception as e:
            print(f"Rule Engine Error: {e}")

    full_system_prompt = f"""你是【紫微天機道長】，一位修道多年的命理宗師。\n{client_system_prompt}\n【紫微心法秘卷】\n{MASTER_BOOK}"""

    def generate_unified_response():
        is_full_report = any(kw in (user_prompt + client_system_prompt) for kw in ["詳評", "命譜詳評", "格局報告"])
        
        def call_ai_engine_internal(target_prompt, target_system_prompt):
            if AI_PROVIDER == 'groq':
                res = call_groq_api(target_prompt, target_system_prompt)
            else:
                res = call_gemini_api(target_prompt, target_system_prompt)
            if res: yield res

        if matched_results and is_full_report:
            yield "【天機連線成功...】大師正在開啟法眼，為您批註命譜...\n\n"
            group_titles = {"A": "【第一章：星曜坐守與神煞特徵】", "B": "【第二章：命宮宮干飛化】", "C": "【第三章：宮位間的交互飛化】"}
            explanation_system_prompt = "你是一位精通紫微斗數與子平八字的命理宗師。請結合整體命盤，針對章節中的格局進行整合性、權威性的白話解析。強制繁體中文，字數 150 字。"
            
            for g_code, g_title in group_titles.items():
                g_results = [r for r in matched_results if r.get("rule_group") == g_code]
                if g_results:
                    yield f"\n{g_title}\n" + "-"*30 + "\n"
                    rules_text = ""
                    for res in g_results[:12]:
                        p_name = res.get('detected_palace_names', '全盤')
                        yield f"● 【{p_name}】{res.get('description')}：{res.get('text')}\n"
                        rules_text += f"● 【{p_name}】{res.get('description')}：{res.get('text')}\n"
                    
                    yield "\n💡大師章節詳解："
                    yield from call_ai_engine_internal(f"章節格局：\n{rules_text}\n\n整體數據：\n{user_prompt}", explanation_system_prompt)
                    yield "\n"

            yield "\n" + "="*40 + "\n"
            yield "【紫微天機 · 終極命判總結】\n"
            yield from call_ai_engine_internal(f"綜合以上所有格局，為緣主做一個最終的命運詳解與建議：\n{user_prompt}", full_system_prompt)
            return

        yield from call_ai_engine_internal(user_prompt, full_system_prompt)

    return Response(stream_with_context(generate_unified_response()), content_type='text/plain; charset=utf-8')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
