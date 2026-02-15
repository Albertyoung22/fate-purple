
import os
import json
import requests
import sys
import threading
import logging
import subprocess
import time
from datetime import datetime
from flask import Flask, request, jsonify, make_response, send_file, Response, stream_with_context, send_from_directory
from flask_cors import CORS
import lunar_python
from lunar_python import Lunar, Solar
from master_book import MASTER_BOOK
from rule_engine import create_chart_from_dict, evaluate_rules, PALACE_NAMES

# --- Configuration & Constants Loading ---

def load_config():
    config_path = 'config.json'
    defaults = {
        "server": {"host": "0.0.0.0", "port": 5000, "debug": False},
        "ollama": {"api_url": "http://localhost:11434/api/generate", "default_model": "gemma2:2b"},
        "gemini": {"api_key": "", "model": "gemini-2.5-flash"},
        "app": {"title": "紫微八字 · 天機命譜系統", "geometry": "1000x750", "icon_path": "icon.png"}
    }
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                for k, v in user_config.items():
                    if k in defaults and isinstance(v, dict):
                        defaults[k].update(v)
                    else:
                        defaults[k] = v
        except Exception as e:
            print(f"Error loading config.json: {e}")
    return defaults

def load_constants():
    const_path = 'ziwei_constants.json'
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

# --- Backend Logic & Data Management ---

CHAT_LOG_FILE = 'chat_history.json'
RECORD_FILE = 'user_records.json'

def load_json_file(filename):
    if not os.path.exists(filename):
        return []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_json_file(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def log_chat(model, prompt, response):
    logs = load_json_file(CHAT_LOG_FILE)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "model": model,
        "prompt": prompt,
        "response": response
    }
    logs.append(entry)
    if len(logs) > 1000:
        logs = logs[-1000:]
    save_json_file(CHAT_LOG_FILE, logs)

# --- App Globals ---
app = Flask(__name__)
# Enable CORS for all domains to allow proxy/remote access easily
CORS(app) 

OLLAMA_API_URL = CONFIG['ollama']['api_url']
DEFAULT_MODEL = CONFIG['ollama']['default_model']
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or CONFIG['gemini'].get('api_key', "")
GEMINI_MODEL = CONFIG['gemini'].get('model', "gemini-2.5-flash")

STEMS = CONSTANTS['STEMS']
BRANCHES = CONSTANTS['BRANCHES']
SI_HUA_TABLE = CONSTANTS['SI_HUA_TABLE']

def call_gemini_api(prompt, system_prompt="", stream=True):
    """呼叫 Google Gemini API 的通用函式"""
    if not GEMINI_API_KEY:
        return None
    
    full_prompt = f"{system_prompt}\n\n{prompt}"
    url = f"https://generativelanguage.googleapis.com/v1/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "temperature": CONFIG['gemini'].get('temperature', 0.7),
            "maxOutputTokens": CONFIG['gemini'].get('max_output_tokens', 1024),
        }
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 429:
                raise requests.exceptions.HTTPError("429 Too Many Requests", response=response)
            
            response.raise_for_status()
            data = response.json()
            return data['candidates'][0]['content']['parts'][0]['text']
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                wait_time = (attempt + 1) * 3
                print(f"Gemini API 429 (Attempt {attempt+1}). Retry in {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                print(f"Gemini API Fail: {e}")
                return None
        except Exception as e:
            print(f"Gemini API Error: {e}")
            return None
    return None

def get_current_year_ganzhi():
    """Calculates the Heavenly Stem and Earthly Branch for the current year."""
    now = datetime.now()
    year = now.year
    if now.month < 2 or (now.month == 2 and now.day < 4):
        year -= 1
    stem_idx = (year - 4) % 10
    branch_idx = (year - 4) % 12
    return STEMS[stem_idx], BRANCHES[branch_idx]

def detect_intent_and_context(prompt, chart_data):
    instructions = ""
    injected_data = ""
    prompt_lower = prompt.lower()
    
    topics = {
        "studies": {
            "keywords": ["學業", "考試", "成績", "升學", "唸書", "讀書", "考運"],
            "focus": "官祿宮、父母宮、文昌、文曲、化科、魁鉞",
            "instruction": "專注於分析緣主的【學業與考運】。請重點查看官祿宮氣數，以及文昌、文曲、化科等星曜的分布。若有凶星干擾，請給予化解之建議。"
        },
        "wealth": {
            "keywords": ["財運", "賺錢", "投資", "股票", "彩券", "薪水", "收入", "破財"],
            "focus": "財帛宮、田宅宮、福德宮、祿存、化祿、武曲、太陰、貪狼",
            "instruction": "專注於分析緣主的【財運與投資】。請重點查看財帛宮強弱、田宅宮守財能力，並尋找祿存、化祿等財星。請直斷正財與偏財機運。"
        },
        "love": {
            "keywords": ["感情", "婚姻", "桃花", "另一半", "對象", "結婚", "離婚", "分手"],
            "focus": "夫妻宮、福德宮、紅鸞、天喜、貪狼、廉貞、太陽、太陰",
            "instruction": "專注於分析緣主的【感情與婚姻】。請察看夫妻宮之穩定性，以及紅鸞、天喜等桃花星。若有化忌或煞星，請點出感情可能的波折。"
        },
        "career": {
            "keywords": ["事業", "工作", "升遷", "創業", "職場", "老闆", "轉職", "官祿"],
            "focus": "官祿宮、奴僕宮、紫微、太陽、廉貞、武曲、天相",
            "instruction": "專注於分析緣主的【事業與職場發展】。請分析官祿宮格局，判斷適合創業或任職，並查看奴僕宮有沒有貴人或小人。"
        },
        "health": {
            "keywords": ["健康", "疾病", "身體", "開刀", "意外", "血光", "生病"],
            "focus": "疾厄宮、命宮、災煞、天刑、羊陀、化忌",
            "instruction": "專注於分析緣主的【健康狀況】。請細查疾厄宮與命宮之煞星，特別注意五行過旺或過弱之處，提醒預防潛在疾病。"
        },
        "parents": {
            "keywords": ["父母", "爸爸", "媽媽", "雙親", "六親", "長輩"],
            "focus": "父母宮、兄弟宮(母宮)、太陽(父)、太陰(母)",
            "instruction": "專注於分析緣主的【父母親情】。請查看父母宮與兄弟宮，判斷與雙親之緣分深淺與刑剋。"
        },
        "bazi": {
            "keywords": ["八字", "子平", "五行", "日主", "喜用", "十神", "算命"],
            "focus": "四柱八字、日主強弱、喜用神、流年干支、十神生剋",
            "instruction": "請啟動【子平八字】論命模式。重點分析「日主強弱」、「格局高低」與「喜用神」。請依據四柱干支的沖刑合害，論斷緣主的一生運勢起伏。請務必結合「流年干支」與本命的互動。"
        }
    }
    
    found_topic = False
    for key, val in topics.items():
        if any(kw in prompt_lower for kw in val["keywords"]):
            instructions += f"\n【重點主題】：{val['instruction']}\n(請忽略與此主題無關的雜訊，針對{val['focus']}進行深度論斷)\n"
            found_topic = True
            
    temporal_keywords = ["流年", "今年", "運勢", "明年", "202"] 
    is_temporal = any(kw in prompt_lower for kw in temporal_keywords)
    is_bazi = any(kw in prompt_lower for kw in topics["bazi"]["keywords"])

    if (is_temporal or "年" in prompt or not found_topic) and not is_bazi: 
        y_stem, y_branch = get_current_year_ganzhi()
        sihua = SI_HUA_TABLE.get(y_stem, {})
        liu_nian_palace_name = "未知"
        liu_nian_stars = []
        if chart_data:
            for palace in chart_data:
                if palace.get('zhi') == y_branch:
                    liu_nian_palace_name = palace.get('name', '流年命宮')
                    liu_nian_stars = palace.get('stars', [])
                    break
        
        injected_data += f"\n【流年天機資訊 (系統自動推演)】\n"
        injected_data += f"● 當下年份：{y_stem}{y_branch}年\n"
        injected_data += f"● 流年命宮：位於【{y_branch}宮】(本命{liu_nian_palace_name})\n"
        injected_data += f"● 流年四化：\n"
        injected_data += f"  - 祿：{sihua.get('lu')} (化祿)\n"
        injected_data += f"  - 權：{sihua.get('quan')} (化權)\n"
        injected_data += f"  - 科：{sihua.get('ke')} (化科)\n"
        injected_data += f"  - 忌：{sihua.get('ji')} (化忌)\n"
        
        if is_temporal:
            instructions += "\n【時空運勢指令】：緣主詢問關於流年或特定時間的運勢。請務必結合上述「流年命宮」與「流年四化」進行推演。流年四化對運勢影響甚鉅，請特別著墨。\n"

    return instructions, injected_data

def _build_cors_preflight_response():
    resp = make_response()
    resp.headers.add("Access-Control-Allow-Origin", "*")
    resp.headers.add("Access-Control-Allow-Headers", "*")
    resp.headers.add("Access-Control-Allow-Methods", "*")
    return resp

def _corsify_actual_response(resp):
    resp.headers.add("Access-Control-Allow-Origin", "*")
    return resp

# --- Routes ---

@app.route('/')
def index():
    print("Root route accessed.")
    if os.path.exists('fate.html'):
        return send_file('fate.html')
    return "Error: fate.html not found", 404

@app.route('/<path:filename>')
def serve_static(filename):
    # Expanded allowed extensions
    if filename.lower().endswith(('.png', '.ico', '.jpg', '.jpeg', '.html', '.css', '.js', '.json', '.map')):
        if os.path.exists(filename):
            return send_file(filename)
    return "File Not Found", 404

@app.route('/api/save_record', methods=['POST', 'OPTIONS'])
def save_record():
    if request.method == 'OPTIONS': return _build_cors_preflight_response()
    data = request.json or {}
    print(f"接收到存檔請求: {data.get('name')}")
    record = {
        "timestamp": datetime.now().isoformat(), "name": data.get("name", "Unknown"),
        "gender": data.get("gender"), "birth_date": data.get("birth_date"),
        "birth_hour": data.get("birth_hour"), "lunar_date": data.get("lunar_date")
    }
    records_file = RECORD_FILE
    records = []
    if os.path.exists(records_file):
        try:
            with open(records_file, 'r', encoding='utf-8') as f: records = json.load(f)
        except: pass
    records.append(record)
    with open(records_file, 'w', encoding='utf-8') as f: json.dump(records, f, ensure_ascii=False, indent=2)
    return _corsify_actual_response(jsonify({"success": True}))

@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS': return _build_cors_preflight_response()
    
    data = request.json or {}
    user_prompt = data.get('prompt', '')
    client_system_prompt = data.get('system_prompt', '')
    model = data.get('model', DEFAULT_MODEL)
    chart_data = data.get('chart_data')
    gender = data.get('gender', 'M')
    
    if not user_prompt: 
        return _corsify_actual_response(jsonify({"error": "No prompt provided"})), 400
    
    options = data.get('options', {})
    
    print(f"收到 AI 請求: {user_prompt[:20]}...")
    
    matched_results = []
    if chart_data:
        try:
            print("正在執行紫微規則引擎檢測...")
            rule_file = "ziwei_rules.json"
            rules = []
            if os.path.exists(rule_file):
                with open(rule_file, 'r', encoding='utf-8') as f:
                    rules = json.load(f)
            
            chart = create_chart_from_dict(chart_data, gender=gender)
            matched_results = evaluate_rules(chart, rules)
            print(f"規則引擎命中 {len(matched_results)} 條規則。")
        except Exception as e:
            print(f"規則引擎執行失敗: {e}")

    full_system_prompt = f"""你是【紫微天機道長】，一位修道多年的命理宗師。
    
【絕對任務】：請根據緣主提供的【紫微斗數命盤】與【八字資訊】，進行專業的命理批註。
【禁止行為】：
1. 禁止分析緣主的「寫作風格」或「論述方式」。緣主提供的文字是「命盤數據」與「算命指令」，不是文章作品。
2. 禁止反問緣主問題（如「請告訴我更多...」）。命盤已在眼前，請直接論斷。
3. 禁止使用英文。必須使用純正的【台灣繁體中文】。

【角色設定】：
1. **鐵口直斷**：吉凶禍福直接點出，不模稜兩可。
2. **引經據典**：引用《紫微心法》與《四柱八字》口訣佐證。
3. **慈悲指引**：在點出凶象後，必須給予改運建議。

{client_system_prompt}

【紫微心法秘卷】
{MASTER_BOOK}

請開始為緣主批命。"""

    prompt_context = user_prompt
    try:
        intent_instructions, injected_data = detect_intent_and_context(user_prompt, chart_data)
        if injected_data:
            prompt_context += injected_data
        if intent_instructions:
            full_system_prompt += intent_instructions
    except Exception as e:
        print(f"意圖偵測失敗: {e}")

    def generate_unified_response():
        is_daily_query = "錦囊" in (user_prompt + client_system_prompt)
        is_full_report = any(kw in (user_prompt + client_system_prompt) for kw in ["詳評", "命譜詳評", "格局報告"])

        def call_ai_engine(target_prompt, target_system_prompt):
            if GEMINI_API_KEY:
                res = call_gemini_api(target_prompt, target_system_prompt)
                if res:
                    chunk_size = 3
                    for i in range(0, len(res), chunk_size):
                        yield res[i:i+chunk_size]
                        time.sleep(0.01)
                    return True
            
            ai_payload = {
                "model": model,
                "prompt": target_prompt,
                "system": target_system_prompt,
                "stream": True,
                "options": options
            }
            try:
                endpoint = OLLAMA_API_URL
                with requests.post(endpoint, json=ai_payload, stream=True, timeout=(10, 300)) as r:
                    r.raise_for_status()
                    for line in r.iter_lines():
                        if line:
                            chunk = json.loads(line)
                            if "response" in chunk:
                                yield chunk["response"]
                return True
            except Exception as e:
                print(f"Ollama Fallback Error: {e}")
                return False

        if is_daily_query:
            yield "【大師感應中...】正在為您抽取今日錦囊，請稍候...\n\n"
            short_system_prompt = "你是一位精通紫微斗數的決策宗師。你的任務是針對【流日命宮】給予一句精要錦囊。禁止分析格局，禁止廢話，字數100字內，強制繁體中文。"
            summary_prompt = f"請根據以下流日數據給予今日錦囊：\n{user_prompt}"
            if (yield from call_ai_engine(summary_prompt, short_system_prompt)): return

        is_karma_query = "前世今生故事模式" in (user_prompt + client_system_prompt) or \
                         any(kw in user_prompt for kw in ["前世", "因果", "業力", "輪迴"])
        if is_karma_query:
            yield "【三世因果解碼報告】\n------------------------------------------\n"
            karma_system_prompt = """你是一位精通三世因果的紫微通靈大師。
請略過世俗的財富地位分析，專注解讀命盤中的【福德宮】(靈魂前世)、【命宮】(今生業力) 與【身宮】(執行模式)。
請以「說故事」的方式，為緣主勾勒出一幅前世今生的因果圖像。語氣需神秘。字數300字。"""
            if (yield from call_ai_engine(f"{user_prompt}", karma_system_prompt)): return

        is_ritual_query = any(kw in (user_prompt + client_system_prompt) for kw in ["轉運", "改運", "儀式", "佈局"])
        if is_ritual_query:
            yield "【道家轉運開運儀式】\n------------------------------------------\n"
            ritual_system_prompt = "你是一位精通堪輿與道家科儀的開運大師。請設計轉運儀式。字數300字。"
            if (yield from call_ai_engine(f"{user_prompt}", ritual_system_prompt)): return
            
        is_dream_query = any(kw in (user_prompt + client_system_prompt) for kw in ["解夢", "夢境", "夢到"])
        if is_dream_query:
            yield "【紫微潛意識夢境解碼】\n------------------------------------------\n"
            dream_system_prompt = "你是一位結合心理學與紫微斗數的夢境解析師。請解讀夢境。字數300字。"
            if (yield from call_ai_engine(f"{user_prompt}", dream_system_prompt)): return

        is_bazi_query = any(kw in (user_prompt + client_system_prompt) for kw in ["八字", "子平", "算命", "五行", "日主"])
        if is_bazi_query and not is_full_report:
            import re
            yield "【子平八字精批】\n------------------------------------------\n"
            clean_prompt = user_prompt
            if "【全盤星系配置】" in clean_prompt:
                clean_prompt = re.sub(r"【全盤星系配置】：.*?【八字四柱資訊】", "【八字四柱資訊】", clean_prompt, flags=re.DOTALL)
            bazi_system_prompt = "你是一位精通《子平八字》的命理宗師。禁止提及紫微斗數。純粹分析八字。字數400字。"
            if (yield from call_ai_engine(f"{clean_prompt}", bazi_system_prompt)): return
            
        is_love_query = any(kw in (user_prompt + client_system_prompt) for kw in ["桃花", "姻緣", "感情", "戀愛", "脫單", "攻略"])
        if is_love_query:
            yield "【紫微戀愛桃花攻略】\n------------------------------------------\n"
            love_system_prompt = "你是一位精通紫微合婚與戀愛心理的兩性導師。請提供桃花戀愛攻略。字數300字。"
            if (yield from call_ai_engine(f"{user_prompt}", love_system_prompt)): return

        is_finance_query = any(kw in (user_prompt + client_system_prompt) for kw in ["投資", "理財", "財運", "股票", "房產"])
        if is_finance_query:
            yield "【紫微財運投資佈局】\n------------------------------------------\n"
            finance_system_prompt = "你是一位精通紫微斗數的財富管理大師。請提供投資理財建議。字數300字。"
            if (yield from call_ai_engine(f"{user_prompt}", finance_system_prompt)): return

        # --- Default / Full Report ---
        if matched_results and is_full_report:
            yield "【天機運算中...】大師正在詳批您的命盤與格局，請稍候...\n\n"
            yield "【紫微命譜格局偵測報告】\nUse logic as rule descriptions:\n"
            
            group_a = [r for r in matched_results if r.get("rule_group") == "A"]
            group_b = [r for r in matched_results if r.get("rule_group") == "B"]
            group_c = [r for r in matched_results if r.get("rule_group") == "C"]

            if group_a:
                yield "一、 星曜坐守與神煞特徵\n------------------------------------------\n"
                for res in group_a: yield f"● 【{res.get('detected_palace_names', '全盤')}】{res.get('description')}：{res.get('text')}\n"
                yield "\n"
            if group_b:
                yield "二、 命宮宮干飛化\n------------------------------------------\n"
                for res in group_b: yield f"● 【{res.get('detected_palace_names', '命宮飛入')}】{res.get('description')}：{res.get('text')}\n"
                yield "\n"
            if group_c:
                yield "三、 宮位間的交互飛化\n------------------------------------------\n"
                for res in group_c: yield f"● 【{res.get('detected_palace_names', '關聯宮位')}】{res.get('description')}：{res.get('text')}\n"
                yield "\n"
            
            yield f"{'='*40}\n\n四、道長綜合結論\n------------------------------------------\n"
        
        rules_context_str = ""
        if matched_results:
            for r in matched_results[:25]: 
                rules_context_str += f"- {r.get('description')}：{r.get('text')}\n"
        
        summary_prompt = f"""請根據以下【命盤原始數據】與【格局偵測報告】，為緣主進行最終的【命譜詳評與運勢預測】。
【命盤原始數據】：{user_prompt}
【偵測格局】：{rules_context_str}
【指令】：綜合论断。"""
        
        if (yield from call_ai_engine(summary_prompt, full_system_prompt)): return
        
        # Fallback raw Ollama if Gemini failed inside prompt construction (unlikely to reach here if Gemini worked)
        ai_payload = {
            "model": model,
            "prompt": summary_prompt,
            "system": full_system_prompt,
            "stream": True,
            "options": options
        }
        try:
            endpoint = OLLAMA_API_URL
            with requests.post(endpoint, json=ai_payload, stream=True, timeout=(10, 300)) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        if "response" in chunk:
                            yield chunk["response"]
        except Exception as e:
            yield f"\n[Error: {e}]"

    return Response(stream_with_context(generate_unified_response()), content_type='text/plain; charset=utf-8', headers={
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive"
    })

if __name__ == '__main__':
    # Use environment variable for port or default to 5000
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Headless FatePurple Server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=CONFIG['server']['debug'])
