
import os
import json
import requests
import sys
import threading
import webbrowser
import logging
import subprocess
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
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

def load_json_file(filename):
    if not os.path.exists(filename): return []
    try:
        with open(filename, 'r', encoding='utf-8') as f: return json.load(f)
    except: return []

def save_json_file(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def log_chat(model, prompt, response):
    logs = load_json_file(CHAT_LOG_FILE)
    logs.append({
        "timestamp": datetime.now().isoformat(),
        "model": model,
        "prompt": prompt,
        "response": response
    })
    save_json_file(CHAT_LOG_FILE, logs[-1000:]) # Keep last 1000

# --- App Globals ---
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# AI Priority & Key Pools (Supports multiple keys separated by comma)
def get_key_list(env_name, config_key):
    val = os.environ.get(env_name) or CONFIG['gemini'].get(config_key, "")
    if isinstance(val, list): return val
    return [k.strip() for k in val.split(",") if k.strip()]

GROQ_KEYS = get_key_list("GROQ_API_KEY", "groq_key")
GEMINI_KEYS = get_key_list("GEMINI_API_KEY", "api_key")

GROQ_MODEL = "llama-3.1-8b-instant"
GEMINI_MODEL = "gemini-2.0-flash"
import random

# --- AI Engine Callers ---
def call_ollama_api(prompt, system_prompt=""):
    """呼叫本地 Ollama API (根據 config.json 設定)"""
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
        res = requests.post(url, json=payload, timeout=5) # 縮短超時時間
        if res.status_code == 200:
            return res.json().get("response")
    except Exception as e:
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
class BackendApp(tk.Tk):
    def __init__(self, flask_app):
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
        self.txt_chat_detail.insert("1.0", f"【提問】:\n{c.get('prompt')}\n\n【回答】:\n{c.get('response')}")
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
            # 優先順序：1. 本地 Ollama (省錢) -> 2. Groq (速度) -> 3. Gemini (備援)
            print(f">>> AI 請求 (Prompt: {p[:15]}...)")
            res = call_ollama_api(p, s)
            if res: return res

            print(">>> 嘗試 Groq (8B)...")
            res = call_groq_api(p, s)
            if not res:
                print(">>> Groq 失敗，切換 Gemini 備援...")
                res = call_gemini_api(p, s)
            return res

        if matched and is_full:
            yield "【天機分析成功...】宗師正在為您詳批格局...\n\n"
            titles = {"A": "【第一章：星曜坐守與神煞特徵】", "B": "【第二章：命宮宮干飛化】", "C": "【第三章：宮位間的交互飛化】"}
            
            # 單條規則解讀的專屬系統提示詞 (節省 Token 並加速回應)
            mini_sys = "你是【紫微天機道長】，命理宗師。請用白話解讀此格局，字數 50 字內。"

            for g_code, g_title in titles.items():
                items = [r for r in matched if r.get("rule_group") == g_code]
                if items:
                    yield f"\n{g_title}\n" + "-"*35 + "\n"
                    for r in items[:12]:
                        rule_txt = f"● 【{r.get('detected_palace_names','全盤')}】{r.get('description')}：{r.get('text')}\n"
                        yield rule_txt
                        
                        # 即時呼叫 AI 解析該格局
                        explain_prompt = f"格局：{r.get('description')}\n內容：{r.get('text')}\n請給予大師解讀。"
                        explanation = call_ai(explain_prompt, mini_sys)
                        if explanation:
                            yield f"   💡 大師解讀：{explanation}\n\n"
                        else:
                            yield "   (大師沈默中，請參閱前文)\n\n"
            
            yield "\n" + "="*45 + "\n【天機判語】命盤格局已詳批完成。祝緣主福慧漸增，道氣常存。\n"
            log_chat("Hybrid-Report", user_prompt, "Successfully generated detailed report.")
        else:
            final = call_ai(user_prompt, final_system_prompt)
            yield (final or "連線斷開，請檢查後端日誌。")
            log_chat("Hybrid-Fallback", user_prompt, final or "ERR")

    return Response(stream_with_context(generate()), content_type='text/plain; charset=utf-8', headers={"Access-Control-Allow-Origin": "*"})

if __name__ == '__main__':
    ui = BackendApp(app)
    ui.mainloop()
