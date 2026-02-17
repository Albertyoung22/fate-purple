
import os
import json
import requests
import sys
import threading
import webbrowser
import logging
import subprocess
import time

# --- GUI Support Check ---
try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox
    HAS_TK = True
except ImportError:
    HAS_TK = False
    print("Tkinter not found (Headless environment detected). GUI will be disabled.")
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, make_response, send_file, Response, stream_with_context, send_from_directory
from flask_cors import CORS
import lunar_python
from lunar_python import Lunar, Solar

# --- FORCE IPV4 PATCH (Gemini Connectivity Fix) ---
import google.generativeai as genai
import socket
import urllib3.util.connection as urllib3_cn

def allowed_gai_family():
    return socket.AF_INET
urllib3_cn.allowed_gai_family = allowed_gai_family
# ------------------------------------------------

from master_book import MASTER_BOOK
from rule_engine import create_chart_from_dict, evaluate_rules, PALACE_NAMES

# --- Configuration & Constants Loading ---
def load_config():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, 'config.json')
    defaults = {
        "server": {"host": "0.0.0.0", "port": 5000, "debug": False},
        "gemini": {
            "provider": "groq", 
            "api_key": "", 
            "groq_key": "",
            "model": "llama-3.1-8b-instant", 
            "temperature": 0.7, 
            "max_output_tokens": 1024
        },
        "ollama": {
            "enable": True,
            "url": "http://127.0.0.1:11434/api/generate",
            "model": "gemma2:2b"
        }
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

# --- Global Data Paths ---
CHAT_LOG_FILE = 'chat_history.json'
RECORD_FILE = 'user_records.json'

# --- Persistence Layer (JSON vs MongoDB) ---
MONGO_URI = os.environ.get("MONGO_URI")
db = None
users_collection = None
chats_collection = None

if MONGO_URI:
    print(f"DEBUG: Found MONGO_URI environment variable (Length: {len(MONGO_URI)})") # Debug check
    # Explicitly install dnspython if missing (Render fix)
    try:
        import dns
    except ImportError:
        print("Installing dnspython...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "dnspython"])

    try:
        import pymongo
        from pymongo import MongoClient
        print(f"DEBUG: Pymongo Version: {pymongo.version}")
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000) # 5s timeout
        
        # Try to get default database, if fails (e.g. URI has no path), use 'fate_purple'
        try:
            db = client.get_database()
        except:
            db = client["fate_purple"]
        users_collection = db["user_records"]
        chats_collection = db["chat_history"]
        print(f"✅ MongoDB connected: {db.name}")
        
        # FORCE CHECK: The client is lazy, so we must command it to check connectivity now
        print("DEBUG: Pinging MongoDB...")
        client.admin.command('ping')
        print("DEBUG: Ping successful!")

        if "test" in db.name and not "?" in MONGO_URI: # Heuristic check
             print("WARNING: Default database is 'test'. You may want to specify a DB name in URI.")
    except Exception as e:
        import traceback
        print(f"❌ MongoDB connection failed. Detailed Error:\n{traceback.format_exc()}")
        db = None
        users_collection = None
        chats_collection = None

def load_json_file(filename):
    # MongoDB Mode
    if db:
        if filename == RECORD_FILE and users_collection is not None:
            return list(users_collection.find({}, {'_id': 0}))
        elif filename == CHAT_LOG_FILE and chats_collection is not None:
            return list(chats_collection.find({}, {'_id': 0}).sort("timestamp", 1))
    
    # File Mode
    if not os.path.exists(filename): return []
    try:
        with open(filename, 'r', encoding='utf-8') as f: return json.load(f)
    except: return []

def save_json_file(filename, data):
    # MongoDB Mode
    if db:
        # For bulk save, we might want to just insert the new item, but the current logic passes the WHOLE list.
        # To adapt without rewriting everything, we'll check if it's an append operation.
        # But here 'data' is the full list.
        # OPTIMIZATION: In a real app, we shouldn't pass the full list. 
        # However, for compatibility with existing code structure:
        if filename == RECORD_FILE and users_collection is not None:
            # Dangerous: Replacing all data? No, let's just insert the LAST item if it's new.
            # But the caller (log_chat/save_record) usually appends and passes the full list.
            # Let's change the caller to pass only the NEW item? No, that requires changing callers.
            # Let's just grab the last item from `data` assuming it's an append.
            if data:
                last_item = data[-1]
                # Simple check to avoid duplicates if possible, or just insert.
                # Timestamps are unique enough.
                if users_collection.count_documents({"timestamp": last_item.get("timestamp")}, limit=1) == 0:
                    users_collection.insert_one(last_item)
            return
        elif filename == CHAT_LOG_FILE and chats_collection is not None:
            if data:
                last_item = data[-1]
                if chats_collection.count_documents({"timestamp": last_item.get("timestamp")}, limit=1) == 0:
                    chats_collection.insert_one(last_item)
            return

    # File Mode
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def log_chat(model, prompt, response, user_info=None):
    # In MongoDB mode, we don't need to load all logs just to append one.
    entry = {
        "timestamp": datetime.now().isoformat(),
        "model": model,
        "prompt": prompt,
        "response": response
    }
    if user_info:
        entry.update(user_info)
    
    if db and chats_collection is not None:
        chats_collection.insert_one(entry)
    else:
        logs = load_json_file(CHAT_LOG_FILE)
        logs.append(entry)
        save_json_file(CHAT_LOG_FILE, logs[-1000:]) # Keep last 1000

# --- App Globals ---
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# AI Priority & Key Pools (Supports multiple keys separated by comma)
def get_key_list(env_name, config_key):
    # Render or other PAAS will provide env vars, local relies on config.json
    val = os.environ.get(env_name) or CONFIG['gemini'].get(config_key, "")
    if isinstance(val, list): return val
    if not val: return []
    return [k.strip() for k in str(val).split(",") if k.strip()]

GROQ_KEYS = get_key_list("GROQ_API_KEY", "groq_key")
GEMINI_KEYS = get_key_list("GEMINI_API_KEY", "api_key")

GROQ_MODEL = "llama-3.1-8b-instant"
GEMINI_MODEL = "gemini-2.0-flash"
import random

# --- AI Engine Callers ---
def call_ollama_api(prompt, system_prompt=""):
    """呼叫本地 Ollama API (根據 config.json 設定)"""
    # 如果是在 Render 等雲端環境，通常無法連線到本地 Ollama，直接跳過
    if os.environ.get('RENDER'): return None

    ollama_cfg = CONFIG.get('ollama', {})
    if not ollama_cfg.get('enable', True): return None

    try:
        url = ollama_cfg.get('url', "http://127.0.0.1:11434/api/generate")
        payload = {
            "model": ollama_cfg.get('model', "gemma2:2b"),
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {"num_ctx": 4096, "temperature": 0.7}
        }
        res = requests.post(url, json=payload, timeout=2) # 縮短超時時間，避免卡頓
        if res.status_code == 200:
            return res.json().get("response")
    except Exception as e:
        # 僅在偵錯模式顯示，避免干擾主日誌
        if CONFIG['server'].get('debug'): print(f"Ollama API offline: {e}")
    return None

def call_groq_api(prompt, system_prompt=""):
    if not GROQ_KEYS: return None
    # 隨機挑選金鑰進行負載平衡
    for _ in range(3): # 最多嘗試 3 次重試
        try:
            from groq import Groq
            current_key = random.choice(GROQ_KEYS)
            client = Groq(api_key=current_key)
            completion = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
                temperature=0.7, max_completion_tokens=1024
            )
            return completion.choices[0].message.content
        except Exception as e:
            if "429" in str(e):
                print(">>> Groq 擁擠中，稍後重試...")
                time.sleep(2)
                continue
            print(f"Groq API Error: {e}")
            break
    return None

def call_gemini_api(prompt, system_prompt=""):
    if not GEMINI_KEYS: return None
    for _ in range(2):
        try:
            current_key = random.choice(GEMINI_KEYS)
            genai.configure(api_key=current_key)
            model_instance = genai.GenerativeModel(GEMINI_MODEL)
            response = model_instance.generate_content(f"{system_prompt}\n\n{prompt}")
            return response.text
        except Exception as e:
            if "429" in str(e):
                time.sleep(2)
                continue
            print(f"Gemini API Error: {e}")
            break
    return None

# --- UI Application Class ---
# --- UI Application Class ---
if HAS_TK:
    BaseClass = tk.Tk
else:
    BaseClass = object

class BackendApp(BaseClass):
    def __init__(self, flask_app):
        if not HAS_TK: return
        super().__init__()
        self.flask_app = flask_app
        self.title("紫微八字 · 天機命譜系統 [全功能後端中控台]")
        self.geometry("1040x800")
        self.configure(bg="#1e1e1e")
        
        self.is_running = False
        self.ngrok_process = None
        self.ngrok_url = None

        self.setup_ui()
        self.setup_logging()
        
        # Start server automatically
        self.after(500, self.start_server)
        self.refresh_records()
        self.refresh_chats()

    def setup_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background="#1e1e1e")
        style.configure("Panel.TFrame", background="#252526")
        style.configure("TLabel", background="#1e1e1e", foreground="#d4d4d4", font=("Microsoft JhengHei", 10))
        style.configure("Header.TLabel", background="#252526", foreground="#ffffff", font=("Microsoft JhengHei", 12, "bold"))
        style.configure("TNotebook", background="#1e1e1e", borderwidth=0)
        style.configure("TNotebook.Tab", background="#2d2d2d", foreground="#999999", padding=[15, 5], font=("Microsoft JhengHei", 10))
        style.map("TNotebook.Tab", background=[("selected", "#3b82f6")], foreground=[("selected", "#ffffff")])

        # Header
        header = ttk.Frame(self, style="Panel.TFrame", padding=15)
        header.pack(fill="x")
        ttk.Label(header, text="紫微天機 · 後端中控台 (V2.5 雙引擎版)", style="Header.TLabel").pack(side="left")

        # Tabs
        self.notebook = ttk.Notebook(self, style="TNotebook")
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

        # Tab 1: Monitor
        self.tab_monitor = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(self.tab_monitor, text="  伺服器監控  ")
        self.setup_monitor_tab()

        # Tab 2: Records
        self.tab_records = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(self.tab_records, text="  使用者名冊  ")
        self.setup_records_tab()

        # Tab 3: Chats
        self.tab_chats = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(self.tab_chats, text="  AI 對話紀錄  ")
        self.setup_chats_tab()

        # Tab 4: Ngrok
        self.tab_ngrok = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(self.tab_ngrok, text="  遠端連線 (Ngrok)  ")
        self.setup_ngrok_tab()

    def setup_monitor_tab(self):
        toolbar = ttk.Frame(self.tab_monitor, padding=10)
        toolbar.pack(fill="x")
        tk.Button(toolbar, text="開啟網頁 (Browser)", command=lambda: webbrowser.open("http://localhost:5000/"), 
                 bg="#3b82f6", fg="white", font=("Microsoft JhengHei", 10, "bold"), padx=15).pack(side="left", padx=5)
        tk.Button(toolbar, text="清空日誌", command=lambda: self.txt_log.delete("1.0", "end"), 
                 bg="#4b5563", fg="white", font=("Microsoft JhengHei", 9)).pack(side="left", padx=5)
        tk.Button(toolbar, text="關閉系統", command=self.quit_app, 
                 bg="#ef4444", fg="white", font=("Microsoft JhengHei", 9, "bold"), padx=10).pack(side="right", padx=5)

        self.txt_log = scrolledtext.ScrolledText(self.tab_monitor, bg="black", fg="#00ff00", font=("Consolas", 10), insertbackground="white")
        self.txt_log.pack(fill="both", expand=True, padx=10, pady=10)

    def setup_records_tab(self):
        toolbar = ttk.Frame(self.tab_records, padding=10)
        toolbar.pack(fill="x")
        tk.Button(toolbar, text="重新整理名冊", command=self.refresh_records, bg="#3b82f6", fg="white").pack(side="left")

        cols = ("time", "name", "gender", "birth", "lunar")
        self.tree_records = ttk.Treeview(self.tab_records, columns=cols, show='headings')
        for c in cols: self.tree_records.heading(c, text=c.capitalize())
        self.tree_records.pack(fill="both", expand=True, padx=10, pady=10)

    def setup_chats_tab(self):
        paned = tk.PanedWindow(self.tab_chats, orient="vertical", bg="#1e1e1e", sashwidth=4)
        paned.pack(fill="both", expand=True, padx=10, pady=10)

        top = ttk.Frame(paned)
        paned.add(top, height=300)
        tk.Button(top, text="重新整理對話", command=self.refresh_chats, bg="#3b82f6", fg="white").pack(anchor="w", pady=5)
        
        cols = ("time", "model", "prompt")
        self.tree_chats = ttk.Treeview(top, columns=cols, show='headings')
        for c in cols: self.tree_chats.heading(c, text=c.capitalize())
        self.tree_chats.pack(fill="both", expand=True)
        self.tree_chats.bind("<<TreeviewSelect>>", self.on_chat_select)

        self.txt_chat_detail = scrolledtext.ScrolledText(paned, bg="#2d2d2d", fg="white", font=("Microsoft JhengHei", 10))
        paned.add(self.txt_chat_detail)

    def setup_ngrok_tab(self):
        frame = ttk.Frame(self.tab_ngrok, padding=30)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Ngrok 遠端穿透服務", font=("Microsoft JhengHei", 14, "bold")).pack(pady=10)
        
        self.btn_ngrok = tk.Button(frame, text="啟動 Ngrok 隧道", command=self.toggle_ngrok, 
                                bg="#8b5cf6", fg="white", font=("Microsoft JhengHei", 11, "bold"), padx=20, pady=10)
        self.btn_ngrok.pack(pady=20)
        
        self.lbl_ngrok = ttk.Label(frame, text="狀態: 未啟動")
        self.lbl_ngrok.pack()
        
        self.ent_ngrok = ttk.Entry(frame, font=("Consolas", 11), width=50)
        self.ent_ngrok.pack(pady=10)

    def refresh_records(self):
        for i in self.tree_records.get_children(): self.tree_records.delete(i)
        for r in reversed(load_json_file(RECORD_FILE)):
            self.tree_records.insert("", "end", values=(r.get("timestamp","")[:16], r.get("name"), r.get("gender"), r.get("birth_date"), r.get("lunar_date")))

    def refresh_chats(self):
        for i in self.tree_chats.get_children(): self.tree_chats.delete(i)
        self.chat_cache = load_json_file(CHAT_LOG_FILE)
        for idx, c in enumerate(reversed(self.chat_cache)):
            self.tree_chats.insert("", "end", iid=str(len(self.chat_cache)-1-idx), values=(c.get("timestamp","")[:19], c.get("model"), c.get("prompt")[:50]))

    def on_chat_select(self, e):
        sel = self.tree_chats.selection()
        if not sel: return
        c = self.chat_cache[int(sel[0])]
        self.txt_chat_detail.configure(state="normal")
        self.txt_chat_detail.delete("1.0", "end")
        info = f"【緣主】: {c.get('user_name','?')} | {c.get('gender','')} | {c.get('birth_date','')} {c.get('birth_hour','')} | {c.get('lunar_date','')}\n"
        self.txt_chat_detail.insert("1.0", f"{info}\n【提問】:\n{c.get('prompt')}\n\n【回答】:\n{c.get('response')}")
        self.txt_chat_detail.configure(state="disabled")

    def toggle_ngrok(self):
        if self.ngrok_process:
            self.ngrok_process.terminate(); self.ngrok_process = None
            self.btn_ngrok.config(text="啟動 Ngrok 隧道", bg="#8b5cf6")
            self.lbl_ngrok.config(text="狀態: 已停止")
        else:
            try:
                self.ngrok_process = subprocess.Popen(["ngrok", "http", "5000"], creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                self.btn_ngrok.config(text="停止 Ngrok 隧道", bg="#ef4444")
                threading.Thread(target=self.wait_ngrok, daemon=True).start()
            except: messagebox.showerror("錯誤", "找不到 ngrok.exe，請確保已安裝並加入 PATH")

    def wait_ngrok(self):
        time.sleep(3)
        try:
            res = requests.get("http://127.0.0.1:4040/api/tunnels").json()
            url = res['tunnels'][0]['public_url']
            self.after(0, lambda: (self.ent_ngrok.delete(0, "end"), self.ent_ngrok.insert(0, url), self.lbl_ngrok.config(text="狀態: 在線 (Online)", foreground="#4ade80")))
        except: self.after(0, lambda: self.lbl_ngrok.config(text="狀態: 取得網址失敗"))

    def setup_logging(self):
        class Redir:
            def __init__(self, widget): self.widget = widget
            def write(self, s): self.widget.after(0, lambda: (self.widget.insert("end", s), self.widget.see("end")))
            def flush(self): pass
        sys.stdout = sys.stderr = Redir(self.txt_log)

    def start_server(self):
        t = threading.Thread(target=lambda: self.flask_app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False), daemon=True)
        t.start()
        print("Flask 伺服器已啟動於 http://localhost:5000")

    def quit_app(self):
        if self.ngrok_process: self.ngrok_process.terminate()
        if messagebox.askokcancel("退出", "確定要關閉全系統嗎？"): self.destroy(); sys.exit(0)

# --- Flask Routes ---
@app.route('/')
def index(): return send_file('fate.html')

@app.route('/admin')
def admin_page(): return send_file('admin.html')

@app.route('/api/db_check')
def db_check():
    status = {
        "mongo_uri_set": bool(MONGO_URI),
        "db_connected": db is not None,
        "users_collection": users_collection is not None,
        "db_name": db.name if db else None
    }
    return jsonify(status)

@app.route('/api/admin/data')
def get_admin_data():
    records = load_json_file(RECORD_FILE)
    chats = load_json_file(CHAT_LOG_FILE)
    
    # Determine DB Status text
    status_text = "Local JSON"
    if MONGO_URI:
        if db is not None:
             status_text = f"MongoDB ({db.name})"
        else:
             status_text = "MongoDB Connect Failed"
    
    return jsonify({
        "records_count": len(records),
        "chats_count": len(chats),
        "records": list(reversed(records[-50:])), # Last 50 records
        "chats": list(reversed(chats[-50:])),    # Last 50 chats
        "status": "Online",
        "uptime": "Running",
        "db_status": status_text
    })

@app.route('/<path:filename>')
def serve_static(filename):
    if filename.lower().endswith(('.png', '.ico', '.jpg', '.jpeg', '.html', '.css', '.js', '.json')):
        if os.path.exists(filename): return send_file(filename)
    return "Not Found", 404

@app.route('/api/save_record', methods=['POST', 'OPTIONS'])
def save_record():
    if request.method == 'OPTIONS':
        resp = make_response(); resp.headers.add("Access-Control-Allow-Origin", "*"); resp.headers.add("Access-Control-Allow-Headers", "*"); return resp
    data = request.json or {}
    record = {
        "timestamp": datetime.now().isoformat(), "name": data.get("name", "Unknown"),
        "gender": data.get("gender"), "birth_date": data.get("birth_date"),
        "birth_hour": data.get("birth_hour"), "lunar_date": data.get("lunar_date")
    }
    
    if db and users_collection is not None:
        users_collection.insert_one(record)
    else:
        recs = load_json_file(RECORD_FILE); recs.append(record); save_json_file(RECORD_FILE, recs)
        
    return make_response(jsonify({"success": True}), 200, {"Access-Control-Allow-Origin": "*"})

@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        resp = make_response(); resp.headers.add("Access-Control-Allow-Origin", "*"); resp.headers.add("Access-Control-Allow-Headers", "*"); return resp
    
    data = request.json or {}
    user_prompt = data.get('prompt', '')
    client_sys = data.get('system_prompt', '')
    gender = data.get('gender', 'M')
    chart_data = data.get('chart_data')
    
    # Extract User Identity
    user_info = {
        "user_name": data.get("name", "Unknown"),
        "birth_date": data.get("birth_date", ""),
        "birth_hour": data.get("birth_hour", ""),
        "lunar_date": data.get("lunar_date", ""),
        "gender": data.get("gender", "")
    }

    matched = []
    if chart_data:
        try:
            chart = create_chart_from_dict(chart_data, gender=gender)
            rule_path = "ziwei_rules.json"
            if os.path.exists(rule_path):
                with open(rule_path, 'r', encoding='utf-8') as f: matched = evaluate_rules(chart, json.load(f))
        except Exception as e: print(f"規則引擎錯誤: {e}")

    def generate():
        is_full = any(kw in (user_prompt + client_sys) for kw in ["詳評", "命譜詳評", "格局報告"])
        
        # 動態系統提示詞：平常對話不帶秘卷以節省 Token
        if is_full:
            final_system_prompt = f"你是【紫微天機道長】，命理宗師。請針對緣主的命盤數據給予深度的格局批註。\n{client_sys}\n【紫微心法秘卷】\n{MASTER_BOOK}"
        else:
            final_system_prompt = f"你是【紫微天機道長】，語氣優雅慈悲。請直接回應該問題。"

        def call_ai(p, s):
            # 優先順序：1. 本地 Ollama -> 2. Groq -> 3. Gemini
            print(f">>> AI 請求 (Prompt: {p[:15]}...)")
            
            # Phase 1: Local
            # 如果是 Render 部署，Ollama 應該在 setup 時被禁用或跳過，這裡再做一次保險
            if not os.environ.get('RENDER'):
                res = call_ollama_api(p, s)
                if res and len(res.strip()) > 5: return res

            # Phase 2: Groq
            print(">>> 嘗試 Groq (8B)...")
            res = call_groq_api(p, s)
            if res and len(res.strip()) > 5: return res
            
            # Phase 3: Gemini (Fallback)
            print(f">>> Groq 失敗或無回應 (res={res})，啟動 Gemini 備援...")
            res = call_gemini_api(p, s)
            if res and len(res.strip()) > 5: return res
            
            return None

        if matched and is_full:
            yield "【天機分析成功...】宗師正在為您詳批格局...\n\n"
            titles = {"A": "【第一章：星曜坐守與神煞特徵】", "B": "【第二章：命宮宮干飛化】", "C": "【第三章：宮位間的交互飛化】"}
            
            all_chapter_summaries = "" 
            
            # 章節式解讀 (語氣優化：禁止使用學術或說明書用語)
            chapter_sys = "你是【紫微天機道長】，命理宗師。請針對此命盤格局，直接給予緣主白話且深入的命理分析。語氣要權威且慈悲，切勿包含「本章節」、「綜上所述」、「規則」等生硬詞彙。請直接切入重點，分析吉凶。"

            for g_code, g_title in titles.items():
                items = [r for r in matched if r.get("rule_group") == g_code]
                if items:
                    yield f"\n{g_title}\n" + "-"*35 + "\n"
                    
                    # 1. 先列出該章節所有規則
                    chapter_content = ""
                    for r in items[:15]: 
                        rule_txt = f"● 【{r.get('detected_palace_names','全盤')}】{r.get('description')}：{r.get('text')}"
                        yield rule_txt + "\n"
                        chapter_content += rule_txt + "\n"
                    
                    # 2. 針對該章節進行一次性 AI 總評
                    yield f"\n💡 大師章節批註：\n"
                    explain_prompt = f"章節：{g_title}\n包含規則：\n{chapter_content}\n請給予本章節的綜合命理解讀。"
                    explanation = call_ai(explain_prompt, chapter_sys)
                    
                    if explanation:
                        # 排版優化：還原為標準換行符號，交由前端 CSS 處理
                        clean_exp = explanation.replace("\n", "")
                        formatted_exp = clean_exp.replace("。", "。\n").strip()
                        yield f"{formatted_exp}\n\n"
                        
                        summary_snapshot = clean_exp[:250] + "..." if len(clean_exp) > 250 else clean_exp
                        all_chapter_summaries += f"### {g_title} 重點摘要：\n{summary_snapshot}\n\n"
                    else:
                        yield "(大師沈默中...)\n\n"
            
            if all_chapter_summaries:
                yield "="*45 + "\n【天機判語 · 命理終極總結】\n"
                
                mini_final_sys = "你是【紫微天機道長】，命理宗師。請根據命盤摘要給予緣主最後的建議（300字）。請用白話文，語氣慈悲，直接給予人生指引。"
                final_prompt = f"以下是緣主的命盤章節摘要：\n{all_chapter_summaries}\n\n用戶提問：{user_prompt}\n\n請做最後的總結與建議，每遇到句號請換行。"
                
                final_advice = call_ai(final_prompt, mini_final_sys)
                if final_advice and len(final_advice.strip()) > 10:
                     clean_final = final_advice.replace("\n", "")
                     formatted_final = clean_final.replace("。", "。\n").strip()
                     yield formatted_final
                else:
                     yield "連線不穩定，無法取得最終建議。"
            else:
                yield "無法生成足夠資訊以進行總結。"
            
                yield "連線斷開，請檢查後端日誌。"
            log_chat("Hybrid-Report-Chapter", user_prompt, "Successfully generated detailed report.", user_info)
        else:
            # 一般對話也優化排版
            final = call_ai(user_prompt, final_system_prompt)
            if final:
                clean_final = final.replace("\n", "") 
                formatted_final = clean_final.replace("。", "。\n").strip()
                yield formatted_final
            else:
                yield "連線斷開，請檢查後端日誌。"
            log_chat(data.get("model", "Hybrid-Fallback"), user_prompt, final or "ERR", user_info)

    return Response(stream_with_context(generate()), content_type='text/plain; charset=utf-8', headers={"Access-Control-Allow-Origin": "*"})

if __name__ == '__main__':
    # Check for Headless mode (e.g. Render, Docker, or GitHub Codespaces)
    if os.environ.get('HEADLESS') or os.environ.get('RENDER') or not HAS_TK:
        print("Starting in HEADLESS mode (Web Server Only)...")
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
    else:
        # Local Desktop Mode with Tkinter Dashboard
        try:
            ui = BackendApp(app)
            ui.mainloop()
        except Exception as e:
            # Fallback if no display found (linux server etc)
            print(f"GUI launch failed ({e}), falling back to HEADLESS mode...")
            app.run(host="0.0.0.0", port=5000, debug=False)
