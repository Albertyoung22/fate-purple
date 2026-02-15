
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
from pyngrok import ngrok
import lunar_python
from lunar_python import Lunar, Solar

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

# --- UI Application Class ---
class BackendApp(tk.Tk):
    def __init__(self, flask_app):
        super().__init__()
        self.flask_app = flask_app
        self.title("紫微八字 · 天機命譜系統")
        self.geometry("1000x750")
        self.configure(bg="#1e1e1e")
        
        self.is_running = False
        self.ngrok_process = None
        self.ngrok_url = None

        # Windows Taskbar Icon Fix
        try:
            import ctypes
            myappid = 'fatepurple.ziwei.master.v1'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except:
            pass

        try:
            # 優先嘗試使用 Pillow (PIL) 載入，支援度最強
            from PIL import Image, ImageTk
            img = Image.open("icon.png")
            icon = ImageTk.PhotoImage(img)
            self.iconphoto(True, icon)
            print("成功載入應用程式圖示 (icon.png) via Pillow")
            # Keep a reference to prevent garbage collection
            self._icon_ref = icon
        except Exception as e_pil:
            print(f"Pillow 載入失敗: {e_pil}")
            try:
                # 降級嘗試：使用 base64 原生讀取
                import base64
                with open("icon.png", "rb") as img_file:
                    icon_data = base64.b64encode(img_file.read()).decode("utf-8")
                icon = tk.PhotoImage(data=icon_data)
                self.iconphoto(True, icon)
                print("成功載入應用程式圖示 (icon.png) via Tkinter")
            except Exception as e:
                print(f"載入圖示完全失敗: {e}")
                try:
                    self.iconbitmap("favicon.ico") 
                except:
                    pass

        self.setup_ui()
        self.setup_logging()
        
        # Start server automatically
        self.after(500, self.start_server)
        self.start_monitoring()

    def setup_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background="#1e1e1e")
        style.configure("Panel.TFrame", background="#252526")
        style.configure("TLabel", background="#1e1e1e", foreground="#d4d4d4", font=("Microsoft JhengHei", 10))
        style.configure("Header.TLabel", background="#252526", foreground="#ffffff", font=("Microsoft JhengHei", 12, "bold"))
        style.configure("Status.TLabel", background="#252526", foreground="#d4d4d4", font=("Microsoft JhengHei", 10))
        
        # Notebook (Tabs)
        style.configure("TNotebook", background="#1e1e1e", borderwidth=0)
        style.configure("TNotebook.Tab", background="#2d2d2d", foreground="#999999", padding=[10, 5], font=("Microsoft JhengHei", 10))
        style.map("TNotebook.Tab", background=[("selected", "#3b82f6")], foreground=[("selected", "#ffffff")])

        # Header
        header = ttk.Frame(self, style="Panel.TFrame", padding=15)
        header.pack(fill="x", pady=(0, 2))
        ttk.Label(header, text="紫微八字 · 天機命譜 - 後端中控台", style="Header.TLabel").pack(side="left")

        # Tabs Container
        self.notebook = ttk.Notebook(self, style="TNotebook")
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

        # Tab 1: Monitor
        self.tab_monitor = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(self.tab_monitor, text="  伺服器監控  ")
        self.setup_monitor_tab()

        # Tab 2: User Records
        self.tab_records = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(self.tab_records, text="  使用者名冊  ")
        self.setup_records_tab()

        # Tab 3: Chat History
        self.tab_chats = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(self.tab_chats, text="  AI 對話紀錄  ")
        self.setup_chats_tab()

        # Tab 4: Ngrok (Remote Access)
        self.tab_ngrok = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(self.tab_ngrok, text="  遠端連線 (Ngrok)  ")
        self.setup_ngrok_tab()

    def setup_monitor_tab(self):
        # Status Bar
        status_bar = ttk.Frame(self.tab_monitor, style="Panel.TFrame", padding=10)
        status_bar.pack(fill="x", pady=5)
        
        self.lbl_ollama = ttk.Label(status_bar, text="● Ollama: 偵測中...", style="Status.TLabel")
        self.lbl_ollama.pack(side="left", padx=20)
        
        self.lbl_server = ttk.Label(status_bar, text="● 伺服器: 準備中...", style="Status.TLabel")
        self.lbl_server.pack(side="left", padx=20)

        # Toolbar
        toolbar = ttk.Frame(self.tab_monitor, style="TFrame", padding=5)
        toolbar.pack(fill="x")

        tk.Button(toolbar, text="開啟網頁 (Browser)", command=self.open_browser, 
                 bg="#3b82f6", fg="white", font=("Microsoft JhengHei", 9, "bold"), relief="flat", padx=10).pack(side="left", padx=5)
                 
        tk.Button(toolbar, text="重整狀態", command=self.check_ollama_status,
                 bg="#6b7280", fg="white", font=("Microsoft JhengHei", 9), relief="flat", padx=10).pack(side="left", padx=5)

        tk.Button(toolbar, text="檢查資料完整性", command=self.run_check,
                 bg="#10b981", fg="white", font=("Microsoft JhengHei", 9), relief="flat", padx=10).pack(side="left", padx=5)

        tk.Button(toolbar, text="關閉系統", command=self.quit_app,
                 bg="#ef4444", fg="white", font=("Microsoft JhengHei", 9, "bold"), relief="flat", padx=10).pack(side="right", padx=5)

        # Console
        console_frame = ttk.Frame(self.tab_monitor, style="TFrame", padding=10)
        console_frame.pack(fill="both", expand=True)
        ttk.Label(console_frame, text="即時日誌 (Server Log):", style="TLabel").pack(anchor="w")
        
        self.txt_log = scrolledtext.ScrolledText(console_frame, bg="black", fg="#00ff00", insertbackground="white", font=("Consolas", 10))
        self.txt_log.pack(fill="both", expand=True)
        
        self.txt_log.tag_config("INFO", foreground="#00aaaa")
        self.txt_log.tag_config("ERROR", foreground="#ff5555")
        self.txt_log.tag_config("FLASK", foreground="#ffff55")

    def setup_records_tab(self):
        toolbar = ttk.Frame(self.tab_records, style="TFrame", padding=10)
        toolbar.pack(fill="x")
        tk.Button(toolbar, text="重新整理列表", command=self.refresh_records,
                 bg="#3b82f6", fg="white", font=("Microsoft JhengHei", 9), relief="flat").pack(side="left")

        cols = ("timestamp", "name", "gender", "birth_date", "lunar")
        self.tree_records = ttk.Treeview(self.tab_records, columns=cols, show='headings', selectmode="browse")
        
        self.tree_records.heading("timestamp", text="紀錄時間")
        self.tree_records.heading("name", text="姓名")
        self.tree_records.heading("gender", text="性別")
        self.tree_records.heading("birth_date", text="國曆生日")
        self.tree_records.heading("lunar", text="農曆資料")
        
        self.tree_records.column("timestamp", width=150)
        self.tree_records.column("name", width=100)
        self.tree_records.column("gender", width=60)
        self.tree_records.column("birth_date", width=100)
        self.tree_records.column("lunar", width=250)

        scrollbar = ttk.Scrollbar(self.tab_records, orient="vertical", command=self.tree_records.yview)
        self.tree_records.configure(yscrollcommand=scrollbar.set)
        
        self.tree_records.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y", pady=10)

    def setup_chats_tab(self):
        paned = tk.PanedWindow(self.tab_chats, orient="vertical", bg="#1e1e1e", sashwidth=4, sashrelief="flat")
        paned.pack(fill="both", expand=True, padx=10, pady=10)

        top_frame = ttk.Frame(paned, style="TFrame")
        paned.add(top_frame, height=300)

        toolbar = ttk.Frame(top_frame, style="TFrame", padding=(0,0,0,5))
        toolbar.pack(fill="x")
        tk.Button(toolbar, text="重新整理對話", command=self.refresh_chats,
                 bg="#3b82f6", fg="white", font=("Microsoft JhengHei", 9), relief="flat").pack(side="left")

        cols = ("time", "model", "prompt_short", "response_short")
        self.tree_chats = ttk.Treeview(top_frame, columns=cols, show='headings', selectmode="browse")
        
        self.tree_chats.heading("time", text="時間")
        self.tree_chats.heading("model", text="模型")
        self.tree_chats.heading("prompt_short", text="提問摘要")
        self.tree_chats.heading("response_short", text="回答摘要")
        
        self.tree_chats.column("time", width=150)
        self.tree_chats.column("model", width=100)
        self.tree_chats.column("prompt_short", width=250)
        self.tree_chats.column("response_short", width=250)
        
        scroll_chats = ttk.Scrollbar(top_frame, orient="vertical", command=self.tree_chats.yview)
        self.tree_chats.configure(yscrollcommand=scroll_chats.set)
        
        self.tree_chats.pack(side="left", fill="both", expand=True)
        scroll_chats.pack(side="right", fill="y")
        
        self.tree_chats.bind("<<TreeviewSelect>>", self.on_chat_select)

        bottom_frame = ttk.Frame(paned, style="TFrame")
        paned.add(bottom_frame)
        
        ttk.Label(bottom_frame, text="詳細內容:", style="TLabel").pack(anchor="w", pady=(5,0))
        self.txt_chat_detail = scrolledtext.ScrolledText(bottom_frame, bg="#2d2d2d", fg="white", font=("Microsoft JhengHei", 10))
        self.txt_chat_detail.pack(fill="both", expand=True)

    def setup_ngrok_tab(self):
        # Instructions
        intro_frame = ttk.Frame(self.tab_ngrok, style="TFrame", padding=20)
        intro_frame.pack(fill="x")
        
        ttk.Label(intro_frame, text="Ngrok 遠端連線服務", style="Header.TLabel").pack(anchor="w", pady=(0, 10))
        ttk.Label(intro_frame, text="使用 Ngrok 可以將您的本機網站 (Localhost) 發布到網際網路上，\n讓其他人可以透過公開網址存取您的紫微系統。", style="TLabel").pack(anchor="w")
        
        # Controls
        ctrl_frame = ttk.Frame(self.tab_ngrok, style="Panel.TFrame", padding=20)
        ctrl_frame.pack(fill="x", padx=20, pady=20)

        self.btn_ngrok_toggle = tk.Button(ctrl_frame, text="啟動 Ngrok 隧道", command=self.toggle_ngrok,
                 bg="#8b5cf6", fg="white", font=("Microsoft JhengHei", 12, "bold"), relief="flat", padx=20, pady=10)
        self.btn_ngrok_toggle.pack(pady=10)
        
        self.lbl_ngrok_status = ttk.Label(ctrl_frame, text="目前狀態: 未啟動", style="Status.TLabel", font=("Microsoft JhengHei", 10))
        self.lbl_ngrok_status.pack(pady=5)
        
        # URL Display
        url_frame = ttk.Frame(ctrl_frame, style="Panel.TFrame")
        url_frame.pack(fill="x", pady=20)
        
        ttk.Label(url_frame, text="公開網址 (Public URL):", style="Status.TLabel").pack(side="left")
        self.entry_ngrok_url = ttk.Entry(url_frame, font=("Consolas", 11), width=50)
        self.entry_ngrok_url.pack(side="left", padx=10)
        
        tk.Button(url_frame, text="複製", command=self.copy_ngrok_url,
                 bg="#4b5563", fg="white", font=("Microsoft JhengHei", 9), relief="flat").pack(side="left")

    def toggle_ngrok(self):
        if self.ngrok_process:
            self.stop_ngrok()
        else:
            self.start_ngrok()

    def start_ngrok(self):
        self.log("正在啟動 Ngrok...", "INFO")
        self.lbl_ngrok_status.config(text="目前狀態: 正在啟動...", foreground="#fbbf24")
        
        try:
            # Check if ngrok is installed
            subprocess.run(["ngrok", "--version"], check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        except Exception:
            messagebox.showerror("錯誤", "找不到 'ngrok' 指令。\n請確認您已安裝 Ngrok 並將其加入系統 PATH 環境變數中。")
            self.lbl_ngrok_status.config(text="目前狀態: 啟動失敗 (找不到程式)", foreground="#ef4444")
            return

        try:
            # Start ngrok process
            cmd = ["ngrok", "http", "5000"]
            self.ngrok_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            self.btn_ngrok_toggle.config(text="停止 Ngrok 隧道", bg="#ef4444")
            self.log("Ngrok 程序已啟動 (PID: {})".format(self.ngrok_process.pid), "INFO")
            
            # Start thread to fetch URL
            threading.Thread(target=self.wait_for_ngrok_url, daemon=True).start()
            
        except Exception as e:
            self.log(f"Ngrok 啟動失敗: {e}", "ERROR")
            self.lbl_ngrok_status.config(text="目前狀態: 異常", foreground="#ef4444")

    def stop_ngrok(self):
        if self.ngrok_process:
            self.log("正在停止 Ngrok...", "INFO")
            self.ngrok_process.terminate()
            self.ngrok_process = None
            
        self.btn_ngrok_toggle.config(text="啟動 Ngrok 隧道", bg="#8b5cf6")
        self.lbl_ngrok_status.config(text="目前狀態: 未啟動", foreground="#d4d4d4")
        self.entry_ngrok_url.delete(0, "end")
        self.log("Ngrok 已停止。", "INFO")

    def wait_for_ngrok_url(self):
        time.sleep(2) # Wait for startup
        attempts = 0
        while self.ngrok_process and attempts < 10:
            try:
                # Query local ngrok API
                res = requests.get("http://127.0.0.1:4040/api/tunnels")
                data = res.json()
                public_url = data['tunnels'][0]['public_url']
                
                # Update UI
                self.after(0, lambda u=public_url: self.on_ngrok_connected(u))
                return
            except Exception:
                pass
            
            time.sleep(1)
            attempts += 1
            
        self.after(0, lambda: self.log("無法獲取 Ngrok URL (可能尚未登入或網絡問題)", "ERROR"))

    def on_ngrok_connected(self, url):
        self.log(f"Ngrok 連線成功! URL: {url}", "INFO")
        self.lbl_ngrok_status.config(text="目前狀態: 連線正常 (Online)", foreground="#4ade80")
        self.entry_ngrok_url.delete(0, "end")
        self.entry_ngrok_url.insert(0, url)

    def copy_ngrok_url(self):
        url = self.entry_ngrok_url.get()
        if url:
            self.clipboard_clear()
            self.clipboard_append(url)
            messagebox.showinfo("複製", "網址已複製到剪貼簿。")

    def refresh_records(self):
        for item in self.tree_records.get_children():
            self.tree_records.delete(item)
        
        data = load_json_file(RECORD_FILE)
        for item in reversed(data):
            ts = item.get("timestamp", "")
            try: dt = datetime.fromisoformat(ts); ts_str = dt.strftime("%Y-%m-%d %H:%M")
            except: ts_str = ts
            self.tree_records.insert("", "end", values=(ts_str, item.get("name", ""), item.get("gender", ""), item.get("birth_date", ""), item.get("lunar_date", "")))

    def refresh_chats(self):
        for item in self.tree_chats.get_children(): self.tree_chats.delete(item)
        data = load_json_file(CHAT_LOG_FILE)
        self.chat_data_cache = data
        for idx, item in enumerate(reversed(data)):
            ts = item.get("timestamp", "")
            try: dt = datetime.fromisoformat(ts); ts_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except: ts_str = ts
            p = item.get("prompt", "").replace("\n", " ")[:30] + "..."
            r = item.get("response", "").replace("\n", " ")[:30] + "..."
            real_idx = len(data) - 1 - idx
            self.tree_chats.insert("", "end", iid=str(real_idx), values=(ts_str, item.get("model", ""), p, r))

    def on_chat_select(self, event):
        selected = self.tree_chats.selection()
        if not selected: return
        idx = int(selected[0])
        if 0 <= idx < len(self.chat_data_cache):
            item = self.chat_data_cache[idx]
            detail = f"時間: {item.get('timestamp')}\n模型: {item.get('model')}\n--------------------------------------------------\n【提問】:\n{item.get('prompt')}\n--------------------------------------------------\n【AI 回答】:\n{item.get('response')}\n"
            self.txt_chat_detail.configure(state="normal")
            self.txt_chat_detail.delete("1.0", "end")
            self.txt_chat_detail.insert("1.0", detail)
            self.txt_chat_detail.configure(state="disabled")

    def setup_logging(self):
        class Redirector:
            def __init__(self, widget, tag="INFO"): self.widget = widget; self.tag = tag
            def write(self, str): self.widget.after(0, self._append, str)
            def _append(self, str): self.widget.insert("end", str, self.tag); self.widget.see("end")
            def flush(self): pass
        
        sys.stdout = Redirector(self.txt_log, "INFO")
        sys.stderr = Redirector(self.txt_log, "FLASK")
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        for handler in logger.handlers[:]: logger.removeHandler(handler)
        class TextHandler(logging.Handler):
            def __init__(self, widget): super().__init__(); self.widget = widget
            def emit(self, record):
                msg = self.format(record)
                self.widget.after(0, lambda: self.widget.insert("end", msg + "\n", "FLASK"))
                self.widget.after(0, self.widget.see, "end")
        logger.addHandler(TextHandler(self.txt_log))

    def log(self, msg, level="INFO"):
        self.txt_log.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n", level)
        self.txt_log.see("end")

    def start_server(self):
        if self.is_running: return
        self.is_running = True
        def run():
            self.log("正在啟動 Flask 伺服器...", "INFO")
            self.flask_app.run(host=CONFIG['server']['host'], port=CONFIG['server']['port'], debug=CONFIG['server']['debug'], use_reloader=False)
        self.server_thread = threading.Thread(target=run, daemon=True)
        self.server_thread.start()
        self.lbl_server.config(text=f"● 伺服器: 運行中 (Port {CONFIG['server']['port']})", foreground="#4ade80")

    def start_monitoring(self): self.monitor_loop()
    def monitor_loop(self): self.check_ollama_status(); self.after(5000, self.monitor_loop)
    def check_ollama_status(self):
        try:
            requests.get("http://localhost:11434", timeout=1)
            self.lbl_ollama.config(text="● Ollama: 連線正常", foreground="#4ade80")
        except: self.lbl_ollama.config(text="● Ollama: 未偵測到", foreground="#f87171")

    def open_browser(self): webbrowser.open("http://localhost:5000/")
    def run_check(self): self.log("\n--- 執行資料檢查 ---", "INFO"); threading.Thread(target=self._run_check_thread, daemon=True).start()
    def _run_check_thread(self):
        try: res = subprocess.run(["python", "check_records.py"], capture_output=True, text=True, encoding='utf-8'); print(res.stdout); 
        except Exception as e: print(f"檢查失敗: {e}")
    def quit_app(self):
        if self.ngrok_process: self.stop_ngrok()
        if messagebox.askokcancel("退出", "確定要關閉伺服器嗎？"): self.destroy(); sys.exit(0)

# --- Configuration & Constants Loading ---

def load_config():
    config_path = 'config.json'
    defaults = {
        "server": {"host": "0.0.0.0", "port": 5000, "debug": False},
        "ollama": {"api_url": "http://localhost:11434/api/generate", "default_model": "gemma2:2b"},
        "gemini": {"api_key": "", "model": "gemini-1.5-flash"},
        "app": {"title": "紫微八字 · 天機命譜系統", "geometry": "1000x750", "icon_path": "icon.png"}
    }
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                # Deep merge defaults (simplified)
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

# --- App Globals ---
app = Flask(__name__)
OLLAMA_API_URL = CONFIG['ollama']['api_url']
DEFAULT_MODEL = CONFIG['ollama']['default_model']
GEMINI_API_KEY = CONFIG['gemini'].get('api_key', "")
GEMINI_MODEL = CONFIG['gemini'].get('model', "gemini-1.5-flash")

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

STEMS = CONSTANTS['STEMS']
BRANCHES = CONSTANTS['BRANCHES']
SI_HUA_TABLE = CONSTANTS['SI_HUA_TABLE']

def get_current_year_ganzhi():
    """Calculates the Heavenly Stem and Earthly Branch for the current year."""
    now = datetime.now()
    year = now.year
    # Adjustment for Lunar New Year (simplified: cutoff roughly Feb 4th)
    if now.month < 2 or (now.month == 2 and now.day < 4):
        year -= 1
        
    stem_idx = (year - 4) % 10
    branch_idx = (year - 4) % 12
    # 1984 (Jia Zi): 1984 - 4 = 1980. 1980 % 12 = 0. -> Index 0 (Zi). Correct.
    # 2024 (Jia Chen): 2024 - 4 = 2020. 2020 % 12 = 4. -> Index 4 (Chen). Correct.
    
    return STEMS[stem_idx], BRANCHES[branch_idx]

def detect_intent_and_context(prompt, chart_data):
    """
    Analyzes user prompt to determine the topic and context.
    Returns specific instructions and data injection.
    """
    instructions = ""
    injected_data = ""
    
    prompt_lower = prompt.lower()
    
    # --- 1. Topic Detection ---
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
            
    # --- 2. Temporal Detection (Liu Nian) ---
    temporal_keywords = ["流年", "今年", "運勢", "明年", "202"] # 202x
    is_temporal = any(kw in prompt_lower for kw in temporal_keywords)
    
    # Always calculate current year context if "Year" is mentioned or implied
    if is_temporal or "年" in prompt or not found_topic: # If no topic found, maybe general fortune which includes year
        y_stem, y_branch = get_current_year_ganzhi()
        
        # Calculate Liu Nian Si Hua
        sihua = SI_HUA_TABLE.get(y_stem, {})
        
        # Find Liu Nian Ming Gong
        liu_nian_palace_name = "未知"
        liu_nian_stars = []
        
        if chart_data:
            for palace in chart_data:
                # Assuming palace has 'zhi' and 'stars' list
                # fate.html structure: { id: 0, gan: 'xx', zhi: 'xx', stars: [...] }
                if palace.get('zhi') == y_branch:
                    liu_nian_palace_name = palace.get('name', '流年命宮')
                    liu_nian_stars = palace.get('stars', [])
                    break
        
        # Format the injection
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

@app.route('/')
def index(): return send_file('fate.html')

@app.route('/<path:filename>')
def serve_static(filename):
    # 用於提供 logo_v2.png, icon.png, favicon.ico 等靜態圖片
    if filename.lower().endswith(('.png', '.ico', '.jpg', '.jpeg')):
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

from master_book import MASTER_BOOK

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
    
    # Initialize payload and results
    matched_results = []
    options = data.get('options', {})
    payload = {
        "model": model,
        "prompt": user_prompt,
        "system": client_system_prompt,
        "stream": True,
        "options": options
    }
    
    print(f"收到 AI 請求: {user_prompt[:20]}...")
    if chart_data and isinstance(chart_data, list):
        summary = " | ".join([f"{p.get('palaceName')}:{p.get('gan')}{p.get('zhi')}" for p in chart_data[:3]])
        print(f"命盤資料摘要: {summary}...")
    
    # --- 1. Rule Engine Evaluation ---
    if chart_data:
        try:
            print("正在執行紫微規則引擎檢測...")
            from rule_engine import create_chart_from_dict, evaluate_rules
            
            rule_file = "ziwei_rules.json"
            rules = []
            if os.path.exists(rule_file):
                with open(rule_file, 'r', encoding='utf-8') as f:
                    rules = json.load(f)
            
            chart = create_chart_from_dict(chart_data, gender=gender)
            matched_results = evaluate_rules(chart, rules)
            
            if matched_results:
                from rule_engine import PALACE_NAMES

                print(f"規則引擎命中 {len(matched_results)} 條規則。")
            else:
                print("規則引擎未命中任何規則。")
                
        except Exception as e:
            print(f"規則引擎執行失敗: {e}")
            # Non-blocking, continue to AI

    # --- 2. AI Generation ---
    # We still ask AI to generate the REST of the interpretation, 
    # BUT we prepend the rule results to the FINAL output directly.
    # However, user said "Don't use AI to explain". 
    # If the user request IS for a full report, we probably still want AI for the parts NOT covered by rules.
    # But for the RULE part, we output it RAW.
    
    # Strategy: 
    # We send the context to AI but tell it NOT to repeat the rules we already found?
    # Or just let AI do its thing and we prepend our hard facts at the top.
    # The user said "Before AI explains... direct citation".
    
    # Revised System Prompt to enforce role and prevent meta-analysis
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

    # Inject rules into prompt context so AI aligns with them (consistency)
    prompt_context = user_prompt

    # --- New: Intent & Context Detection ---
    intent_instructions = ""
    injected_data = ""
    try:
        intent_instructions, injected_data = detect_intent_and_context(user_prompt, chart_data)
        if injected_data:
            prompt_context += injected_data
    except Exception as e:
        print(f"意圖偵測失敗: {e}")
        
    if intent_instructions:
        full_system_prompt += intent_instructions

    # Limit detected rules to avoid context overflow, but ensure enough for AI to explain
    # --- 3. Construct Final Response ---
    
    # --- 3. Construct Unified Response ---
    def generate_unified_response():
        # 嚴格判斷是否為「今日錦囊」：檢查指令或系統 Prompt 是否包含錦囊
        is_daily_query = "錦囊" in (user_prompt + client_system_prompt)
        
        # 嚴格判斷：只有在指令中包含「詳評」或「格局」等字眼時，才視為需要顯示規則的詳評模式
        is_full_report = any(kw in (user_prompt + client_system_prompt) for kw in ["詳評", "命譜詳評", "格局報告"])

        # --- 如果是今日錦囊，使用極簡模式 ---
        if is_daily_query:
            yield "【大師感應中...】正在為您抽取今日錦囊，請稍候...\n\n"
            short_system_prompt = "你是一位精通紫微斗數的決策宗師。你的任務是針對【流日命宮】給予一句精要錦囊。禁止分析格局，禁止廢話，字數100字內，強制繁體中文。"
            summary_prompt = f"請根據以下流日數據給予今日錦囊：\n{user_prompt}"
            
            if GEMINI_API_KEY:
                gemini_res = call_gemini_api(summary_prompt, short_system_prompt)
                if gemini_res:
                    yield "【大師今日錦囊】\n"
                    yield "------------------------------------------\n"
                    # 3字一組生動顯示，確保緩衝區刷新
                    chunk_size = 3
                    for i in range(0, len(gemini_res), chunk_size):
                        yield gemini_res[i:i+chunk_size]
                        time.sleep(0.02)
                    return

        # --- 判斷是否為「前世因果」請求 ---
        # 前端 pastLife 按鈕會傳送帶有「前世今生故事模式」的指令
        is_karma_query = "前世今生故事模式" in (user_prompt + client_system_prompt) or \
                         any(kw in user_prompt for kw in ["前世", "因果", "業力", "輪迴"])
        
        if is_karma_query:
            yield "【時空連線中...】正在讀取您的前世記憶，請稍候...\n\n"
            karma_system_prompt = """你是一位精通三世因果的紫微通靈大師。
請略過世俗的財富地位分析，專注解讀命盤中的【福德宮】(靈魂前世)、【命宮】(今生業力) 與【身宮】(執行模式)。
特別關注：
1. 【地空、地劫】：前世的修行或未竟之志。
2. 【陀羅、擎羊】：前世的糾纏與業債。
3. 【化忌】：前世虧欠的領域。
4. 【天刑、陰煞】：看不見的業力干擾。

請以「說故事」的方式，為緣主勾勒出一幅前世今生的因果圖像，並給予今生修行的建議。
語氣需神秘、深邃且充滿慈悲。字數約 300 字。強制繁體中文。"""
            
            summary_prompt = f"請根據以下命盤數據，解讀緣主的前世因果與業力課題：\n{user_prompt}"

            if GEMINI_API_KEY:
                gemini_res = call_gemini_api(summary_prompt, karma_system_prompt)
                if gemini_res:
                    yield "【三世因果解碼報告】\n"
                    yield "------------------------------------------\n"
                    # 3字一組生動顯示
                    chunk_size = 3
                    for i in range(0, len(gemini_res), chunk_size):
                        yield gemini_res[i:i+chunk_size]
                        time.sleep(0.02)
                    return

        # --- 判斷是否為「轉運儀式」請求 ---
        is_ritual_query = any(kw in (user_prompt + client_system_prompt) for kw in ["轉運", "改運", "儀式", "佈局"])
        if is_ritual_query:
            yield "【堪輿佈局中...】正在為您設計轉運儀式，請稍候...\n\n"
            ritual_system_prompt = """你是一位精通堪輿與道家科儀的開運大師。
請根據命盤中的【田宅宮】(環境磁場)、【財帛宮】(財氣方位) 與【命宮】(個人五行)，為緣主量身打造一套「轉運儀式」。
內容必須包含：
1. **幸運方位**：指出適合緣主納氣或安床的方位。
2. **開運物品**：建議擺放的法器或幸運物（如水晶、植物、金屬等）。
3. **簡易科儀**：一個緣主可以立刻執行的淨化或祈福小儀式（如灑淨、冥想、拜祭）。
語氣需正向、神聖且具體可行。字數約 300 字。強制繁體中文。"""
            
            summary_prompt = f"請根據以下命盤數據，設計專屬的轉運儀式：\n{user_prompt}"
            
            if GEMINI_API_KEY:
                gemini_res = call_gemini_api(summary_prompt, ritual_system_prompt)
                if gemini_res:
                    yield "【道家轉運開運儀式】\n"
                    yield "------------------------------------------\n"
                    # 3字一組生動顯示
                    chunk_size = 3
                    for i in range(0, len(gemini_res), chunk_size):
                        yield gemini_res[i:i+chunk_size]
                        time.sleep(0.02)
                    return

        # --- 判斷是否為「夢境解碼」請求 ---
        is_dream_query = any(kw in (user_prompt + client_system_prompt) for kw in ["解夢", "夢境", "夢到"])
        if is_dream_query:
            yield "【潛意識連結中...】正在解析夢境符號，請稍候...\n\n"
            dream_system_prompt = """你是一位結合心理學與紫微斗數的夢境解析師。
請根據緣主的【福德宮】(潛意識狀態) 與【疾厄宮】(身心壓力)，來解讀其夢境背後的深層含義。
請分析：
1. **夢境映射**：夢境符號對應現實生活中的哪個層面（壓力、渴望、預警）。
2. **潛意識訊息**：靈魂深處透過夢境想要傳達的話語。
3. **安神建議**：如何透過調整作息或心態來改善睡眠品質。
語氣需溫柔、療癒且具洞察力。字數約 300 字。強制繁體中文。"""
            
            summary_prompt = f"請結合以下命盤狀態，為緣主解析夢境：\n{user_prompt}"
            
            if GEMINI_API_KEY:
                gemini_res = call_gemini_api(summary_prompt, dream_system_prompt)
                if gemini_res:
                    yield "【紫微潛意識夢境解碼】\n"
                    yield "------------------------------------------\n"
                    # 3字一組生動顯示
                    chunk_size = 3
                    for i in range(0, len(gemini_res), chunk_size):
                        yield gemini_res[i:i+chunk_size]
                        time.sleep(0.02)
                    return

        # --- 判斷是否為「八字」請求 ---
        is_bazi_query = any(kw in (user_prompt + client_system_prompt) for kw in ["八字", "子平", "算命", "五行", "日主"])
        if is_bazi_query and not is_full_report:
            import re
            yield "【八字排盤中...】大師正在推算您的日主強弱與喜用神，請稍候...\n\n"
            
            # --- 強制清洗 Prompt，移除紫微斗數相關資訊 (針對尚未刷新頁面的用戶) ---
            clean_prompt = user_prompt
            # 移除「全盤星系配置」區塊
            if "【全盤星系配置】" in clean_prompt:
                clean_prompt = re.sub(r"【全盤星系配置】：.*?【八字四柱資訊】", "【八字四柱資訊】", clean_prompt, flags=re.DOTALL)
            # 移除「時空宮位分布」區塊
            if "【時空宮位分布】" in clean_prompt:
                clean_prompt = re.sub(r"【時空宮位分布】：.*?【八字四柱資訊】", "【八字四柱資訊】", clean_prompt, flags=re.DOTALL)
            
            bazi_system_prompt = """你是一位精通《子平八字》的命理宗師。
請略過紫微斗數，**專注分析緣主的四柱八字**。
請提供：
1. **八字格局**：定出日主強弱（身強/身弱）與格局（如正官格、七殺格等）。
2. **喜用神分析**：明確指出喜神與忌神（如喜木火、忌金水）。
3. **十神論命**：分析四柱中「十神」（比劫、食傷、財星、官殺、印星）的配置與生剋。
4. **流年運勢**：結合本命與流年干支的沖刑合害（如天剋地沖、三合三會），論斷吉凶。
語氣需古樸、專業，並引用經典口訣。字數約 400 字。強制繁體中文。"""
            
            summary_prompt = f"請根據以下命盤中的【八字資訊】，進行子平八字論命：\n{clean_prompt}"
            
            if GEMINI_API_KEY:
                gemini_res = call_gemini_api(summary_prompt, bazi_system_prompt)
                if gemini_res:
                    yield "【子平八字精批】\n"
                    yield "------------------------------------------\n"
                    chunk_size = 3
                    for i in range(0, len(gemini_res), chunk_size):
                        yield gemini_res[i:i+chunk_size]
                        time.sleep(0.02)
                    return
        is_love_query = any(kw in (user_prompt + client_system_prompt) for kw in ["桃花", "姻緣", "感情", "戀愛", "脫單", "攻略"])
        if is_love_query:
            yield "【紅鸞星動中...】正在推算您的桃花運勢，請稍候...\n\n"
            love_system_prompt = """你是一位精通紫微合婚與戀愛心理的兩性導師。
請專注分析命盤中的【夫妻宮】(對象特質)、【福德宮】(感情觀) 與【紅鸞/天喜】(桃花時機)。
請給予緣主：
1. **正緣特徵**：未來伴侶可能的外貌、性格或職業特徵。
2. **桃花時機**：近期最有機會脫單或感情升溫的時間點。
3. **攻略建議**：針對緣主的性格盲點，提供具體的戀愛建議或相處之道。
語氣需活潑、犀利又帶點幽默。字數約 300 字。強制繁體中文。"""
            
            summary_prompt = f"請根據以下命盤數據，提供專屬的桃花戀愛攻略：\n{user_prompt}"
            
            if GEMINI_API_KEY:
                gemini_res = call_gemini_api(summary_prompt, love_system_prompt)
                if gemini_res:
                    yield "【紫微戀愛桃花攻略】\n"
                    yield "------------------------------------------\n"
                    # 3字一組生動顯示
                    chunk_size = 3
                    for i in range(0, len(gemini_res), chunk_size):
                        yield gemini_res[i:i+chunk_size]
                        time.sleep(0.02)
                    return

        # --- 判斷是否為「財運預測」請求 ---
        is_finance_query = any(kw in (user_prompt + client_system_prompt) for kw in ["投資", "理財", "財運", "股票", "房產"])
        if is_finance_query:
            yield "【財氣運算中...】大師正在分析您的財帛宮與投資運勢，請稍候...\n\n"
            finance_system_prompt = """你是一位精通紫微斗數的財富管理大師。
請重點分析緣主的【財帛宮】(理財能力)、【官祿宮】(事業正財) 與【田宅宮】(不動產與庫存)。
請提供：
1. **財運格局**：緣主是適合「正財」(工作致富) 還是「偏財」(投資投機)。
2. **投資建議**：適合的投資標的(如股票、基金、房地產、外匯)與風險屬性。
3. **流年財運**：近期財運走勢，何時該進攻、何時該保守。
4. **股票操作**：若緣主詢問股票，請結合「武曲」(金)、「太陰」(不動產/穩健)、「貪狼」(投機) 等星曜特性給予建議。
語氣需專業、務實且具前瞻性。字數約 300 字。強制繁體中文。"""
            
            summary_prompt = f"請根據以下命盤數據，提供專屬的投資理財建議：\n{user_prompt}"
            
            if GEMINI_API_KEY:
                gemini_res = call_gemini_api(summary_prompt, finance_system_prompt)
                if gemini_res:
                    yield "【紫微財運投資佈局】\n"
                    yield "------------------------------------------\n"
                    # 3字一組生動顯示
                    chunk_size = 3
                    for i in range(0, len(gemini_res), chunk_size):
                        yield gemini_res[i:i+chunk_size]
                        time.sleep(0.02)
                    return

        # --- 以下為「命譜詳評」或「一般對話」模式 ---
        
        # 嚴格判斷：只有在指令中包含「詳評」或「格局」等字眼時，才視為需要顯示規則的詳評模式
        is_full_report = any(kw in (user_prompt + client_system_prompt) for kw in ["詳評", "命譜詳評", "格局報告"])

        # First, immediately yield raw rule data (fast feedback)
        # 只有在明確的「命譜詳評」請求下，才顯示完整的命錄格局報告
        if matched_results and is_full_report:
            yield "【天機運算中...】大師正在詳批您的命盤與格局，請稍候...\n\n"
            yield "【紫微命譜格局偵測報告】\n"
            yield "您可以將這些邏輯視為「判定規則」，用來解讀命盤中各個生命領域的特質：\n\n"
            
            # 分組邏輯
            group_a = [r for r in matched_results if r.get("rule_group") == "A"]
            group_b = [r for r in matched_results if r.get("rule_group") == "B"]
            group_c = [r for r in matched_results if r.get("rule_group") == "C"]

            if group_a:
                yield "一、 星曜坐守與神煞特徵\n"
                yield "------------------------------------------\n"
                for res in group_a:
                    yield f"● 【{res.get('detected_palace_names', '全盤')}】{res.get('description')}：{res.get('text')}\n"
                yield "\n"

            if group_b:
                yield "二、 命宮宮干飛化（個人意識的投射）\n"
                yield "------------------------------------------\n"
                for res in group_b:
                    yield f"● 【{res.get('detected_palace_names', '命宮飛入')}】{res.get('description')}：{res.get('text')}\n"
                yield "\n"

            if group_c:
                yield "三、 宮位間的交互飛化（關聯與流向）\n"
                yield "------------------------------------------\n"
                for res in group_c:
                    yield f"● 【{res.get('detected_palace_names', '關聯宮位')}】{res.get('description')}：{res.get('text')}\n"
                yield "\n"

            yield f"{'='*40}\n\n"
            yield "四、道長綜合結論\n"
            yield "------------------------------------------\n"
        
        # --- AI 綜合結論部分 (詳評模式) ---
        rules_context_str = ""
        if matched_results:
            for r in matched_results[:25]: 
                rules_context_str += f"- {r.get('description')}：{r.get('text')}\n"
        
        summary_prompt = f"""請根據以下【命盤原始數據】與【格局偵測報告】，為緣主進行最終的【命譜詳評與運勢預測】。

【命盤原始數據】：
{user_prompt}

【偵測格局】：
{rules_context_str}

【大師指令：鐵口直斷模式】：
1. **格局演繹**：將上述散落的星曜與飛化進行「全盤合參」，論斷此命格局是高低。
2. **直指利弊**：不可模稜兩可。直接點出此生最強的「貴人位」與最險的「破敗處」。
3. **時空預測**：結合流年與日期，給予具體運勢斷語及改運建議。
4. **大智若愚**：語氣需權威。字數約 500 字。
5. **文字要求**：強制繁體中文。
"""
        
        # --- 優先使用 Gemini API ---
        if GEMINI_API_KEY:
            gemini_res = call_gemini_api(summary_prompt, full_system_prompt)
            if gemini_res:
                # 3字一組生動顯示，確保緩衝區刷新
                chunk_size = 3
                for i in range(0, len(gemini_res), chunk_size):
                    yield gemini_res[i:i+chunk_size]
                    time.sleep(0.02)
                return

        # --- 若無 Gemini 或失敗，則退回 Ollama ---
        ai_payload = {
            "model": model,
            "prompt": summary_prompt,
            "system": full_system_prompt,
            "stream": True,
            "options": options
        }
        
        try:
            # 調高 timeout 限制，避免 Read timeout (10秒連線, 300秒讀取)
            endpoint = OLLAMA_API_URL
            with requests.post(endpoint, json=ai_payload, stream=True, timeout=(10, 300)) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        if "response" in chunk:
                            yield chunk["response"]
        except Exception as e:
            yield f"\n[大師正在深思中，連線稍有延遲: {e}]"

    return Response(stream_with_context(generate_unified_response()), content_type='text/plain; charset=utf-8', headers={
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive"
    })

        


if __name__ == '__main__':
    print("啟動綜合版伺服器介面 (含 Ngrok)...")
    gui = BackendApp(app); gui.mainloop()
