
import os
import json
import requests
import sys
import threading
import webbrowser
import logging
import time
import asyncio
import edge_tts
if os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# --- GUI Support Check ---
try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox
    HAS_TK = True
except ImportError:
    HAS_TK = False
    print("Tkinter not found (Headless environment detected). GUI will be disabled.")
from datetime import datetime, timedelta, timezone
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
            "max_output_tokens": 3000
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
MONGO_URI = os.environ.get("MONGO_URI") or CONFIG.get("mongo_uri")
USE_MONGODB = CONFIG.get("use_mongodb", True) # Default to True, but allow disabling
db = None
users_collection = None
chats_collection = None
MONGO_AVAILABLE = False

if MONGO_URI and USE_MONGODB:
    print(f"DEBUG: Found MONGO_URI environment variable (Length: {len(MONGO_URI)})") # Debug check
    # MongoDB connection setup
    try:
        import pymongo
        from pymongo import MongoClient
        print(f"DEBUG: Pymongo 版本: {pymongo.version}")
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000, connectTimeoutMS=10000, socketTimeoutMS=15000)
        
        # Try to get default database, if fails (e.g. URI has no path), use 'fate_purple'
        try:
            db = client.get_database()
        except:
            db = client["fate_purple"]
        users_collection = db["user_records"]
        chats_collection = db["chat_history"]
        print(f"✅ MongoDB 客戶端已連接資料庫: {db.name}")
        
        # REMOVED synchronous ping check to avoid blocking startup
        # client.admin.command('ping') 

        if "test" in db.name and not "?" in MONGO_URI: # Heuristic check
             print("警告: 預設資料庫為 'test'。您可能需要在 URI 中指定資料庫名稱。")
        MONGO_AVAILABLE = True
    except Exception as e:
        import traceback
        print(f"❌ MongoDB 連線失敗。詳細錯誤:\n{traceback.format_exc()}")
        db = None
        users_collection = None
        chats_collection = None
        MONGO_AVAILABLE = False

# --- Google Sheets Integration ---
SHEETS_CREDENTIALS_FILE = 'credentials.json'
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID") or CONFIG.get("spreadsheet_id")
sheets_service = None

def get_sheets_service():
    global sheets_service
    if sheets_service: return sheets_service
    
    if os.path.exists(SHEETS_CREDENTIALS_FILE):
        try:
            # Load credentials and ensure private_key is correctly formatted
            with open(SHEETS_CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
                info = json.load(f)
            
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            
            SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
            creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
            sheets_service = build('sheets', 'v4', credentials=creds)
            print(f"✅ Google 試算表服務已初始化")
            return sheets_service
        except Exception as e:
            print(f"❌ Google 試算表初始化失敗: {e}")
            return None
    return None

def append_to_sheet(sheet_name, row_data):
    service = get_sheets_service()
    if not service or not SPREADSHEET_ID: return
    
    try:
        range_name = f"{sheet_name}!A1"
        body = {'values': [row_data]}
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID, range=range_name,
            valueInputOption="USER_ENTERED", body=body).execute()
    except Exception as e:
        err_msg = str(e)
        if "400" in err_msg and "not supported for this document" in err_msg:
            print(f"❌ 試算表 ID 格式錯誤 (ID: {SPREADSHEET_ID})")
            if len(SPREADSHEET_ID) == 33:
                print("🚨 偵測到 ID 為 33 字元，極大機率是被截斷了！正確 ID 通常為 44 字元。")
                print("請至 config.json 重新貼上完整的 Spreadsheet ID。")
            else:
                print("提示：請檢查 config.json 中的 spreadsheet_id 是否正確且為有效的試算表（非資料夾）。")
        else:
            print(f"⚠️ 試算表寫入錯誤 ({sheet_name}): {e}")


def load_json_file(filename):
    global MONGO_AVAILABLE
    # MongoDB Mode (with fallback)
    if users_collection is not None and MONGO_AVAILABLE:
        try:
            if filename == RECORD_FILE:
                return list(users_collection.find({}, {'_id': 0}))
            elif filename == CHAT_LOG_FILE:
                return list(chats_collection.find({}, {'_id': 0}).sort("timestamp", 1))
        except Exception as e:
            print(f"⚠️ Mongo 讀取錯誤 ({e})，切換至本地 JSON...")
            # If we hit a timeout, maybe disable Mongo for a while? 
            # For now, let's keep trying but logging is annoying if it happens every time.
            # Let's simple disable it for this session if it fails once to ensure speed.
            # MONGO_AVAILABLE = False # Uncomment to permanent disable after split failure
            pass

    # Local File Mode
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"載入 {filename} 錯誤: {e}")
    return []

def save_json_file(filename, data):
    global MONGO_AVAILABLE
    # MongoDB Mode (with fallback)
    if users_collection is not None and MONGO_AVAILABLE:
        try:
            if filename == RECORD_FILE and data:
                # Naive implementation: assume the last item is the new one
                users_collection.insert_one(data[-1])
                # Also save to local file for backup? Yes.
            elif filename == CHAT_LOG_FILE and data:
                 chats_collection.insert_one(data[-1])
        except Exception as e:
            print(f"⚠️ Mongo 寫入錯誤 ({e})，切換至本地 JSON...")
            # MONGO_AVAILABLE = False # Uncomment to disable after failure
    
    # Local File Mode (Always save or fallback)
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"儲存 {filename} 錯誤: {e}")

HIDDEN_INSIGHTS_FILE = 'hidden_insights.json'
def load_hidden_insights():
    if os.path.exists(HIDDEN_INSIGHTS_FILE):
        try:
            with open(HIDDEN_INSIGHTS_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: return {}
    return {
        "report": "", "daily": "", "pastLife": "", "ritual": "", 
        "love": "", "finance": "", "bazi": "", "simple": "", "chat": ""
    }

def save_hidden_insights(data):
    with open(HIDDEN_INSIGHTS_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)

def log_chat(model, prompt, response, user_info=None):
    # In MongoDB mode, we don't need to load all logs just to append one.
    entry = {
        "timestamp": datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%dT%H:%M:%S'),
        "model": model,
        "prompt": prompt,
        "response": response
    }
    if user_info:
        entry.update(user_info)
    
    if db is not None and chats_collection is not None:
        chats_collection.insert_one(entry)
    else:
        logs = load_json_file(CHAT_LOG_FILE)
        logs.append(entry)
        save_json_file(CHAT_LOG_FILE, logs[-1000:]) # Keep last 1000

    # --- Google Sheets Export ---
    try:
        row = [
            entry.get("timestamp"),
            entry.get("user_name", ""),
            entry.get("gender", ""),
            entry.get("birth_date", ""),
            entry.get("birth_hour", ""),
            entry.get("lunar_date", ""),
            model,
            prompt,
            response
        ]
        threading.Thread(target=append_to_sheet, args=("Chats", row), daemon=True).start()
    except: pass

def get_location_from_ip(ip):
    """Resolve IP address to City/Region using ip-api.com"""
    if not ip or ip in ['127.0.0.1', 'localhost']:
        return "台灣 (本地測試)"
    try:
        # ip-api.com (Free for non-commercial, 45 req/min)
        res = requests.get(f"http://ip-api.com/json/{ip}?fields=status,message,country,regionName,city", timeout=2).json()
        if res.get('status') == 'success':
            return f"{res.get('country')} {res.get('regionName')} {res.get('city')}"
    except:
        pass
    return "未知地點"

def get_heavenly_timing():
    """Calculate current Chinese Zodiac Hour and Solar Term Context"""
    # Use timezone-aware datetime for UTC+8
    now = datetime.now(timezone(timedelta(hours=8)))
    hour = now.hour
    
    # 1. 十二時辰判定
    branches = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    # 子時是 23-01, 丑時是 01-03...
    idx = (hour + 1) // 2 % 12
    branch_hour = branches[idx] + "時"
    
    # 2. 節氣與節慶感應 (簡化邏輯：目前正值農曆馬年新春)
    # 在實際應用中可以引入 lunar_python 進行精確判斷
    season_msg = "目前正值【馬年新春】佳節期間，萬象更新，喜氣洋洋。"
    if 23 <= hour or hour < 5:
        time_advice = f"此刻正值「{branch_hour}」深夜，萬籟俱寂，是與靈魂對話的最佳時刻，但也請緣主注意休息。"
    elif 5 <= hour < 9:
        time_advice = f"此刻旭日初升，正值「{branch_hour}」，朝氣蓬勃，利於規劃未來。"
    else:
        time_advice = f"此刻時值「{branch_hour}」。"
        
    return f"{season_msg} {time_advice}"

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
        if CONFIG['server'].get('debug'): print(f"Ollama API 離線: {e}")
    return None

def stream_groq_api(prompt, system_prompt=""):
    available_keys = list(GROQ_KEYS)
    random.shuffle(available_keys)
    
    for current_key in available_keys:
        try:
            from groq import Groq
            client = Groq(api_key=current_key)
            completion = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
                temperature=0.7, max_tokens=3000, stream=True
            )
            for chunk in completion:
                content = chunk.choices[0].delta.content
                if content: yield content
            return
        except Exception as e:
            err_str = str(e)
            if "429" in err_str:
                print(f">>> Groq API (Key: {current_key[:10]}...) 繁忙/限流，嘗試備援金鑰...")
                continue
            elif "401" in err_str or "Invalid API Key" in err_str:
                print(f"❌ Groq API 金鑰失效 ({current_key[:10]}...)，已從清單移除。")
                if current_key in GROQ_KEYS:
                    GROQ_KEYS.remove(current_key)
            else:
                print(f"Groq API 錯誤: {e}")
                break

def call_groq_api(prompt, system_prompt=""):
    full_response = ""
    for chunk in stream_groq_api(prompt, system_prompt):
        full_response += chunk
    return full_response if full_response else None

def stream_gemini_api(prompt, system_prompt=""):
    available_keys = list(GEMINI_KEYS)
    random.shuffle(available_keys)
    
    for current_key in available_keys:
        try:
            genai.configure(api_key=current_key)
            model_instance = genai.GenerativeModel(GEMINI_MODEL)
            response = model_instance.generate_content(f"{system_prompt}\n\n{prompt}", stream=True)
            for chunk in response:
                if chunk.text: yield chunk.text
            return
        except Exception as e:
            err_str = str(e)
            if "429" in err_str:
                print(f">>> Gemini API (Key: {current_key[:10]}...) 繁忙/限流，嘗試備援金鑰...")
                continue
            elif "401" in err_str or "Invalid API Key" in err_str or "API_KEY_INVALID" in err_str:
                 print(f"❌ Gemini API 金鑰失效 ({current_key[:10]}...)，已從清單移除。")
                 if current_key in GEMINI_KEYS:
                     GEMINI_KEYS.remove(current_key)
            else:
                print(f"Gemini API 錯誤: {e}")
                break

def call_gemini_api(prompt, system_prompt=""):
    full_response = ""
    for chunk in stream_gemini_api(prompt, system_prompt):
        full_response += chunk
    return full_response if full_response else None

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
        titles = ("錄入時間", "姓名", "性別", "生日", "農曆")
        self.tree_records = ttk.Treeview(self.tab_records, columns=cols, show='headings')
        for i, c in enumerate(cols): self.tree_records.heading(c, text=titles[i])
        self.tree_records.pack(fill="both", expand=True, padx=10, pady=10)

    def setup_chats_tab(self):
        paned = tk.PanedWindow(self.tab_chats, orient="vertical", bg="#1e1e1e", sashwidth=4)
        paned.pack(fill="both", expand=True, padx=10, pady=10)

        top = ttk.Frame(paned)
        paned.add(top, height=300)
        tk.Button(top, text="重新整理對話", command=self.refresh_chats, bg="#3b82f6", fg="white").pack(anchor="w", pady=5)
        
        cols = ("time", "model", "prompt")
        titles = ("對話時間", "AI 模型", "提問內容摘要")
        self.tree_chats = ttk.Treeview(top, columns=cols, show='headings')
        for i, c in enumerate(cols): self.tree_chats.heading(c, text=titles[i])
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
    sheets_ok = False
    try:
        if get_sheets_service() and SPREADSHEET_ID: sheets_ok = True
    except: pass

    status = {
        "mongo_uri_set": bool(MONGO_URI),
        "db_connected": db is not None,
        "users_collection": users_collection is not None,
        "db_name": db.name if db is not None else None,
        "google_sheets_connected": sheets_ok
    }
    return jsonify(status)

@app.route('/api/admin/data')
def get_admin_data():
    # Detect if we should use Mongo directly for counts/recent to avoid timeouts
    if users_collection is not None and MONGO_AVAILABLE:
        try:
            records_count = users_collection.count_documents({})
            chats_count = chats_collection.count_documents({})
            records = list(users_collection.find({}, {'_id': 0}).sort("timestamp", -1).limit(50))
            chats = list(chats_collection.find({}, {'_id': 0}).sort("timestamp", -1).limit(50))
        except Exception as e:
            print(f"⚠️ Mongo Admin Data 讀取失敗: {e}")
            records_count = 0
            chats_count = 0
            records = []
            chats = []
    else:
        # Local JSON Fallback (only for small files)
        full_records = load_json_file(RECORD_FILE)
        full_chats = load_json_file(CHAT_LOG_FILE)
        records_count = len(full_records)
        chats_count = len(full_chats)
        records = list(reversed(full_records[-50:]))
        chats = list(reversed(full_chats[-50:]))
    
    # Determine DB Status text
    # Determine DB Status text
    status_parts = []
    
    if USE_MONGODB and MONGO_URI:
        if db is not None:
             status_parts.append(f"MongoDB ({db.name})")
        else:
             status_parts.append("MongoDB (連線失敗)")
    
    if get_sheets_service() and SPREADSHEET_ID:
        status_parts.append("Google 試算表")
        
    if not status_parts:
        status_parts.append("本地 JSON")
        
    status_text = " + ".join(status_parts)
    
    return jsonify({
        "records_count": records_count,
        "chats_count": chats_count,
        "records": records,
        "chats": chats,
        "status": "Online",
        "uptime": "Running",
        "db_status": status_text
    })

@app.route('/api/admin/hidden_insights', methods=['GET', 'POST'])
def handle_hidden_insights():
    if request.method == 'GET':
        return jsonify(load_hidden_insights())
    
    data = request.json or {}
    insights = load_hidden_insights()
    insights.update(data)
    save_hidden_insights(insights)
    return jsonify({"success": True})

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
        "timestamp": datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%dT%H:%M:%S'), "name": data.get("name", "Unknown"),
        "gender": data.get("gender"), "birth_date": data.get("birth_date"),
        "birth_hour": data.get("birth_hour"), "lunar_date": data.get("lunar_date")
    }
    
    if db is not None and users_collection is not None:
        users_collection.insert_one(record)
    else:
        recs = load_json_file(RECORD_FILE); recs.append(record); save_json_file(RECORD_FILE, recs)

    # --- Local Excel Fallback ---
    try:
        import pandas as pd
        df = pd.DataFrame(recs)
        df.rename(columns={
            "timestamp": "紀錄時間", "name": "姓名", "gender": "性別",
            "birth_date": "國曆生日", "birth_hour": "時辰(支)", "lunar_date": "農曆日期"
        }, inplace=True)
        excel_path = 'user_records.xlsx'
        df.to_excel(excel_path, index=False, engine='openpyxl')
        print(f"💾 已同步備份至本地 Excel: {excel_path}")
    except Exception as e:
        if "pandas" not in str(e).lower(): 
            print(f"⚠️ 本地 Excel 備份失敗: {e}")

    # --- Google Sheets Export ---
    try:
        row = [
            record.get("timestamp"),
            record.get("name"),
            record.get("gender"),
            record.get("birth_date"),
            record.get("birth_hour"),
            str(record.get("lunar_date"))
        ]
        threading.Thread(target=append_to_sheet, args=("Users", row), daemon=True).start()
    except: pass
        
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
        
        # 注入後台「隱藏密令」
        insights = load_hidden_insights()
        target_type = data.get("model", "chat")
        hidden_msg = insights.get(target_type, "")
        
        # 獲取天時資訊 (時辰、節氣)
        heavenly_timing = get_heavenly_timing()
        
        # 獲取使用者地理位置 (透過 IP)
        user_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
        location = get_location_from_ip(user_ip)
        
        # 擴充 Log 資訊，讓管理員在後台看得到位置
        user_info["ip"] = user_ip
        user_info["location"] = location
        
        # 注入地理位置與天時指令
        geo_msg = f"注意：緣主目前位於「{location}」。{heavenly_timing}"
        # 注入隨喜贊助指令 (不露痕跡)
        geo_msg += " 【隱藏點撥】：若你覺得這次的解盤對緣主非常有幫助，請在回話結尾（或適當處）「不露痕跡」地提到：若緣主覺得指引有益，可隨喜護持本壇香火（贊助），這也是一種結緣與功德。語氣要自然且不強求，像是一位慈悲宗師隨口的一句提醒。"
        
        # 根據不同功能的「靈氣屬性」對應當地的神明對象
        temple_map = {
            "love": "月老廟、城隍夫人或求姻緣極其靈驗的古蹟",
            "finance": "土地公(福德正神)、五路財神、或該地區產生的首富常拜的名廟",
            "ritual": "最具代表性的正神大廟（如媽祖廟、行天宮分支）或淨化磁場的觀音寺",
            "daily": "適合散心轉運、吸收地靈之氣的名廟、古剎或著名的清靜自然地景",
            "pastlife": "年代久遠、具有強大因果淨化力量的地藏王廟或歷史名剎",
            "bazi": "該地區最具權威的正位大廟，用以平衡命理五行氣場",
            "report": "當地的信仰中心，如當地的天后宮、保安宮、或最受當地信眾推崇的「守護神」廟宇",
            "simple": "香火鼎盛、正能量氣場強大的名利與平安守護廟宇",
            "chat": "該城市最具代表性的文化深度名廟"
        }
        
        target_key = target_type.lower()
        target_recommend = temple_map.get(target_key, "周邊具備正能量氣場、香火鼎盛的名門大廟")
        
        is_concise_mode = target_type in ["daily", "ritual", "pastLife", "love", "finance"]
        
        # 注入地理位置與天時指令
        geo_msg = f"注意：緣主目前位於「{location}」。{heavenly_timing}"
        
        if not is_concise_mode:
            # 注入隨喜贊助指令 (不露痕跡)
            geo_msg += " 【隱藏點撥】：若你覺得這次的解盤對緣主非常有幫助，請在回話結尾（或適當處）提到：若緣主覺得指引有益，可隨喜護持本壇香火（贊助）。"
            geo_msg += f" \n在分析與指引中，請針對「{location}」周邊，精準推薦相關的『{target_recommend}』。"
            geo_msg += " \n【極重要指令】：絕對禁止提及具體城市名。請以宗師語氣，直接說出廟宇名稱，顯得像是天機點撥。"
        else:
            # 極簡模式：僅提供地點參考，不要求擬人化語氣
            geo_msg += f" (推薦周邊『{target_recommend}』)"

        # 動態系統提示詞：平常對話不帶秘卷以節省 Token
        # 重要：將前端指定的 client_sys 放在最後，並加上最高指令標籤，確保 AI 嚴格執行格式要求
        priority_tag = "\n【最高優先權指令：請直接執行以下格式與內容要求，禁止多餘描述】\n"
        
        if is_full:
            final_system_prompt = f"你是【紫微天機道長】，命理宗師。\n{geo_msg}\n{hidden_msg}{priority_tag}{client_sys}\n\n【紫微心法秘卷】\n{MASTER_BOOK}"
        else:
            final_system_prompt = f"你是【紫微天機道長】，語氣優雅慈悲。\n{geo_msg}\n{hidden_msg}{priority_tag}{client_sys}"

        # Updated AI Caller with Streaming Support
        def stream_ai(p, s):
            print(f">>> AI 請求 (Prompt: {p[:15]}...)")
            
            # Phase 1: Local Ollama
            if not os.environ.get('RENDER'):
                res = call_ollama_api(p, s)
                if res and len(res.strip()) > 5: 
                    yield res
                    return

            provider = CONFIG.get('gemini', {}).get('provider', 'gemini').lower()
            
            def try_groq_flow():
                has_content = False
                for chunk in stream_groq_api(p, s):
                    has_content = True
                    yield chunk
                return has_content

            def try_gemini_flow():
                has_content = False
                for chunk in stream_gemini_api(p, s):
                    has_content = True
                    yield chunk
                return has_content

            if provider == 'groq':
                print(">>> 優先嘗試 Groq 串流模式...")
                if not (yield from try_groq_flow()):
                    print(">>> Groq 失敗，嘗試 Gemini 備援...")
                    if not (yield from try_gemini_flow()):
                        yield "連線忙碌，請稍後再試。"
            else:
                print(">>> 優先嘗試 Gemini 串流模式...")
                if not (yield from try_gemini_flow()):
                    print(">>> Gemini 失敗，嘗試 Groq 備援...")
                    if not (yield from try_groq_flow()):
                        yield "連線忙碌，請稍後再試。"

        if matched and is_full:
            yield "【天機分析成功...】宗師正在為您詳批格局...\n\n"
            titles = {"A": "【第一章：星曜坐守與神煞特徵】", "B": "【第二章：命宮宮干飛化】", "C": "【第三章：宮位間的交互飛化】"}
            
            all_chapter_summaries = "" 
            chapter_sys = "你是【紫微天機道長】，命理宗師。請針對此命盤格局，直接給予緣主白話且深入的命理分析。語氣要權威且慈悲，切勿包含「本章節」、「綜上所述」、「規則」等生硬詞彙。請直接切入重點，分析吉凶。"

            for g_code, g_title in titles.items():
                items = [r for r in matched if r.get("rule_group") == g_code]
                if items:
                    yield f"\n{g_title}\n" + "-"*35 + "\n"
                    
                    chapter_content = ""
                    for r in items[:15]: 
                        rule_txt = f"● 【{r.get('detected_palace_names','全盤')}】{r.get('description')}：{r.get('text')}"
                        yield rule_txt + "\n"
                        chapter_content += rule_txt + "\n"
                    
                    yield f"\n💡 大師章節批註：\n"
                    explain_prompt = f"章節：{g_title}\n包含規則：\n{chapter_content}\n請給予本章節的綜合命理解讀。"
                    
                    # Use streaming for chapter explanations too
                    explanation_accum = ""
                    for chunk in stream_ai(explain_prompt, chapter_sys):
                        yield chunk
                        explanation_accum += chunk
                    yield "\n\n"
                    
                    summary_snapshot = explanation_accum[:250] + "..." if len(explanation_accum) > 250 else explanation_accum
                    all_chapter_summaries += f"### {g_title} 重點摘要：\n{summary_snapshot}\n\n"
            
            if all_chapter_summaries:
                yield "="*45 + "\n【天機判語 · 命理終極總結】\n"
                
                mini_final_sys = "你是【紫微天機道長】，命理宗師。請根據命盤摘要給予緣主最後的建議（300字）。請用白話文，語氣慈悲，直接給予人生指引。"
                final_prompt = f"以下是緣主的命盤章節摘要：\n{all_chapter_summaries}\n\n用戶提問：{user_prompt}\n\n請做最後的總結與建議，每遇到句號請換行。"
                
                final_accum = ""
                for chunk in stream_ai(final_prompt, mini_final_sys):
                     yield chunk
                     final_accum += chunk
            else:
                yield "無法生成足夠資訊以進行總結。"
            
            log_chat("Hybrid-Report-Chapter", user_prompt, "Detailed report generated.", user_info)
        else:
            # Standard Streaming Chat
            full_response = ""
            for chunk in stream_ai(user_prompt, final_system_prompt):
                if chunk:
                    yield chunk
                    full_response += chunk
            
            log_chat(data.get("model", "Hybrid-Stream"), user_prompt, full_response, user_info)

    return Response(stream_with_context(generate()), content_type='text/plain; charset=utf-8', headers={"Access-Control-Allow-Origin": "*"})

@app.route('/api/tts', methods=['POST', 'OPTIONS'])
def tts_handler():
    if request.method == 'OPTIONS':
        resp = make_response()
        resp.headers.add("Access-Control-Allow-Origin", "*")
        resp.headers.add("Access-Control-Allow-Headers", "*")
        return resp
    
    data = request.json or {}
    text = data.get('text', '')
    if not text: return jsonify({"error": "No text"}), 400
    
    # Simple cleanup
    clean_text = text.replace("*", "").replace("#", "").strip()[:4000]

    async def get_audio():
        # Using zh-CN-YunyangNeural for a more professional/master-like male voice
        communicate = edge_tts.Communicate(clean_text, "zh-CN-YunyangNeural")
        audio = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio += chunk["data"]
        return audio

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio_data = loop.run_until_complete(get_audio())
        loop.close()
        return Response(audio_data, mimetype="audio/mpeg")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Keep-Alive 保持連線機制 (針對 Render 免費版) ---
def keep_alive_pinger():
    """定期對伺服器發送請求，防止免費版進入休眠。"""
    url = "https://fate-purple.onrender.com"  # 自身 URL
    print(f"🚀 [保持連線] 啟動背景探測器：{url}")
    while True:
        try:
            time.sleep(600)  # 每 10 分鐘 (600s) 發送一次
            print(f"⏰ [保持連線] 探測時間：{datetime.now(timezone(timedelta(hours=8))).strftime('%H:%M:%S')}...")
            response = requests.get(url, timeout=10)
            print(f"✅ [保持連線] 探測成功，狀態碼：{response.status_code}")
        except Exception as e:
            print(f"⚠️ [保持連線] 探測失敗：{e}")
            time.sleep(60)

# 僅在 Render 環境啟動背景探測器
if os.environ.get('RENDER'):
    threading.Thread(target=keep_alive_pinger, daemon=True).start()

if __name__ == '__main__':
    # 檢查是否為無介面模式 (例如 Render, Docker, 或 GitHub Codespaces)
    if os.environ.get('HEADLESS') or os.environ.get('RENDER') or not HAS_TK:
        print("系統正以【無介面模式】啟動 (僅網頁伺服器)...")
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
    else:
        # 本地桌面模式，包含 Tkinter 中控台
        try:
            ui = BackendApp(app)
            ui.mainloop()
        except Exception as e:
            # 如果找不到顯示設備則降級運行
            print(f"GUI 啟動失敗 ({e})，正在切換為【無介面模式】...")
            app.run(host="0.0.0.0", port=5000, debug=False)
