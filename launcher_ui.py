import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess
import threading
import time
import requests
import webbrowser
import os
import signal
import sys

# Configuration
BACKEND_SCRIPT = "backend_ollama0204.py"
OLLAMA_URL = "http://localhost:11434"
BACKEND_URL = "http://localhost:5000"

# Colors for "Dark Mode" feel
BG_COLOR = "#1e1e1e"
FG_COLOR = "#d4d4d4"
ACCENT_COLOR = "#3b82f6" # Blue
SUCCESS_COLOR = "#22c55e" # Green
ERROR_COLOR = "#ef4444" # Red
PANEL_BG = "#252526"

class ServerLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("紫微八字 · 天機命譜 - 伺服器監控台")
        self.geometry("700x550")
        self.configure(bg=BG_COLOR)
        
        try:
            # 嘗試載入 PNG 圖示 (支援度較好)
            icon = tk.PhotoImage(file="icon.png")
            self.iconphoto(True, icon)
        except:
            try:
                self.iconbitmap("favicon.ico") 
            except:
                pass

        self.process = None
        self.stop_event = threading.Event()

        self.setup_ui()
        self.start_monitoring()

    def setup_ui(self):
        # Style Configuration
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure("TFrame", background=BG_COLOR)
        style.configure("Panel.TFrame", background=PANEL_BG, relief="flat")
        style.configure("TLabel", background=BG_COLOR, foreground=FG_COLOR, font=("Microsoft JhengHei", 10))
        style.configure("Header.TLabel", background=PANEL_BG, foreground="#ffffff", font=("Microsoft JhengHei", 12, "bold"))
        style.configure("Status.TLabel", background=PANEL_BG, foreground=FG_COLOR, font=("Microsoft JhengHei", 10))
        
        style.configure("Action.TButton", font=("Microsoft JhengHei", 10, "bold"), padding=5)
        style.map("Action.TButton",
            foreground=[('active', 'white')],
            background=[('active', ACCENT_COLOR)]
        )

        # === Header Area ===
        header_frame = ttk.Frame(self, style="Panel.TFrame", padding=15)
        header_frame.pack(fill="x", pady=(0, 2))
        
        lbl_title = ttk.Label(header_frame, text="紫微八字 · 天機命譜 - 控制中心", style="Header.TLabel")
        lbl_title.pack(side="left")

        # === Status Indicators Area ===
        status_frame = ttk.Frame(self, style="Panel.TFrame", padding=10)
        status_frame.pack(fill="x", padx=10, pady=5)

        # Ollama Status
        self.lbl_ollama = ttk.Label(status_frame, text="● 檢測中...", style="Status.TLabel")
        self.lbl_ollama.pack(side="left", padx=20)
        
        # Backend Status
        self.lbl_backend = ttk.Label(status_frame, text="● 伺服器未啟動", style="Status.TLabel")
        self.lbl_backend.pack(side="left", padx=20)

        # === Control Buttons ===
        btn_frame = ttk.Frame(self, style="TFrame", padding=10)
        btn_frame.pack(fill="x", padx=5)

        self.btn_start = tk.Button(btn_frame, text="啟動伺服器", command=self.start_server, 
                                   bg="#047857", fg="white", font=("Microsoft JhengHei", 10, "bold"), 
                                   activebackground="#059669", activeforeground="white", relief="flat", padx=15, pady=5)
        self.btn_start.pack(side="left", padx=5)

        self.btn_stop = tk.Button(btn_frame, text="停止伺服器", command=self.stop_server, 
                                  bg="#b91c1c", fg="white", font=("Microsoft JhengHei", 10, "bold"), state="disabled",
                                  activebackground="#dc2626", activeforeground="white", relief="flat", padx=15, pady=5)
        self.btn_stop.pack(side="left", padx=5)

        self.btn_browser = tk.Button(btn_frame, text="開啟網頁介面", command=self.open_browser, 
                                     bg="#1d4ed8", fg="white", font=("Microsoft JhengHei", 10, "bold"), 
                                     activebackground="#2563eb", activeforeground="white", relief="flat", padx=15, pady=5)
        self.btn_browser.pack(side="right", padx=5)

        self.btn_check = tk.Button(btn_frame, text="檢查資料完整性", command=self.check_records, 
                                     bg="#4b5563", fg="white", font=("Microsoft JhengHei", 10), 
                                     activebackground="#6b7280", activeforeground="white", relief="flat", padx=10, pady=5)
        self.btn_check.pack(side="right", padx=5)

        # === Console Log ===
        log_frame = ttk.Frame(self, style="TFrame", padding=10)
        log_frame.pack(fill="both", expand=True)

        lbl_log = ttk.Label(log_frame, text="系統監控日誌:", style="TLabel")
        lbl_log.pack(anchor="w", pady=(0, 5))

        self.txt_log = scrolledtext.ScrolledText(log_frame, bg="#000000", fg="#00ff00", font=("Consolas", 9), state="disabled")
        self.txt_log.pack(fill="both", expand=True)
        self.txt_log.tag_config("ERROR", foreground="#ff5555")
        self.txt_log.tag_config("INFO", foreground="#55ffff")
        self.txt_log.tag_config("SYSTEM", foreground="#ffff55")

        self.log("系統就緒。請確認 Ollama 已在背景執行，然後點擊「啟動伺服器」。", "SYSTEM")

    def log(self, message, tag="INFO"):
        self.txt_log.config(state="normal")
        timestamp = time.strftime("[%H:%M:%S] ")
        self.txt_log.insert("end", timestamp + message + "\n", tag)
        self.txt_log.see("end")
        self.txt_log.config(state="disabled")

    def start_monitoring(self):
        # Start a thread to periodically check statuses
        thread = threading.Thread(target=self.monitor_loop, daemon=True)
        thread.start()

    def monitor_loop(self):
        while True:
            # Check Ollama
            try:
                requests.get(OLLAMA_URL, timeout=1)
                self.update_status(self.lbl_ollama, "● Ollama 運作中", SUCCESS_COLOR)
            except:
                self.update_status(self.lbl_ollama, "● Ollama 未連線 (請檢查)", ERROR_COLOR)

            # Check Backend
            if self.process:
                if self.process.poll() is not None:
                    # Process died unexpectedly
                    self.update_server_ui_state(False)
                    self.log("伺服器行程已意外終止。", "ERROR")
                    self.process = None

            try:
                requests.get(BACKEND_URL, timeout=1)
                self.update_status(self.lbl_backend, "● 後端伺服器 (Port 5000) 運作中", SUCCESS_COLOR)
            except:
                if self.process:
                    self.update_status(self.lbl_backend, "● 啟動中...", "#facc15") # Yellow
                else:
                    self.update_status(self.lbl_backend, "● 伺服器已停止", "#9ca3af") # Gray

            time.sleep(2)

    def update_status(self, label, text, color):
        label.configure(text=text, foreground=color)

    def start_server(self):
        if self.process:
            return
        
        if not os.path.exists(BACKEND_SCRIPT):
            self.log(f"錯誤: 找不到檔案 {BACKEND_SCRIPT}", "ERROR")
            return

        self.log(f"正在啟動 {BACKEND_SCRIPT}...", "SYSTEM")
        
        # Use simple creationflags for Windows to hide console window if needed, 
        # but here we capture output so CREATE_NO_WINDOW might be useful or just communicate.
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        try:
            # Run with unbuffered python (-u)
            command = [sys.executable, "-u", BACKEND_SCRIPT]
            self.process = subprocess.Popen(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                universal_newlines=True,
                bufsize=1,            # Line buffered
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            ) 
            
            # Start thread to read output
            threading.Thread(target=self.read_process_output, args=(self.process,), daemon=True).start()
            
            self.update_server_ui_state(True)
            self.log("伺服器啟動指令已發送。", "SYSTEM")

        except Exception as e:
            self.log(f"啟動失敗: {e}", "ERROR")

    def stop_server(self):
        if not self.process:
            return
            
        self.log("正在停止伺服器...", "SYSTEM")
        
        # Try to terminate gracefully first
        self.process.terminate()
        
        # On Windows, especially with debug=True enabled in Flask, it spawns child processes.
        # Often simple terminate() only kills the wrapper.
        if os.name == 'nt':
            # Force kill tree
            os.system(f"taskkill /F /T /PID {self.process.pid} >nul 2>&1")
        
        self.process = None
        self.update_server_ui_state(False)
        self.log("伺服器已停止。", "SYSTEM")

    def read_process_output(self, process):
        try:
            for line in iter(process.stdout.readline, ''):
                if line:
                    self.log(line.strip())
                if process.poll() is not None:
                    break
        except Exception as e:
            pass # Process probably closed

    def update_server_ui_state(self, is_running):
        if is_running:
            self.btn_start.config(state="disabled", bg="#064e3b")
            self.btn_stop.config(state="normal", bg="#b91c1c")
        else:
            self.btn_start.config(state="normal", bg="#047857")
            self.btn_stop.config(state="disabled", bg="#7f1d1d")

    def open_browser(self):
        self.log(f"開啟瀏覽器: {BACKEND_URL}", "SYSTEM")
        webbrowser.open(BACKEND_URL)

    def check_records(self):
        script = "check_records.py"
        if not os.path.exists(script):
             self.log("找不到 check_records.py", "ERROR")
             return
             
        self.log("執行資料檢查...", "SYSTEM")
        try:
            result = subprocess.run([sys.executable, script], capture_output=True, text=True, encoding='utf-8')
            self.log(result.stdout)
            if result.stderr:
                self.log(result.stderr, "ERROR")
        except Exception as e:
            self.log(f"執行檢查失敗: {e}", "ERROR")

if __name__ == "__main__":
    app = ServerLauncher()
    try:
        app.mainloop()
    except KeyboardInterrupt:
        if app.process:
            app.stop_server()
