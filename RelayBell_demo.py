# -*- coding: utf-8 -*-

"""

UDP 隤鮋𨺗?交𤣰蝡荔??急???UI嚚靝??坔�?典??蠘�嚚𨅯?蝡舫??Ｙ崕蝡页?銝滚�撱箏銁蝔见?鋆∴?

- 靽萘?嚗関kinter 獢屸𢒰 UI?�DP ?交𤣰?�TS?�P3/YouTube ?剜𦆮?�??單??柴��玨銵冽?蝔卝��grok嚗�虾?賂?

- Web ?�?靘?API嚗?translate嚗éini_translator 瘚�?嚗剹�?send??sendmp3??cmd??state??files??upload??download??delete??timetable/*??schedules/*??logs*??piper/*

- ?批遣 Edge TTS ??Piper嚗�洵鈭屸?雿㵪???gTTS ??SAPI5

- UI ?�??�瘙�??湛?銝餅綉?啜��玨銵具��?獢?銝𠰴�?�䌊閮�?蝔?4 ?�?嚗�?閫�蝬剜?嚗?



 ?啣??�矽?湛?

1) 頛詨� YouTube ???敺䕘??唾??�誑?�蔣?�?憿?mp3?滢?摮睃銁 UPLOADS嚗�?銝𠰴� MP3 ?諹??坔冗嚗㚁?銝血?閰脫??剜𦆮嚗�??滚⏛?歹???

2) ?滨垢蝬脣???ngrok URL ??QRCode ?寧�敶�枂?𣬚崕蝡见?閬𣇉??漤＊蝷綽??怨?鋆質??见??厰?嚗剹�?



?笔?嚗?

  python udp_receiver_with_ui_piper.py



憒�?閬�? EXE嚗朞?蝣箔???mp3?�ogo.ico?�??舫�嚗总fmpeg.exe ?曉??桅??㚚�誯? PyInstaller datas 撣嗅�??

"""

from __future__ import annotations



# ===============================

# == [ANCHOR] 雿輻鍂?�虾隤踵㟲?�憛?==

# ===============================

# [Cloud-Check] Detect environment
import os
import sys
IS_RENDER = "RENDER" in os.environ
IS_LINUX = os.name != "nt"
DISABLE_GUI = IS_RENDER or (os.environ.get("DISABLE_GUI", "False").lower() == "true")

# [Headless] Force dummy audio driver to avoid ALSA errors early
if DISABLE_GUI:
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    print(f"[audio] Headless mode detected. IS_RENDER={IS_RENDER}. Using SDL dummy audio driver.")


USE_NGROK = False           # ?喲???ngrok 撠望㺿 False

USE_MELO_TTS = False        # [NEW] ?臬炏雿輻鍂 MeloTTS (蝚??�?)
USE_EDGE_TTS = True         # ?臬炏雿輻鍂 Edge TTS (??False ?�凒?亥歲?𠬍?雿輻鍂 Piper/gTTS)

USE_AI_GENERATION = not IS_RENDER    # ?臬炏?毺鍂 AI 撱?偘蝔輻???(?脩垢?鞱身銝滚??冽𧋦??Ollama)

HTTP_PORT = int(os.environ.get("PORT", 5050)) # Render 雿輻鍂?啣?霈𦠜彍 PORT


PORT = 8888                 # UDP ??�??

YT_AUTO_CLOSE_MIN = 30      # ?刻攟撟閖�暹??芷??㚁??�?嚗争?靽萘?甈�?

TIMETABLE_SCAN_SEC = 5      # 隤脰”?�??望?嚗�?嚗?

DISABLE_UDP = IS_RENDER     # ?券𤩅蝡臭??笔? UDP ?交𤣰蝺?

DISABLE_WEB = False         # True ?�??笔? Flask + ngrok嚗�??祆?嚗?

# [NEW] Fire Alarm Hardware Config
FIRE_ALARM_PORT = None      # ?怎�閮𡃏?頛詨�??(?亥身??None ?�??毺鍂)
FIRE_ALARM_PIN = "CTS"      # ?菜葫?喃?: CTS ??DSR


# =======================================



# ---- ?望�批𥲤?伐??嫣噶 PyInstaller嚗?---

import serial, serial.tools.list_ports
if not IS_LINUX:
    try:
        import serial.win32, serial.serialwin32  # noqa: F401
    except ImportError:
        pass

try:
    import ollama
    HAS_OLLAMA = True
    OLLAMA_ERR = ""
except ImportError as e:
    print(f"[WARN] Ollama import failed: {e}")
    HAS_OLLAMA = False
    OLLAMA_ERR = str(e)



# ===============================





# ===============================

# == [ANCHOR] 璅蹱??臬�/?典?撌亙� ==

# ===============================

import sys
import os
import certifi
import ssl
import time
import json
import threading
from datetime import datetime, timedelta



# [Debug] Capture boot logs for GUI display

_BOOT_LOGS = []



def _log_boot(msg):

    print(msg)

    _BOOT_LOGS.append(msg)


# [AUTO-ENVIRONMENT-SWITCH]
# [AUTO-ENVIRONMENT-SWITCH]
# Check if we need to switch to AI environment immediately
# if globals().get("USE_MELO_TTS", True): # Default True here for check
#     import sys
#     import os
#     import subprocess
#     
#     # Define expected AI python path
#     _ai_env_py = r"d:\PythonTest\BreezyVoice_Local\venv\Scripts\python.exe"
#     
#     # If the target env exists, and we are NOT currently running it, and NOT frozen
#     if not getattr(sys, 'frozen', False) and os.path.exists(_ai_env_py) and sys.executable.lower() != _ai_env_py.lower():
#         print(f"[BOOT] Detecting Environment...")
#         print(f"[BOOT] Current: {sys.executable}")
#         print(f"[BOOT] Target : {_ai_env_py}")
#         print(f"[BOOT] Switching to AI environment...")
#         
#         try:
#             # Re-launch this script using the correct python
#             subprocess.call([_ai_env_py, os.path.abspath(__file__)] + sys.argv[1:])
#             sys.exit(0) # Stop this instance
#         except Exception as switch_e:
#              print(f"[BOOT] Auto-switch failed: {switch_e}")
#              # Continue anyway, might fallback to EdgeTTS

# [DEBUG] Global Exception Hook for Frozen App
def _global_excepthook(exc_type, exc_value, exc_traceback):
    try:
        import traceback
        err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        with open("startup_crash.log", "w", encoding="utf-8") as f:
            f.write(f"Timestamp: {datetime.now()}\n")
            f.write("Global Crash:\n")
            f.write(err_msg)
    except: pass

if getattr(sys, 'frozen', False):
    sys.excepthook = _global_excepthook



# [Fix] Explicitly set SSL cert path for PyInstaller frozen environment

# MUST be done before importing requests/aiohttp/ssl

if getattr(sys, 'frozen', False):

    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))

    candidates = [

        os.path.join(base_path, 'cacert.pem'),  # Prioritize root (explicitly bundled)

        os.path.join(base_path, 'certifi', 'cacert.pem'),

        certifi.where()

    ]

    found = False

    for p in candidates:

        if os.path.exists(p):

            os.environ['SSL_CERT_FILE'] = p

            os.environ['REQUESTS_CA_BUNDLE'] = p  # Also set for requests

            

            # [Monkeypatch] Force certifi.where() to return this path

            # This ensures libraries calling certifi directly get the correct file

            def override_where():

                return p

            certifi.where = override_where
            
            # [CRITICAL] ?游?蝳�鍂 SSL 撽𡑒?隞乩耨敺?Frozen App 銝剔? Edge TTS ????誯?
            try:
                ssl._create_default_https_context = ssl._create_unverified_context
            except Exception: pass


            

            _log_boot(f"[SETUP] Frozen mode: Set SSL_CERT_FILE to {p}")

            _log_boot(f"[SETUP] Frozen mode: Monkeypatched certifi.where() to {p}")

            

            # [Monkeypatch] Force ssl.create_default_context to use our cert

            # This fixes aiohttp/edge-tts if they rely on default SSL context and ignore env vars

            _orig_create_default_context = ssl.create_default_context

            def _patched_create_default_context(purpose=ssl.Purpose.SERVER_AUTH, *, cafile=None, capath=None, cadata=None):
                # [CRITICAL UPDATE] Force unverified context even if called explicitly
                return ssl._create_unverified_context(purpose=purpose, cafile=None, capath=None, cadata=cadata)
            ssl.create_default_context = _patched_create_default_context
            _log_boot(f"[SETUP] Frozen mode: Monkeypatched ssl.create_default_context to use {p}")

            # [CRITICAL FIX] Monkeypatch inspect.getsource to avoid "could not get source code" in frozen app
            import inspect
            _orig_getsource = inspect.getsource
            _orig_getfile = inspect.getfile

            def _patched_getsource(obj):
                try:
                    return _orig_getsource(obj)
                except (OSError, IOError) as e:
                    # Return dummy source if actual source is missing (common in granular frozen apps)
                    return "def dummy_func(*args, **kwargs): pass"
            
            def _patched_getfile(obj):
                try:
                    return _orig_getfile(obj)
                except (OSError, IOError, TypeError):
                    return "dummy_source_file.py"

            inspect.getsource = _patched_getsource
            inspect.getfile = _patched_getfile
            _log_boot(f"[SETUP] Frozen mode: Monkeypatched inspect.getsource to suppress source code errors")
            
            found = True
            break

    if not found:

        _log_boot(f"[SETUP] Frozen mode: Warning - cacert.pem not found in candidates: {candidates}")

        os.environ['SSL_CERT_FILE'] = certifi.where()

else:

    os.environ['SSL_CERT_FILE'] = certifi.where()

    _log_boot(f"[SETUP] Script mode: Set SSL_CERT_FILE to {certifi.where()}")



_log_boot(f"[SETUP] ssl.get_default_verify_paths() = {ssl.get_default_verify_paths()}")



import socket, csv, queue, time
if not DISABLE_GUI:
    import tkinter as tk, tkinter.ttk as ttk
else:
    # Minimal mock for DISABLE_GUI mode to prevent NameErrors
    tk = None
    ttk = None


import tempfile, asyncio, requests, uuid, re, subprocess, ctypes, webbrowser, shutil, atexit, signal, glob

import secrets, hashlib
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from datetime import date, time as dtime

# [Fix] Explicitly register Content-Types to avoid registry issues on Windows
import mimetypes
mimetypes.add_type('text/html', '.html')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('application/json', '.json')





# ===============================

# == [ANCHOR] Tkinter UI嚗? ?�?嚗?==

from pathlib import Path

if not DISABLE_GUI:
    from tkinter import filedialog, messagebox, simpledialog
    from tkinter.scrolledtext import ScrolledText
else:
    # Mocks for headless mode
    filedialog = messagebox = simpledialog = ScrolledText = None


from functools import wraps

from urllib.parse import quote

import pygame

import yt_dlp

import edge_tts

from flask import Flask, request, send_from_directory, jsonify, abort, redirect, send_file, render_template, render_template_string, url_for, session, make_response

from flask_sock import Sock



# bcrypt for password hashing

try:

    import bcrypt

    _HAS_BCRYPT = True

except ImportError:

    _HAS_BCRYPT = False

    print("[AUTH] Warning: bcrypt not installed. Authentication will be disabled. Install with: pip install bcrypt")

# [NEW] Chime Config
CHIME_ENABLED = True
try:
    _chime_cfg_p = os.path.join(DATA_DIR, "chime_config.json")
    if os.path.exists(_chime_cfg_p):
        with open(_chime_cfg_p, "r") as f:
            CHIME_ENABLED = json.load(f).get("enabled", True)
except: pass

def _save_chime_config():
    try:
        _chime_cfg_p = os.path.join(DATA_DIR, "chime_config.json")
        with open(_chime_cfg_p, "w") as f:
            json.dump({"enabled": CHIME_ENABLED}, f)
    except: pass




# ==== [schedules ?脣? JSON 閫??撌亙] ====

def _ensure_obj(value):

    """Ensure the value is a dictionary or list, even if it is a JSON string."""

    if not isinstance(value, str):

        return value

    try:

        v = json.loads(value)

    except Exception:

        return value

    if isinstance(v, str):

        try:

            v2 = json.loads(v)

            return v2

        except Exception:

            return v

    return v



def _get_json_tolerant():

    """Tolerantly get JSON from the request."""

    data = request.get_json(silent=True)

    if data is None:

        raw = request.data.decode('utf-8', errors='ignore') if request.data else None

        if raw:

            data = _ensure_obj(raw)

        elif request.form:

            payload = request.form.get('payload')

            data = _ensure_obj(payload) if payload else dict(request.form)

    return _ensure_obj(data)



def _debug_req(prefix='[DEBUG]/schedules'):

    print(f"{prefix} content_type={request.headers.get('Content-Type')}, len={len(request.data or b'')}, is_json={request.is_json}")

from gtts import gTTS

from serial.tools import list_ports



try:

    from waitress import serve as _serve

    _HAS_WAITRESS = True

except Exception:

    _HAS_WAITRESS = False



# ===============================

# == [ANCHOR] 蝧餉陌?嘥???==

# ===============================

try:
    from deep_translator import GoogleTranslator
    HAS_DEEPTRANS = True
except ImportError:
    HAS_DEEPTRANS = False
    print("[translate] deep_translator not installed.")



# ===============================

# == [ANCHOR] Location & Weather Helper ==

# ===============================



def _get_server_location():

    """Detect server location (lat, lon, city, region) via IP APIs."""

    # Default: Taipei 101

    res = {"lat": 25.0330, "lon": 121.5654, "city": "Taipei", "region": "Taipei City"}

    

    try:

        # Method 1: ip-api.com

        loc_r = requests.get("http://ip-api.com/json/?fields=status,lat,lon,city,regionName&lang=zh-CN", timeout=3)

        if loc_r.status_code == 200:

            loc_data = loc_r.json()

            if loc_data.get("status") == "success":

                res["lat"] = loc_data.get("lat", res["lat"])

                res["lon"] = loc_data.get("lon", res["lon"])

                res["city"] = loc_data.get("city") or res["city"]

                res["region"] = loc_data.get("regionName") or res["region"]

                print(f"[Location] Auto-detected (ip-api): {res}")

                return res

    except Exception:

        pass



    try:

        # Method 2: ipwho.is

        loc_r2 = requests.get("https://ipwho.is/?lang=zh-CN", timeout=5)

        if loc_r2.status_code == 200:

            data2 = loc_r2.json()

            if data2.get("success"):

                res["lat"] = data2.get("latitude", res["lat"])

                res["lon"] = data2.get("longitude", res["lon"])

                res["city"] = data2.get("city") or res["city"]

                res["region"] = data2.get("region") or res["region"]

                print(f"[Location] Auto-detected (ipwho.is): {res}")

                return res

    except Exception:

        pass

        

    return res



def _get_weather_report():
    loc = _get_server_location()
    lat = loc["lat"]
    lon = loc["lon"]
    loc_name = loc["city"] or loc["region"] or "Taipei"

    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code&timezone=auto"
        r = requests.get(url, timeout=5)
        if r.status_code != 200: return "Weather data currently unavailable."
        
        data = r.json().get("current", {})
        temp = data.get("temperature_2m", "N/A")
        humid = data.get("relative_humidity_2m", "N/A")
        
        now_str = datetime.now().strftime("%H:%M")
        return f"Current weather in {loc_name} at {now_str}: Temperature {temp}°C, Humidity {humid}%."
    except Exception as e:
        print("Weather error:", e)
        return "Failed to fetch weather data."



# ---- qrcode嚗𥅾?∪?隞交?蝷箔誨?選?----

try:

    import qrcode

    from PIL import Image, ImageTk

    _HAS_QR = True

except Exception:

    _HAS_QR = False



# ===============================

# == [ANCHOR] 頝臬??�??坔冗 ==

# ===============================





def _is_frozen():

    return getattr(sys, "frozen", False)



def resource_path(relative_path: str) -> str:

    if getattr(sys, "frozen", False):

        exe_dir = os.path.dirname(sys.executable)

        p1 = os.path.join(exe_dir, relative_path)

        if os.path.exists(p1): return p1

        if hasattr(sys, "_MEIPASS"):

            p2 = os.path.join(sys._MEIPASS, relative_path)

            if os.path.exists(p2): return p2

        return p1

    base = os.path.abspath(os.path.dirname(__file__))

    return os.path.join(base, relative_path)



if _is_frozen():

    try: os.chdir(os.path.dirname(sys.executable))

    except Exception: pass



# ===============================

# == [ANCHOR] Flask App Init ==

# ===============================

def get_data_dir():

    if os.name == "nt":

        base = os.getenv("LOCALAPPDATA") or os.path.expanduser("~")

        return os.path.join(base, "udp_http_receiver")

    return os.path.join(os.path.expanduser("~/.local/share"), "udp_http_receiver")



APP_DIR = (os.path.dirname(sys.executable) if _is_frozen()

           else os.path.abspath(os.path.dirname(__file__)))



DATA_DIR   = get_data_dir()

UPLOAD_DIR = os.path.join(APP_DIR, "UploadedMP3")

os.makedirs(UPLOAD_DIR, exist_ok=True)

RECORD_DIR = os.path.join(APP_DIR, "Recoding")

os.makedirs(RECORD_DIR, exist_ok=True)


# ===============================
# == [ANCHOR] MeloTTS Setup ==
# ===============================

MELO_SPEAKER = "ZH" # [NEW] ?典? Melo 隤噼�?ID (?鞱身銝剜?)
HAS_MELO = False
MELO_ERR = ""
melo_model = None

try:
    _melo_state = globals().get("USE_MELO_TTS", False)
    print(f"[DEBUG-INIT] Starting Setup Check. USE_MELO_TTS is: {_melo_state}")
    
    if _melo_state:
        print(f"[DEBUG-INIT] Entering MeloTTS setup block...")
        try:
             import torch
             # Try importing MeloTTS
             # Installation: pip install melotts
             try:
                from melo.api import TTS
             except ImportError:
                # Try fallback or re-raise
                print("[SETUP] melo.api not found. Please run: pip install melotts")
                raise

             # Check device
             device = 'cuda' if torch.cuda.is_available() else 'cpu'
             print(f"[SETUP] Initializing MeloTTS (ZH) on {device}...")
             
             # Initialize Model (Auto-download if needed)
             # Note: This might take time on first run
             _log_boot(f"[SETUP] Loading MeloTTS model (Device={device})...")
             melo_model = TTS(language='ZH', device=device)
             
             HAS_MELO = True
             _log_boot("[SETUP] MeloTTS Loaded Successfully.")
             
             try:
                 spks = melo_model.hps.data.spk2id
                 print(f"[SETUP] Available Melo Speakers: {spks}")
             except: pass
             
        except ImportError as e:
             HAS_MELO = False
             MELO_ERR = f"Import Error: {e} (Please pip install melotts)"
             _log_boot(f"[WARN] MeloTTS Import Failed: {e}")
        except Exception as e:
             HAS_MELO = False
             MELO_ERR = str(e)
             import traceback
             full_trace = traceback.format_exc()
             print(f"[DEBUG-INIT] MeloTTS init failed:\n{full_trace}")
             _log_boot(f"[WARN] MeloTTS Init Failed: {e}")

except Exception as e:
    HAS_MELO = False
    MELO_ERR = str(e)
    print(f"[DEBUG-INIT] General Exception caught: {e}")



# [Changed] Define global executable paths using resource_path for PyInstaller

_FFMPEG = resource_path("ffmpeg.exe")

if not os.path.exists(_FFMPEG):

    # Fallback to system path or APP_DIR if not in bundled resources

    _FFMPEG = os.path.join(APP_DIR, "ffmpeg.exe")

    if not os.path.exists(_FFMPEG):

        _FFMPEG = "ffmpeg" # Depend on PATH



_MPV = resource_path("mpv.exe")

if not os.path.exists(_MPV):

    _MPV = os.path.join(APP_DIR, "mpv.exe")

    if not os.path.exists(_MPV):

        _MPV = None





def _copytree_preserve(src: str, dst: str) -> None:

    """Copy directory tree without clobbering existing user edits."""

    if not os.path.isdir(src):

        return

    for root, dirs, files in os.walk(src):

        rel = os.path.relpath(root, src)

        target_root = dst if rel in (".", "") else os.path.join(dst, rel)

        os.makedirs(target_root, exist_ok=True)

        for file_name in files:

            src_file = os.path.join(root, file_name)

            dst_file = os.path.join(target_root, file_name)

            if os.path.exists(dst_file):

                continue

            try:

                shutil.copy2(src_file, dst_file)

            except Exception as copy_exc:

                print(f"[STATIC] Copy {src_file} failed: {copy_exc}")





def _prepare_static_root() -> str:

    """Prefer external static/ui files so HTML can stay outside the executable."""

    env_dir = os.environ.get("UDP_STATIC_DIR")

    if env_dir:

        env_dir = os.path.abspath(env_dir)

        if os.path.isdir(env_dir):

            print(f"[STATIC] Using UDP_STATIC_DIR={env_dir}")

            return env_dir

        print(f"[STATIC] UDP_STATIC_DIR set to {env_dir} but directory missing, falling back.")



    external_dir = os.path.join(APP_DIR, "static")

    if os.path.isdir(external_dir):

        return external_dir



    packaged_dir = resource_path("static")

    if os.path.isdir(packaged_dir) and packaged_dir != external_dir:

        try:

            _copytree_preserve(packaged_dir, external_dir)

            print(f"[STATIC] Copied packaged static assets to {external_dir}")

            return external_dir

        except Exception as exc:

            print(f"[STATIC] Failed to copy packaged static assets: {exc}")

            return packaged_dir



    try:

        os.makedirs(external_dir, exist_ok=True)

    except Exception as exc:

        print(f"[STATIC] Could not create {external_dir}: {exc}")

    return external_dir





STATIC_ROOT = _prepare_static_root()

UI_TEMPLATE_DIR = os.path.join(STATIC_ROOT, "ui")

os.makedirs(UI_TEMPLATE_DIR, exist_ok=True)



app = Flask(__name__, static_folder=STATIC_ROOT, static_url_path='/static')

app.config['TEMPLATES_AUTO_RELOAD'] = True  # Enable template auto-reload

app.template_folder = UI_TEMPLATE_DIR

sock = Sock(app)

app.secret_key = secrets.token_hex(16)

@app.route('/api/speak_v2', methods=['POST'])
def api_speak_v2():
    try:
        d = request.form if request.form else request.get_json(silent=True) or {}
        text = d.get("text")
        lang = d.get("lang")
        gender = d.get("gender")
        
        if not text: return jsonify(ok=False, error="no text"), 400
        
        # Prepend metadata
        meta = ""
        if lang and lang != "auto": meta += f"L={lang}|"
        if gender and gender != "auto": meta += f"G={gender}|"
        
        if meta:
            if meta.endswith("|"): meta = meta[:-1]
            text = f"{{{{{meta}}}}}" + text

        # Queue it
        handle_msg(text, ("API_V2", request.remote_addr))
        return jsonify(ok=True, message="queued")
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

@app.route('/api/get_relay_config')
def api_get_relay_config():
    return jsonify(ok=True, auto_on=RELAY_AUTO_ON)

@app.route('/api/set_relay_config', methods=['POST'])
def api_set_relay_config():
    global RELAY_AUTO_ON
    try:
        data = request.json or {}
        val = data.get('auto_on')
        if val is not None:
             RELAY_AUTO_ON = bool(val)
             _save_relay_config()
             
             # Sync Tkinter if running
             try:
                 if 'relay_auto_var' in globals():
                     ui_safe(lambda: relay_auto_var.set(RELAY_AUTO_ON))
             except: pass
             
        return jsonify(ok=True, auto_on=RELAY_AUTO_ON)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

@app.route('/api/tts_preview', methods=['POST'])
def api_tts_preview():
    import edge_tts, asyncio, io
    from flask import send_file
    try:
        d = request.json or {}
        text = d.get('text')
        lang = d.get('lang')
        gender = d.get('gender')
        rate_val = d.get('rate', 0)
        
        if not text: return jsonify(ok=False, error="No text"), 400
        
        # Resolve voice using existing function
        # lang might be 'nan', 'nan-TW' -> get_voice_id_auto fallback to zh-TW?
        # If user selects 'nan', we expect zh-TW fallback or error.
        # But get_voice_id_auto handles 'auto' too.
        
        # Map rate to EdgeTTS format string e.g., "+10%" or "-10%"
        try:
            r_int = int(rate_val)
            rate_str = f"{r_int:+d}%"
        except:
            rate_str = "+0%"
            
        voice = get_voice_id_auto(text, lang_code=lang, gender_code=gender)
        
        async def _gen():
            tts = edge_tts.Communicate(text, voice, rate=rate_str)
            out = io.BytesIO()
            async for chunk in tts.stream():
                if chunk["type"] == "audio":
                    out.write(chunk["data"])
            out.seek(0)
            return out

        # Run async generation in a fresh loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio_io = loop.run_until_complete(_gen())
        loop.close()
        
        return send_file(audio_io, mimetype="audio/mpeg", as_attachment=False, download_name="preview.mp3")

    except Exception as e:
        print(f"[TTS_PREVIEW] Error: {e}")
        return jsonify(ok=False, error=str(e)), 500



@app.route('/api/get_chime_config')
def api_get_chime_config():
    return jsonify(ok=True, enabled=CHIME_ENABLED)

@app.route('/api/set_chime_config', methods=['POST'])
def api_set_chime_config():
    global CHIME_ENABLED
    try:
        data = request.json or {}
        val = data.get('enabled')
        if val is not None:
             CHIME_ENABLED = bool(val)
             # Save to voice config (reuse existing persistence)
             _save_voice_config()
             
             # Sync Tkinter if running
             try:
                 if 'chime_var' in globals():
                     ui_safe(lambda: chime_var.set(CHIME_ENABLED))
             except: pass
             
        return jsonify(ok=True, enabled=CHIME_ENABLED)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

@app.route('/api/translate', methods=['POST'])
def api_translate():
    if not HAS_DEEPTRANS:
        return jsonify(ok=False, error="Translation module not available"), 501
    try:
        data = request.json or request.form
        if not data:
            data = request.get_json(silent=True) or {}
        
        text = data.get('text')
        target = data.get('target', 'zh-TW')
        source = data.get('source', 'auto')
        
        if not text:
            return jsonify(ok=False, error="Missing text"), 400
            
        from deep_translator import GoogleTranslator
        translated = GoogleTranslator(source=source, target=target).translate(text)
        return jsonify(ok=True, translated=translated)
    except Exception as e:
        print(f"[TRANSLATE] Error: {e}")
        return jsonify(ok=False, error=str(e)), 500

@app.route('/demo')
def demo_page():
    return render_template('demo.html')


@app.route('/api/melo_voices')
def api_melo_voices():
    if not HAS_MELO or not melo_model:
        return jsonify(ok=False, error="Melo not ready")
    try:
        spks = melo_model.hps.data.spk2id
        return jsonify(ok=True, voices=spks)
    except Exception as e:
        return jsonify(ok=False, error=str(e))

@app.route('/api/melo_status')
def api_melo_status():
    return jsonify(ok=True, ready=HAS_MELO, speaker=MELO_SPEAKER, enabled=USE_MELO_TTS, error=MELO_ERR)

@app.route('/g/<group_id>')
def group_view(group_id):
    """Serve student.html for group viewing with autoplay enabled."""
    try:
        # Serve student.html with autoplay=1 parameter
        from flask import send_file, make_response
        student_html_path = os.path.join(UI_TEMPLATE_DIR, 'student.html')
        
        if not os.path.exists(student_html_path):
            return f"Error: student.html not found at {UI_TEMPLATE_DIR}", 404
        
        # Read the HTML file
        with open(student_html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Create response with proper MIME type
        response = make_response(html_content)
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
        
        # Note: The student_agent.py already appends ?autoplay=1 to URLs containing '/g/'
        # so we don't need to modify the HTML here
        return response
    except Exception as e:
        return f"Error loading group view: {str(e)}", 500

@app.route('/api/ai_script', methods=['POST'])
def api_ai_script():
    """Call Ollama Gemma 2 (2B) to generate broadcast script."""
    # Check config first, fallback to global constant if key missing
    if not config.get("use_ai_generation", USE_AI_GENERATION):
        return jsonify(ok=False, error="AI ?�??蠘�撌脣???(隢贝秐閮剖??�𢒰?见?)"), 403

    if not HAS_OLLAMA:
        return jsonify(ok=False, error=f"Ollama library not installed. Details: {OLLAMA_ERR}"), 501

    try:
        data = request.json or request.form
        keyword = data.get('keyword')
        if not keyword:
            return jsonify(ok=False, error="Missing keyword"), 400
            
        system_prompt = """
        雿删𣶹?冽糓?啣?撣�?銝剖??�誨?剔頂蝯?AI ?拍???
        隢𧢲覔?帋蝙?刻��?靘𤤿??屸??萄??㵪??�?銝�畾萇? 50-100 摮梹?隤墧除閬芸??�迤撘讐??∪?撱?偘蝔踴�?
        
        ?鞾?閬�?蝭��?
        1. ?�撓?箝�𣬚??�??滚�摰對?蝯訫?蝳�迫雿輻鍂隞颱?銵冽?蝚西? (?𤃬???�arkdown ?澆? (??*蝎烾?**)?�???(=) ?硋�隞𣇉鸌畾羓泵?麄�?
        2. ?�??蹱?皞𡝗?暺䂿泵??(嚗䎚����?嚗�??䎚�???
        3. ?刻?敹�?皜�苊?𡒊Ⅱ嚗屸�?滢蝙?典捆?㯄�䭾??湧𨺗摮𡑒炊霈�?�?敶?(靘见?嚗𡁻�?溻�諹??滨?憭𡁻𨺗摮梹??寧鍂?湔?蝣箇?閰???
        4. 隤𧼮蘂閬��𡁻?瘚�噐嚗屸�?�??喳???(TTS) ?𡑒???
        5. 隢衤蝙?函?擃𥪯葉?�?銝滩?雿輻鍂?望???
        """
        
        user_input = f"撱?偘?𣈯枤摮梹?{keyword}"
        print(f"[AI] Generating script for: {keyword} using Gemma 2 (2B)")
        
        # Invoke Ollama
        try:
            response = ollama.chat(model='gemma2:2b', messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_input},
            ])
        except ollama.ResponseError as e:
            if e.status_code == 404:
                print(f"[AI] Model not found: {e}")
                return jsonify(ok=False, error="AI Model not found. Please run 'ollama pull gemma2:2b' first."), 404
            raise e
        
        result_text = response['message']['content'].strip()
        
        # [Safety] Strip potential garbage if AI hallucinated tags
        import re
        result_text = re.sub(r"^@\w+[:嚗鞲\s*", "", result_text)
        result_text = re.sub(r"\{\{.*?\}\}", "", result_text) # Strip metadata if AI generated it
        
        # [Cleanup] Remove equal signs and other unwanted symbols as requested
        result_text = result_text.replace("=", "").replace("*", "").replace("#", "")
        
        # [Strict Cleanup] Remove Emojis and other non-text symbols
        # Filter out characters outside of Basic Multilingual Plane (often emojis) and specific symbol ranges
        # This regex removes supplementary characters (where most emojis live) and some common symbol ranges
        result_text = re.sub(r'[\U00010000-\U0010ffff]', '', result_text) 
        # Also remove specific miscellaneous symbols if any remain
        result_text = re.sub(r'[\u2600-\u27BF\u2300-\u23FF]', '', result_text)

        return jsonify(ok=True, script=result_text)
        
    except Exception as e:
        print(f"[AI] Generation failed: {e}")
        return jsonify(ok=False, error=str(e)), 500

@app.route('/api/get_timetable_status')
def api_get_timetable_status():
    return jsonify(ok=True, enabled=timetable_enabled, count=STATE["timetable"]["count"])

# [Waitress Detected at boot, no override needed]
# ===============================

@app.errorhandler(404)

def page_not_found(e):

    # Log 404 to main GUI to help debugging

    try:

        url = request.path

        method = request.method

        msg = f"??404 Not Found: {method} {url}"

        print(msg)

        text_area_insert(msg, "Web")

    except: 

        pass

    return e



@app.route("/mic")

def mobile_mic_redirect():

    return redirect("/static/ui/broadcast.html")



@app.route('/favicon.ico')

def favicon():

    return send_from_directory(APP_DIR, 'logo.ico', mimetype='image/vnd.microsoft.icon')







# ===============================

# == [ANCHOR] WebSocket Live Stream (Relay) ==

# ===============================

LIVE_CLIENTS = set()

LIVE_HEADER_CHUNKS = [] # Cache first few chunks for new viewers

RELAY_BROADCASTER_WS = None



# = [ANCHOR] WebSocket Signaling (P2P Call) ==
# ===============================
CALL_CLIENTS = {}

# ===============================
# == [ANCHOR] WebSocket Agent Command Pump ==
# ===============================
@sock.route('/ws/agent')
def ws_agent_handler(ws):
    client_id = None
    try:
        print(f"[WS-Agent] New connection from {request.remote_addr}")
        while True:
            data = ws.receive()
            if not data: break
            
            # Protocol: REGISTER|{id}|{group}
            if data.startswith("REGISTER|"):
                parts = data.split("|")
                if len(parts) >= 2:
                    client_id = parts[1]
                    group = parts[2] if len(parts) > 2 else "default"
                    with AGENT_WS_LOCK:
                        # Close existing if duplicate
                        if client_id in AGENT_WS_CLIENTS and AGENT_WS_CLIENTS[client_id] != ws:
                            try: AGENT_WS_CLIENTS[client_id].close()
                            except: pass
                        AGENT_WS_CLIENTS[client_id] = ws
                    print(f"[WS-Agent] Registered: {client_id} ({group})")
                    ws.send("REGISTERED|OK")
            elif data == "PING":
                ws.send("PONG")
    except Exception as e:
        print(f"[WS-Agent] Connection error ({client_id}): {e}")
    finally:
        if client_id:
            with AGENT_WS_LOCK:
                if AGENT_WS_CLIENTS.get(client_id) == ws:
                    del AGENT_WS_CLIENTS[client_id]
            print(f"[WS-Agent] Disconnected: {client_id}")



@sock.route('/ws/live')

def live_stream(ws):

    global RELAY_BROADCASTER_WS, LIVE_HEADER_CHUNKS

    

    # 1. Parse Role

    # flask-sock passes the WebSocket, but we can access `request` context

    role = request.args.get('role', 'subscriber')

    

    # Check if we assume it's a broadcaster (simple auth: if they claim so)

    # In a real app, check a token. Here, trust the query param.

    is_broadcaster = (role == 'broadcaster')



    print(f"[WS] Connect: IP={request.remote_addr}, Role={role}")



    if is_broadcaster:

        # == Broadcaster Setup ==

        # Kick off existing broadcaster if any? Or reject?

        # Let's overwrite for simplicity (last one wins)

        if RELAY_BROADCASTER_WS and RELAY_BROADCASTER_WS != ws:

             try: RELAY_BROADCASTER_WS.close()

             except: pass

        

        RELAY_BROADCASTER_WS = ws

        LIVE_HEADER_CHUNKS.clear() # New stream, new headers

        

        # Start Local Playback (FFplay)

        # Stop any audio

        try:

            pygame.mixer.music.stop()

            pygame.mixer.stop()

        except: pass

        



        

        text_area_insert(f"?𣞁 ?湔偘靘�?撌脤�?? ({request.remote_addr})", "Live")

        

        proc = None

        

        # Priority: MPV -> FFplay

        _MPV = os.path.join(APP_DIR, "mpv.exe")

        if not os.path.exists(_MPV): _MPV = None



        if _MPV:

             # Use MPV (Better for streaming pipes)

            cmd = [_MPV, 

                   "--no-terminal", 

                   "--force-window=no", 

                   "--video=no", 

                   "--cache=no", 

                   "--demuxer-thread=no", 

                   "--untimed", 

                   "--profile=low-latency",

                   "--audio-buffer=0",       # Minimize audio buffer

                   "--stream-buffer-size=4k",# Minimize input stream buffer

                   "--volume=500",           # Boost volume 500%

                   "-"]

            try:

                proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, bufsize=0)

                print(f"[WS] MPV started PID={proc.pid}")

                text_area_insert(f"?湔偘?剜𦆮??MPV)?笔? (PID={proc.pid})", "Live")

            except Exception as e:

                text_area_insert(f"??MPV ?笔?憭望?: {e}", "Live")

        

        elif _FFMPEG:

             # Use FFplay

             cmd = [_FFMPEG.replace("ffmpeg.exe", "ffplay.exe").replace("ffmpeg", "ffplay"), 

                   "-i", "-", 

                   "-nodisp", "-autoexit", 

                   "-fflags", "nobuffer", 

                   "-flags", "low_delay", 

                   "-framedrop", 

                   "-strict", "experimental",

                   "-probesize", "32",       # Minimal probe size (32 bytes)

                   "-analyzeduration", "0",  # No analyze duration

                   "-avioflags", "direct",   # Reduce IO buffering

                   "-sync", "ext",

                   "-af", "volume=5.0"]      # Boost volume 500%

             

             try:

                 # Capture stderr for debugging

                 proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, bufsize=0)

                 print(f"[WS] FFplay started PID={proc.pid}")

                 text_area_insert(f"?湔偘?剜𦆮??FFplay)?笔? (PID={proc.pid})", "Live")

             except Exception as e:

                 msg = f"Player startup failed: {e}"

                 print(msg)

                 text_area_insert(f"??{msg}", "Live")

        else:

             msg = "Missing player: mpv/ffmpeg/ffplay not found."

             print(f"[WS] {msg}")

             text_area_insert(f"?𩤃? {msg}", "Live")





        # Loop

        try:

            chunk_count = 0

            while True:

                data = ws.receive()

                if data:

                    chunk_count += 1

                    if chunk_count % 50 == 0:

                        print(f"[WS] Received chunk #{chunk_count}, len={len(data)}")



                    # 1. Cache Header

                    if len(LIVE_HEADER_CHUNKS) < 3:

                        LIVE_HEADER_CHUNKS.append(data)

                    

                    # 2. Relay to Subscribers

                    try:

                        subscribers = list(LIVE_CLIENTS)

                        for sub in subscribers:

                            try:

                                sub.send(data)

                            except:

                                LIVE_CLIENTS.discard(sub)

                    except Exception as e:

                        print(f"[WS] Relay error: {e}")



                    # 3. Pipe to Local FFplay

                    if proc and proc.stdin:

                        try:

                            # Check if process is still alive

                            if proc.poll() is not None:

                                msg = f"?湔偘?剜𦆮?其葉??(Code: {proc.returncode})"

                                print(f"[WS] {msg}")

                                text_area_insert(f"??{msg}", "Live")

                                

                                stderr_out = proc.stderr.read()

                                if stderr_out:

                                    err_str = stderr_out.decode('utf-8', errors='ignore')

                                    print(f"[WS] FFplay Stderr: {err_str}")

                                    text_area_insert(f"?航炊閮𦠜�: {err_str[:200]}", "Live")

                                proc = None

                            else:

                                proc.stdin.write(data)

                                proc.stdin.flush()

                        except Exception as e:

                             print(f"[WS] Write to ffplay fail: {e}")

                             proc = None

                else:

                    break

        except Exception as e:

            print(f"[WS] Broadcaster Error: {e}")

        finally:

            # Cleanup

            if RELAY_BROADCASTER_WS == ws:

                RELAY_BROADCASTER_WS = None

                LIVE_HEADER_CHUNKS.clear()

                text_area_insert(f"?對? ?湔偘靘�??瑞?", "Live")



                # Force disconnect all subscribers so they reset

                try:

                    for sub in list(LIVE_CLIENTS):

                        try: sub.close()

                        except: pass

                    LIVE_CLIENTS.clear()

                except Exception as e:

                    print(f"[WS] Error closing subs: {e}")



                if proc:

                    try: proc.kill()

                    except: pass

                    

    else:

        # == Subscriber Setup ==

        LIVE_CLIENTS.add(ws)

        # Send Cached Headers immediately

        if LIVE_HEADER_CHUNKS:

            try:

                for chunk in LIVE_HEADER_CHUNKS:

                    ws.send(chunk)

            except: pass

            

        try:

            # Just keep connection open to receive

            while True:

                # We don't expect data from subscriber, but we must read to keep socket alive?

                # Or just block.

                data = ws.receive()

                if not data: break 

                # Ignore received data from subscriber

        except:

            pass

        finally:

            LIVE_CLIENTS.discard(ws)

            print(f"[WS] Subscriber disconnected: {request.remote_addr}")



@sock.route('/ws/call')

def call_signaling(ws):

    global CALL_CLIENTS

    my_id = None

    try:

        while True:

            data = ws.receive()

            if not data: break

            

            try:

                msg = json.loads(data)

                mtype = msg.get('type')

                

                if mtype == 'login':

                    my_id = msg.get('id')

                    CALL_CLIENTS[my_id] = ws

                    print(f"[WS-Call] user {my_id} logged in")

                    ws.send(json.dumps({'type': 'login_ack', 'id': my_id}))

                    

                elif mtype in ('offer', 'answer', 'candidate', 'ready', 'invite', 'text_message'):

                    target = msg.get('target')

                    target_ws = CALL_CLIENTS.get(target)

                    if target_ws:

                        try:

                            target_ws.send(data)

                        except:

                            print(f"[WS-Call] Failed to send to {target}")

                    else:

                        print(f"[WS-Call] Target {target} not found")

                        # Notify sender?

                        

                elif mtype == 'list_users':

                    # Optional: send list of connected signaling users

                    users = list(CALL_CLIENTS.keys())

                    ws.send(json.dumps({'type': 'user_list', 'users': users}))



                else:

                    print(f"[WS-Call] Unknown type {mtype}")

                    

            except Exception as e:

                print(f"[WS-Call] Error processing: {e}")

                

    except Exception as e:

        print(f"[WS-Call] Connection error: {e}")

    finally:

        if my_id and CALL_CLIENTS.get(my_id) == ws:

            del CALL_CLIENTS[my_id]

        print(f"[WS-Call] user {my_id} disconnected")



# ===============================

# == [ANCHOR] Audio Blob Playback ==

# ===============================

@app.route('/api/speak_audio_blob', methods=['POST'])

def api_speak_audio_blob():

    """Upload and play audio blob immediately."""

    try:

        auto_unmute_if_needed()

        f = request.files.get('file')

        if not f: return jsonify(ok=False, error="no file"), 400

        

        # Save temp file

        ext = os.path.splitext(f.filename or "rec.wav")[1] or ".wav"

        fname = f"rec_{int(time.time())}_{secrets.token_hex(4)}{ext}"

        # [MODIFIED] Use RECORD_DIR for mic recordings

        save_path = os.path.join(RECORD_DIR, fname)

        f.save(save_path)

        

        print(f"[Debug] ?嗅�?�𨺗銝𠰴�: {save_path} (Size: {os.path.getsize(save_path)} bytes)")



        # Fix: Check for empty or too small files (prevent FFmpeg crash)

        file_size = os.path.getsize(save_path)

        if file_size < 1024:

            try: os.remove(save_path)

            except: pass

            msg = f"?�𨺗瑼娍??𤾸? ({file_size} bytes)嚗�虾?賡??喳仃?埈??�?憭芰�"

            text_area_insert(f"??{msg}", "Rec")

            return jsonify(ok=False, error=msg), 400



        # Fix: Convert webm/other to MP3 for consistency and Pygame compatibility

        if ext.lower() == ".webm":

            if not _FFMPEG:

                err = "ffmpeg not found. Please install ffmpeg.exe."

                text_area_insert(f"??{err}", "Rec")

                raise RuntimeError(err)

            

            text_area_insert(f"?? 甇?銁撠?WebM 頧㗇???MP3...", "Rec")

            try:

                mp3_fname = os.path.splitext(fname)[0] + ".mp3"

                mp3_path = os.path.join(RECORD_DIR, mp3_fname)

                print(f"[Debug] ?见?頧㗇? WebM -> MP3: {mp3_path}")

                

                # Convert: -vn (no video), 44.1k, stereo, 192k bitrate mp3

                cmd = [_FFMPEG, "-y", "-i", save_path, "-vn", "-ar", "44100", "-ac", "2", "-b:a", "192k", mp3_path]

                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                

                if res.returncode != 0:

                    raise subprocess.CalledProcessError(res.returncode, cmd, output=res.stdout, stderr=res.stderr)



                if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 0:

                    sz = os.path.getsize(mp3_path)

                    print(f"[Debug] 頧㗇??𣂼?, MP3 Size: {sz} bytes")

                    text_area_insert(f"??頧㗇??𣂼? ({sz} bytes)嚗峕??蹱偘??, "Rec")

                else:

                    msg = "頧㗇?敺峕?獢�?憭望?憭批???0"

                    text_area_insert(f"??{msg}", "Rec")

                    print(f"[Debug] {msg}")



                # Success, remove original

                try: os.remove(save_path)

                except: pass

                

                save_path = mp3_path

                fname = mp3_fname

                ext = ".mp3"

            except subprocess.CalledProcessError as cpe:

                err_msg = cpe.stderr if cpe.stderr else str(cpe)

                text_area_insert(f"??ffmpeg 頧㗇?憭望?嚗㝯err_msg}", "Rec")

                raise RuntimeError(f"頧㗇? MP3 憭望?: {err_msg}")

            except Exception as cvt_err:

                text_area_insert(f"??頧㗇??潛?靘见?嚗㝯cvt_err}", "Rec")

                raise RuntimeError(f"頧㗇? MP3 ?潛?靘见?: {cvt_err}")



        # Save metadata so it appears in file list

        _write_upload_meta(save_path, "?�𨺗-" + datetime.now().strftime("%H%M%S"), fname, "audio")



        # Queue for playback

        print(f"[Debug] ?澆㙈 play_mp3_file({save_path})")



        # Optional Chime: Merge audio if requested and ffmpeg is available

        use_chime = request.form.get("chime") == "true" and _FFMPEG

        final_play_path = save_path



        if use_chime:

            try:

                # Prepare inputs

                inputs = []

                # Fix: Resolve relative paths for ffmpeg

                start_p = resource_path(START_SOUND) if not os.path.isabs(START_SOUND) else START_SOUND

                end_p = resource_path(END_SOUND) if not os.path.isabs(END_SOUND) else END_SOUND

                

                if os.path.exists(start_p): inputs.append(start_p)

                inputs.append(save_path)

                if os.path.exists(end_p): inputs.append(end_p)

                

                if len(inputs) > 1:

                    # Create concat list

                    list_txt = os.path.splitext(save_path)[0] + "_list.txt"

                    merged_mp3 = os.path.splitext(save_path)[0] + "_chime.mp3"

                    

                    with open(list_txt, "w", encoding="utf-8") as lf:

                        for p in inputs:

                            # Escape paths for ffmpeg concat demuxer

                            p_esc = p.replace("\\", "/")

                            lf.write(f"file '{p_esc}'\n")

                    

                    # Merge (re-encode to safe MP3 to handle mismatch formats)

                    # -y: overwrite

                    # -f concat -safe 0 -i list.txt

                    # -b:a 192k (bitrate)

                    cmd_merge = [_FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", list_txt, "-b:a", "192k", merged_mp3]

                    mres = subprocess.run(cmd_merge, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                    

                    # Cleanup list file

                    try: os.remove(list_txt)

                    except: pass

                    

                    if mres.returncode == 0 and os.path.exists(merged_mp3) and os.path.getsize(merged_mp3) > 100:

                        final_play_path = merged_mp3

                        print(f"[Debug] ?�蔥?𣂼?: {final_play_path}")

                    else:

                        print(f"[Debug] ?�蔥憭望?: {mres.stderr.decode('utf-8', errors='ignore')}")

            except Exception as e:

                print(f"[Debug] Chime merge error: {e}")



        play_mp3_file(final_play_path) 

        

        play_mp3_file(final_play_path) 

        

        # [MODIFIED] Return recording URL with 'rec/' prefix context

        return jsonify(ok=True, file=f"rec/{os.path.basename(final_play_path)}")

    except Exception as e:

        return jsonify(ok=False, error=str(e)), 500



def _writable_dir(p: str) -> bool:

    try:

        os.makedirs(p, exist_ok=True)

        test = os.path.join(p, ".touch_perm_test")

        with open(test, "w", encoding="utf-8") as f:

            f.write("ok")

        os.remove(test)

        return True

    except Exception:

        return False



_BASE_FOR_TT = APP_DIR if _writable_dir(APP_DIR) else DATA_DIR  # 隤脰”?箸??桅?

# ?�迂銝𠰴�?��瑼𥪜?嚗�鉄?唾?/?𣇉?/敶梁?嚗?

AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac"}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".webm", ".m4v"}

ALLOWED_EXTS = AUDIO_EXTS | IMAGE_EXTS | VIDEO_EXTS





def _classify_upload_mtype(ext: str) -> str:

    ext = (ext or "").lower()

    if ext in VIDEO_EXTS:

        return "video"

    if ext in AUDIO_EXTS:

        return "audio"

    if ext in IMAGE_EXTS:

        return "image"

    return "file"





def _write_upload_meta(save_path: str, orig_name: str, saved_name: str, mtype: str, stat_res=None):

    try:

        st = stat_res or os.stat(save_path)

        meta = {

            "orig": orig_name,

            "saved": saved_name,

            "mtime": st.st_mtime,

            "size": st.st_size,

            "mtype": mtype or "file",

        }

        with open(f"{save_path}.json", "w", encoding="utf-8") as mf:

            json.dump(meta, mf, ensure_ascii=False)

    except Exception:

        pass



# ===============================

# == [ANCHOR] 閮箸𪃾蝝�??==

# ===============================

UDP_DIAG = os.environ.get("UDP_DIAG", "0") == "1"

DIAG_DIR = Path.home() / ".udp_receiver"

DIAG_DIR.mkdir(exist_ok=True)

DIAG_FILE = DIAG_DIR / "relay_diag.txt"



# CWA嚗�葉憭格除鞊∠蔡嚗匧𧑐??API ?煾麯嚗�?閮剖??啣?霈𦠜彍 CWA_API_KEY 霈�?吔??亦�蝛箏??�蝙??USGS嚗?

CWA_API_KEY = (os.environ.get("CWA_API_KEY", "") or "").strip()



def _diag(msg: str):

    if UDP_DIAG:

        try:

            with DIAG_FILE.open("a", encoding="utf-8") as f:

                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")

        except Exception:

            pass





def ui_safe(func, *args, **kwargs):

    try:

        _root = globals().get("root")

        if _root and getattr(_root, "winfo_exists", lambda: False)():

            _root.after(0, lambda: func(*args, **kwargs))

    except Exception:

        pass



def wake_screen():

    try:

        if os.name == "nt":

            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)

            # Use F24 (0x87) instead of SPACE (0x20) to avoid triggering focused buttons

            VK_F24 = 0x87; KEYEVENTF_KEYUP = 0x0002

            ctypes.windll.user32.keybd_event(VK_F24, 0, 0, 0); time.sleep(0.05)

            ctypes.windll.user32.keybd_event(VK_F24, 0, KEYEVENTF_KEYUP, 0)

    except Exception:

        pass



# ===============================

# == [ANCHOR] ?�𧋦?�?怠? ==

# ===============================

_TEXT_BUFFER: list[str] = []



def text_area_insert(msg: str, src: str | None = None):

    try:

        ta = globals().get("text_area")

        origin = (src or getattr(_sender_ctx, "name", None) or "System")

        line = f"{datetime.now().strftime('%H:%M:%S')}  [{origin}] {msg}\n"

        if ta and ta.winfo_exists():

            ta.insert("1.0", line)

            ta.see("1.0")

        else:

            _TEXT_BUFFER.append(line)

    except Exception:

        pass



def flush_text_buffer_if_any():

    try:

        if not _TEXT_BUFFER: return

        ta = globals().get("text_area")

        if ta and ta.winfo_exists():

            for line in _TEXT_BUFFER:

                ta.insert("1.0", line)

            _TEXT_BUFFER.clear()

            ta.see("1.0")

    except Exception:

        pass



# ===============================

# == [ANCHOR] ?典?閮剖? ==

# ===============================

_sender_ctx = threading.local()



CONFIG_FILE = "sound_config.json"

DEFAULT_CONFIG = {"start_sound":"beforemic.mp3","end_sound":"beforemic2.mp3","mute_sound":"mute.mp3", "use_ai_generation": True}



voice_gender = "female"

voice_language = "zh-TW"  # ?鞱身銝剜??剖𥼚

voice_rate = "-20%"

voice_muted = False

stop_playback_event = threading.Event()



VOLUME_LEVEL = 80



speech_queue = queue.Queue(maxsize=100)

youtube_queue = queue.Queue(maxsize=30)

mp3_queue = queue.Queue(maxsize=30)



def enqueue_drop_old(q: queue.Queue, item):

    if q.full():

        with q.mutex:

            q.queue.clear()

    q.put(item)





STATE = {
    "muted": False,
    "lang": "zh-TW",
    "gender": "female",
    "rate": "-20%",
    "volume": VOLUME_LEVEL,
    "playing": "idle",
    "progress": 0,
    "ngrok_url": None,
    "mp3_progress": 0,
    "mpv_ipc_path": None,
    "auto_unmute_on_play": True,
    "timetable": {"enabled": True, "loaded": False, "count": 0, "path": ""},
    "azure_speech_key": "",
    "azure_speech_region": "",
    "edge_tts_status": "Checking...",
}

try:

    with open(os.path.join(APP_DIR, "azure_config.json"), "r", encoding="utf-8") as f:

        _ac = json.load(f)

        STATE["azure_speech_key"] = _ac.get("azure_speech_key", "")

        STATE["azure_speech_region"] = _ac.get("azure_speech_region", "")

except Exception:

    pass



AUTO_UNMUTE_ON_PLAY = True

_updating_volume_ui = False



# ===============================

# == [ANCHOR] 摮貊?蝡舀綉?園?蝵?==

# ===============================

STUDENT_UDP_LISTEN_PORT = 8080        # ?交𤣰摮貊?蝡?HELLO (?寧� 8080 Alternative HTTP)

STUDENT_UDP_CMD_PORT = 8081           # 摮貊?蝡舫?閮剜𦻖?嗅𦶢隞斤? UDP ??(?寧� 8081 Alternative HTTP)

STUDENT_HELLO_TIMEOUT = 60            # 頞�?甇斤??豢𧊋?嗅� HELLO 閬𣇉�?Ｙ?

STUDENT_DISCOVER_INTERVAL = 15        # 撱?偘 DISCOVER ?�??䈑?蝘𡜐?

STUDENT_DISCOVER_IP = "255.255.255.255"



# 摮貊?蝡舀??殷?client_id -> {ip, port, hostname, group, mac, last_seen}
students_clients = {}
students_lock = threading.Lock()
students_stop_event = threading.Event()

# WebSocket 摮貊?蝡荔?client_id -> WebSocket Object
AGENT_WS_CLIENTS = {}
AGENT_WS_LOCK = threading.Lock()



# ===============================

# == [ANCHOR] ?單??嘥???==

# ===============================

# --- ??pygame.mixer.init() 銋见??惩� ---

try:

    pygame.mixer.quit()

except Exception:

    pass

# 44.1kHz/16bit/stereo嚗𠩯uffer 蝔滚凝憭找?暺痹??踹??剝𨺗鋡怠?撠?

pygame.mixer.pre_init(44100, -16, 2, 1024)



try:
    if DISABLE_GUI:
        os.environ["SDL_AUDIODRIVER"] = "dummy"
    pygame.mixer.init()
except Exception:
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    try:
        pygame.mixer.init()
        print("[audio] pygame mixer using dummy driver")
    except Exception as e:
        print("[audio] pygame mixer init failed:", e)



MIXER_LOCK = threading.RLock()



def load_config():

    if not os.path.exists(CONFIG_FILE):

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:

            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:

        return json.load(f)



def save_config(config):

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:

        json.dump(config, f, ensure_ascii=False, indent=2)



config = load_config()

START_SOUND = resource_path(config["start_sound"])

END_SOUND   = resource_path(config["end_sound"])

MUTE_SOUND  = resource_path(config["mute_sound"])



# ===============================

# == [ANCHOR] ?芾?敹恍�罸枤閮剖? ==

# ===============================

SHORTCUTS_FILE = "shortcuts.json"
BUDDHA_SHORTCUTS_FILE = "buddha_shortcuts.json"



def load_shortcuts():

    if not os.path.exists(SHORTCUTS_FILE):

        return []

    try:

        with open(SHORTCUTS_FILE, "r", encoding="utf-8") as f:

            return json.load(f)

    except Exception:

        return []



def save_shortcuts(data):

    try:

        with open(SHORTCUTS_FILE, "w", encoding="utf-8") as f:

            json.dump(data, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print("Save shortcuts error:", e)

def load_buddha_shortcuts():
    if not os.path.exists(BUDDHA_SHORTCUTS_FILE): return []
    try:
        with open(BUDDHA_SHORTCUTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception: return []

def save_buddha_shortcuts(data):
    try:
        with open(BUDDHA_SHORTCUTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Save Buddha shortcuts error:", e)



# ===============================

# == [ANCHOR] USB-Relay ?菜葫/?批� ==

# ===============================

CH34x_VIDPIDS = {"1A86:7523", "1A86:5523"}

REL_BRANDS = ("CH340", "CH341", "USB-SERIAL", "USB SERIAL", "WCH", "QINHENG", "USB-Serial Controller")



RELAY_LOCK = threading.RLock()

RELAY_INFO = {"port": None, "last_cmd": "-", "last_result": "-", "last_error": "", "ports": [], "last_update_ts": 0}



def _relay_set(key, val):

    RELAY_INFO[key] = val

    RELAY_INFO["last_update_ts"] = time.time()

    STATE["relay"] = {

        "port": RELAY_INFO.get("port"),

        "last_cmd": RELAY_INFO.get("last_cmd"),

        "last_result": RELAY_INFO.get("last_result"),

        "last_error": RELAY_INFO.get("last_error"),

        "ports": RELAY_INFO.get("ports"),

        "ts": RELAY_INFO.get("last_update_ts"),

    }

    try:

        refresh_relay_ui()

    except Exception:

        pass



def get_ports_snapshot_text():

    items = RELAY_INFO.get("ports") or []

    if not items: return "(?∪虾閬讠? COM 鋆萘蔭)"

    lines = []

    for dev, desc, hwid in items:

        lines.append(f"{dev:<8} {desc}  [{hwid}]")

    return "\n".join(lines)



def list_all_comports():

    try:

        ports = list(list_ports.comports())

        snapshot = []

        for p in ports:

            snapshot.append((getattr(p, "device", ""), getattr(p, "description", ""), getattr(p, "hwid", "")))

        _relay_set("ports", snapshot)

        return ports

    except Exception as e:

        _diag(f"list_ports.comports() error: {e}")

        _relay_set("last_error", f"list_ports error: {e}")

        return []



def get_manual_relay_port():

    env = os.environ.get("RELAY_PORT")

    if env:

        _diag(f"Manual port from ENV -> {env}")

        return env.strip()

    cfg = DIAG_DIR / "relay_port.txt"

    if cfg.exists():

        try:

            val = cfg.read_text(encoding="utf-8").strip()

            _diag(f"Manual port from file -> {val}")

            return val

        except Exception as e:

            _diag(f"Read relay_port.txt error: {e}")

    return None



def auto_detect_lcus_port(max_wait_s: float = 8.0):

    manual = get_manual_relay_port()

    if manual:

        with RELAY_LOCK:

            _relay_set("port", manual); _relay_set("last_cmd", "ManualPort")

            _relay_set("last_result", "OK"); _relay_set("last_error", "")

        return manual

    start = time.time()

    while time.time() - start < max_wait_s:

        ports = list_all_comports()

        for p in ports:

            dev = getattr(p, "device", None) or getattr(p, "name", None)

            if not dev: continue

            hwid = (getattr(p, "hwid", "") or "").upper()

            desc = (getattr(p, "description", "") or "").upper()

            is_ch34x = (

                "VID_1A86&PID_7523" in hwid or

                "VID_1A86&PID_5523" in hwid or

                any(k in (hwid + " " + desc) for k in ("CH340", "CH341", "QINHENG", "USB-SERIAL"))

            )

            if not is_ch34x: continue

            try:

                import serial as _serial

                with _serial.Serial(dev, 9600, timeout=0.8) as _:

                    pass

                with RELAY_LOCK:

                    _diag(f"[probe] open ok -> {dev}")

                    _relay_set("port", dev)

                    _relay_set("last_cmd", "Probe")

                    _relay_set("last_result", "OK")

                    _relay_set("last_error", "")

                return dev

            except Exception as e:

                _diag(f"[probe] open fail {dev}: {e}")

                with RELAY_LOCK:

                    _relay_set("last_cmd", "Probe")

                    _relay_set("last_result", "FAIL")

                    _relay_set("last_error", f"{dev}: {e}")

        time.sleep(0.6)

    with RELAY_LOCK:

        _diag("auto_detect_lcus_port: no port available after wait")

        _relay_set("last_cmd", "Probe"); _relay_set("last_result", "FAIL")

        _relay_set("last_error", "no available COM after wait")

    return None



RELAY_PORT = get_manual_relay_port() or auto_detect_lcus_port()



def control_usb_relay(status, retries=5):

    global RELAY_PORT

    import serial as _serial

    cmd_on  = b'\xA0\x01\x01\xA2'

    cmd_off = b'\xA0\x01\x00\xA1'

    payload = cmd_on if status == "ON" else cmd_off

    _relay_set("last_cmd", f"Write:{status}")

    for _ in range(retries):

        port = get_manual_relay_port() or RELAY_PORT

        if not port:

            port = auto_detect_lcus_port()

        if not port:

            time.sleep(0.5)

            continue

        try:

            with RELAY_LOCK:

                with _serial.Serial(port, 9600, timeout=1) as ser:

                    try:

                        ser.setDTR(True); ser.setRTS(True)

                        ser.reset_input_buffer(); ser.reset_output_buffer()

                    except Exception:

                        pass

                    time.sleep(0.12)

                    ser.write(payload); ser.flush(); time.sleep(0.06)

                RELAY_PORT = port

                _relay_set("port", port); _relay_set("last_result", "OK"); _relay_set("last_error", "")

            save_to_csv(f"Relay set to {status}", "System", status)

            ui_safe(lambda: status_label.config(text=f" 隤鮋𨺗?毺鍂銝哨?蝜潮𤓖?剁?{status}"))

            return

        except Exception as e:

            _diag(f"Relay control error: {e}")

            with RELAY_LOCK:

                _relay_set("last_result", "FAIL"); _relay_set("last_error", str(e)[:180])

            RELAY_PORT = None

            time.sleep(0.8)

    save_to_csv("Relay control failed", "System", "Failed")

    ui_safe(lambda: status_label.config(text="??蝜潮𤓖?冽綉?嗅仃??))



def rescan_relay_ports():

    ports = list_all_comports()

    snapshot = []

    for p in ports:

        snapshot.append((getattr(p, "device", ""), getattr(p, "description", ""), getattr(p, "hwid", "")))

    _relay_set("ports", snapshot)

    _relay_set("last_cmd", "Rescan")

    _relay_set("last_result", "OK")

    _relay_set("last_error", "")



def test_relay_on():

    try:

        _relay_set("last_cmd", "TestON")

        control_usb_relay("ON")

        _relay_set("last_result", "OK"); _relay_set("last_error", "")

    except Exception as e:

        _relay_set("last_result", "FAIL"); _relay_set("last_error", str(e)[:180])



def test_relay_off():

    try:

        _relay_set("last_cmd", "TestOFF")

        control_usb_relay("OFF")

        _relay_set("last_result", "OK"); _relay_set("last_error", "")

    except Exception as e:

        _relay_set("last_result", "FAIL"); _relay_set("last_error", str(e)[:180])





# ==== [4-Relay COM 閮剖??�綉?跑 ====



RELAY4_LOCK = threading.RLock()

RELAY4_INFO = {

    "port": None,

    "ch_state": {1: 0, 2: 0, 3: 0, 4: 0},

    "last_cmd": "-",

    "last_result": "-",

    "last_error": "",

    "last_update_ts": 0,

}



def _relay4_set(key, val):

    RELAY4_INFO[key] = val

    RELAY4_INFO["last_update_ts"] = time.time()



def get_manual_relay4_port():

    """敺?~/.udp_receiver/relay4_port.txt ?𣇉兛憓�???RELAY4_PORT 霈�??4-Relay COM??""

    env = os.environ.get("RELAY4_PORT")

    if env:

        # _diag(f"[4R] Manual port from ENV -> {env}")

        return env.strip()

    cfg = DIAG_DIR / "relay4_port.txt"

    if cfg.exists():

        try:

            val = cfg.read_text(encoding="utf-8").strip()

            if val:

                # _diag(f"[4R] Manual port from relay4_port.txt -> {val}")

                return val

        except Exception as e:

            _diag(f"[4R] Read relay4_port.txt error: {e}")

    return None



def auto_detect_4relay_port(max_wait_s: float = 8.0):

    """4-Relay ?芸??�?嚗𡁶椘?𤩺𪄳?䔶??臬鱓 Relay?滨? CH34x COM??""

    manual = get_manual_relay4_port()

    if manual:

        with RELAY4_LOCK:

            _relay4_set("port", manual)

            _relay4_set("last_cmd", "ManualPort")

            _relay4_set("last_result", "OK")

            _relay4_set("last_error", "")

        return manual



    start = time.time()

    while time.time() - start < max_wait_s:

        ports = list_all_comports()

        for p in ports:

            dev = getattr(p, "device", None) or getattr(p, "name", None)

            if not dev:

                continue

            hwid = (getattr(p, "hwid", "") or "").upper()

            desc = (getattr(p, "description", "") or "").upper()

            is_ch34x = (

                "VID_1A86&PID_7523" in hwid or

                "VID_1A86&PID_5523" in hwid or

                any(k in (hwid + " " + desc) for k in ("CH340", "CH341", "QINHENG", "USB-SERIAL"))

            )

            if not is_ch34x:

                continue



            # ?芸??輸??桀?蝯血鱓 Relay 雿輻鍂??COM

            current_single = RELAY_INFO.get("port") or RELAY_PORT

            if current_single and dev == current_single:

                continue



            try:

                import serial as _serial

                with _serial.Serial(dev, 9600, timeout=0.8):

                    pass

                with RELAY4_LOCK:

                    _diag(f"[4R probe] open ok -> {dev}")

                    _relay4_set("port", dev)

                    _relay4_set("last_cmd", "Probe")

                    _relay4_set("last_result", "OK")

                    _relay4_set("last_error", "")

                return dev

            except Exception as e:

                _diag(f"[4R probe] open fail {dev}: {e}")

        time.sleep(0.6)



    _diag("[4R] auto_detect_4relay_port: no port available after wait")

    with RELAY4_LOCK:

        _relay4_set("last_cmd", "Probe")

        _relay4_set("last_result", "FAIL")

        _relay4_set("last_error", "no available COM after wait")

    return None





def list_4relay_candidate_ports():

    """

    ?堒枂?桀??舐鍂??4-Relay COM 皜�鱓嚗?

    - ?芣???CH34x / USB-SERIAL ?賊??�?

    - ?㗛??輸??桀?甇?眏??Relay 雿輻鍂??COM嚗㇌ELAY_PORT ??RELAY_INFO["port"]嚗?

    """

    ports = list_all_comports()

    result = []

    current_single = (RELAY_INFO.get("port") or RELAY_PORT) if "RELAY_INFO" in globals() else RELAY_PORT

    for p in ports:

        dev = getattr(p, "device", None) or getattr(p, "name", None)

        if not dev:

            continue

        hwid = (getattr(p, "hwid", "") or "").upper()

        desc = (getattr(p, "description", "") or "").upper()

        is_ch34x = (

            "VID_1A86&PID_7523" in hwid or

            "VID_1A86&PID_5523" in hwid or

            any(k in (hwid + " " + desc) for k in ("CH340", "CH341", "QINHENG", "USB-SERIAL"))

        )

        if not is_ch34x:

            continue

        if current_single and dev == current_single:

            # ?輸??桀?蝯血鱓 Relay 雿輻鍂??COM

            continue

        result.append(dev)

    return result





RELAY4_PORT = get_manual_relay4_port() or auto_detect_4relay_port()





def control_usb_relay4(ch: int, on: bool, retries: int = 5, port_override: str | None = None):

    """?批� 4-Relay 蝚?ch 頝舐匱?餃膥嚗?~4嚗剹�?



    ?�彍嚗?

      ch            : 蝚砍嗾頝荔?1~4嚗?

      on            : True=?詨??�alse=?𧢲𦆮

      retries       : 憭望??�?閰行活??

      port_override : ?交?摰𡄯?撘瑕�雿輻鍂閰?COM嚗䔶??滩䌊?訫�皜?

    """

    global RELAY4_PORT

    if ch not in (1, 2, 3, 4):

        raise ValueError("ch 敹�???1~4")



    import serial as _serial

    on_flag = 1 if on else 0

    payload = bytes([0xA0, ch, on_flag, (0xA0 + ch + on_flag) & 0xFF])

    _relay4_set("last_cmd", f"CH{ch}:{'ON' if on else 'OFF'}")



    last_err = ""

    for _ in range(retries):

        if port_override:

            port = port_override

        else:

            port = get_manual_relay4_port() or RELAY4_PORT

            if not port:

                port = auto_detect_4relay_port()

        if not port:

            time.sleep(0.5)

            continue

        try:

            with RELAY4_LOCK:

                with _serial.Serial(port, 9600, timeout=1) as ser:

                    try:

                        ser.setDTR(True)

                        ser.setRTS(True)

                        ser.reset_input_buffer()

                        ser.reset_output_buffer()

                    except Exception:

                        pass

                    time.sleep(0.12)

                    ser.write(payload)

                    ser.flush()

                    time.sleep(0.1)

                RELAY4_PORT = port

                st = RELAY4_INFO.get("ch_state") or {1: 0, 2: 0, 3: 0, 4: 0}

                st[int(ch)] = 1 if on else 0

                _relay4_set("ch_state", st)

                _relay4_set("port", port)

                _relay4_set("last_result", "OK")

                _relay4_set("last_error", "")

                ui_safe(refresh_relay4_ui)

                return True

        except Exception as e:

            last_err = str(e)[:180]

            _diag(f"[4R] control fail on {port}: {e}")

            time.sleep(0.5)



    with RELAY4_LOCK:

        _relay4_set("last_result", "FAIL")

        _relay4_set("last_error", last_err or "unknown error")

    raise RuntimeError(last_err or "4-Relay control failed")



RELAY_ACTIVE_CNT = 0

RELAY_ACTIVE_LOCK = threading.RLock()


# [NEW] Relay Config Persistence
RELAY_CONFIG_PATH = Path(DATA_DIR) / "relay_config.json"
RELAY_AUTO_ON = True

def _save_relay_config():
    try:
        data = {"auto_on": RELAY_AUTO_ON}
        RELAY_CONFIG_PATH.write_text(json.dumps(data), encoding="utf-8")
        print(f"[Config] Saved relay config: {data}")
    except Exception as e:
        print(f"[Config] Save relay config failed: {e}")

def _load_relay_config():
    global RELAY_AUTO_ON
    try:
        if RELAY_CONFIG_PATH.exists():
            data = json.loads(RELAY_CONFIG_PATH.read_text(encoding="utf-8"))
            RELAY_AUTO_ON = data.get("auto_on", True)
            print(f"[Config] Loaded relay config: auto_on={RELAY_AUTO_ON}")
    except Exception as e:
        print(f"[Config] Load relay config failed: {e}")

# Load immediately
_load_relay_config()


def relay_acquire(tag: str = "") -> bool:

    global RELAY_ACTIVE_CNT

    first_open = False

    with RELAY_ACTIVE_LOCK:

        RELAY_ACTIVE_CNT += 1

        if RELAY_ACTIVE_CNT == 1:
            if RELAY_AUTO_ON:
                first_open = True
                control_usb_relay("ON")
            else:
                _diag(f"[Relay] acquire({tag}) but Auto-On disabled. Skipping ON.")

    return first_open



def relay_release(tag: str = ""):

    global RELAY_ACTIVE_CNT

    with RELAY_ACTIVE_LOCK:

        RELAY_ACTIVE_CNT = max(0, RELAY_ACTIVE_CNT - 1)

        if RELAY_ACTIVE_CNT == 0:
            if RELAY_AUTO_ON:
                control_usb_relay("OFF")
            else:
                _diag(f"[Relay] release({tag}) but Auto-On disabled. Skipping OFF.")



def relay_force_off():

    global RELAY_ACTIVE_CNT

    with RELAY_ACTIVE_LOCK:

        RELAY_ACTIVE_CNT = 0

    control_usb_relay("OFF")



# ===============================

# == [ANCHOR] ?剜𦆮?批� ==

# ===============================

# ---- FX嚗�?撠?蝯鞉??喉?撠�鍂 ----

pygame.mixer.set_num_channels(8)              # 蝣箔??匧?銝�暺鮋�𡁻?

FX_CHANNEL = pygame.mixer.Channel(1)          # 0蝯衣頂蝯梁鍂嚗??訶X?𡁻?

SOUND_CACHE = {}



def _get_fx_sound(path):

    p = resource_path(path)

    if not os.path.exists(p):

        raise FileNotFoundError(p)

    if p not in SOUND_CACHE:

        snd = pygame.mixer.Sound(p)           # 撱箄降?𦠜?蝷粹𨺗?寞? WAV/OGG嚗峕?蝛?

        snd.set_volume(STATE["volume"]/100.0)

        SOUND_CACHE[p] = snd

    else:

        SOUND_CACHE[p].set_volume(STATE["volume"]/100.0)

    return SOUND_CACHE[p]



def play_fx(filename, ignore_interrupt=True):

    try:

        if stop_playback_event.is_set() and not ignore_interrupt:

            return

        snd = _get_fx_sound(filename)

        FX_CHANNEL.play(snd)

        while FX_CHANNEL.get_busy():

            if stop_playback_event.is_set() and not ignore_interrupt:

                FX_CHANNEL.stop()

                break

            time.sleep(0.01)

        time.sleep(0.05)  # 撠誩??埝除嚗屸�?滚?撠?

    except Exception as e:

        print("FX ?剜𦆮憭望?嚗?, e)



def set_playing_status(text):

    ui_safe(playing_label.config, text=text)

    ui_safe(progress_text_label.config, text=text)

    STATE["playing"] = text



def set_volume(level: int):

    global VOLUME_LEVEL, _updating_volume_ui

    try:

        VOLUME_LEVEL = max(0, min(100, int(level)))

    except:

        return

    try:

        pygame.mixer.music.set_volume(VOLUME_LEVEL/100.0)

    except:

        pass

    STATE["volume"] = VOLUME_LEVEL

    def _apply():

        global _updating_volume_ui

        _updating_volume_ui = True

        try:

            if 'volume_scale' in globals():

                volume_scale.set(VOLUME_LEVEL)

            if 'volume_label' in globals():

                volume_label.config(text=f"?喲?嚗㝯VOLUME_LEVEL}%")

            status_label.config(text=f" 隤鮋𨺗?毺鍂銝哨??喲? {VOLUME_LEVEL}%嚗?)

        finally:

            _updating_volume_ui = False

    ui_safe(_apply)



def _set_progress(pct):

    try:

        progress_var.set(pct)

        progress_text_var.set(f"{pct}%")

    except Exception:

        pass



def play_sound(filename, duration_estimate=None, ignore_interrupt=False):

    try:

        with MIXER_LOCK:

            pygame.mixer.music.set_volume(STATE["volume"]/100.0)

            try: pygame.mixer.music.stop()

            except Exception: pass

            pygame.mixer.music.load(filename)

            pygame.mixer.music.play()

        t = 0

        if not duration_estimate or duration_estimate <= 0:

            try:

                from mutagen.mp3 import MP3  # type: ignore

                if filename.lower().endswith(".mp3"):

                    duration_estimate = MP3(filename).info.length

                else:

                    duration_estimate = 10

            except Exception:

                duration_estimate = 10

        ui_safe(_set_progress, 0); STATE["progress"] = 0

        while pygame.mixer.music.get_busy():

            if stop_playback_event.is_set() and not ignore_interrupt:

                with MIXER_LOCK:

                    pygame.mixer.music.stop()

                break

            time.sleep(0.1); t += 0.1

            percent = min(100, int(100*t/duration_estimate))

            STATE["progress"] = percent

            ui_safe(_set_progress, percent)

        STATE["progress"] = 100

        ui_safe(_set_progress, 100)

        # ?�𧋦??while 銋见??牐?嚗?

        time.sleep(0.05)  # 霈枏偏撌渡Ⅱ撖阡��???unload

        with MIXER_LOCK:

            try: pygame.mixer.music.unload()

            except Exception: pass

    except Exception as e:

        print("?剜𦆮憭望?嚗?, e)



def _interrupt_current_playback():

    stop_playback_event.set()

    with MIXER_LOCK:

        try: pygame.mixer.music.stop()

        except Exception: pass

    stop_playback_event.clear()

    ui_safe(_set_progress, 0); STATE["progress"] = 0



def with_relay_playback(play_func):

    def wrapper(*args, **kwargs):

        first = relay_acquire(play_func.__name__)

        if first:

            time.sleep(3)

        try:

            return play_func(*args, **kwargs)

        finally:

            relay_release(play_func.__name__)

    return wrapper



# ---- ffmpeg ?菜葫嚗út-dlp ?剁?----



def _detect_ffmpeg() -> str | None:

    cands = [

        shutil.which("ffmpeg"),

        resource_path("ffmpeg.exe"),

        os.path.join(APP_DIR, "ffmpeg.exe"),

        os.path.join(os.getcwd(), "ffmpeg.exe"),

    ]

    for c in cands:

        if c and os.path.isfile(c):

            return c

    return None



_FFMPEG = _detect_ffmpeg()



# ===============================

# == [ANCHOR] YouTube / MP3 ?剜𦆮 ==

# ===============================



def sanitize_filename(name: str, maxlen: int = 180) -> str:

    name = re.sub(r'[\\/:*?"<>|]+', ' ', name).strip()

    name = re.sub(r'\s+', ' ', name)

    name = name.rstrip('.')

    if not name:

        name = "youtube"

    return name[:maxlen]



def _generate_upload_filename(ext: str, prefix: str = "upload") -> str:

    """Return ASCII filename like upload_YYYYMMDD_HHMMSS(_n).ext to avoid unsafe chars."""

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    base = f"{prefix}_{ts}"

    ext = ext if ext.startswith(".") or not ext else f".{ext}"

    candidate = f"{base}{ext}"

    i = 1

    while os.path.exists(os.path.join(UPLOAD_DIR, candidate)):

        candidate = f"{base}_{i}{ext}"

        i += 1

    return candidate



def _unique_stem_in_uploads(stem: str) -> str:

    """蝣箔? uploads ?找??滚?嚗�誑 .mp3 瑼Ｘ䰻嚗㚁?敹�??�? (1)??2)??""

    base = os.path.join(UPLOAD_DIR, f"{stem}.mp3")

    if not os.path.exists(base):

        return stem

    i = 1

    while True:

        cand = os.path.join(UPLOAD_DIR, f"{stem} ({i}).mp3")

        if not os.path.exists(cand):

            return f"{stem} ({i})"

        i += 1



def download_youtube_audio_to_uploads(url: str) -> tuple[str, float, str]:

    """

    銝贝? YouTube ?唾? ??uploads 鞈�?憭橘?瑼𥪜?=敶梁?璅䠷?.mp3嚗�???(mp3_path, duration_sec, title)

    """

    if not _FFMPEG:

        raise RuntimeError("蝟餌絞?芣𪄳??ffmpeg嚗𣬚�瘜閗???mp3?�?摰㕑? ffmpeg ?𡝗? ffmpeg.exe ?曉銁蝔见??𣬚𤌍?��?)



    # ?�䔝皜祆?憿諹??瑕漲

    with yt_dlp.YoutubeDL({'quiet': True, 'nocheckcertificate': True}) as probe:

        info = probe.extract_info(url, download=False)

    title = info.get('title') or "youtube"

    duration = float(info.get('duration') or 10.0)

    stem = _unique_stem_in_uploads(sanitize_filename(title))

    outtmpl = os.path.join(UPLOAD_DIR, f"{stem}.%(ext)s")



    ydl_opts = {

        'format':'bestaudio/best',

        'outtmpl': outtmpl,

        'noplaylist': True,

        'quiet': False,

        'nocheckcertificate': True,

        'force_overwrites': False,

        'ffmpeg_location': _FFMPEG,

        'postprocessors': [

            {'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'192'}

        ],

    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        ydl.download([url])



    final_mp3 = os.path.join(UPLOAD_DIR, f"{stem}.mp3")

    if not os.path.exists(final_mp3):

        # 撠烐彍?�?嚗𡁜??閧??舀??滢???mp3嚗�?隢碶?銝齿?嚗㚁??𡁏?敺峕??湔?撠?

        cand = glob.glob(os.path.join(UPLOAD_DIR, f"{stem}.*"))

        if cand:

            mp3s = [c for c in cand if c.lower().endswith(".mp3")]

            final_mp3 = mp3s[0] if mp3s else cand[0]

        else:

            raise FileNotFoundError("銝贝?摰峕?雿�𧊋?曉�頛詨枂瑼𢛵�?)



    save_to_csv(f"YouTube saved: {os.path.basename(final_mp3)}", "System", "Success")

    return final_mp3, duration, title



@with_relay_playback

def play_youtube_audio_with_relay(url):

    try:

        set_playing_status(" 甇?銁銝贝? YouTube ?唾?銝虫?摮䁅秐 uploads ...")

        mp3_path, duration, title = download_youtube_audio_to_uploads(url)

        if stop_playback_event.is_set() or voice_muted:

            set_playing_status("?對? ?剜𦆮撌脖葉??); ui_safe(_set_progress, 0); STATE["progress"]=0; return

        set_playing_status(f" 銝贝?摰峕?嚗㝯os.path.basename(mp3_path)}嚗屸?憪𧢲偘?撾�?)

        text_area_insert(f" YouTube ??uploads嚗㝯os.path.basename(mp3_path)}嚗ùtitle}嚗?)

        save_to_csv(f"PlayYouTubeSaved:{os.path.basename(mp3_path)}", "System")

        _really_play_mp3_file(mp3_path)  # 銝滚⏛?歹?靽嘥???uploads

        if not stop_playback_event.is_set() and not voice_muted:

            set_playing_status("??YouTube?唾??剜𦆮摰𣬚佅嚗�?獢�歇靽萘???uploads嚗?)

            text_area_insert("??YouTube ?唾??剜𦆮摰峕?嚗�歇靽萘?瑼娍?嚗?)

            save_to_csv(f"PlayYouTubeAudioDone:{os.path.basename(mp3_path)}", "System")

        else:

            set_playing_status("?對? ?剜𦆮撌脖葉??); ui_safe(_set_progress, 0); STATE["progress"]=0

    except Exception as e:

        print("YouTube ?剜𦆮憭望?嚗?, e)

        text_area_insert(f"??YouTube ?剜𦆮/銝贝?憭望?嚗㝯e}")

        save_to_csv(f"PlayYouTubeAudioFail:{url}", "System")

        set_playing_status("??YouTube?唾??閧?憭望?"); ui_safe(_set_progress, 0); STATE["progress"]=0



def youtube_worker():

    while True:

        url = youtube_queue.get()

        try:

            if stop_playback_event.is_set() or voice_muted:

                continue

            play_youtube_audio_with_relay(url)

        finally:

            youtube_queue.task_done()



def mp3_worker():

    while True:

        item = mp3_queue.get()

        print(f"[Debug] MP3 Worker ?硋枂: {item}")

        try:

            if stop_playback_event.is_set() or voice_muted:

                print(f"[Debug] ?仿??剜𦆮 (Stop={stop_playback_event.is_set()}, Mute={voice_muted})")

                continue

            if isinstance(item, tuple) and item and item[0] == "URL":

                url = item[1]

                set_playing_status(" 甇?銁銝贝? MP3 ...")

                path = _download_mp3_to_temp(url)

                if not path:

                    set_playing_status("??銝贝?/?剜𦆮MP3憭望?")

                    ui_safe(_set_progress, 0); STATE["progress"] = 0

                else:

                    try:

                        _really_play_mp3_file(path)

                    finally:

                        try: os.remove(path)

                        except Exception: pass

            else:

                _really_play_mp3_file(item)

        except Exception as e:

            print(f"[Debug] MP3 Worker Error: {e}")

        finally:

            mp3_queue.task_done()



@with_relay_playback

def _really_play_mp3_file(path):

    print(f"[Debug] 皞硋??剜𦆮 MP3: {path}")

    # Fix: Resolve resource path BEFORE checking existence to support frozen app
    mp3_path = resource_path(path) if not os.path.isabs(path) else path

    if not os.path.exists(mp3_path):
        print(f"[Debug] 瑼娍?銝滚??? {mp3_path} (Original: {path})")
        return

    set_playing_status(f" ?剜𦆮MP3銝?..({os.path.basename(path)})")


    text_area_insert(f" ?祆? MP3嚗㝯os.path.basename(path)}")

    save_to_csv(f"PlayMP3Local:{os.path.basename(path)}", "System")

    

    try:

        play_sound(mp3_path, duration_estimate=10)

    except Exception as e:

        print(f"[Debug] Pygame play error: {e}")

        text_area_insert(f"???剜𦆮憭望?嚗㝯e}", "System")

        

    if not stop_playback_event.is_set() and not voice_muted:

        set_playing_status("???剜𦆮MP3摰峕?")

        text_area_insert("???祆? MP3 ?剜𦆮摰峕?")

        save_to_csv(f"PlayMP3LocalDone:{os.path.basename(path)}", "System")

    else:

        set_playing_status("?對? ?剜𦆮撌脖葉??); ui_safe(_set_progress, 0); STATE["progress"]=0



def play_mp3_file(path):

    print(f"[Debug] ?惩� MP3 Queue: {path}")

    enqueue_drop_old(mp3_queue, path)



def _download_mp3_to_temp(url: str) -> str | None:

    text_area_insert(f"漎�? 銝贝? MP3嚗㝯url}")

    save_to_csv(f"DownloadMP3:{url}", "System")

    try:

        r = requests.head(url, allow_redirects=True, timeout=10)

        ct = r.headers.get('content-type','').lower()

        if not (ct.startswith('audio/') or url.lower().endswith('.mp3')):

            r2 = requests.get(url, stream=True, timeout=10)

            ct2 = r2.headers.get('content-type','').lower()

            r2.close()

            if not (ct2.startswith('audio/') or url.lower().endswith('.mp3')):

                raise ValueError("URL 銝齿糓?航儘霅条??唾?")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:

            r = requests.get(url, timeout=30)

            fp.write(r.content)

            return fp.name

    except Exception as e:

        text_area_insert(f"??銝贝? MP3 憭望?嚗㝯e}")

        save_to_csv(f"DownloadMP3Fail:{url}", "System")

        return None



# ===============================

# == [ANCHOR] Edge/Piper/gTTS/SAPI5 隤鮋𨺗 ==

# ===============================



def detect_language(text):

    # ?�?雿輻鍂??UI 撘瑕�?豢?嚗��?滩◤摮堒??菜葫閬�?嚗?

    # 憒�?雿輻鍂?��鈭��諹䌊?訫�皜研�㵪??滩?銝𧢲䲮?�??��皜?

    # ?血??湔𦻖?𧼮�雿輻鍂?��?�?閮�隞?Ⅳ

    selected_label = lang_label_var.get()

    selected_code = lang_label2code.get(selected_label, "auto")

    

    if selected_code != "auto":

        return selected_code



    # ?芸??菜葫?讛摩

    if re.search(r'[\u3040-\u30ff\u31f0-\u31ff]', text): return "ja-JP"

    if re.search(r'[\u4e00-\u9fff]', text): return "zh-TW"

    if re.search(r'[\uac00-\ud7af]', text): return "ko-KR"

    # 蝪∪鱓?文?嚗朞𥅾?望?摮埈?頞�?銝�?𠰴?閬𣇉�?望?

    if len(re.findall(r'[a-zA-Z]', text)) > len(text)/2: return "en-US"

    

    return "zh-TW" # Fallback



VOICE_ID_TABLE = {

    "zh-TW":{"female":"zh-TW-HsiaoChenNeural","male":"zh-TW-YunJheNeural","audrey_education":"audrey_education"},

    "en-US":{"female":"en-US-JennyNeural","male":"en-US-GuyNeural","audrey_education":"audrey_education"},

    "ja-JP":{"female":"ja-JP-NanamiNeural","male":"ja-JP-KeitaNeural","audrey_education":"audrey_education"},

    "ko-KR":{"female":"ko-KR-SunHiNeural","male":"ko-KR-InJoonNeural","audrey_education":"audrey_education"},

    "vi-VN":{"female":"vi-VN-HoaiMyNeural","male":"vi-VN-NamMinhNeural","audrey_education":"audrey_education"},
    "id-ID":{"female":"id-ID-GadisNeural","male":"id-ID-ArdiNeural","audrey_education":"audrey_education"},
    "km-KH":{"female":"km-KH-SreymomNeural","male":"km-KH-PisethNeural","audrey_education":"audrey_education"},
    "lo-LA":{"female":"lo-LA-KeomanyNeural","male":"lo-LA-ChanthavongNeural","audrey_education":"audrey_education"},
    "th-TH":{"female":"th-TH-PremwadeeNeural","male":"th-TH-NiwatNeural","audrey_education":"audrey_education"},
    "my-MM":{"female":"my-MM-NilarNeural","male":"my-MM-ThihaNeural","audrey_education":"audrey_education"},
    "ms-MY":{"female":"ms-MY-YasminNeural","male":"ms-MY-OsmanNeural","audrey_education":"audrey_education"},
    "tl-PH":{"female":"tl-PH-BlessicaNeural","male":"tl-PH-AngeloNeural","audrey_education":"audrey_education"},


    "nan-TW":{"female":None,"male":None,"audrey_education":"audrey_education"},

    "auto":{"female":"zh-TW-HsiaoChenNeural","male":"zh-TW-YunJheNeural","audrey_education":"audrey_education"},

}

LANG_OPTIONS=[("?芸??菜葫 (Auto)","auto"), ("銝剜?嚗�蝱???","zh-TW"),("?望?嚗�??页?","en-US"),("?交?嚗�𠯫?穿?","ja-JP"),("?𤘪?嚗�??页?","ko-KR"),("頞𠰴?隤?,"vi-VN"), ("?砍?撖?擃䀹?","km-KH"), ("撖桀?","lo-LA"), ("瘜啣?","th-TH"), ("蝺祉璛","my-MM"), ("擐砌?镼蹂?","ms-MY"), ("?啣側隤?,"id-ID"), ("?脣?鞈?,"tl-PH"), ("?啗?","nan-TW")]

lang_label2code={lab:code for lab,code in LANG_OPTIONS}; lang_code2label={code:lab for lab,code in LANG_OPTIONS}

GENDER_LABELS=[

    ("憟唾�","female"),

    ("?瑁�","male"),

]

gender_label2code={lab:code for lab,code in GENDER_LABELS}

gender_label2code.update({

    "Female":"female",

    "Male":"male",

})

gender_code2label={code:lab for lab,code in GENDER_LABELS}



def get_voice_id_auto(text, lang_code=None, gender_code=None):
    if lang_code and ("-Neural" in lang_code or "-" in lang_code and len(lang_code) > 10): 
        return lang_code # Direct voice ID
    if not lang_code: lang_code = detect_language(text)
    if not gender_code: gender_code = gender_label2code.get(gender_label_var.get(), "female")
    # Make sure gender_code is lowercase "female" or "male"
    gender_code = (gender_code or "female").lower()
    return VOICE_ID_TABLE.get(lang_code, VOICE_ID_TABLE["zh-TW"]).get(gender_code, "zh-TW-HsiaoChenNeural")



def auto_unmute_if_needed():

    global voice_muted

    if STATE.get("auto_unmute_on_play", True) and voice_muted:

        voice_muted = False

        STATE["muted"] = False

        stop_playback_event.clear()

        ui_safe(status_label.config, text=" 隤鮋𨺗?毺鍂銝哨??芸?閫?膄?𣈯𨺗嚗?, fg="#188a3a")

        set_playing_status(" 隤鮋𨺗?毺鍂銝?)





@with_relay_playback

def taigi_play_wav_with_fx(path):

    """?啗??�?摰峕?敺䕘?憟㛖鍂?𡒊凒?交偘?整�讛??潘?Relay ?𦥑??滚??鍦�摰嫖?蝯鞉??㰕elay ?栶�?""

    try:

        auto_unmute_if_needed()

        ui_safe(set_playing_status, f" ?啗??剜𦆮嚗㝯os.path.basename(path)}")

        # ?滚??喉?FX ?𡁻?嚗䔶??𤘪𪃾銝餅偘嚗?

        try:

            if os.path.exists(START_SOUND):

                play_fx(START_SOUND, ignore_interrupt=True)

        except Exception:

            pass

        # 銝餅偘

        play_sound(path, duration_estimate=10)

        # 蝯鞉???

        try:

            if not (stop_playback_event.is_set() or voice_muted):

                if os.path.exists(END_SOUND):

                    play_sound(END_SOUND, ignore_interrupt=True)

        except Exception:

            pass

        ui_safe(set_playing_status, "???啗??剜𦆮摰峕?")

    except Exception as e:

        text_area_insert(f"???啗??剜𦆮靘见?嚗㝯e}")

@with_relay_playback

def tts_full_play(text, force_chime_off=False): asyncio.run(speak_text_async(text, force_chime_off))



# ===== Piper (?Ｙ? TTS) 閮剖? =====

PIPER_CFG_PATH = Path(DATA_DIR) / "piper.json"

PIPER_FORCE = False  # ?誯??�誘?冽?撘瑕� Piper ?芸?嚗�? handle_msg嚗?



def _piper_find_model():

    """

    Search for .onnx files in the current directory or 'piper' subdirectory.

    Returns the path to the first found .onnx file, or None.

    Adapted from piper_standalone.py.

    """

    try:

        # Look for .onnx files in APP_DIR

        models = glob.glob(os.path.join(APP_DIR, "*.onnx"))

        if models:

            return models[0]

        # Check inside piper folder

        models = glob.glob(os.path.join(APP_DIR, "piper", "*.onnx"))

        if models:

            return models[0]

    except Exception:

        pass

    return None



def _piper_find_exe():

    """

    Search for piper.exe in 'piper' subdirectory of APP_DIR.

    """

    try:

        # Assuming standard structure: APP_DIR/piper/piper.exe

        exe_path = os.path.join(APP_DIR, "piper", "piper.exe")

        if os.path.isfile(exe_path):

            return exe_path

        # Or in APP_DIR?

        exe_path_root = os.path.join(APP_DIR, "piper.exe")

        if os.path.isfile(exe_path_root):

            return exe_path_root

    except Exception:

        pass

    return ""



def _piper_load_cfg():

    try:

        if PIPER_CFG_PATH.exists():

            j = json.loads(PIPER_CFG_PATH.read_text(encoding="utf-8"))

        else:

            j = {}

        

        # 撽𡑒??Ｘ?頝臬??臬炏?㗇?嚗𣬚�?�??齿?

        exe = j.get("piper_exe") or ""

        if not (exe and os.path.isfile(exe)):

            found_exe = _piper_find_exe()

            if found_exe: j["piper_exe"] = found_exe

        

        mdl = j.get("model") or ""

        if not (mdl and os.path.isfile(mdl)):

            found_model = _piper_find_model()

            if found_model: j["model"] = found_model



        j.setdefault("piper_exe", "")

        j.setdefault("model", "")

        j.setdefault("length_scale", 1.0)

        j.setdefault("noise_scale", 0.667)

        j.setdefault("noise_w", 0.8)

        j.setdefault("speaker", "")

        return j

    except Exception:

        return {

            "piper_exe": _piper_find_exe(), 

            "model": _piper_find_model() or "", 

            "length_scale": 1.0, 

            "noise_scale": 0.667, 

            "noise_w": 0.8, 

            "speaker": ""

        }



def _piper_available():

    exe = PIPER_CFG.get("piper_exe") or ""

    mdl = PIPER_CFG.get("model") or ""

    ok = os.path.isfile(exe) and os.path.isfile(mdl)

    if not ok:

        try:

            # Debug log (only if we expected it to work or during check)

            # Cannot use text_area_insert here easily if called frequently, 

            # but usually called in fallback logic context.

            pass

        except: pass

    return ok



def _piper_match_model(lang_code: str) -> str:

    """Find a model matching the language code (e.g. 'en-US' -> '*en_US*')"""

    if not lang_code: return ""

    # Normalize: zh-TW -> zh_TW, en-US -> en_US

    simplified = lang_code.replace("-", "_")

    parts = simplified.split("_")

    # Base pattern: e.g. "en_US"

    

    # Priority 1: Exact match in filename

    # Priority 2: Primary language match (e.g. 'en')

    

    candidates = []

    # Scan APP_DIR and APP_DIR/piper

    dirs_to_scan = [APP_DIR, os.path.join(APP_DIR, "piper")]

    try:

        for d in dirs_to_scan:

            if not os.path.isdir(d): continue

            for p in glob.glob(os.path.join(d, "*.onnx")):

                name = os.path.basename(p)

                if simplified in name:

                    return p # Found fairly specific match

                # If only primary language matches (e.g. 'en' in 'en_US')

                if parts[0] in name:

                    candidates.append(p)

    except: pass

    

    if candidates: return candidates[0]

    return ""  # Not found





def _piper_run_to_wav(text: str, out_wav: str, lang_code: str = None) -> tuple[bool, str]:

    # ?躰ㄐ?�虾?冽�扳炎?亦?敺格𦆮撖穿??芾???exe 撠梢�嗘?甇亙?蝞烾�𡁻?嚗峕芋?见??Ｗ?靘�𪄳

    exe = PIPER_CFG.get("piper_exe") or ""

    if not (exe and os.path.isfile(exe)):

        return (False, "piper.exe ?芸停蝺?)



    default_model = PIPER_CFG.get("model") or ""

    

    # 瘙箏?雿輻鍂?芸�𧢲芋??

    use_model = default_model

    if lang_code:

        # ?𡑒岫?曉??㕑?閮�?�芋??

        found = _piper_match_model(lang_code)

        if found:

            use_model = found

            # ?交𪄳?啁?璅∪?頝罸?閮凋??䕘??臬銁 log ?鞟內嚗��?剁?

    

    if not (use_model and os.path.isfile(use_model)):

        return (False, f"?芣𪄳?啣虾?冽芋??(lang={lang_code}, default={default_model})")



    # Check config

    if not os.path.isfile(use_model + ".json"):

        return (False, f"璅∪?閮剖?瑼娪�憭? {use_model}.json")



    cmd = [

        exe, "--model", use_model, "--output_file", out_wav,

        "--length-scale", str(PIPER_CFG.get("length_scale", 1.0)),

        "--noise-scale", str(PIPER_CFG.get("noise_scale", 0.667)),

        "--noise-w", str(PIPER_CFG.get("noise_w", 0.8)),

    ]

    spk = (PIPER_CFG.get("speaker") or "").strip()

    if spk:

        # 瘜冽?嚗朞𥅾?�?璅∪?嚗�? speaker ID ?航�銝漤�?剁??躰ㄐ?急?靽萘?

        cmd += ["--speaker", spk]

    try:

        # Match standalone script: Popen with text=True, encoding='utf-8'

        process = subprocess.Popen(

            cmd,

            stdin=subprocess.PIPE,

            stdout=subprocess.PIPE,

            stderr=subprocess.PIPE,

            text=True,

            encoding='utf-8'

        )

        stdout, stderr = process.communicate(input=text)

        

        ok = (process.returncode == 0 and os.path.isfile(out_wav) and os.path.getsize(out_wav) > 0)

        log = stderr if stderr else (stdout if stdout else "")

        if not ok and not log:

            log = f"No output. ExitCode={process.returncode}, WavExists={os.path.isfile(out_wav)}"



        return (ok, log if log else ("OK" if ok else "no output"))

    except Exception as e:

        return (False, str(e))



async def speak_text_async(text, force_chime_off=False):
    try:
        should_chime = CHIME_ENABLED and (not force_chime_off)
        # Parse Per-Message Metadata: {{L=xx|G=xx}}text
        local_lang = None
        local_gender = None
        
        # [Safety] Strip sender tag if present (e.g. "@API_V2: ...")
        # Matches "@Tag: " or "@Tag嚗?" at start
        if text.startswith("@"):
            import re
            text = re.sub(r"^@[\w_]+[:嚗鞲\s*", "", text)

        if text.startswith("{{") and "}}" in text:
            try:
                end_idx = text.find("}}")
                meta_str = text[2:end_idx]
                text = text[end_idx+2:]
                for part in meta_str.split("|"):
                    if "=" in part:
                        k, v = part.split("=", 1)
                        if k == "L": local_lang = v
                        if k == "G": local_gender = v
            except Exception: pass

        stop_playback_event.clear()  # ?鞾�?滚?撠𡡞𨺗鋡急??嗵??𨀣迫?埈??𤘪𪃾
        if stop_playback_event.is_set() or voice_muted:
            return
        ui_safe(set_playing_status, " ?𡑒?銝哨?")
        ui_safe(_set_progress, 0); STATE["progress"] = 0

        # [Fix] Unified Rate Fetching
        active_rate = STATE.get("voice_rate") or STATE.get("rate") or str(globals().get("voice_rate", "0%"))
        if not active_rate.endswith("%"): active_rate += "%"
        if not (active_rate.startswith("+") or active_rate.startswith("-")):
            active_rate = "+" + active_rate
            
        print(f"[DEBUG] speak_text_async: Using active_rate={active_rate}")

        lang = local_lang if local_lang else detect_language(text)
        is_taigi = (lang == "nan-TW")



        # ?啗?頝臬?嚗帋漱蝯血??典遆撘𤩺偘?橘??踹??滩??滚?/蝯鞉???

        if is_taigi:

            play_taigi_tts(text)

            return



        # [NEW] 0. MeloTTS (Priority 1)
        # ?𣂼� Melo ?�??�葉??(zh-TW, zh-CN, zh)
        is_zh = (lang and (lang.startswith("zh") or "zh" in lang))
        
        will_use_melo = (USE_MELO_TTS and HAS_MELO and melo_model and is_zh)

        if stop_playback_event.is_set() or voice_muted:
            return

        if USE_MELO_TTS:
            if not (HAS_MELO and melo_model):
                 text_area_insert(f"?𩤃? 頝喲? MeloTTS (Init={HAS_MELO}, Err={MELO_ERR})", "TTS")
            elif not is_zh:
                 text_area_insert(f"?對? MeloTTS ?�?銝剜?嚗𣬚𤌍?滩?蝟?{lang} 撠�歲?𦒘蒂雿輻鍂?蹱螱撘閙?", "TTS")
        
        if will_use_melo:
            try:
                # ?文?閫坿𠧧 
                melo_speaker_id = 0 # default
                try:
                    # Check gender preferences to map to Melo speakers if available?
                    # Currently Melo ZH usually has one speaker with id 0, or accents
                    # Let's see if we can find gender specific? 
                    # If not, just use default.
                    
                    spks = melo_model.hps.data.spk2id
                    # E.g. {'ZH': 0}
                    if 'ZH' in spks:
                        melo_speaker_id = spks['ZH']
                    elif spks:
                        melo_speaker_id = list(spks.values())[0]
                except:
                    pass

                STATE["playing"] = "melo_generating"
                ui_safe(set_playing_status, f"??AI ?�?銝?(MeloTTS)...")
                text_area_insert(f"?嬕儭?MeloTTS ?�?銝?..", "TTS")
                
                # Speed Control
                speed_factor = 1.0
                try:
                    val_str = active_rate.replace("%", "").strip()
                    val = float(val_str)
                    speed_factor = 1.0 + (val / 100.0)
                    speed_factor = max(0.5, min(2.0, speed_factor))
                except: pass

                # Save to wav
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as fp:
                    wav_path = fp.name
                
                # Inference (MeloTTS)
                # tts_to_file(text, speaker_id, output_path, speed=1.0)
                melo_model.tts_to_file(text, melo_speaker_id, wav_path, speed=speed_factor)
                
                if os.path.exists(wav_path) and os.path.getsize(wav_path) > 0:
                     ui_safe(set_playing_status, f"?? MeloTTS ?剜𦆮銝?..")
                     try:
                        if should_chime and os.path.exists(START_SOUND):
                            play_fx(START_SOUND, ignore_interrupt=True)
                            time.sleep(0.5) 
                     except: pass
                     
                     play_sound(wav_path)
                     try: os.remove(wav_path)
                     except: pass
                     
                     if not (stop_playback_event.is_set() or voice_muted):
                        ui_safe(set_playing_status, f"???𡑒?摰峕?嚗㇈eloTTS嚗?)
                        try:
                            if should_chime and os.path.exists(END_SOUND):
                                play_sound(END_SOUND, ignore_interrupt=True)
                        except: pass
                     return
                else:
                     text_area_insert("?𩤃? MeloTTS ?Ｗ枂蝛箸?獢?, "TTS")

            except Exception as e:
                 text_area_insert(f"??MeloTTS 憭望?: {e}", "TTS")
                 # Fallthrough to next engine


        if PIPER_FORCE and _piper_available():
            try:
                ui_safe(set_playing_status, "?? ?𡑒?銝?(Piper Force)...")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as fp:
                    wav_path = fp.name

                ok, log = _piper_run_to_wav(text, wav_path, lang_code=lang)

                if not ok:
                    text_area_insert(f"??Piper ?�?憭望?嚗Êorce嚗㚁?{log}", "TTS")
                else:
                    # [Chime] Piper Force
                    if should_chime and os.path.exists(START_SOUND):
                         play_fx(START_SOUND, ignore_interrupt=True)
                    play_sound(wav_path)
                    try: os.remove(wav_path)
                    except: pass

                    if not (stop_playback_event.is_set() or voice_muted):
                        try:
                            if should_chime and os.path.exists(END_SOUND):
                                play_sound(END_SOUND, ignore_interrupt=True)
                        except Exception:
                            pass
                        ui_safe(set_playing_status, "???𡑒?摰峕?嚗㇊iper ?Ｙ?嚚𠨑orce嚗?)
                    return

            except Exception as e:
                text_area_insert(f"??Piper force 靘见?嚗㝯e}", "TTS")


        # 1. Azure Speech SDK (Official) - Highest Priority if configured
        azure_key = os.environ.get("AZURE_SPEECH_KEY") or STATE.get("azure_speech_key")
        azure_region = os.environ.get("AZURE_SPEECH_REGION") or STATE.get("azure_speech_region")
        
        if TRIAL_EXPIRED:
            text_area_insert("?𩤃? 閰衣鍂?笔歇?𠬍??��雿輻鍂 gTTS ?蹱螱", "TTS")
        elif azure_key and azure_region:
            ui_safe(set_playing_status, "?? ?𡑒?銝?(Azure TTS)...")
            try:
                import azure.cognitiveservices.speech as speechsdk
                
                # Setup Config
                speech_config = speechsdk.SpeechConfig(subscription=azure_key, region=azure_region)
                v_azure = get_voice_id_auto(text, lang_code=local_lang, gender_code=local_gender) or "zh-TW-HsiaoChenNeural"
                speech_config.speech_synthesis_voice_name = v_azure
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as fp:
                    wav_path = fp.name
                
                audio_config = speechsdk.audio.AudioOutputConfig(filename=wav_path)
                synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
                
                # [Fix] Ensure rate has sign (+/-) for Azure/EdgeTTS
                rate_str = active_rate 
                ssml_text = f"<speak version='1.0' xml:lang='{lang}' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='http://www.w3.org/2001/mstts'><voice name='{v_azure}'><mstts:express-as style='general'><prosody rate='{rate_str}'>{text}</prosody></mstts:express-as></voice></speak>"

                result = synthesizer.speak_ssml_async(ssml_text).get()

                if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                    # [Chime] Azure
                    if should_chime and os.path.exists(START_SOUND):
                         play_fx(START_SOUND, ignore_interrupt=True)
                    play_sound(wav_path)
                    try: os.remove(wav_path)
                    except: pass
                    if not (stop_playback_event.is_set() or voice_muted):
                        try:
                            if should_chime and os.path.exists(END_SOUND):
                                play_sound(END_SOUND, ignore_interrupt=True)
                        except: pass
                        ui_safe(set_playing_status, f"???𡑒?摰峕?嚗㇁zure Official: {v_azure}嚗?)
                    return
                else:
                    cancellation_details = result.cancellation_details
                    text_area_insert(f"?𩤃? Azure Speech 憭望?嚗㝯cancellation_details.reason} - {cancellation_details.error_details}", "TTS")

            except ImportError:
                 text_area_insert("?𩤃? ?芸?鋆?azure-cognitiveservices-speech嚗諹歲??Azure 摰䀹䲮頝臬?", "TTS")
            except Exception as e:
                 text_area_insert(f"?𩤃? Azure Speech 靘见?嚗㝯e}", "TTS")


        # Edge TTS Logic
        primary_voice = get_voice_id_auto(text, lang_code=local_lang, gender_code=local_gender) or "zh-TW-HsiaoChenNeural"
        safe_tw = "zh-TW-HsiaoChenNeural"
        safe_en = "en-US-JennyNeural"
        # [Fix] Ensure rate is sanitized for Edge TTS too
        sanitized_rate_edge = "+0%"
        if voice_rate:
             vr = str(voice_rate).strip()
             if vr.endswith("%"):
                 if not vr.startswith("+") and not vr.startswith("-"):
                     sanitized_rate_edge = "+" + vr
                 else:
                     sanitized_rate_edge = vr
             else:
                 try: sanitized_rate_edge = f"{int(float(vr)):+d}%"
                 except: pass

        trials = [
            (primary_voice, active_rate),
            (primary_voice, None),
            (safe_tw, None),
            (safe_en, None),
        ]

        # [Circuit Breaker] check
        should_use_edge = (USE_EDGE_TTS and STATE.get("edge_tts_fails", 0) < 3)
         
        if not TRIAL_EXPIRED and should_use_edge:
             for v, r in trials:
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                        mp3_path = fp.name
                    
                    ui_safe(set_playing_status, f"?? ?𡑒?銝?(EdgeTTS: {v})...")
                    
                    if r is not None:
                        tts = edge_tts.Communicate(text=text, voice=v, rate=r, volume='+50%')
                    else:
                        tts = edge_tts.Communicate(text=text, voice=v, volume='+50%')
                    
                    await tts.save(mp3_path)

                    if not os.path.exists(mp3_path) or os.path.getsize(mp3_path) == 0:
                        raise RuntimeError("edge-tts returned empty file")

                    if stop_playback_event.is_set() or voice_muted:
                        try: os.remove(mp3_path)
                        except Exception: pass
                        return

                    # [Chime] EdgeTTS
                    if should_chime and os.path.exists(START_SOUND):
                         play_fx(START_SOUND, ignore_interrupt=True)
                    play_sound(mp3_path)
                    try: os.remove(mp3_path)
                    except Exception: pass

                    if not (stop_playback_event.is_set() or voice_muted):
                        try:
                            if should_chime and os.path.exists(END_SOUND):
                                play_sound(END_SOUND, ignore_interrupt=True)
                        except Exception:
                            pass
                        ui_safe(set_playing_status, f"???𡑒?摰峕?嚗ùv}{'' if r is None else f', {r}'}嚗?)
                        STATE["edge_tts_fails"] = 0
                    return

                except Exception as e:
                    # [Fallback] If SSL/Connect error
                    err_str = str(e)
                    if "SSL" in err_str or "CERTIFICATE" in err_str or "ClientConnectorError" in err_str:
                         print(f"[EdgeTTS] SSL/Network error: {e}. Retrying with unverified context...")
                         try:
                             import ssl
                             _orig = ssl.create_default_context
                             ssl.create_default_context = ssl._create_unverified_context
                             try:
                                 with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                                    mp3_path = fp.name
                                 
                                 ui_safe(set_playing_status, f"?? ?𡑒?銝?(EdgeTTS Unverified: {v})...")
                                 if r is not None:
                                     tts = edge_tts.Communicate(text=text, voice=v, rate=r, volume='+50%')
                                 else:
                                     tts = edge_tts.Communicate(text=text, voice=v, volume='+50%')
                                 
                                 await tts.save(mp3_path)

                                 # [Chime] EdgeTTS (Unverified)
                                 if should_chime and os.path.exists(START_SOUND):
                                     play_fx(START_SOUND, ignore_interrupt=True)
                                 play_sound(mp3_path)
                                 try: os.remove(mp3_path)
                                 except: pass

                                 if not (stop_playback_event.is_set() or voice_muted):
                                     ui_safe(set_playing_status, f"???𡑒?摰峕?嚗㇎nverified SSL: {v}嚗?)
                                     STATE["edge_tts_fails"] = 0
                                 return # Success
                             finally:
                                 ssl.create_default_context = _orig
                         except Exception as e2:
                             print(f"[EdgeTTS] Retry failed: {e2}")

                    reason = str(e)
                    text_area_insert(f"?𩤃? Edge TTS 憭望?嚗ǒoice={v}, rate={r}嚗㚁?{reason}", "TTS")
                    continue





        # 2nd Priority: gTTS

        text_area_insert("?對? Edge TTS 銝滚虾?剁?頧厩鍂 gTTS ?蹱螱??, "TTS")

        try:

            # Map simplified lang codes for gTTS

            # lang (e.g. "zh-TW", "en-US") comes from detect_language() earlier in function

            gtts_map = {

                "zh-TW": "zh-tw", "zh-CN": "zh-cn",

                "en-US": "en", "en-GB": "en",

                "ja-JP": "ja",

                "ko-KR": "ko",

                "vi-VN": "vi",

                "id-ID": "id",

                # gTTS often fails on unknown codes, default to zh-tw or en?

            }

            t_lang = gtts_map.get(lang, "zh-tw")

            

            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:

                tmp = fp.name

            gTTS(text, lang=t_lang).save(tmp)

            if not (stop_playback_event.is_set() or voice_muted):

                # [Chime] gTTS
                if should_chime and os.path.exists(START_SOUND):
                     play_fx(START_SOUND, ignore_interrupt=True)
                play_sound(tmp)

            try:

                os.remove(tmp)

            except Exception:

                pass

            if not (stop_playback_event.is_set() or voice_muted):

                try:

                    if os.path.exists(END_SOUND):

                        play_sound(END_SOUND, ignore_interrupt=True)

                except Exception:

                    pass

                ui_safe(set_playing_status, "???𡑒?摰峕?嚗āTTS ?蹱螱嚗?)

            return

        except Exception as e:

            text_area_insert(f"??gTTS ?蹱螱憭望?嚗㝯e}嚗�?閰?Piper...", "TTS")

            pass



        # 3rd Priority: Piper

        # Reload CFG just in case user added it recently

        global PIPER_CFG

        if not _piper_available():

            PIPER_CFG = _piper_load_cfg()



        if not TRIAL_EXPIRED and _piper_available():
            text_area_insert(f"?對? gTTS 銝滚虾?剁?頧厩鍂 Piper ?蹱螱??, "TTS")
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as fp:
                    wav_path = fp.name
                ok, log = _piper_run_to_wav(text, wav_path, lang_code=lang)
                if ok:
                    if stop_playback_event.is_set() or voice_muted:
                        try: os.remove(wav_path)
                        except: pass
                        return
                    # [Chime] Piper Fallback
                    if should_chime and os.path.exists(START_SOUND):
                         play_fx(START_SOUND, ignore_interrupt=True)
                    play_sound(wav_path)
                    try: os.remove(wav_path)
                    except: pass
                    if not (stop_playback_event.is_set() or voice_muted):
                        try:
                            if os.path.exists(END_SOUND):
                                play_sound(END_SOUND, ignore_interrupt=True)
                        except Exception:
                            pass
                        ui_safe(set_playing_status, "???𡑒?摰峕?嚗㇊iper ?Ｙ?嚗?)
                    return
                else:
                    text_area_insert(f"??Piper ?�?憭望?嚗㝯log}", "TTS")
            except Exception as e:
                text_area_insert(f"??Piper 靘见?嚗㝯e}", "TTS")
        else:
             # Debug info for user
             pe = PIPER_CFG.get("piper_exe") or "?芾身摰?
             pm = PIPER_CFG.get("model") or "?芾身摰?
             text_area_insert(f"?𩤃? Piper 撠𡁏𧊋撠梁?嚗𠄌xe: {pe}, Model: {pm}嚗?, "TTS")



        try:

            import pyttsx3

            eng = pyttsx3.init(); eng.say(text); eng.runAndWait()

            if not (stop_playback_event.is_set() or voice_muted):

                ui_safe(set_playing_status, "???𡑒?摰峕?嚗𠄎API5 ?Ｙ?嚗?)

            return

        except Exception:

            pass



        ui_safe(set_playing_status, "???𡑒?憭望?")

        ui_safe(_set_progress, 0); STATE["progress"] = 0



    except Exception as e:

        print("隤鮋𨺗?�?憭望?嚗?, e)

        ui_safe(set_playing_status, "???𡑒?憭望?")

        ui_safe(_set_progress, 0); STATE["progress"] = 0



def speak_text(text, force_chime_off=False): tts_full_play(text, force_chime_off)



def speech_worker():

    while True:

        text = speech_queue.get()

        try:

            if stop_playback_event.is_set() or voice_muted: continue

            speak_text(text)

        finally:

            speech_queue.task_done()



# ===============================

# == [ANCHOR] 蝬脰楝撌亙� ==

# ===============================



def get_local_ip():

    try:

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 80))

        ip = s.getsockname()[0]; s.close(); return ip

    except: return "?⊥??硋? IP"



# ===============================

# == [ANCHOR] QR ?函?撠讛?蝒?==

# ===============================

_qr_popup_refs = []  # ?脫迫敶勗?鋡怠??曉???



def show_qr_popup(title_text: str, url_text: str):

    if not _HAS_QR:

        try:

            messagebox.showinfo(title_text, f"URL嚗㝯url_text}\n\n嚗�𧊋摰㕑? qrcode/Pillow嚗𣬚�瘜閖＊蝷?QR嚗?)

        except Exception:

            pass

        return

    if DISABLE_GUI or not root:
        print(f"QR Popup ({title_text}): {url_text}")
        return
    win = tk.Toplevel(root)

    win.title(title_text)

    win.configure(bg=THEME["bg_card"])

    win.attributes("-topmost", True)

    win.resizable(False, False)

    # ?Ｙ? QR

    try:

        img = qrcode.make(url_text).resize((240,240))

        photo = ImageTk.PhotoImage(img)

        _qr_popup_refs.append(photo)

        tk.Label(win, image=photo, bg=THEME["bg_card"]).pack(padx=16, pady=(16,8))

    except Exception as e:

        tk.Label(win, text=f"QR ?�?憭望?嚗㝯e}", bg=THEME["bg_card"], fg="#EF4444").pack(padx=16, pady=12)



    ent = tk.Entry(win, width=46, font=("Consolas", 11), relief="solid", bd=1)

    ent.insert(0, url_text); ent.configure(state="readonly")

    ent.pack(padx=16, pady=(4,10))



    btns = tk.Frame(win, bg=THEME["bg_card"]); btns.pack(pady=(0,16))

    def _copy():

        try:

            root.clipboard_clear(); root.clipboard_append(url_text)

            messagebox.showinfo("撌脰?鋆?, "URL 撌脰?鋆賢�?芾票蝪?)

        except Exception: pass

    def _open():

        try: webbrowser.open(url_text)

        except Exception: pass

    tk.Button(btns, text="銴�ˊ URL", command=_copy, bg="#F1F5F9", relief="flat", font=THEME["font_s"]).pack(side="left", padx=6)

    tk.Button(btns, text="?函�讛汗?券???, command=_open, bg="#D1FAE5", relief="flat", font=THEME["font_s"]).pack(side="left", padx=6)

    tk.Button(btns, text="?𣈯?", command=win.destroy, bg="#FEE2E2", relief="flat", font=THEME["font_s"]).pack(side="left", padx=6)



# ===============================

# == [ANCHOR] ?滨垢 URL + QR ==

# ===============================



def compute_frontend_url() -> str:

    try:

        ip = get_local_ip()

        if not ip or "?⊥??硋?" in ip:

            ip = "127.0.0.1"

        ui_index = os.path.join(UI_TEMPLATE_DIR, "index.html")

        path = "/static/ui/index.html" if os.path.exists(ui_index) else "/"

        return f"http://{ip}:{HTTP_PORT}{path}"

    except Exception:

        return f"http://127.0.0.1:{HTTP_PORT}/"



def open_frontend_and_qr_popup():

    if DISABLE_WEB:

        try:

            messagebox.showwarning("?滨垢?芸???, "?桀?閮剖???DISABLE_WEB=True嚗峕𧊋?笔? Flask 隡箸??具�?)

        except Exception:

            pass

        return

    url = compute_frontend_url()

    try:

        webbrowser.open(url)

        ui_safe(ngrok_status_label.config, text=f" ?滨垢嚗㝯url}")

    except Exception:

        ui_safe(lambda: show_qr_popup("?祉雯?批�??QR", url))



# ===============================

# == [ANCHOR] CSV 蝝�??==

# ===============================



def save_to_csv(message, sender="", relay_status=None, ip=None):

    msg = "" if message is None else str(message)

    if msg.strip().lower().startswith("announce"):  # Skip pure announce records

        return

    today = datetime.now().strftime("%Y-%m-%d"); filename = os.path.join(DATA_DIR, f"log_{today}.csv")

    os.makedirs(DATA_DIR, exist_ok=True)

    with open(filename, 'a', newline='', encoding='utf-8') as f:

        csv.writer(f).writerow([

            datetime.now().strftime("%H:%M:%S"), sender, msg, (relay_status or "N/A"), (ip or "")

        ])



# ===============================

# == [ANCHOR] ?啗? TTS (itaigi ??gTTS ?蹱螱) ==

# ===============================



# ===============================
# == [ANCHOR] ?啗? TTS (itaigi ??gTTS ?蹱螱) ==
# ===============================

def generate_taigi_tts(text, gender=None, speed_percent=None):
    """
    ?Ｙ??啗?隤鮋𨺗瑼?(銝齿偘????
    ?𧼮�: 瑼娍?蝯訫?頝臬? (雿齿䲰 UPLOAD_DIR)
    """
    # 瘙箏??脣ê̌
    if gender:
        # e.g. "female" or "male"
        voice_label = "normal_f2" if str(gender).startswith("f") else "normal_m2"
    else:
        # Fallback to global setting
        g = globals().get("voice_gender") or "female"
        voice_label = "normal_f2" if g.startswith("f") else "normal_m2"

    # 瘙箏?瑼𥪜? (?臭?)
    import hashlib
    h = hashlib.md5(text.encode("utf-8")).hexdigest()[:8]
    ts = int(time.time())
    # Save to UPLOAD_DIR for easier download/preview
    base_name = f"taigi_{ts}_{h}.mp3"
    final_path = os.path.join(UPLOAD_DIR, base_name)
    
    # 1. ?𡑒岫撠�鍂璅∠?
    try:
        headers = {"x-api-key": TAIGI_TTS_API_KEY, "Content-Type": "application/json"}
        payload = {"text": text, "model": "model5", "voice_label": voice_label, "user": ""}
        
        # Use existing fallback logic if available
        if "TAIGI_TTS_ENDPOINTS" in globals() and "_post_with_fallback" in globals():
             r = _post_with_fallback(TAIGI_TTS_ENDPOINTS, headers, payload, timeout=30)
        else:
             r = requests.post(TAIGI_TTS_ENDPOINT, headers=headers, json=payload, timeout=30)

        if r.status_code == 200:
            jr = r.json()
            url = jr.get("converted_audio_url") or jr.get("url")
            if url:
                r2 = requests.get(url, stream=True, timeout=30)
                if r2.status_code == 200:
                    # Save RAW content first
                    raw_ext = ".wav"
                    temp_raw = final_path + ".raw" + raw_ext
                    
                    with open(temp_raw, "wb") as fp:
                        for chunk in r2.iter_content(chunk_size=8192):
                            if chunk: fp.write(chunk)
                    
                    # ?笔漲隤踵㟲 + 頧㗇? MP3
                    # Calculate factor
                    factor = 1.0
                    if speed_percent is not None:
                        # speed_percent e.g. 1.2 or 0.8
                        factor = float(speed_percent)
                    else:
                        # Use global
                        v_rate = globals().get("voice_rate") # e.g. "+20%" or "-10%"
                        if v_rate:
                            try:
                                val = int(v_rate.replace("%","").strip())
                                factor = 1.0 + (val / 100.0)
                            except: pass

                    # Clamp
                    if factor < 0.5: factor = 0.5
                    if factor > 3.0: factor = 3.0
                    
                    # FFMPEG Convert/Effect
                    if globals().get("_FFMPEG"):
                        # If factor is effectively 1.0, just convert to MP3
                        # else usage atempo
                        filter_args = []
                        if abs(factor - 1.0) > 0.01:
                            filter_args = ["-filter:a", f"atempo={factor}"]
                        
                        cmd = [_FFMPEG, "-y", "-i", temp_raw, "-ac", "2", "-ar", "44100", "-b:a", "192k"] + filter_args + [final_path]
                        
                        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        
                        # Clean raw
                        try: os.remove(temp_raw)
                        except: pass
                        
                        if os.path.exists(final_path):
                            return final_path
                    else:
                        # No ffmpeg, just rename wav to mp3 (hacky) or keep wav? 
                        # Ideally system needs ffmpeg. If not, just return wav path?
                        # Let's assume we rename to .wav if ffmpeg missing
                        final_path_wav = final_path.replace(".mp3", ".wav")
                        os.rename(temp_raw, final_path_wav)
                        return final_path_wav

    except Exception as e:
        print(f"[TaigiGen] Dedicated module failed: {e}")

    # 2. Fallback itaigi
    try:
        api_url = f"https://itaigi.tw/api/tts/{text}"
        resp = requests.get(api_url, timeout=7)
        if resp.status_code == 200 and resp.content:
             with open(final_path, "wb") as f:
                 f.write(resp.content)
             return final_path
    except Exception as e:
        print(f"[TaigiGen] itaigi failed: {e}")

    # 3. Fallback gTTS
    try:
        tts = gTTS(text, lang='zh-tw') # gTTS uses zh-tw for Taiwanese accent approximation if nan not avail
        tts.save(final_path)
        return final_path
    except Exception as e:
        print(f"[TaigiGen] gTTS failed: {e}")

    raise RuntimeError("All Taigi TTS methods failed")


def play_taigi_tts(text):
    # ?芸?雿輻鍂撠�鍂?啗?璅∠?嚗ēearn-language.tokyo嚗㚁?憭望??漤��??itaigi/gTTS??
    try:
        # Generate
        path = generate_taigi_tts(text)
        
        # Play (Server Side)
        if path:
            # If it comes from dedicated module (often wav or mp3), we use fx player
            # But generate_taigi_tts now returns a file in UPLOAD_DIR
            taigi_play_wav_with_fx(path)
            
            # Optional: Clean up if you don't want to keep broadcast files?
            # But user said "Download", so maybe keep it.
            # Let's keep it in UPLOAD_DIR.
            
    except Exception as e:
        text_area_insert(f"?𩤃? ?啗??剖𥼚憭望?嚗㝯e}", "TTS")

@app.route('/taigi/say', methods=['POST'])
def api_taigi_say():
    try:
        data = request.json or request.form or {}
        text = data.get("text")
        if not text: return jsonify(ok=False, error="No text"), 400
        
        gender = data.get("gender") # "male" or "female" or "m" / "f"
        play = data.get("play")
        speed = data.get("speed") # float 1.0
        
        if play == "true" or play is True:
             # Server Playback
             def _task():
                 try:
                     path = generate_taigi_tts(text, gender, speed)
                     taigi_play_wav_with_fx(path)
                 except Exception as e:
                     text_area_insert(f"?𩤃? API?啗?憭望?: {e}")
             threading.Thread(target=_task, daemon=True).start()
             return jsonify(ok=True, message="Playing")
        else:
             # Generation Only (Preview/Download)
             path = generate_taigi_tts(text, gender, speed)
             filename = os.path.basename(path)
             
             # Register in metadata for UPLOAD_DIR listing
             _write_upload_meta(path, f"Taigi-{text[:10]}", filename, "audio")
             
             return jsonify(ok=True, file=filename, url=f"/download/{filename}")

    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

@app.route('/download/<path:filename>')
def download_file(filename):
    # Serve files from UPLOAD_DIR
    try:
        return send_from_directory(UPLOAD_DIR, filename, as_attachment=True)
    except Exception as e:
         # Fallback check RECORD_DIR just in case
        if os.path.exists(os.path.join(RECORD_DIR, filename)):
            return send_from_directory(RECORD_DIR, filename, as_attachment=True)
        return str(e), 404




# ===============================

# == [ANCHOR] ?刻攟撟閗???==

# ===============================

fs_win = None



def show_fullscreen_message(msg):

    global fs_win

    try:

        if fs_win is not None and fs_win.winfo_exists(): fs_win.destroy()

    except: pass

    if DISABLE_GUI or not root:
        print(f"Fullscreen Message: {msg}")
        return
    fs_win = tk.Toplevel(root); fs_win.attributes("-fullscreen", True); fs_win.attributes("-topmost", True)

    fs_win.config(bg="#0F172A"); fs_win.attributes('-alpha', 0.95)

    def close_win(event=None):

        try: fs_win.destroy()

        except: pass

    for ev in ["<Button>","<Button-1>","<Button-2>","<Button-3>","<Key>","<Escape>"]: fs_win.bind(ev, close_win)

    frame = tk.Frame(fs_win, bg="#0F172A"); frame.pack(expand=True, fill="both")

    tk.Label(frame, text=" 蝺𦠜�亥??舫�𡁶䰻", font=("Microsoft JhengHei UI", 44, "bold"), fg="#38BDF8", bg="#0F172A").pack(pady=(90,40))

    tk.Label(frame, text=msg, font=("Microsoft JhengHei UI", 36, "bold"), fg="#F8FAFC", bg="#0F172A", wraplength=1400, justify="center").pack(expand=True)

    tk.Label(frame, text="嚗�??𨳍��?隞餅??菜???Esc ?𣈯?嚗?, font=("Microsoft JhengHei UI", 22), fg="#94A3B8", bg="#0F172A").pack(pady=(40,30))

    fs_win.focus_force(); fs_win.grab_set(); fs_win.lift()



# ===============================

# == [ANCHOR] 隤脰”嚗�????垍?/閫貊䔄嚗?==

# ===============================

TIMETABLE_PATH = os.path.join(_BASE_FOR_TT, "timetable.json")

timetable_enabled = True

timetable_data = {

    "enabled": True,

    "treat_saturday_as_school": False,

    "skip_holidays": True,

    "holidays": [],

    "items": []

}

_TIMETABLE_MTIME = None

_last_fired = set()



def _norm_dow(d):

    if isinstance(d, int): return d

    if isinstance(d, str):

        d = d.strip().lower()

        mapping = {"mon":1,"tue":2,"wed":3,"thu":4,"fri":5,"sat":6,"sun":7,

                   "1":1,"2":2,"3":3,"4":4,"5":5,"6":6,"7":7}

        return mapping.get(d, None)

    return None



def _parse_csv_lines(lines: list[str]):

    items = []

    for row in csv.reader(lines):

        if not row or row[0].strip().startswith("#"):

            continue

        if len(row) < 3:

            continue

        dow_s = row[0].strip()

        time_s = row[1].strip()

        action = row[2].strip()

        label = row[3].strip() if len(row) >= 4 else ""

        nd = _norm_dow(dow_s)

        if nd:

            items.append({"dow": nd, "time": time_s, "action": action, "label": label})

    return items



def _load_timetable_from_disk():

    global timetable_data, timetable_enabled, _TIMETABLE_MTIME

    os.makedirs(DATA_DIR, exist_ok=True)

    data = {"enabled": True, "treat_saturday_as_school": False, "skip_holidays": True, "holidays": [], "items": []}

    path_json = TIMETABLE_PATH

    path_csv = os.path.join(_BASE_FOR_TT, "timetable.csv")

    loaded = False

    try:

        if os.path.isfile(path_json):

            with open(path_json, "r", encoding="utf-8") as f:

                raw = json.load(f)

            data["enabled"] = bool(raw.get("enabled", True))

            data["treat_saturday_as_school"] = bool(raw.get("treat_saturday_as_school", False))

            data["skip_holidays"] = bool(raw.get("skip_holidays", True))

            data["holidays"] = list(raw.get("holidays", []))

            items = raw.get("items", [])

            norm_items = []

            for it in items:

                it = dict(it)

                if "date" in it:

                    norm_items.append({"date": it["date"], "time": it.get("time", "08:00"), "action": it.get("action",""), "label": it.get("label","")})

                else:

                    dow = it.get("dow") or it.get("weekday") or it.get("days")

                    if isinstance(dow, (list, tuple)):

                        for d in dow:

                            nd = _norm_dow(d)

                            if nd: norm_items.append({"dow": nd, "time": it.get("time","08:00"), "action": it.get("action",""), "label": it.get("label","")})

                    else:

                        nd = _norm_dow(dow)

                        if nd: norm_items.append({"dow": nd, "time": it.get("time","08:00"), "action": it.get("action",""), "label": it.get("label","")})

            data["items"] = norm_items

            loaded = True

        elif os.path.isfile(path_csv):

            with open(path_csv, "r", encoding="utf-8") as f:

                lines = f.read().splitlines()

            data["items"] = _parse_csv_lines(lines)

            loaded = True

        else:

            sample = {

                "enabled": True,

                "treat_saturday_as_school": False,

                "skip_holidays": True,

                "holidays": [],

                "items": [

                    {"dow":1, "time":"07:58", "action":"Bell:ClassStart", "label":"銝𡃏玨??},

                    {"dow":1, "time":"08:00", "action":"ShowMsg:?拙?嚗�?摮詨�𡢅?", "label":"閮𦠜�"},

                    {"dow":1, "time":"10:00", "action":"PlayMP3:Award.mp3", "label":"?垍??單?"},

                ]

            }

            with open(path_json, "w", encoding="utf-8") as f:

                json.dump(sample, f, ensure_ascii=False, indent=2)

            data = sample; loaded = True

    except Exception as e:

        text_area_insert(f"??頛匧�隤脰”憭望?嚗㝯e}")

    timetable_data = data

    timetable_enabled = bool(timetable_data.get("enabled", True))

    try:

        _TIMETABLE_MTIME = os.path.getmtime(path_json)

    except Exception:

        _TIMETABLE_MTIME = None

    STATE["timetable"] = {

        "enabled": timetable_enabled,

        "loaded": loaded,

        "count": len(timetable_data.get("items", [])),

        "path": TIMETABLE_PATH

    }

    if 'timetable_status_var' in globals():

        ui_safe(timetable_status_var.set, f" 隤脰”嚗㝯'?毺鍂' if timetable_enabled else '?𦦵鍂'}嚗�歇頛匧� {STATE['timetable']['count']} 蝑?)

    if 'timetable_path_var' in globals():

        ui_safe(lambda: timetable_path_var.set(f"頝臬?嚗㝯STATE['timetable']['path']}"))

    if 'refresh_timetable_tree' in globals():

        ui_safe(refresh_timetable_tree)



def _is_holiday(today: date) -> bool:

    if today.isoweekday() == 6 and not timetable_data.get("treat_saturday_as_school", False):

        return True

    if timetable_data.get("skip_holidays", True):

        ymd = today.strftime("%Y-%m-%d")

        if ymd in (timetable_data.get("holidays") or []):

            return True

    return False



def _parse_hhmm_to_minutes(s: str) -> int | None:

    try:

        h, m = s.strip().split(":")

        return int(h)*60 + int(m)

    except Exception:

        return None



def compute_next_ring(now_dt=None):

    if now_dt is None: now_dt = datetime.now()

    if not timetable_data.get("items"): return None

    for day_offset in range(0, 14):

        d = (now_dt.date() if hasattr(now_dt, "date") else date.today()) + timedelta(days=day_offset)

        if _is_holiday(d): continue

        wd = d.isoweekday(); ymd = d.strftime("%Y-%m-%d")

        candidates = []

        for i, it in enumerate(timetable_data.get("items", [])):

            t = (it.get("time") or "").strip()

            if not t: continue

            mins = _parse_hhmm_to_minutes(t)

            if mins is None: continue

            if it.get("date"):

                if it["date"] == ymd: continue

            else:

                dow = it.get("dow") or it.get("weekday") or it.get("days")

                ok = False

                if isinstance(dow, (list, tuple)):

                    ok = any(int(d)==wd if isinstance(d, int) or str(d).isdigit() else False for d in dow)

                else:

                    try: ok = int(dow) == wd

                    except Exception: ok = False

                if not ok: continue

            if day_offset == 0:

                now_mins = now_dt.hour*60 + now_dt.minute

                if mins <= now_mins: continue

            candidates.append((mins, it.get("label","")))

        if candidates:

            mins, label = sorted(candidates)[0]

            hh, mm = divmod(mins, 60)

            return ymd, f"{hh:02d}:{mm:02d}", label

    return None



def update_next_label():

    try:

        if not timetable_enabled:

            ui_safe(timetable_next_var.set, " 銝衤?甈∴??䈑??芸??㯄??𣈯?嚗?); return

        nxt = compute_next_ring()

        if not nxt:

            ui_safe(timetable_next_var.set, " 銝衤?甈∴???)

        else:

            ymd, hhmm, label = nxt

            disp = f" 銝衤?甈∴?{ymd} {hhmm}" + (f"嚚画label}" if label else "")

            ui_safe(timetable_next_var.set, disp)

    except Exception:

        pass



def _now_hhmm() -> str: return datetime.now().strftime("%H:%M")

def _today_str() -> str: return datetime.now().strftime("%Y-%m-%d")

def _sender_ip_from_addr(addr) -> str | None:

    return addr[0] if isinstance(addr, tuple) and len(addr) >= 1 else None



def _trigger_action(action: str, label: str = "", src: str = "Timetable", idx: int | None = None):

    sender = f"{src}{'' if idx is None else '#'+str(idx)}"

    text_area_insert(f" 隤脰”閫貊䔄嚗ùsender}嚗㚁?{label or action}")

    save_to_csv(f"Schedule:{label or action}", sender)

    try:

        threading.Thread(target=handle_msg, args=(action, sender), daemon=True).start()

    except Exception as e:

        text_area_insert(f"??隤脰”閫貊䔄憭望?嚗㝯e}")



_last_fired_today = set()

SCHEDULES_PATH = Path(DATA_DIR) / 'schedules.json'

_SCHEDULES_MTIME = None

_schedules_last_fired = set()



def timetable_scheduler_loop():

    global _last_fired_today

    while True:

        try:

            if timetable_enabled and timetable_data.get("items"):

                today = date.today()

                if not _is_holiday(today):

                    hhmm = _now_hhmm()

                    ymd = _today_str()

                    wd = today.isoweekday()

                    for i, it in enumerate(timetable_data.get("items", [])):

                        action = (it.get("action") or "").strip()

                        if not action: continue

                        label = it.get("label",""); key = f"{ymd} {hhmm} #{i}"

                        if key in _last_fired_today: continue

                        if it.get("date"):

                            if it["date"] == ymd and it.get("time") == hhmm:

                                _last_fired_today.add(key); _trigger_action(action, label, idx=i)

                        else:

                            if int(it.get("dow", 0)) == wd and it.get("time") == hhmm:

                                _last_fired_today.add(key); _trigger_action(action, label, idx=i)

            prefix = _today_str()

            for k in list(_last_fired_today):

                if not k.startswith(prefix): _last_fired_today.discard(k)

        except Exception as e:

            text_area_insert(f"?𩤃? 隤脰”?垍??券𥲤隤歹?{e}")

        time.sleep(TIMETABLE_SCAN_SEC)



def timetable_play_index(idx: int):

    items = timetable_data.get("items", [])

    for i, it in enumerate(items):

        if i == idx:

            _trigger_action(it.get("action",""), it.get("label",""), idx=idx)

            return

    text_area_insert(f"?𩤃? 隤脰”蝝Ｗ?頞�枂蝭�?嚗㝯idx}")



# ===== ?脫迫?滨垢/敺𣬚垢?峕??䭾?敺芰兛?鮋��??餅?/?駁?嚗?=====

_DEDUP_LOCK = threading.RLock()

_RECENT_MSG_TS = {}

DEDUP_WINDOW_SEC = float(os.environ.get("LOOP_DEDUP_WINDOW", "2.0"))



def _is_duplicate_message(sender_ip: str | None, text: str) -> bool:

    t = (text or "").strip()

    # ?刻攟撟閗??荔??急偘???𣈯𨺗嚗劐??𡁜縧?㵪??踹?????厰?鋡怠蕭??

    if t.startswith("ShowMsg:") or t.startswith("SilentMsg:"):

        return False

    key = (sender_ip or "-", (text or "").strip())

    now = time.time()

    with _DEDUP_LOCK:

        last = _RECENT_MSG_TS.get(key)

        if last is not None and (now - last) < DEDUP_WINDOW_SEC:

            try:

                _diag(f"[LoopGuard] drop dup from {sender_ip}: {text[:80]}")

            except Exception:

                pass

            return True

        _RECENT_MSG_TS[key] = now

        if len(_RECENT_MSG_TS) > 2000:

            cutoff = now - (DEDUP_WINDOW_SEC * 5.0)

            for k, v in list(_RECENT_MSG_TS.items()):

                if v < cutoff:

                    _RECENT_MSG_TS.pop(k, None)

    return False



# ===============================

# == [ANCHOR] ?�誘?閧? ==

# ===============================



def handle_msg(text, addr):

    global voice_muted, voice_gender, voice_language, config, voice_rate, timetable_enabled, PIPER_FORCE, PIPER_CFG



    sender_ip = _sender_ip_from_addr(addr) if isinstance(addr, tuple) else None

    sender = addr[0] if isinstance(addr, tuple) else str(addr)



    if isinstance(addr, tuple):

        sender_ip = addr[0]

        sender_tag = addr[1] if len(addr) >= 2 else ""

        sender = f"{sender_tag}@{sender_ip}" if sender_tag else sender_ip



    if isinstance(addr, tuple) and _is_duplicate_message(sender_ip, text):

        return



    # Check for Weather Report Command

    if text.strip() == "WeatherReport":

        text_area_insert(f"?嗅�瘞?情?剖𥼚隢𧢲? from {sender}")

        weather_text = _get_weather_report()

        # Proceed to speak this text

        text = weather_text

        # Optional: insert to text area to show what is being spoken

        text_area_insert(f"瘞?情?剖𥼚?批捆嚗㝯text}")



    _sender_ctx.name = sender

    wake_screen()



    if text == "ScheduleReload":

        _load_timetable_from_disk()

        text_area_insert(" 撌脤??啗??亥玨銵?)

        return



    if text == "ScheduleEnable":

        timetable_enabled = True; STATE["timetable"]["enabled"] = True

        if 'timetable_status_var' in globals(): ui_safe(timetable_status_var.set, " 隤脰”嚗𡁜???)

        return



    if text == "ScheduleDisable":

        timetable_enabled = False; STATE["timetable"]["enabled"] = False

        if 'timetable_status_var' in globals(): ui_safe(timetable_status_var.set, " 隤脰”嚗𡁜???)

        return



    if text.startswith("SchedulePlay:"):

        try:

            idx = int(text.split(":",1)[1].strip())

            timetable_play_index(idx)

        except Exception:

            text_area_insert("?𩤃? SchedulePlay ?�彍?航炊")

        return



    if text.startswith("YTFull:"):

        text_area_insert(f"嚗�?蝷綽?隢𧢲㺿?其?頛厰𨺗閮𦠜偘?暹??典?蝡舀偘?曉膥?刻攟撟𤏪?{text}")

        return



    if text.strip() == "YTClose":

        text_area_insert(" 撌脫𦻖??YTClose嚗�陛?𣇉??芰雁?�??冽偘?曉膥?�?页?")

        set_playing_status("?對? 撌脤??匧�?Ｗ? YouTube嚗�?蝷綽?")

        ui_safe(_set_progress, 0); STATE["progress"] = 0

        return



    if text.startswith("SetVolume:"):

        try:

            v = int(text.split(":", 1)[1].strip())

            set_volume(v)

            auto_unmute_if_needed()  # Volume change => Unmute

            text_area_insert(f" ?喲?閮剔� {STATE['volume']}%嚗�???{sender}嚗?)

            save_to_csv(f"SetVolume:{STATE['volume']}", sender, ip=sender_ip)

        except Exception:

            pass

        return

    if text.strip() == "VolUp":

        set_volume(STATE["volume"] + 5); auto_unmute_if_needed(); save_to_csv("VolUp", sender, ip=sender_ip); text_area_insert(f" ?喲?嚗贝秐 {STATE['volume']}%"); return

    if text.strip() == "VolDown":

        set_volume(STATE["volume"] - 5); auto_unmute_if_needed(); save_to_csv("VolDown", sender, ip=sender_ip); text_area_insert(f" ?喲?嚗滩秐 {STATE['volume']}%"); return



    if text.startswith("PlayTaigi:"):

        auto_unmute_if_needed()

        taigi_content = text.split(":", 1)[1].strip()

        text_area_insert(f"儭??啗??剖𥼚嚗㝯taigi_content}")

        save_to_csv(f"PlayTaigi: {taigi_content}", sender, ip=sender_ip)

        threading.Thread(target=play_taigi_tts, args=(taigi_content,), daemon=True).start()

        return



    # [NEW] Handle generic scheduled messages with language prefix

    if text.startswith("lang:tw|") or text.startswith("lang:nan|"):

        auto_unmute_if_needed()

        # Remove prefix

        taigi_content = text.split("|", 1)[1].strip()

        text_area_insert(f"儭??嗅�?啗?撱?偘嚗㝯taigi_content}")

        save_to_csv(f"TaigiBroadcast: {taigi_content}", sender, ip=sender_ip)

        # Call Taigi TTS directly for Server Playback

        threading.Thread(target=play_taigi_tts, args=(taigi_content,), daemon=True).start()

        # Note: Do NOT fall through to generic speech_queue, or it will play standard TTS too.

        return



    if text.startswith("ShowMsg:"):

        auto_unmute_if_needed()

        msg_content = text.split(":", 1)[1].strip()

        

        # [NEW] Check for Taigi prefix inside ShowMsg content

        is_taigi = False

        taigi_payload = msg_content

        if msg_content.startswith("lang:tw|"):

            is_taigi = True

            taigi_payload = msg_content.split("|", 1)[1].strip()

        elif msg_content.startswith("lang:nan|"):

            is_taigi = True

            taigi_payload = msg_content.split("|", 1)[1].strip()

            

        text_area_insert(f"?𣂼�?Ｗ??㕑�?睲???{sender}嚗㝯msg_content}")

        save_to_csv(f"ShowMsg: {msg_content}", sender, ip=sender_ip)

        ui_safe(lambda: show_fullscreen_message(msg_content))

        

        # Broadcast via SSE (Send original with prefix so clients can detect too)

        _set_announce(msg_content, "", sound=1)



        # Server Playback: Route to Taigi engine or Standard engine

        if is_taigi:

             threading.Thread(target=play_taigi_tts, args=(taigi_payload,), daemon=True).start()

        else:

             enqueue_drop_old(speech_queue, msg_content)

        return



    if text.startswith("SilentMsg:"):

        msg_content = text.split(":", 1)[1].strip()

        text_area_insert(f"?𣂼�?Ｗ??∟�?睲???{sender}嚗㝯msg_content}")

        save_to_csv(f"SilentMsg: {msg_content}", sender, ip=sender_ip)

        ui_safe(lambda: show_fullscreen_message(msg_content))

        _set_announce(msg_content, "", sound=0)

        return



    if text == "RelayOn":

        control_usb_relay("ON")

        text_area_insert(f" ?嗅� RelayOn ?�誘嚗�???{sender}嚗?)

        return



    if text == "RelayOff":

        control_usb_relay("OFF")

        text_area_insert(f" ?嗅� RelayOff ?�誘嚗�???{sender}嚗?)

        return



    if text in ("CancelALL", "CancelAll", "ForceClear", "StopAll"):

        stop_playback_event.set(); voice_muted = True; STATE["muted"] = True

        try: pygame.mixer.music.stop()

        except Exception: pass

        try: pygame.mixer.stop() # Stops all channels (EFX, etc)

        except Exception: pass

        with speech_queue.mutex: speech_queue.queue.clear()

        with youtube_queue.mutex: youtube_queue.queue.clear()

        with mp3_queue.mutex: mp3_queue.queue.clear()

        relay_force_off()

        set_playing_status("?對? 撌脣撥?嗅?瘨??𨀣迫")

        ui_safe(_set_progress, 0); STATE["progress"] = 0

        ui_safe(status_label.config, text="?對? 撌脰◤?删垢撘瑕�?𨀣迫", fg="#b31c2a")

        text_area_insert(f"?對? {sender} ?潮��撥?嗅?瘨�𦶢隞歹?嚗�??堒歇皜�征嚗?)

        save_to_csv("CancelALL", sender, ip=sender_ip)

        return



    if text.strip() == "Bell:ClassStart":

        auto_unmute_if_needed(); _interrupt_current_playback(); play_mp3_file("ClassStart.mp3"); text_area_insert(" 銝𡃏玨?湔偘??ClassStart.mp3"); save_to_csv("Bell:ClassStart", sender, ip=sender_ip); return

    if text.strip() == "Bell:ClassEnd":

        auto_unmute_if_needed(); _interrupt_current_playback(); play_mp3_file("ClassEnd.mp3"); text_area_insert(" 銝贝玨?湔偘??ClassEnd.mp3"); save_to_csv("Bell:ClassEnd", sender, ip=sender_ip); return

    if text.strip() == "Bell:EarthquakeAlarm":

        auto_unmute_if_needed(); _interrupt_current_playback(); play_mp3_file("justearthquakeAlarm.mp3"); text_area_insert(" ?圈?霅血𥼚?剜𦆮 justearthquakeAlarm.mp3"); save_to_csv("Bell:EarthquakeAlarm", sender, ip=sender_ip); return



    if text.strip() == "MP3Pause":

        try: pygame.mixer.music.pause()

        except Exception: pass

        set_playing_status("?賂? MP3 ?怠?嚗īygame嚗?)

        return



    if text.strip() == "MP3Resume":

        try: pygame.mixer.music.unpause()

        except Exception: pass

        set_playing_status("?塚? MP3 蝜潛?嚗īygame嚗?)

        return



    if text.strip() == "MP3Stop":

        try: pygame.mixer.music.stop()

        except Exception: pass

        ui_safe(_set_progress, 0); STATE["progress"] = 0

        set_playing_status("?對? MP3 ?𨀣迫嚗īygame嚗?)

        return



    if text.strip() == "MP3Seek":

        text_area_insert("?對? MP3Seek嚗䮝ygame 銝齿𣈲??Seek嚗�歇敹賜裦")

        return



    if "youtube.com/watch" in text or "youtu.be/" in text or "/shorts/" in text:

        auto_unmute_if_needed(); text_area_insert(f" 銝贝?銝行偘??YouTube ?唾?嚗㝯text}")

        stop_playback_event.set(); stop_playback_event.clear()

        enqueue_drop_old(youtube_queue, text.strip()); save_to_csv("PlayYouTube", sender, ip=sender_ip); return



    if text in ("Boy", "??, "?瑁�"):
        def _to_boy():
            if 'gender_label_var' in globals(): gender_label_var.set("?瑁�")
            update_voice()
        ui_safe(_to_boy)
        return

    if text in ("Girl", "憟?, "憟唾�"):
        def _to_girl():
            if 'gender_label_var' in globals(): gender_label_var.set("憟唾�")
            update_voice()
        ui_safe(_to_girl)
        return

    if text in ("Mute", "?𣈯𨺗"):

        voice_muted = True; STATE["muted"] = True; stop_playback_event.set()

        try: pygame.mixer.music.stop()

        except Exception: pass

        ui_safe(status_label.config, text=" 隤鮋𨺗撌脤??喉??剜𦆮銝剜𪃾嚗?, fg="#888")

        set_playing_status(" 隤鮋𨺗撌脤???); ui_safe(_set_progress, 0); STATE["progress"] = 0; save_to_csv("Mute", sender, ip=sender_ip); return

    if text in ("Unmute", "閫?膄?𣈯𨺗", "?𡝗??𣈯𨺗"):

        voice_muted = False; STATE["muted"] = False; stop_playback_event.clear()

        ui_safe(status_label.config, text=" 隤鮋𨺗?毺鍂銝?, fg="#188a3a")

        set_playing_status(" 隤鮋𨺗?毺鍂銝?); save_to_csv("Unmute", sender, ip=sender_ip); return



    if text.startswith("SetRate:"):

        r = text[8:].strip()

        try:

            v = int(r.replace("%", ""))

            ui_safe(rate_scale.set, v); ui_safe(rate_label.config, text=f"隤鮋��?{v}%")

            voice_rate = f"{v}%"; STATE["rate"] = voice_rate

            save_to_csv(f"SetRate:{voice_rate}", sender, ip=sender_ip)

        except Exception:

            pass

        return



    if text.startswith("SetLang:"):

        lang = text[8:].strip()

        if lang in lang_code2label:

            ui_safe(lang_label_var.set, lang_code2label[lang]); update_voice(); save_to_csv(f"SetLang:{lang}", sender, ip=sender_ip)

        elif lang in [lab for lab, _ in LANG_OPTIONS]:

            ui_safe(lang_label_var.set, lang); update_voice(); save_to_csv(f"SetLang:{lang}", sender, ip=sender_ip)

        return

    if text.startswith("SetMeloSpeaker:"):
        global MELO_SPEAKER
        spk = text[15:].strip()
        MELO_SPEAKER = spk
        STATE["melo_speaker"] = spk
        _save_voice_config()
        text_area_insert(f" Melo ?漤𨺗?∟身??{spk}嚗�???{sender}嚗?)
        return

    if text.startswith("SetMeloEnabled:"):
        global USE_MELO_TTS
        val = text[15:].strip().lower()
        USE_MELO_TTS = (val == "true")
        STATE["melo_enabled"] = USE_MELO_TTS
        _save_voice_config()
        status_msg = "撌脣??? if USE_MELO_TTS else "撌脣???
        text_area_insert(f" Melo AI 隤鮋𨺗 {status_msg}嚗�???{sender}嚗?)
        return



    if text.startswith("PlayWithChime:"):

        auto_unmute_if_needed()

        arg = text[14:].strip()

        text_area_insert(f" 靘�䌊 {sender}嚗䥪layWithChime ??{arg}")

        save_to_csv(f"PlayWithChime:{arg}", sender, ip=sender_ip)

        _interrupt_current_playback()



        final_path = ""

        if arg.startswith("uploads/"):

            final_path = os.path.join(UPLOAD_DIR, os.path.basename(arg))

        elif arg.startswith("rec/"):

            # [NEW] Handle recordings

            final_path = os.path.join(RECORD_DIR, os.path.basename(arg))

        else:

            final_path = resource_path(arg) if not os.path.isabs(arg) else arg



        if final_path and os.path.exists(final_path) and _FFMPEG:

            try:

                inputs = []

                sp = os.path.abspath(resource_path(START_SOUND))

                ep = os.path.abspath(resource_path(END_SOUND))

                if os.path.exists(sp): inputs.append(sp)

                inputs.append(os.path.abspath(final_path))

                if os.path.exists(ep): inputs.append(ep)



                if len(inputs) > 1:

                    temp_base = os.path.splitext(final_path)[0]

                    merged_mp3 = temp_base + f"_chime_{secrets.token_hex(2)}.mp3"

                    list_txt = temp_base + f"_list_{secrets.token_hex(2)}.txt"



                    print(f"[Debug] Merge inputs: {inputs}")

                    text_area_insert(f"?? ?閧??單??�蔥 ({len(inputs)} clips)...")



                    with open(list_txt, "w", encoding="utf-8") as lf:

                        for p in inputs:

                            lf.write(f"file '{p.replace(os.sep, '/')}'\n")

                    

                    # Re-encode to ensure compatibility

                    res = subprocess.run([_FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", list_txt, "-b:a", "192k", merged_mp3], 

                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                    

                    try: os.remove(list_txt)

                    except: pass

                    

                    if res.returncode != 0:

                        err = res.stderr.decode('utf-8', errors='ignore')

                        print(f"[Error] FFMPEG Fail: {err}")

                        text_area_insert(f"??FFMPEG憭望?: {err}")

                    

                    if os.path.exists(merged_mp3) and os.path.getsize(merged_mp3) > 100:

                        final_path = merged_mp3

                        text_area_insert("???�蔥?𣂼?嚗屸?憪𧢲偘??)

            except Exception as e:

                print(f"[Error] PlayWithChime merge exception: {e}")

                text_area_insert(f"???�蔥靘见?: {str(e)}")



        if final_path:

            _really_play_mp3_file(final_path)

        return



    if text.startswith("PlayMP3:"):

        auto_unmute_if_needed()

        arg = text[8:].strip()

        text_area_insert(f" 靘�䌊 {sender}嚗䥪layMP3 ??{arg}")

        save_to_csv(f"PlayMP3:{arg}", sender, ip=sender_ip)

        _interrupt_current_playback()

        with mp3_queue.mutex:

            mp3_queue.queue.clear()

        if arg.startswith("http"):

            enqueue_drop_old(mp3_queue, ("URL", arg))

        elif arg.startswith("uploads/"):

            base = os.path.basename(arg); path = os.path.join(UPLOAD_DIR, base); _really_play_mp3_file(path)

        elif arg.startswith("rec/"):

            # [NEW] Handle recordings

            base = os.path.basename(arg); path = os.path.join(RECORD_DIR, base); _really_play_mp3_file(path)

        else:

            path = resource_path(arg) if not os.path.isabs(arg) else arg; _really_play_mp3_file(path)

        return



        return



    if text.startswith("PlayChime:"):

        # PlayChime:Start or PlayChime:End

        mode = text.split(":",1)[1].strip().lower()

        auto_unmute_if_needed()          

        

        target = None

        if mode == "start":

            text_area_insert(f" ?剜𦆮?见??鞟內??-> Relay ON")

            # Request: PlayChime:Start -> Relay ON -> Sound

            try: control_usb_relay("ON")

            except Exception as e: text_area_insert(f"??Relay ON Fail: {e}")

            target = START_SOUND

            

        elif mode == "end":

            text_area_insert(f" ?剜𦆮蝯鞉??鞟內??)

            target = END_SOUND

            

        if target:

            try:

                # If path is relative, resolve it

                path = resource_path(target) if not os.path.isabs(target) else target

                if os.path.exists(path):

                     play_sound(path) # This blocks until playback finishes

                else:

                    text_area_insert(f"?𩤃? ?鞟內?單?銝滚??剁?{target}")

            except Exception as e:

                text_area_insert(f"???鞟內?單偘?曉仃?梹?{e}")

        

        # Request: PlayChime:End -> Sound -> Relay OFF

        if mode == "end":

            text_area_insert(f" 蝯鞉??單偘??-> Relay OFF")

            try: control_usb_relay("OFF")

            except Exception as e: text_area_insert(f"??Relay OFF Fail: {e}")

            

        return



    if text.startswith("PiperForce:"):  # PiperForce:1 / PiperForce:0

        on = text.split(":",1)[1].strip().lower()

        PIPER_FORCE = on in ("1","true","on","yes")

        text_area_insert(f" Piper 撘瑕�?芸?嚗㝯PIPER_FORCE}")

        save_to_csv(f"PiperForce:{PIPER_FORCE}", sender, ip=sender_ip)

        return



    if text.startswith("PiperSet:"):  # 靘页?PiperSet: length=1.05, noise=0.6, noisew=0.8, speaker=0

        try:

            kv = text.split(":",1)[1]

            for part in kv.split(","):

                k,v = part.strip().split("=",1)

                k = k.strip().lower(); v = v.strip()

                if k in ("length","length_scale"): PIPER_CFG["length_scale"] = float(v)

                elif k in ("noise","noise_scale"): PIPER_CFG["noise_scale"] = float(v)

                elif k in ("noisew","noise_w"):    PIPER_CFG["noise_w"] = float(v)

                elif k == "speaker":               PIPER_CFG["speaker"] = v

            _piper_save_cfg(PIPER_CFG)

            text_area_insert(f" Piper ?�彍?湔鰵嚗㝯PIPER_CFG}")

        except Exception as e:

            text_area_insert(f"??PiperSet 閫??憭望?嚗㝯e}")

        return



    # [NEW] Strip Metadata for GUI Display
    display_text = text
    if text.startswith("{{") and "}}" in text:
        try:
            end_idx = text.find("}}")
            display_text = text[end_idx+2:]
        except: pass

    text_area_insert(f"靘�䌊 {sender}嚗㝯display_text}"); save_to_csv(text, sender, ip=sender_ip)

    

    # Generic text speech => Auto Unmute

    auto_unmute_if_needed()

    
    if TRIAL_EXPIRED:
        text_area_insert("?𩤃? 閰衣鍂?笔歇?𠬍??⊥??瑁?隤鮋𨺗?�?", "TTS")
        return

    if not (stop_playback_event.is_set() or voice_muted): enqueue_drop_old(speech_queue, text)



# ===============================

# == [ANCHOR] Flask Web API ==

# ===============================





# Announcement storage (JSON on disk)

_ANN_PATH = os.path.join(DATA_DIR, 'announce.json')

TIMETABLE_FILE = os.path.join(_BASE_FOR_TT, 'timetable.json')

TIMETABLE_PATH = TIMETABLE_FILE  # Alias for compatibility



# Timetable global state

timetable_data = {"enabled": True, "items": []}

timetable_enabled = True



def _validate_timetable(data):

    """撽𡑒?隤脰”鞈�??澆?"""

    if not isinstance(data, dict):

        return False, "payload must be object"

    if "items" in data and not isinstance(data["items"], list):

        return False, "items must be array"

    return True, None



def _load_timetable_from_disk():

    """敺䂿?蝣蠘??亥玨銵?""

    global timetable_data, timetable_enabled

    print(f"[TIMETABLE] Loading timetable from: {TIMETABLE_PATH}")

    try:

        if os.path.exists(TIMETABLE_PATH):

            print(f"[TIMETABLE] File exists, loading...")

            with open(TIMETABLE_PATH, "r", encoding="utf-8") as f:

                timetable_data = json.load(f)

            print(f"[TIMETABLE] Loaded {len(timetable_data.get('items', []))} items")

        else:

            print(f"[TIMETABLE] File does not exist, using defaults")

            timetable_data = {"enabled": True, "items": []}

        timetable_enabled = bool(timetable_data.get("enabled", True))

        STATE["timetable"]["enabled"] = timetable_enabled

        STATE["timetable"]["count"] = len(timetable_data.get("items", []))

        STATE["timetable"]["loaded"] = True

        print(f"[TIMETABLE] Load complete. enabled={timetable_enabled}, items={len(timetable_data.get('items', []))}")

    except Exception as e:

        print(f"[TIMETABLE] Error loading timetable: {e}")

        import traceback

        traceback.print_exc()

        timetable_data = {"enabled": True, "items": []}

        timetable_enabled = True



# Load timetable on startup

_load_timetable_from_disk()





# ===============================

# == [ANCHOR] Web Class Server Integration ==

# ===============================

ADMIN_KEY = os.environ.get("ADMIN_KEY", "teacher")

SITE_TITLE = os.environ.get("SITE_TITLE", "Classroom Broadcast")



# -------- OnlineTracker --------

try:

    from online_tracker import OnlineTracker

except Exception:

    import threading as _thr

    from typing import Dict

    from flask import request as _req

    def _client_ip() -> str:

        xf = (_req.headers.get("X-Forwarded-For") or "").split(",")[0].strip()

        return xf or _req.remote_addr or ""

    class OnlineTracker:

        def __init__(self, groups: int = 6, ttl: int = 15, stale: int = 600):

            self.groups = groups; self.ttl = ttl; self.stale = stale

            self._lock = _thr.Lock()

            self._online: Dict[str, Dict[str, dict]] = {str(i): {} for i in range(1, self.groups+1)}

        def mark_heartbeat(self, gid: int, payload=None):

            ip = _client_ip(); ua = _req.headers.get("User-Agent", "")

            ts = time.time(); gkey = str(int(gid))

            data = {"ip": ip, "ua": ua[:200], "last": ts}

            if payload:

                for k in ("playing","ct","dur","url","ended","muted","vol"):

                    if k in payload: data[k] = payload[k]

            with self._lock:

                slot = self._online.setdefault(gkey, {})

                cur = slot.get(ip)

                if cur: cur.update({k:v for k,v in data.items() if k!="first"})

                else: data["first"] = ts; slot[ip] = data

            return {"ip": ip, "gid": int(gid), "ts": ts}

        def snapshot_by_group(self):

            now_ts = time.time()

            by_group = {str(i): [] for i in range(1, self.groups+1)}

            with self._lock:

                for gkey, slot in self._online.items():

                    to_drop = [ip for ip,e in slot.items() if (now_ts - e.get("last",0)) > self.stale]

                    for ip in to_drop: slot.pop(ip, None)

                for gkey, slot in self._online.items():

                    for _, e in slot.items():

                        item = dict(e); item["alive"] = (now_ts - item.get("last",0)) <= self.ttl

                        by_group[gkey].append(item)

            return by_group, now_ts



tracker = OnlineTracker(groups=6, ttl=15, stale=600)



# -------- ?�??--------

groups_lock = threading.Lock()

groups = {

    i: {

        "version": 0,

        "queue": [],

        "state": {

            "url": "",

            "type": "video",

            "playing": False,

            "speed": 1.0,

            "volume": 1.0,

            "title": ""   # 瘥讐??芾?璅䠷?

        }

    } for i in range(1,7)

}

group_targets = {str(i): [] for i in range(1,7)}

live_sync = {i: None for i in range(1,7)}

TARGETS_FILE = os.path.join(APP_DIR, "targets.json")



# -------- Clients (Native) --------

clients_lock = threading.Lock()

clients = {} # {ip: {mac, hostname, group, last_seen, platform}}



def _wake_on_lan(mac_str):

    # Simple Magic Packet sender

    try:

        if len(mac_str) == 12: pass

        elif len(mac_str) == 17: mac_str = mac_str.replace(mac_str[2], '')

        else: raise ValueError("Invalid MAC")

        data = bytes.fromhex('FF' * 6 + mac_str * 16)

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        sock.sendto(data, ("255.255.255.255", 9))

        sock.close()

        return True

    except Exception as e:

        print(f"WOL Error: {e}")

        return False



def load_targets():

    global group_targets

    try:

        with open(TARGETS_FILE, "r", encoding="utf-8") as f:

            data = json.load(f)

            group_targets = {str(k): list(v) for k, v in data.items()}

    except Exception:

        group_targets = {str(i): [] for i in range(1,7)}

load_targets()



def now(): return time.time()

def bump(g): groups[g]["version"] += 1; return groups[g]["version"]

def snapshot(g): st = dict(groups[g]["state"]); st["version"] = groups[g]["version"]; return st

def all_snapshots(): return {str(g): snapshot(g) for g in groups.keys()}

def client_ip():

    xf = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()

    return xf or request.remote_addr or ""

def push_cmd(g, cmd, only_ips=None):

    v = bump(g)

    entry = {"v": v, "cmd": cmd, "ts": now()}

    if only_ips: entry["ips"] = list(only_ips)

    groups[g]["queue"].append(entry)

    if len(groups[g]["queue"]) > 500:

        groups[g]["queue"] = groups[g]["queue"][-500:]

    return v



# ===============================

# == [ANCHOR] 摮貊?蝡舀綉?嗅???==

# ===============================

def student_udp_listener():

    """?交𤣰摮貊?蝡舫��???HELLO 撠�?"""

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:

        sock.bind(("0.0.0.0", STUDENT_UDP_LISTEN_PORT))

        sock.settimeout(1.0)

        text_area_insert(f"[Student Controller] UDP ??�?笔???0.0.0.0:{STUDENT_UDP_LISTEN_PORT}", "StudentCtrl")

    except Exception as e:

        text_area_insert(f"[Student Controller] UDP ??�憭望?嚗㝯e}", "StudentCtrl")

        return

    

    while not students_stop_event.is_set():

        try:

            data, addr = sock.recvfrom(4096)

        except socket.timeout:

            continue

        except OSError:

            break

        

        try:

            text = data.decode("utf-8", errors="ignore").strip()

            parts = text.split("|")

            

            if len(parts) >= 2 and parts[0] == "HELLO":

                client_id = parts[1] or addr[0]

                group = parts[2] if len(parts) > 2 and parts[2] else "default"

                try:

                    p_val = int(parts[3]) if len(parts) > 3 and parts[3] else STUDENT_UDP_CMD_PORT

                    if p_val == 0:

                        listen_port = addr[1]  # NAT Traversal: use source port

                    else:

                        listen_port = p_val

                except ValueError:

                    listen_port = STUDENT_UDP_CMD_PORT

                mac = parts[4] if len(parts) > 4 else ""

                hostname = parts[5] if len(parts) > 5 else client_id

                

                with students_lock:

                    students_clients[client_id] = {

                        "ip": addr[0],

                        "port": listen_port,

                        "group": group,

                        "mac": mac,

                        "hostname": hostname,

                        "last_seen": datetime.now(),

                    }

                # [DEBUG] Log HELLO

                print(f"[DEBUG] Student HELLO: IP={addr[0]}, Port={listen_port}, ID={client_id}")

        except Exception as e:

            _diag(f"[Student Controller] Parse HELLO error: {e}")

    

    sock.close()



def student_broadcast_discover():

    """摰𡁏?撱?偘 DISCOVER嚗峕??鍦飛?毺垢?𧼮� HELLO"""

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    msg = b"DISCOVER"

    text_area_insert(f"[Student Controller] DISCOVER 撱?偘?笔?嚗�? {STUDENT_DISCOVER_INTERVAL} 蝘𡜐?", "StudentCtrl")

    

    while not students_stop_event.is_set():

        try:

            sock.sendto(msg, (STUDENT_DISCOVER_IP, STUDENT_UDP_CMD_PORT))

        except Exception as e:

            _diag(f"[Student Controller] DISCOVER broadcast error: {e}")

        

        students_stop_event.wait(STUDENT_DISCOVER_INTERVAL)

    

    sock.close()



def send_student_udp_command(ip: str, port: int, cmd: str, args: str = "", client_id: str = None):
    """?潮��綉?嗆?隞斤策摮貊?蝡?(?芸?韏?WebSocket)"""
    msg = f"CMD|{cmd}|{args}"
    
    # 1. Try WebSocket first if client_id is known
    if client_id:
        with AGENT_WS_LOCK:
            ws = AGENT_WS_CLIENTS.get(client_id)
            if ws:
                try:
                    ws.send(msg)
                    print(f"[WS-Agent] Sent CMD to {client_id}: {cmd}")
                    return True
                except Exception as e:
                    print(f"[WS-Agent] WS Send Error ({client_id}): {e}")
                    # WS failed, will fallback to UDP

    # 2. Fallback to UDP
    try:
        print(f"[DEBUG] Sending UDP to {ip}:{port} -> {msg}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(msg.encode("utf-8"), (ip, port))
        sock.close()
        return True
    except Exception as e:
        print(f"[DEBUG] Send UDP Error: {e}")
        _diag(f"[Student Controller] Send command error to {ip}:{port}: {e}")
        return False



def send_magic_packet(mac: str, broadcast_ip: str = "255.255.255.255", port: int = 9):

    """?潮�?WOL (Wake-on-LAN) 擳磰?撠�?"""

    try:

        mac_clean = mac.replace(":", "").replace("-", "").lower()

        if len(mac_clean) != 12:

            raise ValueError(f"Invalid MAC address format: {mac}")

        

        data = b"FF" * 6 + (mac_clean.encode("ascii") * 16)

        magic_packet = bytes.fromhex(data.decode("ascii"))

        

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        sock.sendto(magic_packet, (broadcast_ip, port))

        sock.close()

        return True

    except Exception as e:

        _diag(f"[Student Controller] WOL error for MAC {mac}: {e}")

        return False





# app = Flask(__name__, static_folder=STATIC_ROOT, static_url_path="/static",

#             template_folder=UI_TEMPLATE_DIR)

# (Re-use existing app)

app.template_folder = UI_TEMPLATE_DIR



# ===============================

# == [ANCHOR] 隤滩?蝟餌絞?滨蔭 ==

# ===============================



# Flask Session ?滨蔭

app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

app.config['SESSION_TYPE'] = 'filesystem'

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)  # 2撠𤩺??擧?

app.config['SESSION_COOKIE_HTTPONLY'] = True

app.config['SESSION_COOKIE_SECURE'] = False  # ?砍𧑐?讠䔄閮剔� False嚗𣬚??Ｙ兛憓�㺿??True嚗�? HTTPS嚗?

app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'



# ?冽�?滨蔭?�辣頝臬?

USERS_CONFIG_PATH = os.path.join(APP_DIR, "users_config.json")



def load_users_config():

    """頛匧�?冽�?滨蔭"""

    try:

        if os.path.exists(USERS_CONFIG_PATH):

            with open(USERS_CONFIG_PATH, "r", encoding="utf-8") as f:

                return json.load(f)

        else:

            # ?萄遣暺䁅??滨蔭

            default_config = {

                "users": [],

                "group_passwords": {str(i): "" for i in range(1, 7)},

                "session_timeout_minutes": 120,

                "require_student_login": False

            }

            save_users_config(default_config)

            return default_config

    except Exception as e:

        print(f"[AUTH] Error loading users_config.json: {e}")

        return {

            "users": [],

            "group_passwords": {},

            "session_timeout_minutes": 120,

            "require_student_login": False

        }



def save_users_config(config):

    """靽嘥??冽�?滨蔭"""

    try:

        with open(USERS_CONFIG_PATH, "w", encoding="utf-8") as f:

            json.dump(config, f, ensure_ascii=False, indent=4)

    except Exception as e:

        print(f"[AUTH] Error saving users_config.json: {e}")



def get_user_by_username(username):

    """?寞??冽�?齿䰻?曄鍂??""

    config = load_users_config()

    users = config.get('users', [])

    for user in users:

        if user.get('username') == username and user.get('enabled', True):

            return user

    return None



def verify_password(password, password_hash):

    """撽𡑒?撖�Ⅳ"""

    if not _HAS_BCRYPT:

        # 憒�?瘝埝? bcrypt嚗䔶蝙?函陛?格?撠㵪?銝滚??剁??�鍂?潮??潘?

        return password == password_hash

    try:

        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

    except Exception as e:

        # Fallback: if hash is invalid (e.g. plain text in config), try direct comparison

        if password == password_hash:

            return True

        print(f"[AUTH] Password verification error: {e}")

        return False



def hash_password(password):

    """?�?撖�Ⅳ?�?"""

    if not _HAS_BCRYPT:

        # 憒�?瘝埝? bcrypt嚗諹??墧??�?銝滚??剁??�鍂?潮??潘?

        print("[AUTH] WARNING: Using plaintext password (bcrypt not installed)")

        return password

    try:

        salt = bcrypt.gensalt()

        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    except Exception as e:

        print(f"[AUTH] Password hashing error: {e}")

        return password



def _safe_next_url(target: str | None):

    """蝣箄? next ?�彍摰匧�銝𠉛�?祉?頝臬?"""

    if not target:

        return None

    target = target.strip()

    if not target:

        return None

    if target.startswith("//"):

        return None

    if target.startswith(("http://", "https://")):

        return None

    if not target.startswith("/"):

        return None

    return target



def _login_redirect_response():

    """?�葆 next ?�彍?�蒈?仿??滚?"""

    next_path = request.full_path if request.query_string else request.path

    next_path = (next_path or "").rstrip("?")

    safe_next = _safe_next_url(next_path)

    if safe_next and safe_next != "/login":

        return redirect(f"/login?next={quote(safe_next)}")

    return redirect("/login")



# 隤滩?鋆嗪ˇ??

def _is_api_request():

    """?斗𪃾?嗅?隢𧢲??臬炏撅祆䲰 API嚗屸?閬�???JSON"""

    path = request.path or ""

    return request.is_json or path.startswith("/api/") or path.startswith("/controller/api")



def login_required(f):

    """閬�??駁??�?憌曉膥"""

    @wraps(f)

    def decorated_function(*args, **kwargs):

        if 'user_id' not in session:

            # API 隢𧢲?餈𥪜? JSON

            if _is_api_request():

                return jsonify(ok=False, error="?芰蒈??, need_login=True), 401

            # 蝬脤?隢𧢲??滚??穃�?駁???

            return _login_redirect_response()

        return f(*args, **kwargs)

    return decorated_function



def admin_required(f):

    """閬�?蝞∠??⊥??坔葦甈𢠃??�?憌曉膥"""

    @wraps(f)

    def decorated_function(*args, **kwargs):

        if 'user_id' not in session:

            if _is_api_request():

                return jsonify(ok=False, error="?芰蒈??, need_login=True), 401

            return _login_redirect_response()

        

        role = session.get('role', '')

        if role not in ['admin', 'teacher']:

            if _is_api_request():

                return jsonify(ok=False, error="甈𢠃?銝滩雲"), 403

            return "甈𢠃?銝滩雲", 403

        

        return f(*args, **kwargs)

    return decorated_function



def teacher_or_admin_required(f):

    """閬�??坔葦?𣇉恣?�摱甈𢠃?嚗�ê̌?㵪?"""

    return admin_required(f)



# ===============================

# == [ANCHOR] 隤滩?頝舐眏 ==

# ===============================



@app.route('/login')

def login_page():

    """?駁??�𢒰"""

    next_param = _safe_next_url(request.args.get('next'))

    # 憒�?撌脩蒈?�??滚??穃�擐㚚?

    if 'user_id' in session:

        if next_param:

            return redirect(next_param)

        # ?鞱身銝�敺见葆?墧鰵?�蜓?批蝱

        return redirect('/static/ui/index.html')

    return send_from_directory(UI_TEMPLATE_DIR, 'login.html')



@app.post('/auth/login')

def auth_login():

    """?駁? API"""

    try:

        data = request.get_json(force=True) or {}

        username = data.get('username', '').strip()

        password = data.get('password', '')

        remember = data.get('remember', False)

        next_hint = _safe_next_url(data.get('next'))

        

        if not username or not password:

            return jsonify(ok=False, error="隢贝撓?亙董?笔?撖�Ⅳ"), 400

        

        # ?交𪄳?冽�

        user = get_user_by_username(username)

        

        if not user:

            return jsonify(ok=False, error="撣唾??硋?蝣潮𥲤隤?), 401

        

        # 撽𡑒?撖�Ⅳ

        password_hash = user.get('password_hash', '')

        if not verify_password(password, password_hash):

            return jsonify(ok=False, error="撣唾??硋?蝣潮𥲤隤?), 401

        

        # 閮剔蔭 Session

        session.permanent = remember

        session['user_id'] = user.get('id')

        session['username'] = user.get('username')

        session['role'] = user.get('role', 'user')

        session['display_name'] = user.get('display_name', username)

        

        # 閮㗛??駁?

        try:

            text_area_insert(f"?? ?冽�?駁?嚗㝯user.get('display_name')} ({username}) [{user.get('role')}]", "Auth")

        except:

            pass

        

        # ?寞?閫坿𠧧頝唾?

        redirect_url = next_hint or '/static/ui/index.html'

        

        return jsonify(

            ok=True,

            user={

                'id': user.get('id'),

                'username': user.get('username'),

                'role': user.get('role'),

                'display_name': user.get('display_name')

            },

            redirect=redirect_url

        )

    

    except Exception as e:

        print(f"[AUTH] Login error: {e}")

        return jsonify(ok=False, error=f"?駁?憭望?嚗㝯str(e)}"), 500



@app.post('/auth/logout')

def auth_logout():

    """?餃枂 API"""

    username = session.get('username', 'Unknown')

    display_name = session.get('display_name', username)

    session.clear()

    

    try:

        text_area_insert(f"?? ?冽�?餃枂嚗㝯display_name} ({username})", "Auth")

    except:

        pass

    

    return jsonify(ok=True, message="?餃枂?𣂼?")



@app.get('/auth/status')

def auth_status():

    """?脣??嗅??駁??�??""

    if 'user_id' in session:

        return jsonify(

            ok=True,

            logged_in=True,

            user={

                'id': session.get('user_id'),

                'username': session.get('username'),

                'role': session.get('role'),

                'display_name': session.get('display_name')

            }

        )

    return jsonify(ok=True, logged_in=False)



@app.get('/auth/heartbeat')

@login_required

def auth_heartbeat():

    """Session 敹�歲嚗䔶??�蒈?�???""

    session.modified = True  # ?湔鰵 session ?�?

    return jsonify(ok=True, timestamp=time.time())



@app.post('/auth/change-password')

@login_required

def auth_change_password():

    """靽格㺿撖�Ⅳ"""

    try:

        data = request.get_json(force=True) or {}

        old_password = data.get('old_password', '')

        new_password = data.get('new_password', '')

        

        if not old_password or not new_password:

            return jsonify(ok=False, error="隢𧢲?靘𥡝?撖�Ⅳ?峕鰵撖�Ⅳ"), 400

        

        if len(new_password) < 6:

            return jsonify(ok=False, error="?啣?蝣潸秐撠煾?閬??见?蝚?), 400

        

        # 頛匧�?滨蔭

        config = load_users_config()

        users = config.get('users', [])

        

        # ?交𪄳?嗅??冽�

        user_id = session.get('user_id')

        user = None

        user_index = -1

        for i, u in enumerate(users):

            if u.get('id') == user_id:

                user = u

                user_index = i

                break

        

        if not user:

            return jsonify(ok=False, error="?冽�銝滚???), 404

        

        # 撽𡑒??𠰴?蝣?

        if not verify_password(old_password, user.get('password_hash', '')):

            return jsonify(ok=False, error="?𠰴?蝣潮𥲤隤?), 401

        

        # ?惩??啣?蝣?

        new_hash = hash_password(new_password)

        users[user_index]['password_hash'] = new_hash

        

        # 靽嘥??滨蔭

        config['users'] = users

        save_users_config(config)

        

        try:

            text_area_insert(f"?? ?冽� {user.get('username')} 靽格㺿鈭�?蝣?, "Auth")

        except:

            pass

        

        return jsonify(ok=True, message="撖�Ⅳ靽格㺿?𣂼?")

    

    except Exception as e:

        print(f"[AUTH] Change password error: {e}")

        return jsonify(ok=False, error=f"靽格㺿撖�Ⅳ憭望?嚗㝯str(e)}"), 500



@app.post('/auth/admin/create-user')

@admin_required

def auth_admin_create_user():

    """?萄遣?啁鍂?塚??�恣?�摱嚗?""

    try:

        data = request.get_json(force=True) or {}

        username = data.get('username', '').strip()

        password = data.get('password', '')

        role = data.get('role', 'student')

        display_name = data.get('display_name', username)

        

        if not username or not password:

            return jsonify(ok=False, error="隢𧢲?靘𤤿鍂?嗅??�?蝣?), 400

        

        # 頛匧�?滨蔭

        config = load_users_config()

        users = config.get('users', [])

        

        # 瑼Ｘ䰻?冽�?齿糓?血歇摮睃銁

        if any(u.get('username') == username for u in users):

            return jsonify(ok=False, error="?冽�?滚歇摮睃銁"), 400

        

        # ?萄遣?啁鍂??

        user_id = f"user_{int(time.time())}_{len(users)}"

        password_hash = hash_password(password)

        

        new_user = {

            "id": user_id,

            "username": username,

            "password_hash": password_hash,

            "role": role,

            "display_name": display_name,

            "enabled": True,

            "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),

            "created_by": session.get('username')

        }

        

        users.append(new_user)

        config['users'] = users

        save_users_config(config)

        

        try:

            text_area_insert(f"?𪈠 蝞∠???{session.get('username')} ?萄遣鈭�鰵?冽�嚗㝯username} ({role})", "Auth")

        except:

            pass

        

        # 餈𥪜??�宏?文?蝣澆?撣?

        return_user = {k: v for k, v in new_user.items() if k != 'password_hash'}

        return jsonify(ok=True, user=return_user, message="?冽�?萄遣?𣂼?")

    

    except Exception as e:

        print(f"[AUTH] Create user error: {e}")

        return jsonify(ok=False, error=f"?萄遣?冽�憭望?嚗㝯str(e)}"), 500







@app.get('/uploads/<path:filename>')

def _serve_uploads(filename):

    return send_from_directory(UPLOAD_DIR, filename, as_attachment=False)



# ===============================

# == [ANCHOR] Web Class Server Routes ==

# ===============================



@app.get("/api/ngrok")

def api_ngrok():

    url = STATE.get("ngrok_url")

    return jsonify(ok=True, url=url)



@app.get("/api/title")

def api_title(): return jsonify(title=SITE_TITLE)



@app.route("/auto")

def auto_redirect():

    key = request.args.get("key")

    if key == ADMIN_KEY:

        return redirect("/teacher")

    return redirect("/student")



# ===============================

# == [ANCHOR] Student Controller Routes ==

# ===============================



@app.route("/controller")

@teacher_or_admin_required

def page_controller():

    """?𣂷?摮貊?蝡舀綉?嗅蝱?�𢒰"""

    return render_template("controller.html")



@app.get("/controller/api/clients")

@teacher_or_admin_required

def controller_api_clients():

    """?脣?摮貊?蝡舀???API"""

    now = datetime.now()

    with students_lock:

        view_clients = {}

        for cid, c in students_clients.items():

            last_seen = c.get("last_seen", now - timedelta(days=1))

            online = (now - last_seen).total_seconds() <= STUDENT_HELLO_TIMEOUT

            view_clients[cid] = {

                "hostname": c.get("hostname", ""),

                "ip": c.get("ip", ""),

                "group": c.get("group", ""),

                "mac": c.get("mac", ""),

                "online": online,

                "last_seen_str": last_seen.strftime("%Y-%m-%d %H:%M:%S"),

            }

        online_count = sum(1 for v in view_clients.values() if v["online"])

    

    return jsonify(ok=True, clients=view_clients, online_count=online_count)

    

@app.post("/controller/api/send")

@teacher_or_admin_required

def controller_api_send():

    """?潮��綉?嗆?隞斤策摮貊?蝡?API"""

    try:

        data = request.get_json(force=True) or {}

    except Exception:

        return jsonify(ok=False, error="invalid json"), 400

    

    targets = data.get("targets") or []

    cmd = data.get("cmd", "")

    args = data.get("args", "")

    url_val = data.get("url", "").strip()

    

    if not targets:

        return jsonify(ok=False, error="隢贝秐撠穃㗲?訾??啣飛?罸𤓖??), 400

    

    if cmd == "open_url" and not url_val:

        return jsonify(ok=False, error="隢贝撓?亥??见??�雯?�"), 400

    

    count = 0

    with students_lock:

        for cid in targets:

            c = students_clients.get(cid)

            if not c:

                continue

            

            ip = c["ip"]

            port = c["port"]

            

            try:

                if cmd == "open_url":
                    send_student_udp_command(ip, port, "open_url", url_val, client_id=cid)
                elif cmd == "shutdown":
                    send_student_udp_command(ip, port, "shutdown", "", client_id=cid)
                elif cmd == "reboot":
                    send_student_udp_command(ip, port, "reboot", "", client_id=cid)
                elif cmd == "set_id":
                    send_student_udp_command(ip, port, "set_id", args, client_id=cid)
                elif cmd == "ring":
                    send_student_udp_command(ip, port, "ring", "", client_id=cid)

                elif cmd == "wol":

                    mac = c.get("mac") or ""

                    if mac:

                        send_magic_packet(mac)

                count += 1

            except Exception as e:

                _diag(f"[Student Controller] Failed to send to {cid}@{ip}: {e}")

    

    return jsonify(ok=True, count=count)





@app.post("/api/upload")

@teacher_or_admin_required

def api_upload():

    if 'file' not in request.files: return jsonify(ok=False, error="missing file"), 400

    f = request.files['file']

    if not f.filename: return jsonify(ok=False, error="empty filename"), 400

    display_name = os.path.basename(f.filename or "").strip()

    ext = os.path.splitext(f.filename or "")[1].lower()

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    saved = _generate_upload_filename(ext)

    path = os.path.join(UPLOAD_DIR, saved)

    try: f.save(str(path))

    except Exception as e: return jsonify(ok=False, error=f"save failed: {e}"), 500

    mtype = _classify_upload_mtype(ext)

    st = os.stat(path)

    if not display_name:

        display_name = saved

    meta = {"orig": display_name, "saved": saved, "mtime": st.st_mtime, "size": st.st_size, "mtype": mtype}

    _write_upload_meta(str(path), display_name, saved, mtype, stat_res=st)

    return jsonify(ok=True, meta=meta, url=url_for("_serve_uploads", filename=saved))



@app.get("/api/uploads")

@teacher_or_admin_required

def api_uploads_list():

    items = []; q = (request.args.get("q") or "").lower().strip()

    only = (request.args.get("only") or "").lower().strip()

    try:

        for name in os.listdir(UPLOAD_DIR):

            if name.endswith(".json"): continue

            path = os.path.join(UPLOAD_DIR, name)

            if not os.path.isfile(path): continue

            

            orig = name; mtype = "file"

            meta_path = path + ".json"

            try:

                with open(meta_path, "r", encoding="utf-8") as mf:

                    m = json.load(mf); orig = m.get("orig", orig); mtype = m.get("mtype", mtype)

            except Exception: pass

            

            if q and q not in name.lower() and q not in orig.lower(): continue

            if only in ("av","media") and mtype not in ("audio","video"): continue

            

            st = os.stat(path)

            items.append({

                "saved": name,

                "orig": orig, 

                "url": url_for("_serve_uploads", filename=name),

                "mtype": mtype,

                "size": st.st_size, 

                "mtime": st.st_mtime

            })

        items.sort(key=lambda x: x["mtime"], reverse=True)

        return jsonify(ok=True, items=items, count=len(items))

    except Exception as e:

        return jsonify(ok=False, error=str(e)), 500



@app.get("/api/states")

def api_states():

    return jsonify(ok=True, groups=all_snapshots())



@app.post("/api/heartbeat/<int:gid>")

def api_heartbeat(gid):

    payload = request.get_json(silent=True) or {}

    info = tracker.mark_heartbeat(gid, payload)

    return jsonify(ok=True, **info)



@app.get("/api/online")

@teacher_or_admin_required

def api_online():

    data, ts = tracker.snapshot_by_group()

    return jsonify(ok=True, by_group=data, now=ts)



@app.post("/api/register")

def api_register():

    try:

        data = request.get_json(force=True)

        ip = request.remote_addr

        mac = data.get("mac")

        hostname = data.get("hostname")

        group = data.get("group")

        plat = data.get("platform")

        with clients_lock:

            clients[ip] = {

                "mac": mac, "hostname": hostname, "group": group, 

                "platform": plat, "last_seen": time.time(), "ip": ip

            }

        # Also mark in tracker for online list visibility

        tracker.mark_heartbeat(group or 0) 

        return jsonify(ok=True)

    except Exception as e:

        return jsonify(ok=False, error=str(e)), 400



@app.get("/api/clients")

@teacher_or_admin_required

def api_clients():

    now = time.time()

    res = []

    with clients_lock:

        # Filter out stale clients (> 60s)

        to_del = [k for k,v in clients.items() if now - v["last_seen"] > 60]

        for k in to_del: del clients[k]

        res = list(clients.values())

    return jsonify(ok=True, clients=res)



@app.post("/api/wol")

@teacher_or_admin_required

def api_wol():

    data = request.get_json(force=True)

    mac = data.get("mac")

    if not mac: return jsonify(ok=False, error="no mac"), 400

    ok = _wake_on_lan(mac)

    return jsonify(ok=ok)





@app.get("/api/online.csv")

@teacher_or_admin_required

def api_online_csv():

    data, ts = tracker.snapshot_by_group()

    out = "Group,IP,UserAgent,LastSeen,Alive\n"

    for gid, items in data.items():

        for it in items:

            alive = "Yes" if it["alive"] else "No"

            last = datetime.fromtimestamp(it.get("last",0)).strftime("%Y-%m-%d %H:%M:%S")

            out += f"{gid},{it.get('ip')},{it.get('ua')},{last},{alive}\n"

    return out, 200, {"Content-Type": "text/csv"}



@app.post("/api/cmd")

@teacher_or_admin_required

def api_cmd():

    data = request.get_json(silent=True) or {}

    sel = data.get("groups") or []

    if not sel: return jsonify(ok=False, error="no groups"), 400

    action = data.get("action"); payload = data.get("payload") or {}

    norm_sel = []

    for g in sel:

        try:

            gi = int(g)

            # Allow 0 (Local System) or valid groups 1-6

            if gi == 0 or gi in groups: norm_sel.append(gi)

        except Exception: pass

    if not norm_sel: return jsonify(ok=False, error="no valid groups"), 400



    raw_ips = payload.get("ips") or []

    if isinstance(raw_ips, str):

        only_ips = [p.strip() for p in raw_ips.replace(",", " ").split() if p.strip()]

    elif isinstance(raw_ips, list):

        only_ips = [str(x).strip() for x in raw_ips if str(x).strip()]

    else:

        only_ips = []



    res = {}

    with groups_lock:

        for g in norm_sel:

            # Special handling for Local System (Group 0)

            if g == 0:

                if action == "set_volume":

                    try:

                        v = int(payload.get("volume", STATE["volume"]))

                        set_volume(v)

                        text_area_insert(f" ?喲?閮剔� {v}%嚗�???Web API嚗?)

                        save_to_csv(f"SetVolume:{v}", "WebAPI")

                        res["0"] = {"ok": True, "volume": v}

                    except Exception as e:

                        res["0"] = {"ok": False, "error": str(e)}

                elif action == "CancelALL":

                     # Handle CancelALL for local system if needed, though usually handled via /cmd

                     pass

                continue



            cmd = {"action": action, "payload": {k:v for k,v in payload.items() if k!="ips"}}

            v = push_cmd(g, cmd, only_ips or None)

            st = groups[g]["state"]

            if action in ("set_media", "sync_play"):

                st["url"]  = cmd["payload"].get("url","")

                st["type"] = cmd["payload"].get("type","video")

                st["playing"] = False

                try: st["speed"] = float(cmd["payload"].get("speed", st.get("speed",1.0)))

                except Exception: pass

            elif action == "play":

                st["playing"] = True

            elif action in ("pause", "stop"):

                st["playing"] = False

            elif action == "set_speed":

                try: st["speed"] = float(cmd["payload"].get("speed",1.0))

                except Exception: pass

            elif action == "set_volume":

                try: st["volume"] = float(cmd["payload"].get("volume",1.0))

                except Exception: pass

            elif action == "set_title":

                st["title"] = (cmd["payload"].get("title") or "").strip()



            p = cmd["payload"]

            if action == "sync_play":

                try: spd = float(p.get("speed", st.get("speed", 1.0)))

                except Exception: spd = st.get("speed", 1.0)

                live_sync[g] = {

                    "url": p.get("url") or st.get("url",""),

                    "type": p.get("type") or st.get("type","video"),

                    "seek_to": float(p.get("seek_to") or 0),

                    "speed": spd, "at_ts": int(p.get("at_ts") or time.time()),

                    "tolerance_ms": int(p.get("tolerance_ms") or 400),

                }

            elif action == "play":

                live_sync[g] = {

                    "url": p.get("url") or st.get("url",""),

                    "type": p.get("type") or st.get("type","video"),

                    "seek_to": float(p.get("seek_to") or 0),

                    "speed": float(p.get("speed") or st.get("speed",1.0)),

                    "at_ts": int(time.time()), "tolerance_ms": 400,

                }

            elif action in ("pause", "stop", "set_media"):

                live_sync[g] = None

            elif action == "set_speed" and live_sync[g]:

                try: live_sync[g]["speed"] = float(p.get("speed", st.get("speed",1.0)))

                except Exception: pass

            res[str(g)] = {"version": v, "state": snapshot(g)}

    return jsonify(ok=True, result=res)



@app.get("/poll")

def api_poll():

    try: g = int(request.args.get("g","0"))

    except Exception: return jsonify(ok=False, error="bad group"), 400

    since = int(request.args.get("since","0"))

    if g not in groups: return jsonify(ok=False, error="no such group"), 404



    start = time.time(); timeout = 25.0; interval = 0.25

    while time.time() - start < timeout:

        with groups_lock:

            curv = groups[g]["version"]

            if curv > since:

                ip = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip() or request.remote_addr or ""

                cmds = []

                for e in groups[g]["queue"]:

                    if e["v"] <= since: continue

                    ips = e.get("ips")

                    if ips and ip not in ips: continue

                    cmds.append(e)

                return jsonify(ok=True, version=curv, cmds=cmds, state=snapshot(g),

                               live_sync=live_sync.get(g), now=int(time.time()),

                               title=SITE_TITLE, public_url=STATE.get("ngrok_url"))

        time.sleep(interval)

    with groups_lock:

        return jsonify(ok=True, version=groups[g]["version"], cmds=[], state=snapshot(g),

                       live_sync=live_sync.get(g), now=int(time.time()),

                       title=SITE_TITLE, public_url=STATE.get("ngrok_url"))



@app.get("/teacher")

@teacher_or_admin_required

def page_teacher():

    return render_template("teacher.html", 

                           site_title=SITE_TITLE, 

                           ws_url=f"http://{request.host}")



@app.get("/devices")

@teacher_or_admin_required

def page_devices():

    return render_template("devices.html")





@app.get("/student")

def page_student_default():

    """摮貊?蝡舫?閮剝??ｇ?撠𤾸? home.html"""

    return redirect("/static/ui/home.html")



@app.get("/g/<int:gid>")

def page_student(gid):

    return render_template("student.html", gid=gid, site_title=SITE_TITLE)



@app.get("/qr")

def page_qr():

    url = f"http://{request.host}/auto"

    return render_template("qr.html", url=url, site_title=SITE_TITLE)



@app.get("/api/qr")

def api_qr_img():

    url = request.args.get("text")

    if not url: return "Missing text", 400

    import io

    try:

        import qrcode

        img = qrcode.make(url)

        buf = io.BytesIO()

        img.save(buf, format="PNG")

        buf.seek(0)

        return send_file(buf, mimetype="image/png")

    except:

        return "QR Error", 500

# ====== [ANNOUNCE] ?剔??砍??�?贝? API嚗�䌊?訫?甇亙?蝡?announce.html嚗?======

try:

    announce_state

except NameError:

    announce_state = {

        "message": "",

        "image": "",

        "media": "",

        "media_type": "",

        "sound": 1,   # 1=?𡑒?, 0=銝齿?霈�

        "ts": 0

    }



def _set_announce(message: str, image: str = "", sound: int = 1, media: str = "", media_type: str = ""):

    from time import time as _time_

    try:

        announce_state["message"] = message or ""

        announce_state["image"]   = image or ""

        announce_state["sound"]   = 1 if str(sound) == "1" else 0

        announce_state["media"]   = media or ""

        announce_state["media_type"] = media_type or ""

        announce_state["ts"]      = int(_time_() * 1000)

        try:

            save_to_csv(f"Announce: {announce_state['message']}")

        except Exception:

            pass

    except Exception as e:

        try:

            print("[announce] set error:", e)

        except Exception:

            pass



        except Exception:

            pass



@app.route("/api/weather", methods=["GET", "POST"])

def api_get_weather():

    """?硋?瘞?情?剖𥼚?�?嚗䔶??湔𦻖撱?偘"""

    try:

        text = _get_weather_report()

        return jsonify(ok=True, text=text)

    except Exception as e:

        return jsonify(ok=False, error=str(e))



@app.route("/announce", methods=["GET","POST"])

def api_announce():

    try:

        if request.method == "POST":

            data = request.get_json(silent=True) or {}

            msg  = (data.get("message") if request.is_json else request.form.get("message", "")) or ""

            img  = (data.get("image")   if request.is_json else request.form.get("image", ""))   or ""

            snd  = (data.get("sound")   if request.is_json else request.form.get("sound", "1"))  or "1"

            media = (data.get("media")  if request.is_json else request.form.get("media", ""))   or (data.get("video") if request.is_json else request.form.get("video","")) or ""

            mtype = (data.get("media_type") if request.is_json else request.form.get("media_type","")) or (data.get("type") if request.is_json else request.form.get("type","")) or ""

        else:

            msg  = request.args.get("message","")

            img  = request.args.get("image","")

            snd  = request.args.get("sound","1")

            media = request.args.get("media","") or request.args.get("video","")

            mtype = request.args.get("media_type","") or request.args.get("type","")

        _set_announce((msg or "").strip(), (img or "").strip(), 1 if str(snd)=="1" else 0, (media or "").strip(), (mtype or "").strip())

        return jsonify(ok=True, state=announce_state)

    except Exception as e:

        return jsonify(ok=False, error=str(e)), 500



@app.get("/announce_data")

def api_announce_data():

    return jsonify(announce_state)







def _client_ip_from_request():

    xff = request.headers.get("X-Forwarded-For", "") or request.headers.get("X-Real-IP", "")

    if xff:

        return xff.split(",")[0].strip()

    return request.remote_addr or ""



@app.get("/")
def home():
    # Redirect to demo showcase as requested
    return redirect("/demo")







# ====== [EEW] CWA ?圈?頧㗇𦻖嚗�?靘𤤿策 eew.html 雿輻鍂嚗?======

CWA_API_KEY = "" # Global placeholder, actual load happens below



def _parse_cwa_float(val):

    """?𡑒岫撠?CWA ?喳??�?蝺臬漲嚗𤩺楛摨血?銝脰???float嚗𥕦仃?堒??𧼮� None??""

    try:

        if isinstance(val, str):

            for ch in ["摨?, "?祇?", "km"]:

                val = val.replace(ch, "")

        return float(val)

    except Exception:

        return None



def _diag(msg):

    try:

        print(f"[CWA-DIAG] {msg}")

        # Optionally append to a global log list if needed, or send to frontend via websocket if implemented

        global CWA_LAST_ERROR

        if CWA_LAST_ERROR != msg:

            CWA_LAST_ERROR = msg

    except: pass



def fetch_cwa_events(limit=10):

    """??CWA ?硋??�餈穃𧑐?�?憿航? + 撠誩??�?嚗諹??鞟陛?硋?銵函策 /eew/cwa_feed 雿輻鍂??""

    global CWA_CACHE_EVENTS
    now = time.time()

    

    # Check Cache
    if limit <= 20 and now - CWA_CACHE_EVENTS["time"] < CWA_CACHE_TTL:
        if CWA_CACHE_EVENTS["data"]:
            return CWA_CACHE_EVENTS["data"][:limit]

    # [Added] Lock to prevent concurrent external fetches
    with CWA_FETCH_LOCK:
        # Check again inside lock (Double-Check Locking)
        now = time.time()
        if limit <= 20 and now - CWA_CACHE_EVENTS["time"] < CWA_CACHE_TTL:
            if CWA_CACHE_EVENTS["data"]:
                return CWA_CACHE_EVENTS["data"][:limit]



    if not CWA_API_KEY:

        return []

    base = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"

    datasets = [

        ("E-A0015-001", "CWA-significant"),

        ("E-A0016-001", "CWA-local"),

    ]

    events = []

    

    # We fetch more than requested to populate a decent cache

    fetch_limit = max(limit, 20)

    

    for ds, src in datasets:

        try:

            resp = requests.get(

                f"{base}/{ds}",

                params={"Authorization": CWA_API_KEY, "limit": fetch_limit},

                timeout=10,

                verify=False  # Disable SSL verification to avoid "Missing Subject Key Identifier" error

            )

            resp.raise_for_status()

            data = resp.json()

            eqs = (data.get("records") or {}).get("Earthquake") or []

            for e in eqs:

                info = e.get("EarthquakeInfo") or {}

                origin_time = info.get("OriginTime") or ""

                # [Fix] CWA uses "EarthquakeMagnitude" but previously code used "Magnitude"

                mag_dict = info.get("EarthquakeMagnitude") or info.get("Magnitude") or {}

                mag_val = mag_dict.get("MagnitudeValue") or 0

                epicenter = info.get("Epicenter") or {}

                lat = _parse_cwa_float(epicenter.get("EpicenterLatitude"))

                lon = _parse_cwa_float(epicenter.get("EpicenterLongitude"))

                depth = _parse_cwa_float(info.get("FocalDepth"))

                loc = epicenter.get("Location") or ""

                report_text = e.get("ReportContent") or ""

                # [Added] Image

                img = e.get("ReportImageURI") or e.get("ShakemapImageURI") or ""

                

                eq_no = (info.get("EarthquakeNo") or "").strip()

                eid = f"{ds}_{eq_no or origin_time}"

                

                # [Fix] Format time to ISO 8601 (replace space with T) for better JS compatibility

                iso_time = origin_time.replace(" ", "T") if origin_time else ""



                # [Added] Parse Max Intensity and Shaking Areas

                shaking_areas = e.get("ShakingArea") or []

                max_intensity = "0"

                area_intensities = {} # {CityName: IntensityString}



                for area in shaking_areas:

                    # CWA format: "AreaIntensity": "4蝝? or "5撘?

                    # "CountyName": "?梯𤧣蝮?, "TownName": "..."

                    

                    i_str = area.get("AreaIntensity", "")

                    county = area.get("CountyName", "")

                    

                    # Update Max Intensity

                    if i_str > max_intensity: 

                        max_intensity = i_str

                    

                    # Store in dict

                    if county:

                        current_max = area_intensities.get(county, "0")

                        if i_str > current_max:

                            area_intensities[county] = i_str

                

                events.append({

                    "id": eid,

                    "time": iso_time, # Send ISO format

                    "mag": float(mag_val or 0),

                    "lat": lat,

                    "lon": lon,

                    "depth": depth,

                    "location": loc,

                    "title": report_text or f"{origin_time} {loc} 閬𤩺芋{mag_val}",

                    "src": src,

                    "img": img, # [Added]

                    "intensity": max_intensity, # [Added]

                    "shaking_areas": area_intensities, # [New] { "?啣?撣?: "2蝝?, ... }

                })

        except Exception as ex:
            _diag(f"CWA fetch error for {ds}: {ex}")
            # [Added] If 429, update cache time to prevent immediate retry
            if "429" in str(ex):
                CWA_CACHE_EVENTS["time"] = now + 300 # 5 mins backoff
            continue
    
    # Update Cache Time only if no future backoff is set
    if CWA_CACHE_EVENTS["time"] <= now:
        CWA_CACHE_EVENTS["time"] = now

    # Sort results
    if events:
        events.sort(key=lambda x: x["time"], reverse=True)
        CWA_CACHE_EVENTS["data"] = events
    
    # If fetch failed but we have cache, return it to show "history"
    if not events and CWA_CACHE_EVENTS["data"]:
        return CWA_CACHE_EVENTS["data"][:limit]

    return events[:limit]



def fetch_cwa_warnings(limit=10):

    """??CWA ?硋?憭拇除霅衣鸌?梧?W-C0033-001嚗㚁??𧼮�?𡑒”??""

    global CWA_CACHE_WARNINGS
    now = time.time()

    

    # Check Cache
    if limit <= 50 and now - CWA_CACHE_WARNINGS["time"] < CWA_CACHE_TTL:
        if CWA_CACHE_WARNINGS["data"]:
            return CWA_CACHE_WARNINGS["data"][:limit]

    with CWA_FETCH_LOCK:
        # Double check inside lock
        now = time.time()
        if limit <= 50 and now - CWA_CACHE_WARNINGS["time"] < CWA_CACHE_TTL:
            if CWA_CACHE_WARNINGS["data"]:
                return CWA_CACHE_WARNINGS["data"][:limit]



    if not CWA_API_KEY:

        return []

    url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/W-C0033-001"

    

    fetch_limit = max(limit, 50)

    

    try:

        resp = requests.get(

            url,

            params={"Authorization": CWA_API_KEY, "limit": fetch_limit, "format": "JSON"},

            timeout=10,

            verify=False

        )

        resp.raise_for_status()

        data = resp.json()

        records = (data.get("records") or {}).get("record") or []

        

        res = [] # Changed from 'results' to 'res' to match the provided snippet

        for r in records:

            # Parse fields

            loc_name = (r.get("location") or [])

            if isinstance(loc_name, list):

                # Sometimes it's a list of locations, sometimes structure varies

                # API doc says location is a list of objects usually

                # But W-C0033-001 structure: records -> record (list) -> location (list) -> locationName

                pass

            

            # Actually W-C0033-001 structure:

            # records: { record: [ { datasetInfo:..., location: [ {locationName:..., hazardConditions: {hazards:[...]}} ] } ] }

            # Wait, let's check standard CWA JSON structure for this dataset.

            # Usually: records -> record -> location -> locationName

            # And hazard info.

            

            # Let's try to parse generic structure

            locations = r.get("location") or []

            for loc in locations:

                loc_name = loc.get("locationName")

                hazards = (loc.get("hazardConditions") or {}).get("hazards") or []

                for h in hazards:

                    info = h.get("info") or {}

                    phenomena = info.get("phenomena")

                    significance = info.get("significance")

                    affected = info.get("affectedAreas") # sometimes present

                    

                    # We care about "?訾?撘琿◢" (Strong Wind) or "憸梢◢" (Typhoon)

                    if phenomena in ["?訾?撘琿◢", "憸梢◢"]:

                        res.append({ # Changed from 'results' to 'res'

                            "location": loc_name,

                            "phenomena": phenomena,

                            "significance": significance,

                            "startTime": h.get("validTime", {}).get("startTime"),

                            "endTime": h.get("validTime", {}).get("endTime"),

                            "title": f"{loc_name} {phenomena} {significance}"

                        })

        # Update Cache Time only if no future backoff is set
        if CWA_CACHE_WARNINGS["time"] <= now:
            CWA_CACHE_WARNINGS["time"] = now

        # Sort by StartTime desc
        if res:
            res.sort(key=lambda x: x.get("startTime", ""), reverse=True)
            CWA_CACHE_WARNINGS["data"] = res
        
        # Fallback to cache if empty (but we just fetched 50 items so empty is usually real)
        if not res and CWA_CACHE_WARNINGS["data"]:
             return CWA_CACHE_WARNINGS["data"][:limit]

        return res[:limit]
    except Exception as ex:
        _diag(f"CWA Warning fetch error: {ex}")
        # [Added] Backoff on error/429
        if "429" in str(ex):
            CWA_CACHE_WARNINGS["time"] = now + 300 # 5 mins
        elif CWA_CACHE_WARNINGS["time"] <= now:
            CWA_CACHE_WARNINGS["time"] = now
        
        # Return cache if available
        if CWA_CACHE_WARNINGS["data"]:
            return CWA_CACHE_WARNINGS["data"][:limit]
        return []




@app.route("/eew/cwa_feed", methods=["GET"])

def eew_cwa_feed():

    """?𣂷??滨垢 eew.html ?亥岷 CWA ?�餈穃𧑐?�鍂嚗𢥧SGS 隞滨眏?滨垢?湔𦻖?瓐�?""

    if not CWA_API_KEY:

        return jsonify(ok=False, error="NO_CWA_API_KEY"), 200

    try:

        events = fetch_cwa_events(limit=10)

        return jsonify(ok=True, events=events)

    except Exception as ex:

        # CWA_LAST_ERROR = str(ex) # moved to _diag

        _diag(f"Feed error: {ex}")

        return jsonify(ok=False, error="CWA_FETCH_FAILED", detail=str(ex)), 500



@app.route("/eew/weather_feed", methods=["GET"])

def eew_weather_feed():

    """?𣂷??滨垢?亥岷 CWA 憭拇除霅衣鸌?晞�?""

    if not CWA_API_KEY:

        return jsonify(ok=False, error="NO_CWA_API_KEY"), 200

    try:

        warnings = fetch_cwa_warnings(limit=20)

        return jsonify(ok=True, warnings=warnings)

    except Exception as ex:

        _diag(f"Weather Feed error: {ex}")

        return jsonify(ok=False, error="FETCH_FAILED", detail=str(ex)), 500



# ====== CWA ?啁??�?讠恣?�?頛芾岷?讛摩 ======

CWA_CONF_FILE = os.path.join(APP_DIR, "cwa_config.json")

CWA_LOCK = threading.Lock()

CWA_API_KEY = "CWB-2DA9AED0-4A0D-452C-B615-EE96324133AB" # Pef user request, ensure this default is set

CWA_ENABLED = True # Default True

CWA_BROADCAST_ENABLED = True

CWA_POLL_SEC = 60

CWA_LAST_DATA = None

CWA_LAST_ERROR = ""

# [New] Intensity Settings

CWA_LOCAL_CITY = "" # Auto-detect if empty
CWA_INTENSITY_THRESHOLD = "3" # Default threshold

# [New] CWA Fetching Lock
CWA_FETCH_LOCK = threading.Lock()

# [New] CWA Caching to prevent 429
CWA_CACHE_EVENTS = {"data": [], "time": 0}
CWA_CACHE_WARNINGS = {"data": [], "time": 0}
CWA_CACHE_TTL = 60 # 60 seconds

# [New] CWA TCP Credentials
CWA_TCP_ACCOUNT = ""
CWA_TCP_PASSWORD = ""
CWA_TCP_STATUS = "Disconnected"
CWA_LICENSE_SITE = "" # e.g. "?箏?撣�??堒??笔?擃䀝葉"

# [New] Trial/License Settings
TRIAL_DAYS = 30
TRIAL_EXPIRED = False
FIRST_RUN_TIME = None
TRIAL_REMAINING = 0

def _load_trial_info():
    global FIRST_RUN_TIME, TRIAL_EXPIRED, TRIAL_REMAINING
    p = os.path.join(DATA_DIR, "license.json")
    now = datetime.now()
    try:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                fr_str = data.get("first_run_time")
                if fr_str:
                    FIRST_RUN_TIME = datetime.fromisoformat(fr_str)
        
        if not FIRST_RUN_TIME:
            FIRST_RUN_TIME = now
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"first_run_time": FIRST_RUN_TIME.isoformat()}, f)
        
        # Calculate
        diff = now - FIRST_RUN_TIME
        TRIAL_REMAINING = max(0, TRIAL_DAYS - diff.days)
        if diff.days >= TRIAL_DAYS:
            TRIAL_EXPIRED = False # [MOD] 撱園𩑈閰衣鍂??(銝漤?摰𡁜???
            print(f"[LICENSE] Trial Period Extended. (Started: {FIRST_RUN_TIME})")
        else:
            TRIAL_EXPIRED = False
            print(f"[LICENSE] Trial Days Left: {TRIAL_REMAINING}")
            
    except Exception as e:
        print(f"[LICENSE] Load error: {e}")

# Call it early
_load_trial_info()




def _try_load_cwa_license():
    """
    Attempt to load CWA License (License.xml / LicenseData.xml) to auto-detect
    Local City/County (e.g. '?箏?撣?) if not set in config.
    """
    global CWA_LOCAL_CITY
    
    # Files to check
    candidates = [
        os.path.join(APP_DIR, "License.xml"),
        os.path.join(DATA_DIR, "License.xml"),
        os.path.join(APP_DIR, "LicenseData.xml"),
        os.path.join(DATA_DIR, "LicenseData.xml")
    ]
    
    found_city = None
    
    for p in candidates:
        if not os.path.exists(p):
            continue
            
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                
            # Extract Base64 between <LicenseTerms>...</LicenseTerms>
            # Simple string search to avoid heavy XML parsing if structure is simple
            start_tag = "<LicenseTerms>"
            end_tag = "</LicenseTerms>"
            
            idx1 = content.find(start_tag)
            idx2 = content.find(end_tag)
            
            if idx1 != -1 and idx2 != -1:
                b64_str = content[idx1 + len(start_tag) : idx2].strip()
                if b64_str:
                    import base64
                    raw_bytes = base64.b64decode(b64_str)
                    
                    # Convert to string (ignore errors as it's binary serialization)
                    # Use utf-16-le or utf-8 depending on .NET serialization, 
                    # but usually mixed. We'll try to find known city names.
                    # .NET strings in binary serialization are often UTF-8 or length-prefixed.
                    # We just scan the raw bytes for UTF-8 patterns of Taiwan cities.
                    
                    # List of Taiwan Cities/Counties
                    taiwan_places = [
                        "?粹?撣?, "?箏?撣?, "?啣?撣?, "?啣?撣?, "獢�?撣?, "?啁姘撣?, "?啁姘蝮?,
                        "?埈?蝮?, "?箔葉撣?, "?唬葉撣?, "敶啣?蝮?, "?埈?蝮?, "?脫?蝮?, "?厩儔撣?,
                        "?厩儔蝮?, "?箏?撣?, "?啣?撣?, "擃㗛?撣?, "撅𤩺𨭬蝮?, "摰𡏭嵰蝮?, "?梯𤧣蝮?,
                        "?箸𨭬蝮?, "?唳𨭬蝮?, "瞉擧?蝮?, "?煾?蝮?, "???蝮?
                    ]
                    
                    # Try decoding as utf-8 (common)
                    decoded_str = raw_bytes.decode("utf-8", errors="ignore")
                    
                    for place in taiwan_places:
                        if place in decoded_str:
                            found_city = place
                            # Standardize ??vs ??
                            found_city = found_city.replace("??, "??)
                            break
                            
                    
                    # [New] Also try to extract Account and Password for TCP
                    # CWA Account usually starts with SS or similar
                    import re
                    # Find all matches for SS followed by digits
                    acc_matches = re.finditer(r"SS\d+", decoded_str)
                    for am in acc_matches:
                        found_acc = am.group(0)
                        # Look for a 7-digit password in the window following the account
                        # Typically the password follows very shortly in the binary blob
                        window = decoded_str[am.end() : am.end() + 100]
                        pwd_match = re.search(r"(\d{7})", window)
                        if pwd_match:
                             found_pwd = pwd_match.group(0)
                             global CWA_TCP_ACCOUNT, CWA_TCP_PASSWORD
                             CWA_TCP_ACCOUNT = found_acc
                             print(f"[LICENSE] Found TCP Account: {found_acc}, Pwd: {found_pwd}")
                             
                             # Search for Site Name (SName)
                             # It often contains "擃䀝葉", "?衤葉", "撠誩飛" or specific city/town prefix
                             # We'll look for a reasonably long Chinese string after the password window
                             site_window = decoded_str[pwd_match.end() : pwd_match.end() + 150]
                             # Match Chinese characters, usually including city/town
                             site_match = re.search(r"[\u4e00-\u9fa5]{4,20}", site_window)
                             if site_match:
                                 global CWA_LICENSE_SITE
                                 CWA_LICENSE_SITE = site_match.group(0).replace("??, "??)
                                 print(f"[LICENSE] Found Site Name: {CWA_LICENSE_SITE}")
                             break # Found a valid pair

                    if found_city:
                        print(f"[LICENSE] Found city in license: {found_city}")
                        break
        except Exception as e:
            print(f"[LICENSE] Parse error {p}: {e}")
            
    if found_city:
        # Only override if CWA_LOCAL_CITY is empty
        if not CWA_LOCAL_CITY:
             CWA_LOCAL_CITY = found_city
             print(f"[LICENSE] Auto-configured CWA_LOCAL_CITY = {CWA_LOCAL_CITY}")

def _load_cwa_conf():

    global CWA_API_KEY, CWA_ENABLED, CWA_POLL_SEC, CWA_BROADCAST_ENABLED, CWA_LOCAL_CITY, CWA_INTENSITY_THRESHOLD

    try:

        if os.path.exists(CWA_CONF_FILE):

            with open(CWA_CONF_FILE, "r", encoding="utf-8") as f:

                d = json.load(f)

                k = d.get("key", "").strip()

                if k and len(k) > 30:

                    CWA_API_KEY = k

                if "enabled" in d:

                    CWA_ENABLED = bool(d["enabled"])

                else:

                    CWA_ENABLED = True

                

                CWA_BROADCAST_ENABLED = bool(d.get("broadcast_enabled", True))

                CWA_POLL_SEC = max(15, int(d.get("poll_sec", 60)))

                CWA_LOCAL_CITY = d.get("local_city", "")

                CWA_INTENSITY_THRESHOLD = d.get("intensity_threshold", "3")
                
                global CWA_TCP_ACCOUNT, CWA_TCP_PASSWORD
                CWA_TCP_ACCOUNT = d.get("tcp_account", CWA_TCP_ACCOUNT)
                CWA_TCP_PASSWORD = d.get("tcp_password", CWA_TCP_PASSWORD)

        # After loading config, try loading license override if city or credentials missing
        if not CWA_LOCAL_CITY or not CWA_TCP_ACCOUNT:
            _try_load_cwa_license()


    except: pass



def _save_cwa_conf():

    with CWA_LOCK:

        try:

            with open(CWA_CONF_FILE, "w", encoding="utf-8") as f:

                json.dump({

                    "key": CWA_API_KEY, 

                    "enabled": CWA_ENABLED, 

                    "poll_sec": CWA_POLL_SEC, 

                    "broadcast_enabled": CWA_BROADCAST_ENABLED,

                    "local_city": CWA_LOCAL_CITY,

                    "intensity_threshold": CWA_INTENSITY_THRESHOLD,

                    "tcp_account": CWA_TCP_ACCOUNT,

                    "tcp_password": CWA_TCP_PASSWORD

                }, f)

        except: pass



_load_cwa_conf()



@app.route("/quake/state", methods=["GET", "POST"])

def api_quake_state():

    global CWA_ENABLED, CWA_POLL_SEC, CWA_BROADCAST_ENABLED, CWA_LOCAL_CITY, CWA_INTENSITY_THRESHOLD

    if request.method == "POST":

        d = request.get_json(silent=True) or {}

        if "enabled" in d: CWA_ENABLED = bool(d["enabled"])

        if "broadcast_enabled" in d: CWA_BROADCAST_ENABLED = bool(d["broadcast_enabled"])

        if "poll_sec" in d: CWA_POLL_SEC = max(15, int(d["poll_sec"]))

        if "local_city" in d: CWA_LOCAL_CITY = str(d["local_city"]).strip()

        if "intensity_threshold" in d: CWA_INTENSITY_THRESHOLD = str(d["intensity_threshold"]).strip()

        

        _save_cwa_conf()

        # ?亙??剁?閫貊䔄銝�甈∠??唾憚閰?(async)

        if CWA_ENABLED:

            threading.Thread(target=_cwa_poll_once, daemon=True).start()

    

    return jsonify(
        ok=True, 
        enabled=CWA_ENABLED, 
        broadcast_enabled=CWA_BROADCAST_ENABLED, 
        poll_sec=CWA_POLL_SEC, 
        local_city=CWA_LOCAL_CITY,
        intensity_threshold=CWA_INTENSITY_THRESHOLD,
        has_key=bool(CWA_API_KEY), 
        tcp_account=CWA_TCP_ACCOUNT,
        tcp_status=CWA_TCP_STATUS,
        license_site=CWA_LICENSE_SITE,
        last=CWA_LAST_DATA, 
        last_error=CWA_LAST_ERROR
    )



@app.route("/quake/key", methods=["GET", "POST"])

def api_quake_key():

    global CWA_API_KEY, CWA_LAST_ERROR

    if request.method == "POST":

        d = request.get_json(silent=True) or {}

        k = (d.get("key") or "").strip()

        if k:

            CWA_API_KEY = k

            CWA_LAST_ERROR = "" # Reset error on new key

            _save_cwa_conf()

        return jsonify(ok=True)

    

    masked = (CWA_API_KEY[:4] + "***" + CWA_API_KEY[-4:]) if len(CWA_API_KEY) > 8 else (CWA_API_KEY if CWA_API_KEY else "")

    return jsonify(ok=True, value_masked=masked)



@app.route("/quake/test", methods=["POST"])

def api_quake_test():

    """蝡见朖皜祈岫 CWA ???銝血??喟???(銝滚誨??"""

    try:

        events = fetch_cwa_events(limit=1)

        if events:

            return jsonify(ok=True, sample=events[0])

        return jsonify(ok=False, error="No events found or key invalid")

    except Exception as e:

        return jsonify(ok=False, error=str(e))



@app.route("/quake/diag", methods=["POST"])

def api_quake_diag():

    """閮箸𪃾??𦻖"""

    tried = []

    ok = False

    try:

        # Simple fetch

        import requests

        url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/E-A0015-001?Authorization=" + CWA_API_KEY + "&limit=1"

        r = requests.get(url, timeout=5, verify=False)

        tried.append({"url": url, "status": r.status_code, "body_snippet": r.text[:100], "auth_mode": "param"})

        if r.status_code == 200:

            ok = True

    except Exception as e:

        tried.append({"url": "FetchError", "error": str(e)})

    

    return jsonify(ok=ok, tried=tried)



@app.get("/api/location")

def api_location():

    """Return server's detected location."""

    try:

        loc = _get_server_location()

        return jsonify(ok=True, **loc)

    except Exception as e:

        return jsonify(ok=False, error=str(e))



def _cwa_poll_once(silent=False):

    """?格活頛芾岷?讛摩嚗諹𥅾?㗇鰵銝娪＊?堒𧑐?�?撱?偘"""

    global CWA_LAST_DATA, CWA_LAST_ERROR

    

    if not CWA_API_KEY:

        CWA_LAST_ERROR = "?芾身摰?CWA API Key"

        return



    try:

        CWA_LAST_ERROR = "瑼Ｘ䰻銝?.."

        events = fetch_cwa_events(limit=1)

        if not events:

             CWA_LAST_ERROR = "?亦�鞈�? (??Key ?⊥?)"

             return

             

        ev = events[0]

        CWA_LAST_ERROR = "" # Clear error if successful

        

        # Check logic: is it new? 

        last_id = CWA_LAST_DATA.get("id") if CWA_LAST_DATA else None

        if ev["id"] != last_id:

            # New event!

            CWA_LAST_DATA = ev

            

            # [Added] Check if event is outdated (> 30 mins)

            try:

                t_str = ev['time'].replace('T', ' ')

                ev_dt = datetime.strptime(t_str, "%Y-%m-%d %H:%M:%S")

                now = datetime.now()

                diff = (now - ev_dt).total_seconds()

                

                if diff > 1800: # 30 minutes

                    print(f"[CWA] Event outdated ({int(diff)}s ago), broadcast skipped.")

                    if not silent:

                        _diag(f"Outdated event skipped: {ev['time']}")

                    return

            except Exception as e:

                print(f"[CWA] Time parse warning: {e}")



            # [New] Determine Local Intensity

            # 1. Get Target City

            target_city = CWA_LOCAL_CITY

            if not target_city:

                # Auto-detect

                loc = _get_server_location()

                target_city = loc.get("city") or loc.get("region") or ""

            

            # 2. Lookup Intensity

            local_intensity = "0"

            if target_city and ev.get("shaking_areas"):

                # Try exact match first

                local_intensity = ev["shaking_areas"].get(target_city, "0")

                

                if local_intensity == "0":

                    # Try "?? vs "?? replacement

                    alt_city = target_city.replace("??, "??)

                    local_intensity = ev["shaking_areas"].get(alt_city, "0")

                

                if local_intensity == "0":

                    # Try "?? vs "?? reverse

                    alt_city = target_city.replace("??, "??)

                    local_intensity = ev["shaking_areas"].get(alt_city, "0")

            

            # 3. Construct Msg

            intensity_str = f"?�憭折?摨?{ev.get('intensity', '0')}"

            if target_city and local_intensity != "0":

                intensity_str += f"嚗庙target_city} {local_intensity}"

            

            msg = f"?𣂼𧑐?��笔𥼚?鶃ev['time']} {ev['location']} 閬𤩺芋 {ev['mag']} 瘛勗漲 {ev['depth']}km {intensity_str}"

            print(f"[CWA] New Event: {msg} (Local Int: {local_intensity} @ {target_city})")

            

            if not silent:

                # Broadcast only if Broadcast Enabled

                if CWA_BROADCAST_ENABLED:
                    # [Moved] threading.Thread(target=handle_msg, args=(f"ShowMsg:{msg}", ("System", "CWA")), daemon=True).start()
                    pass

                    

                    # [New] Alarm Trigger Logic based on Intensity

                    

                    def _int_val(s):

                        s = s.replace("蝝?, "").strip()

                        if s in ("5撘?, "5-"): return 5.0

                        if s in ("5撘?, "5+"): return 5.5

                        if s in ("6撘?, "6-"): return 6.0

                        if s in ("6撘?, "6+"): return 6.5

                        try: return float(s)

                        except: return 0.0

                    

                    val_local = _int_val(local_intensity)

                    val_thresh = _int_val(CWA_INTENSITY_THRESHOLD)

                    

                    should_alarm = False

                    if val_local >= val_thresh and val_local > 0:

                        should_alarm = True

                    

                    if should_alarm:
                        if CWA_BROADCAST_ENABLED:
                            # TTS & Text
                            threading.Thread(target=handle_msg, args=(f"ShowMsg:{msg}", ("System", "CWA")), daemon=True).start()
                            # Alarm Sound
                            threading.Thread(target=handle_msg, args=("PlayMP3:justEarthquakeAlarm.mp3", ("System", "CWA")), daemon=True).start()

                    else:

                        print(f"[CWA] Alarm skipped. Local Int {val_local} < Threshold {val_thresh}")



                # [Added] Check Weather Warnings

                # Only check if we have a local city

                if target_city:

                    warnings = fetch_cwa_warnings(limit=50) # Fetch more to cover all cities

                    # Filter for target city and specific types

                    relevant = [w for w in warnings if w["location"] == target_city and w["phenomena"] in ["?訾?撘琿◢", "憸梢◢"]]

                    

                    # Simple logic: If there is an active warning, and we haven't broadcasted it recently?

                    # Since we don't have a robust "seen" list for warnings (they persist for hours),

                    # maybe we just rely on frontend to display?

                    # User asked for "Broadcast" like earthquake.

                    # But earthquake is a one-time event. Warning is a state.

                    # Let's just broadcast if it's "New" (not seen in last poll).

                    # For simplicity, let's skip auto-broadcast for now and focus on Display, 

                    # unless we track "last_warning_hash".

                    # Let's implement a basic "New Warning" check.

                    

                    # (Simplified for now: Just display in frontend, user can "Push Latest")

                    pass



                else:

                    print(f"[CWA] Broadcast skipped (CWA_BROADCAST_ENABLED=False)")

                

    except Exception as e:

        CWA_LAST_ERROR = f"CWA Error: {e}"

        print(f"[CWA] Poll Error: {e}")



def _cwa_bg_loop():
    # Start TCP Client if credentials exist
    if CWA_TCP_ACCOUNT and CWA_TCP_PASSWORD:
        global _cwa_tcp_client
        _cwa_tcp_client = CWATCPClient(account=CWA_TCP_ACCOUNT, password=CWA_TCP_PASSWORD)
        _cwa_tcp_client.start(callback=_handle_cwa_tcp_data)
    
    while True:
        try:
            if CWA_ENABLED:
                _cwa_poll_once()
            time.sleep(CWA_POLL_SEC)
        except Exception:
            time.sleep(10)

class CWATCPClient:
    def __init__(self, host="scseewser.cwa.gov.tw", port=14002, account="", password=""):
        self.host = host; self.port = port
        self.account = account; self.password = password
        self.running = False; self.sock = None; self.callback = None

    def start(self, callback=None):
        self.callback = callback; self.running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        global CWA_TCP_STATUS
        retry_delay = 15
        while self.running:
            try:
                CWA_TCP_STATUS = "Connecting..."
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(30)
                self.sock.connect((self.host, self.port))
                login_msg = f"user:{self.account} pwd:{self.password}\r\n"
                self.sock.send(login_msg.encode('utf-8'))
                CWA_TCP_STATUS = "Connected"
                retry_delay = 15 # Reset delay on success
                
                while self.running:
                    try:
                        data = self.sock.recv(8192)
                        if not data: break
                        text = data.decode('utf-8', errors='ignore')
                        if "<Earthquake" in text and self.callback:
                            self.callback(text)
                    except socket.timeout: continue
                    except Exception: break
            except Exception as e:
                msg = str(e)
                CWA_TCP_STATUS = f"Error: {msg}"
                
                # Suppress Timeout logs to avoid spamming
                if "10060" in msg or "timed out" in msg:
                     if retry_delay < 300: # Log only if we are not in deep sleep mode or just log summary
                         _diag(f"TCP Connection timed out. Retrying in {retry_delay}s...")
                else:
                     _diag(f"TCP Connection Failed: {e}. Retrying in {retry_delay}s...")
                
                time.sleep(retry_delay)
                # Exponential backoff up to 5 mins
                retry_delay = min(retry_delay * 2, 300)
                
            finally:
                if self.sock:
                    try: self.sock.shutdown(socket.SHUT_RDWR); self.sock.close()
                    except: pass
                self.sock = None
        CWA_TCP_STATUS = "Stopped"

def _handle_cwa_tcp_data(xml_str):
    """
    Handle real-time XML from scseewser.
    Parse roughly to satisfy _cwa_poll_once logic or call it with mock data.
    For simplicity, we trigger a poll_once(silent=False) immediately to get the latest details 
    via API but triggered instantly by TCP.
    """
    print(f"[TCP] Earthquake Signal Received! Triggering immediate poll.")
    # We could parse XML here for even faster response, but _cwa_poll_once 
    # already has all the intensity and broadcast logic.
    # To avoid double broadcast, we might need a small cooldown.
    threading.Thread(target=_cwa_poll_once, args=(False,), daemon=True).start()

_cwa_tcp_client = None



# Start BG Thread

threading.Thread(target=_cwa_bg_loop, daemon=True).start()







@app.get("/sched")

def go_sched(): return redirect("/static/ui/sched.html", 302)



@app.get("/eew")

def go_eew():   return redirect("/static/ui/eew.html", 302)



@app.get("/taigi_edu")

def go_taigi_edu(): return redirect("/static/ui/taigi_edu.html", 302)



@app.get("/tt")

def go_tt():    return redirect("/static/ui/tt.html", 302)



@app.get("/whoami")
def whoami():
    p = STATIC_ROOT
    return jsonify(static_folder=p, exists=os.path.exists(p), upload_dir=UPLOAD_DIR)

@app.get("/buddha")
def go_buddha(): return redirect("/static/ui/buddha.html", 302)





# ====== [4-Relay Web API] 雿輻鍂?函? COM嚗㇌ELAY4_PORT嚗㗇綉??======





@app.get("/relay4/status")

def relay4_status():

    """?𧼮� 4-Relay ?桀??�?讠策 relay4.html 雿輻鍂嚗䔶蒂?𣂷??舫� COM 皜�鱓??""

    # ?滨垢?舫�誯? /relay4/status?port=COMx ?�??祆活?芸?雿輻鍂??4-Relay COM

    override_port = (request.args.get("port") or "").strip() or None



    # 瘥𤩺活?澆㙈?賡??唳???4-Relay ?䠷� COM嚗峕?靘𤤿策?滨垢銝𧢲??詨鱓雿輻鍂

    try:

        usb_relay_ports = list_4relay_candidate_ports()

    except Exception as e:

        _diag(f"[4R] list_4relay_candidate_ports error: {e}")

        usb_relay_ports = []

        _relay4_set("last_error", f"list_4relay_candidate_ports error: {e}")



    # ??Relay ?桀?雿輻鍂??COM嚗�策?滨垢憿舐內?�鱓 Relay 撌脩鍂?滨鍂嚗?

    single_port = (RELAY_INFO.get("port") if "RELAY_INFO" in globals() else None) or RELAY_PORT



    # 瘙箏??嗘?甈∪??梁策?滨垢??4-Relay 銝餉? COM

    if override_port:

        # ?�迂?滨垢?急??�??𣂷?憿?COM ??4-Relay 雿輻鍂?格?

        with RELAY4_LOCK:

            _relay4_set("port", override_port)

        current_port = override_port

    else:

        # 瘝埝??�?撠望窒?典??祉? auto_detect / ?见?閮剖??讛摩

        # [Fix] 蝘駁膄 get_manual_relay4_port() 瑼Ｘ䰻嚗𣬚Ⅱ靽?RELAY4_INFO ?芾身摰𡁏??��脣� auto_detect (?折�?�???manual)

        if not (RELAY4_INFO.get("port") or RELAY4_PORT):

            auto_detect_4relay_port()

        current_port = RELAY4_INFO.get("port") or RELAY4_PORT or ""



    with RELAY4_LOCK:

        ch_state = RELAY4_INFO.get("ch_state") or {1: 0, 2: 0, 3: 0, 4: 0}

        return jsonify(

            ok=True,

            port=current_port or "",

            usb_relay_ports=usb_relay_ports,

            single_port=single_port or "",

            ch_state=ch_state,

            last_cmd=RELAY4_INFO.get("last_cmd"),

            last_result=RELAY4_INFO.get("last_result"),

            last_error=RELAY4_INFO.get("last_error"),

        )







@app.post("/relay4/set")

def relay4_set():

    """閮剖??𣂷?頝舐匱?餃膥 ON/OFF嚗麿SON {ch:1-4, on:true/false, port?:COMx}??""

    try:

        data = request.get_json(silent=True) or {}

        ch = int(data.get("ch", 0))

        on_raw = data.get("on", False)

        on = bool(on_raw)

        port_override = (data.get("port") or "").strip() or None



        if ch not in (1, 2, 3, 4):

            return jsonify(ok=False, error="ch 敹�???1~4"), 400



        try:

            control_usb_relay4(ch, on, port_override=port_override)

        except Exception as e:

            return jsonify(ok=False, error=str(e)[:200]), 500



        # ?𣂼?敺䕘??峕郊?𧼮�?�?啁??页??�鉄?舐鍂 COM 皜�鱓?�鱓 Relay COM

        with RELAY4_LOCK:

            ch_state = RELAY4_INFO.get("ch_state") or {1: 0, 2: 0, 3: 0, 4: 0}

            try:

                usb_relay_ports = list_4relay_candidate_ports()

            except Exception as e:

                _diag(f"[4R] list_4relay_candidate_ports error: {e}")

                usb_relay_ports = []

            single_port = (RELAY_INFO.get("port") if "RELAY_INFO" in globals() else None) or RELAY_PORT



            return jsonify(

                ok=True,

                port=RELAY4_INFO.get("port") or RELAY4_PORT or "",

                usb_relay_ports=usb_relay_ports,

                single_port=single_port or "",

                ch_state=ch_state,

                last_cmd=RELAY4_INFO.get("last_cmd"),

                last_result=RELAY4_INFO.get("last_result"),

                last_error=RELAY4_INFO.get("last_error"),

            )

    except Exception as e:

        return jsonify(ok=False, error=str(e)[:200]), 500





app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024



TRANSLATE_ENDPOINT = os.getenv("TRANSLATE_ENDPOINT", "https://libretranslate.de/translate")

TRANSLATE_TIMEOUT = float(os.getenv("TRANSLATE_TIMEOUT", "8.0"))



def _to_lt(code: str) -> str:

    c = (code or "").lower()

    if c in ("auto",): return "auto"

    if c.startswith("zh"): return "zh"

    if c.startswith("en"): return "en"

    if c.startswith("ja"): return "ja"

    if c.startswith("ko"): return "ko"

    if c.startswith("vi"): return "vi"

    if c.startswith("id"): return "id"

    if c.startswith("nan"): return "zh"

    return c[:2] or "auto"



def _to_gt(code: str) -> str:
    c = (code or "").lower()
    if c in ("auto", "any", ""): return "auto"
    if c.startswith("zh"): return "zh-TW"
    if c.startswith("en"): return "en"
    if c.startswith("ja"): return "ja"
    if c.startswith("ko"): return "ko"
    if c.startswith("vi"): return "vi"
    if c.startswith("id"): return "id"
    if c.startswith("nan"): return "zh-TW" # Google has no Hokkien
    if c.startswith("th"): return "th"
    if c.startswith("ms"): return "ms"
    return c[:2]



def _try_libretranslate(q: str, source: str, target: str) -> str:

    payload = {"q": q, "source": _to_lt(source), "target": _to_lt(target), "format": "text"}

    r = requests.post(TRANSLATE_ENDPOINT, json=payload, timeout=TRANSLATE_TIMEOUT)

    r.raise_for_status()

    data = r.json()

    if isinstance(data, dict):

        if "translatedText" in data and data["translatedText"]:

            return data["translatedText"]

        resp = data.get("response")

        if isinstance(resp, dict) and resp.get("translatedText"):

            return resp["translatedText"]

    raise RuntimeError("銝𦠜虜??translatedText")



def _try_mymemory(q: str, source: str, target: str) -> str:

    import urllib.parse as up

    def _guess_src(s: str) -> str:

        s64 = (s or "")[:64]

        if re.search(r"[\u4e00-\u9fff]", s64): return "zh"

        if re.search(r"[\u3040-\u30ff]", s64): return "ja"

        if re.search(r"[\uac00-\ud7af]", s64): return "ko"

        if re.search(r"[A-Za-z]", s64):       return "en"

        return "en"

    src = _to_lt(source)

    if src == "auto" or not src: src = _guess_src(q)

    tgt = _to_lt(target) or "zh"

    url = "https://api.mymemory.translated.net/get" + f"?q={up.quote(q)}&langpair={up.quote(src)}|{up.quote(tgt)}"

    r = requests.get(url, timeout=TRANSLATE_TIMEOUT)

    r.raise_for_status()

    data = r.json()

    txt = (data.get("responseData") or {}).get("translatedText")

    if txt: return txt

    raise RuntimeError("MyMemory ??translatedText")



@app.post("/translate")

def translate_api():
    try:
        data = request.get_json(silent=True) or {}
        print(f"[DEBUG] translate_api input: {data}")
        if "q" in data or "target" in data:
            q = (data.get("q") or data.get("text") or "").strip()
            source = (data.get("source") or "auto").strip()
            target = (data.get("target") or "zh-TW").strip()

            def _canon_lang(x: str) -> str:
                x = (x or "").strip().lower()
                if x in ("zh-tw","zhtw","zh_hant","zh"): return "zh-TW"
                if x in ("nan-tw","nan_tw","tw","nan"): return "nan"
                if "-" in x: return x.split("-")[0]
                return x or "auto"
            
            source = _canon_lang(source)
            target = _canon_lang(target)
            
            if target == "zh": target = "zh-TW"
            
            if source == "auto":
                if any('\u4e00' <= char <= '\u9fff' for char in q):
                    source = "zh-TW"
            
            print(f"[DEBUG] Final Routing: {source} -> {target}")
        else:
            q = (data.get("text") or "").strip()
            source = "auto"
            target = "zh-TW"

        if not q:
            return jsonify(ok=False, error="empty text"), 400

        # Dedicated Taigi (Hokkien) Routing
        if target == "nan":
            print(f"[DEBUG] Taigi special routing for: {q[:20]}...")
            try:
                # Use the logic from taigi_translate
                src_code = "zhtw" if source != "nan" else "tw"
                headers = {"x-api-key": TAIGI_TRANSLATE_API_KEY, "Content-Type": "application/json"}
                payload = {"inputText": q, "inputLan": src_code, "outputLan": "tw"}
                r = _post_with_fallback(TAIGI_TRANSLATE_ENDPOINTS, headers, payload, timeout=20)
                if r.status_code == 200:
                    jr = r.json()
                    if "outputText" in jr:
                        print("[DEBUG] Taigi translation success!")
                        return jsonify(ok=True, translatedText=jr["outputText"], text=jr["outputText"], via="taigi_api")
                print(f"[DEBUG] Taigi API failed (status {r.status_code}), falling back to identity...")
            except Exception as e_taigi:
                print(f"[DEBUG] Taigi API exception: {e_taigi}")
            
            # Fallback for Taigi: just use the original text (it's better than an error)
            return jsonify(ok=True, translatedText=q, text=q, via="taigi_fallback")

        # PREVENT SAME LANGUAGE ERROR: If source and target map to the same Google code, return original
        s_gt = _to_gt(source)
        t_gt = _to_gt(target)
        if s_gt == t_gt and s_gt != "auto":
            print(f"[DEBUG] Source and Target are both {s_gt}, returning original text.")
            return jsonify(ok=True, translatedText=q, text=q, via="identity")

        # Try Google first
        if HAS_DEEPTRANS:
            try:
                print(f"[DEBUG] Google translating: {s_gt} -> {t_gt}")
                translator = GoogleTranslator(source=s_gt, target=t_gt)
                out = translator.translate(q)
                
                if out and out.strip().lower() != q.strip().lower():
                    print(f"[DEBUG] Google success!")
                    return jsonify(ok=True, translatedText=out, text=out, via="google")
                else:
                    print(f"[DEBUG] Google returned source text, trying next...")
            except Exception as eg: 
                print(f"[DEBUG] Google engine error: {eg}")

        # Fallback to LibreTranslate
        try:
            print(f"[DEBUG] LibreTranslate trying: {source} -> {target}")
            out = _try_libretranslate(q, source, target)
            if out and out.strip().lower() != q.strip().lower():
                return jsonify(ok=True, translatedText=out, text=out, via="libretranslate")
        except Exception as el: 
            print(f"[DEBUG] LibreTranslate failed: {el}")

        # Try MyMemory
        try:
            print(f"[DEBUG] MyMemory trying: {source} -> {target}")
            s_my = source if source != "auto" else "en"
            out = _try_mymemory(q, s_my, target)
            if out:
                return jsonify(ok=True, translatedText=out, text=out, via="mymemory")
        except Exception as em: 
            print(f"[DEBUG] All engines failed")
            return jsonify(ok=False, error=f"?�?厩蕃霅臬??𤾸?憭望?: {em}"), 502
    except Exception as e:
        print(f"[DEBUG] translate_api Exception: {e}")
        return jsonify(ok=False, error=str(e)), 500

@app.get("/health")

def health():

    return jsonify(ok=True, ts=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))



@app.after_request

def no_cache(resp):

    resp.headers["Cache-Control"] = "no-store"

    resp.headers["Access-Control-Allow-Origin"] = "*"

    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"

    resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS, GET"

    return resp



@app.route("/translate", methods=["OPTIONS"])

def translate_options():

    return ("", 204)



# === ?批� ===

@app.route("/send", methods=["POST"])

def send():

    msg = request.form.get("msg","")

    if msg.strip(): threading.Thread(target=handle_msg, args=(msg, (_client_ip_from_request(), "Web")), daemon=True).start()

    return ("", 204)



@app.route("/sendmp3", methods=["POST"])

def sendmp3():

    mp3url = request.form.get("mp3url","")

    if mp3url:

        if "youtube.com/watch" in mp3url or "youtu.be/" in mp3url or "/shorts/" in mp3url:

            threading.Thread(target=handle_msg, args=(mp3url, (_client_ip_from_request(), "Web")), daemon=True).start()

        else:

            threading.Thread(target=handle_msg, args=(f"PlayMP3:{mp3url}", (_client_ip_from_request(), "Web")), daemon=True).start()

    return ("", 204)



@app.route("/setrate", methods=["POST"])

def setrate():

    rate = request.form.get("rate","-20%"); threading.Thread(target=handle_msg, args=(f"SetRate:{rate}", (_client_ip_from_request(), "Web")), daemon=True).start()

    return ("", 204)



@app.route("/setlang", methods=["POST"])

def setlang():

    lang = request.form.get("lang","zh-TW"); threading.Thread(target=handle_msg, args=(f"SetLang:{lang}", (_client_ip_from_request(), "Web")), daemon=True).start()

    return ("", 204)



@app.route("/setvol", methods=["POST"])

def setvol():

    vol = request.form.get("vol","")

    if vol != "":

        try: v = int(vol)

        except: v = None

        if v is not None:

            threading.Thread(target=handle_msg, args=(f"SetVolume:{v}", (_client_ip_from_request(), "Web")), daemon=True).start()

    return ("", 204)



@app.route("/volup", methods=["POST"])

def volup():

    threading.Thread(target=handle_msg, args=("VolUp", (_client_ip_from_request(), "Web")), daemon=True).start()

    return ("", 204)



@app.route("/voldown", methods=["POST"])

def voldown():

    threading.Thread(target=handle_msg, args=("VolDown", (_client_ip_from_request(), "Web")), daemon=True).start()

    return ("", 204)



@app.route("/special", methods=["POST"])

def special():

    msg = request.form.get("msg","")

    if msg: threading.Thread(target=handle_msg, args=(msg, (_client_ip_from_request(), "Web")), daemon=True).start()

    return ("", 204)



@app.route("/cmd", methods=["POST"])

def cmd():

    cmd = request.form.get("cmd", "")

    if cmd:

        threading.Thread(target=handle_msg, args=(cmd, (_client_ip_from_request(), "Web")), daemon=True).start()

    return ("", 204)







@app.route("/autounmute", methods=["POST"])

def autounmute():

    global AUTO_UNMUTE_ON_PLAY

    on = request.form.get("on", "1")

    AUTO_UNMUTE_ON_PLAY = (on == "1")

    STATE["auto_unmute_on_play"] = AUTO_UNMUTE_ON_PLAY

    return ("", 204)



# === 銝𠰴� / 皜�鱓 / 銝贝? / ?芷膄 ===





@app.post('/announce_upload')

def announce_upload():

    """Alias for uploading announcement images; returns {ok, url, ...}"""

    f = request.files.get("file")

    if not f or not getattr(f, "filename", ""):

        return jsonify(ok=False, error="no file"), 400

    ext = os.path.splitext(f.filename or "")[1].lower()

    if ext not in ALLOWED_EXTS:

        return jsonify(ok=False, error=f"only {sorted(list(ALLOWED_EXTS))} allowed"), 400

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    final_name = _generate_upload_filename(ext, prefix="announce")

    save_path = os.path.join(UPLOAD_DIR, final_name)

    try:

        f.save(save_path)

        url = f"/uploads/{final_name}"

        return jsonify(ok=True, url=url, name=final_name, ext=ext, is_image=ext in {".jpg",".jpeg",".png",".gif",".webp"})

    except Exception as e:

        return jsonify(ok=False, error=str(e)), 500

@app.route("/upload", methods=["POST"])

def upload():

    f = request.files.get("file")

    if not f or not getattr(f, "filename", ""):

        return jsonify(ok=False, error="no file"), 400

    display_name = os.path.basename(f.filename or "").strip()

    ext = os.path.splitext(f.filename or "")[1].lower()

    if ext not in ALLOWED_EXTS:

        return jsonify(ok=False, error=f"only {sorted(list(ALLOWED_EXTS))} allowed"), 400

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    final_name = _generate_upload_filename(ext)

    save_path = os.path.join(UPLOAD_DIR, final_name)



    try:

        f.save(save_path)

        st = os.stat(save_path)

        if not display_name:

            display_name = final_name

        mtype = _classify_upload_mtype(ext)

        _write_upload_meta(save_path, display_name, final_name, mtype, stat_res=st)

        # Backward compatibility:

        #  - old: {ok, filename: "uploads/<name>", size}

        #  - new: + name, url, ext, is_image

        rel = f"uploads/{final_name}"

        url = f"/uploads/{final_name}"

        is_image = ext in {".jpg",".jpeg",".png",".gif",".webp"}

        return jsonify(ok=True, 

                       filename=rel, size=st.st_size,

                       name=final_name, url=url, ext=ext, is_image=is_image,

                       orig=display_name, mtype=mtype)

    except Exception as e:

        return jsonify(ok=False, error=str(e)), 500



@app.route("/recordings/<path:filename>")

def serve_recordings(filename):

    return send_from_directory(RECORD_DIR, filename)



@app.route("/files", methods=["GET"])

@app.route("/api/uploads", methods=["GET"])

def api_uploads():

    items = []

    source = request.args.get("source", "upload") # default to 'upload' (UploadedMP3)

    

    target_dir = UPLOAD_DIR

    url_prefix = "/uploads"

    name_prefix = "uploads"

    

    if source == "rec":

        target_dir = RECORD_DIR

        url_prefix = "/recordings"

        name_prefix = "rec"



    try:

        for base in os.listdir(target_dir):

            ext = os.path.splitext(base)[1].lower()

            if ext not in ALLOWED_EXTS: continue

            p = os.path.join(target_dir, base)

            if not os.path.isfile(p): continue

            st = os.stat(p)

            

            meta = {}

            js = p + ".json"

            if os.path.exists(js):

                try: 

                    with open(js, "r", encoding="utf-8") as f: meta = json.load(f)

                except: pass

            

            items.append({

                "name": f"{name_prefix}/{base}",

                "saved": base,

                "orig": meta.get("orig_name") or base,

                "url": f"{url_prefix}/{base}",

                "size": st.st_size,

                "mtime": int(st.st_mtime),

                "mtype": meta.get("mtype") or _classify_upload_mtype(ext)

            })

    except Exception: pass

    items.sort(key=lambda x: x["mtime"], reverse=True)

    return jsonify(ok=True, files=items, items=items)



@app.route("/download/<path:name>", methods=["GET"])

def download(name):

    base = os.path.basename(name)

    if not base.lower().endswith(".mp3"): abort(403)

    return send_from_directory(UPLOAD_DIR, base, as_attachment=True, download_name=base)



@app.route("/delete", methods=["POST"])

def delete_file():

    name = request.form.get("name", "")

    base = os.path.basename(name)

    if not base: return jsonify(ok=False, error="bad name"), 400

    p = os.path.join(UPLOAD_DIR, base)

    if not os.path.isfile(p): return jsonify(ok=False, error="not found"), 404

    try:

        os.remove(p)

        meta = p + ".json"

        if os.path.exists(meta):

            try: os.remove(meta)

            except Exception: pass

        return jsonify(ok=True, deleted=base)

    except Exception as e:

        return jsonify(ok=False, error=str(e)), 500



# ===== 鈭衤辣蝝�??Logs API =====



def _log_dates_available():

    dates = []

    try:

        for base in os.listdir(DATA_DIR):

            if base.startswith("log_") and base.endswith(".csv"):

                d = base[4:-4]

                if re.match(r"^\d{4}-\d{2}-\d{2}$", d):

                    dates.append(d)

    except Exception:

        pass

    dates.sort(reverse=True)

    return dates



@app.get("/logs/dates")

def api_logs_dates(): return jsonify(ok=True, dates=_log_dates_available())



@app.get("/logs/download")

def api_logs_download():

    date_s = request.args.get("date", "").strip()

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_s): return jsonify(ok=False, error="bad date"), 400

    path = os.path.join(DATA_DIR, f"log_{date_s}.csv")

    if not os.path.isfile(path): return jsonify(ok=False, error="not found"), 404

    return send_file(path, as_attachment=True, download_name=f"log_{date_s}.csv")



@app.get("/logs")

def api_logs_list():

    date_s = request.args.get("date", "").strip() or datetime.now().strftime("%Y-%m-%d")

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_s): return jsonify(ok=False, error="bad date"), 400

    q = (request.args.get("q") or "").strip()

    offset = max(0, int(request.args.get("offset", "0") or 0))

    try: limit = int(request.args.get("limit", "500") or 500)

    except: limit = 500

    limit = max(1, min(5000, limit))



    path = os.path.join(DATA_DIR, f"log_{date_s}.csv")

    rows = []

    if os.path.isfile(path):

        try:

            with open(path, "r", encoding="utf-8") as f:

                rdr = csv.reader(f)

                for r in rdr:

                    t = (r[0] if len(r) > 0 else "") or ""

                    sender = (r[1] if len(r) > 1 else "") or ""

                    msg = (r[2] if len(r) > 2 else "") or ""

                    relay = (r[3] if len(r) > 3 else "N/A") or "N/A"

                    ip = (r[4] if len(r) > 4 else "") or None

                    rows.append({"time": t, "sender": sender, "ip": ip, "message": msg, "relay": relay})

        except Exception as e:

            return jsonify(ok=False, error=f"read error: {e}"), 500



    if q:

        ql = q.lower()

        def _hit(x):

            return (

                ql in (x.get("sender") or "").lower()

                or ql in (x.get("message") or "").lower()

                or ql in (x.get("relay") or "").lower()

                or ql in (str(x.get("ip") or "")).lower()

            )

        rows = [x for x in rows if _hit(x)]



    total = len(rows); rows.reverse()

    rows = rows[offset: offset + limit]

    return jsonify(ok=True, date=date_s, total=total, rows=rows)



@app.route("/state", methods=["GET"])

def state():

    out = dict(STATE)

    out["ok"] = True

    out["relay"] = STATE.get("relay", {})
    out["relay_auto_on"] = RELAY_AUTO_ON

    out["ts"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return jsonify(out)

@app.post("/api/relay_config")
def api_relay_config():
    try:
        j = request.get_json(force=True) or {}
        global RELAY_AUTO_ON
        if "auto_on" in j:
            RELAY_AUTO_ON = bool(j["auto_on"])
            _save_relay_config()
            try:
                # Sync Tkinter UI
                ui_safe(lambda: relay_auto_var.set(RELAY_AUTO_ON))
            except: pass
        return jsonify(ok=True, auto_on=RELAY_AUTO_ON)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500



# ===== 隤脰” API =====



def _validate_timetable(j: dict) -> tuple[bool, str | None]:

    if not isinstance(j, dict): return False, "payload 敹�???JSON ?拐辣"

    items = j.get("items", [])

    if not isinstance(items, list): return False, "items 敹�??舫腼??

    for i, it in enumerate(items):

        if not isinstance(it, dict): return False, f"items[{i}] 銝齿糓?拐辣"

        t = (it.get("time") or "").strip()

        if not re.match(r"^\d{2}:\d{2}$", t): return False, f"items[{i}].time ?�??HH:MM"

        a = (it.get("action") or "").strip()

        if not a: return False, f"items[{i}].action 銝滚虾蝛箇蒾"

        if "date" in it:

            if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(it["date"])): return False, f"items[{i}].date ?�??YYYY-MM-DD"

        else:

            d = it.get("dow")

            if d not in (1,2,3,4,5,6,7): return False, f"items[{i}].dow 敹�???1..7"

    return True, None







@app.get("/holidays")

def api_get_holidays():

    _helper_ensure_tt_defaults()

    return jsonify({

        "dates": list(timetable_data.get("holidays") or []),

        "names": timetable_data.get("holiday_names") or {},

        "skip_holidays": bool(timetable_data.get("skip_holidays", True)),

        "treat_saturday_as_school": bool(timetable_data.get("treat_saturday_as_school", False)),

        "enabled": bool(timetable_data.get("enabled", True)),

    })



@app.post("/holidays")

def api_set_holidays():

    _helper_ensure_tt_defaults()

    try:

        j = request.get_json(force=True) or {}

    except Exception as e:

        return jsonify(ok=False, error=f"bad json: {e}"), 400



    dates = j.get("dates") or j.get("holidays") or []

    names = j.get("names") or {}

    

    if not isinstance(dates, list):

        return jsonify(ok=False, error="dates must be an array"), 400



    dates = [str(d).strip() for d in dates if str(d).strip()]

    dates.sort()

    

    new = dict(timetable_data)

    new["holidays"] = dates

    new["holiday_names"] = names

    

    if "skip_holidays" in j:

        new["skip_holidays"] = bool(j.get("skip_holidays"))

    if "treat_saturday_as_school" in j:

        new["treat_saturday_as_school"] = bool(j.get("treat_saturday_as_school"))



    ok, err = _validate_timetable(new)

    if not ok:

        return jsonify(ok=False, error=err), 400



    try:

        with open(TIMETABLE_PATH, "w", encoding="utf-8") as f:

            json.dump(new, f, ensure_ascii=False, indent=2)

        _load_timetable_from_disk()

        return jsonify(

            ok=True,

            dates=list(timetable_data.get("holidays") or []),

            names=timetable_data.get("holiday_names") or {},

            skip_holidays=bool(timetable_data.get("skip_holidays", True)),

            treat_saturday_as_school=bool(timetable_data.get("treat_saturday_as_school", False)),

            enabled=bool(timetable_data.get("enabled", True))

        )

    except Exception as e:

        return jsonify(ok=False, error=str(e)), 500











@app.post("/timetable/import_holidays")

def api_timetable_import_holidays():

    """敺噼??輸堺鈭箔?銵峕錇蝮質? (via CDN) ?臬�?啁�?见??�𠯫 (?�??喉?銝滚?瑼?"""

    # ?𡑒岫?臬�隞𠰴僑?�?撟?

    target_years = [datetime.now().year, datetime.now().year + 1]

    fetched_holidays = {} # date -> {week, desc}

    

    try:

        for y in target_years:

            url = f"https://cdn.jsdelivr.net/gh/ruyut/TaiwanCalendar/data/{y}.json"

            try:

                resp = requests.get(url, timeout=5)

                if resp.status_code == 200:

                    items = resp.json()

                    if isinstance(items, list):

                        for item in items:

                            if item.get("isHoliday") is True:

                                raw_date = str(item.get("date", ""))

                                desc = str(item.get("description", "")).strip()

                                week = str(item.get("week", ""))

                                if re.match(r"^\d{8}$", raw_date):

                                    # YYYYMMDD -> YYYY-MM-DD

                                    fmt_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"

                                    fetched_holidays[fmt_date] = {"week": week, "desc": desc}

            except Exception as e:

                print(f"[Import] Failed to fetch {y}: {e}")



        # ?𧼮�?枏�?�??嗵策?滨垢嚗𣬚眏?滨垢瘙箏??臬炏?�蔥

        # return list of objects

        result_list = []

        for d in sorted(fetched_holidays.keys()):

            result_list.append({

                "date": d,

                "week": fetched_holidays[d]["week"],

                "name": fetched_holidays[d]["desc"]

            })

            

        return jsonify(ok=True, count=len(result_list), holidays=result_list)



    except Exception as e:

        return jsonify(ok=False, error=str(e)), 500





def _helper_ensure_tt_defaults():

    """蝣箔? timetable_data ?厰?閮剖�?""

    global timetable_data, timetable_enabled

    if not timetable_data:

        timetable_data = {"enabled": True, "items": []}

    if "enabled" not in timetable_data:

        timetable_data["enabled"] = True

    if "items" not in timetable_data:

        timetable_data["items"] = []






@app.get("/timetable")

def api_timetable():

    _helper_ensure_tt_defaults()

    return jsonify(ok=True, enabled=timetable_enabled, data=timetable_data, count=len(timetable_data.get("items", [])))



@app.route("/timetable/reload", methods=["POST"])

def api_timetable_reload():

    _load_timetable_from_disk()

    return jsonify(ok=True, count=len(timetable_data.get("items", [])), enabled=timetable_enabled)



def _auto_watch_timetable():

    """瘥?30 蝘埝炎??timetable.json ?臬炏鋡怠??冽凒?堆??交??�䌊?閖?頛剹�?""

    try:

        global _TIMETABLE_MTIME

        if os.path.isfile(TIMETABLE_PATH):

            try:

                m = os.path.getmtime(TIMETABLE_PATH)

            except Exception:

                m = None

            if m and _TIMETABLE_MTIME and m > _TIMETABLE_MTIME:

                text_area_insert("?菜葫??timetable.json 霈𦠜凒嚗�歇?芸??滩???, "Timetable")

                _load_timetable_from_disk()

        # ?嘥??�虾??None嚗�神?乩?甈?

        if _TIMETABLE_MTIME is None and os.path.isfile(TIMETABLE_PATH):

            try: _TIMETABLE_MTIME = os.path.getmtime(TIMETABLE_PATH)

            except Exception: pass

    finally:

        try:
            if not DISABLE_GUI and root:
                root.after(30000, _auto_watch_timetable)
        except Exception:
            pass



def _auto_watch_schedules():

    """瘥?30 蝘埝炎??schedules.json ?臬炏鋡怠??冽凒?堆??交??�䌊?閖?頛劐蒂?瑟鰵 UI??""

    try:

        global _SCHEDULES_MTIME

        if SCHEDULES_PATH.exists():

            try:

                m = SCHEDULES_PATH.stat().st_mtime

            except Exception:

                m = None

            if m and _SCHEDULES_MTIME and m > _SCHEDULES_MTIME:

                try:

                    ui_safe(text_area_insert, " ?菜葫??schedules.json 霈𦠜凒嚗�歇?芸??滩???, "Schedules")

                except Exception:

                    pass

                # ?滩?銝行凒??UI

                data = _load_schedules_from_disk()

                if 'sched_tree' in globals():

                    ui_safe(refresh_sched_tree)

            if _SCHEDULES_MTIME is None and m:

                _SCHEDULES_MTIME = m

    finally:

        try:
            if not DISABLE_GUI and root:
                root.after(30000, _auto_watch_schedules)
        except Exception:
            pass





@app.route("/timetable/enable", methods=["POST"])

def api_timetable_enable():

    """?毺鍂/?𦦵鍂?芸??㯄?"""

    global timetable_enabled

    try:

        data = request.get_json(force=True)

        enabled = bool(data.get("enabled", True))



        # Update global state

        timetable_enabled = enabled

        timetable_data["enabled"] = enabled



        # Save to disk

        with open(TIMETABLE_PATH, "w", encoding="utf-8") as f:

            json.dump(timetable_data, f, ensure_ascii=False, indent=2)



        STATE["timetable"]["enabled"] = enabled



        # ?峕郊敺𣬚垢 GUI嚗�𥅾?匧???Tk 銝餅綉?堆?

        def _apply_ui():

            status = " 隤脰”嚗𡁜??? if enabled else " 隤脰”嚗𡁜???

            if 'timetable_status_var' in globals():

                timetable_status_var.set(status)

            if 'refresh_timetable_tree' in globals():

                refresh_timetable_tree()

            update_next_label()



        ui_safe(_apply_ui)



        return jsonify(ok=True, enabled=enabled)

    except Exception as e:

        return jsonify(ok=False, error=str(e)), 500



@app.route("/timetable/set", methods=["POST"])

def api_timetable_set():

    try:

        payload = request.get_json(force=True) or {}

    except Exception as e:

        return jsonify(ok=False, error=f"bad json: {e}"), 400

    ok, err = _validate_timetable(payload)

    if not ok: return jsonify(ok=False, error=err), 400

    with open(TIMETABLE_PATH, "w", encoding="utf-8") as f:

        json.dump(payload, f, ensure_ascii=False, indent=2)

    _load_timetable_from_disk()

    try: text_area_insert(f"撌脰?撖怨玨銵剁?{len(timetable_data.get('items', []))} 蝑�?enabled={timetable_enabled}嚗?)

    except Exception: pass

    return jsonify(ok=True, count=len(timetable_data.get("items", [])), enabled=bool(timetable_data.get("enabled", True)))



@app.route("/timetable/merge", methods=["POST"])

def api_timetable_merge():

    try:

        patch = request.get_json(force=True) or {}

    except Exception as e:

        return jsonify(ok=False, error=f"bad json: {e}"), 400

    new = dict(timetable_data)

    for k in ("enabled", "treat_saturday_as_school", "skip_holidays", "holidays"):

        if k in patch: new[k] = patch[k]

    if "items" in patch: new["items"] = patch["items"]

    ok, err = _validate_timetable(new)

    if not ok: return jsonify(ok=False, error=err), 400

    with open(TIMETABLE_PATH, "w", encoding="utf-8") as f:

        json.dump(new, f, ensure_ascii=False, indent=2)

    _load_timetable_from_disk()

    return jsonify(ok=True, count=len(timetable_data.get("items", [])), enabled=bool(timetable_data.get("enabled", True)))



@app.route("/timetable/play", methods=["POST"])

def api_timetable_play():

    i = request.args.get("i", "")

    try: idx = int(i)

    except Exception: return jsonify(ok=False, error="bad index"), 400

    timetable_play_index(idx)

    return jsonify(ok=True)



# ===============================

# == [ANCHOR] /schedules API ?�?蝡航憚閰?==

# ===============================

@app.get('/schedules')

def api_get_schedules():

    try:

        if SCHEDULES_PATH.exists():

            # Check for empty file to prevent client JSON parse error

            if SCHEDULES_PATH.stat().st_size == 0:

                 return jsonify([])

            

            # Ensure path is string and set cache control

            resp = make_response(send_file(str(SCHEDULES_PATH), mimetype='application/json'))

            resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

            resp.headers["Pragma"] = "no-cache"

            resp.headers["Expires"] = "0"

            return resp

        return jsonify([])

    except Exception as e:

        return jsonify(ok=False, error=str(e)), 500



@app.post('/schedules')

def api_post_schedules():

    try:

        _debug_req()

        data = _get_json_tolerant()

        # ?舀螱?桃? dict ?硋?蝑?list嚗𥟇?蝯�神?交?獢��??list[dict]

        if isinstance(data, dict):

            payload = [data]

        elif isinstance(data, list):

            payload = data

        else:

            return jsonify(ok=False, error=f'invalid payload type: {type(data).__name__}'), 400



        # ?箸𧋦瑼Ｘ瓲嚗𡁏?蝑��??dict

        for i, it in enumerate(payload):

            it = _ensure_obj(it)

            if isinstance(it, str):

                try:

                    it = json.loads(it)

                    payload[i] = it

                except Exception:

                    return jsonify(ok=False, error=f'item {i} is string not json'), 400

            if not isinstance(it, dict):

                return jsonify(ok=False, error=f'item {i} must be object'), 400



        SCHEDULES_PATH.parent.mkdir(parents=True, exist_ok=True)

        with open(SCHEDULES_PATH, 'w', encoding='utf-8') as f:

            json.dump(payload, f, ensure_ascii=False, indent=2)

        try:

            global _SCHEDULES_MTIME

            _SCHEDULES_MTIME = SCHEDULES_PATH.stat().st_mtime

        except Exception:

            pass



        try:

            ui_safe(lambda: (refresh_sched_tree(), text_area_insert(" ?芾??垍?撌脫凒?堆?/schedules 銝𠰴�嚗?, "Web")))

        except Exception:

            pass

        return jsonify(ok=True, saved=len(payload))

    except Exception as e:

        return jsonify(ok=False, error=str(e)), 400



def _load_schedules_from_disk():

    """霈�??schedules.json嚗䔶蒂?湔鰵靽格㺿?�?嚗䔶? UI/?滨垢?峕郊??""

    global _SCHEDULES_MTIME

    try:

        with open(SCHEDULES_PATH, 'r', encoding='utf-8') as f:

            data = json.load(f)

            data = _ensure_obj(data)

            try: _SCHEDULES_MTIME = os.path.getmtime(SCHEDULES_PATH)

            except Exception: _SCHEDULES_MTIME = None

            if isinstance(data, list):

                # 蝣箔?瘥讐??舐�隞?

                fixed = []

                for it in data:

                    it = _ensure_obj(it)

                    if isinstance(it, str):

                        try:

                            it = json.loads(it)

                        except Exception:

                            continue

                    if isinstance(it, dict):

                        fixed.append(it)

                return fixed

            elif isinstance(data, dict):

                return [data]

            else:

                return []

    except Exception:

        return []



def schedules_scheduler_loop():

    global _schedules_last_fired

    while True:

        try:

            items = _load_schedules_from_disk()

            if items:

                now = datetime.now()

                ymd = now.strftime('%Y-%m-%d')

                wd = now.isoweekday()

                hh = now.strftime('%H')

                mm = now.strftime('%M')

                ss = int(now.strftime('%S'))

                for it in items:

                    if not it.get('enabled', True):

                        continue

                    # ?舀螱?格活?鞟? (date)

                    target_date = it.get('date')

                    if target_date:

                        if target_date != ymd:

                            continue

                    else:

                        # ?芣??冽??㗇?摰?date ?�?瑼Ｘ䰻?�?撟?

                        days = it.get('days') or []

                        if days and wd not in days:

                            continue

                    t = (it.get('time') or '').strip()

                    if not t:

                        continue

                    want = t if len(t)==8 else (t+':00')

                    th, tm, ts = [int(x) for x in want.split(':')]

                    if hh != f'{th:02d}' or mm != f'{tm:02d}':

                        continue

                    jitter = int(it.get('jitter') or 0)

                    if abs(ss - ts) > jitter:

                        continue

                    key = f"{it.get('id','?')}@{ymd}{th:02d}{tm:02d}{ts:02d}"

                    if key in _schedules_last_fired:

                        continue

                    _schedules_last_fired.add(key)

                    if it.get('cancel_all'):

                        handle_msg('CancelAll', 'Schedules')

                    if it.get('auto_unmute'):

                        handle_msg('Unmute', 'Schedules')

                    typ = (it.get('type') or 'cmd').lower()

                    payload = (it.get('payload') or '').strip()

                    if typ == 'sendmp3':

                        handle_msg(f'PlayMP3:{payload}', 'Schedules')

                    else:

                        handle_msg(payload, 'Schedules')

            prefix = datetime.now().strftime('%Y-%m-%d')

            _schedules_last_fired = {k for k in _schedules_last_fired if prefix in k}

        except Exception as e:

            try:

                text_area_insert(f'?𩤃? /schedules ?垍??券𥲤隤歹?{e}')

            except Exception:

                pass

        time.sleep(1)



def _compute_next_schedule_status(items):

    now = datetime.now()

    best = None  # (dt, item, idx)



    def parse_time_to_hms(t):

        t = (t or '').strip()

        if not t: return (8,0,0)

        if len(t) == 5: t = t + ':00'

        hh, mm, ss = [int(x) for x in t.split(':')]

        return hh, mm, ss



    for i, it in enumerate(items or []):

        try:

            if not it.get('enabled', True):

                continue

            hh, mm, ss = parse_time_to_hms(it.get('time'))

            if it.get('date'):

                try:

                    d = datetime.strptime(it['date'], '%Y-%m-%d')

                except Exception:

                    continue

                cand = d.replace(hour=hh, minute=mm, second=ss, microsecond=0)

                if cand < now:

                    continue

                if (best is None) or (cand < best[0]):

                    best = (cand, it, i)

                continue

            days = it.get('days') or []

            for add in range(0, 14):

                day = now.date() + timedelta(days=add)

                wd = day.isoweekday()

                if days and (wd not in days):

                    continue

                cand = datetime.combine(day, dtime(hh, mm, ss))

                if cand < now:

                    continue

                if (best is None) or (cand < best[0]):

                    best = (cand, it, i)

                break

        except Exception:

            continue



    if best is None:

        return {'has_next': False, 'count': len(items or []), 'now': now.strftime('%Y-%m-%d %H:%M:%S')}

    cand, it, idx = best

    return {

        'has_next': True,

        'count': len(items or []),

        'now': now.strftime('%Y-%m-%d %H:%M:%S'),

        'next': {

            'index': idx,

            'id': it.get('id'),

            'title': it.get('title'),

            'time': it.get('time'),

            'at': cand.strftime('%Y-%m-%d %H:%M:%S'),

            'in_seconds': int((cand - now).total_seconds()),

            'jitter': int(it.get('jitter') or 0),

            'type': it.get('type'),

            'payload': it.get('payload'),

        }

    }



@app.get('/schedules/status')

def api_schedules_status():

    try:

        items = _load_schedules_from_disk()

        return jsonify(_compute_next_schedule_status(items))

    except Exception as e:

        return jsonify(ok=False, error=str(e)), 500



# ===== ?芾?敹恍�罸枤 API =====

@app.get('/api/shortcuts')

def api_get_shortcuts():

    return jsonify(load_shortcuts())



@app.post('/api/shortcuts')

def api_save_shortcuts():

    try:

        data = request.get_json(force=True)

        if not isinstance(data, list):

            return jsonify(ok=False, error="Expected list"), 400

        save_shortcuts(data)

        return jsonify(ok=True)

    except Exception as e:

        return jsonify(ok=False, error=str(e)), 500

@app.get('/api/buddha_shortcuts')
def api_get_buddha_shortcuts():
    return jsonify(load_buddha_shortcuts())

@app.post('/api/buddha_shortcuts')
def api_save_buddha_shortcuts():
    try:
        data = request.get_json(force=True)
        if not isinstance(data, list):
            return jsonify(ok=False, error="Expected list"), 400
        save_buddha_shortcuts(data)
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500



@app.post('/api/play_shortcut')

def api_play_shortcut():

    try:

        data = request.get_json(force=True)

        mode = (data.get("mode") or ("tts" if data.get("text") else "mp3")).lower()

        if mode not in ("mp3", "tts", "text"):

            mode = "mp3"

        start_chime = bool(data.get("start_chime"))

        end_chime = bool(data.get("end_chime"))



        if mode in ("tts", "text"):

            text = (data.get("text") or "").strip()

            if not text:

                return jsonify(ok=False, error="Missing text"), 400



            def _run_tts():

                auto_unmute_if_needed()

                _interrupt_current_playback()

                first = relay_acquire("shortcut_tts")

                if first:

                    time.sleep(3)

                try:

                    if start_chime and os.path.exists(START_SOUND):

                        play_sound(START_SOUND)

                    text_area_insert(f"隤鮋𨺗?剜𦆮嚗�翰?瘀?嚗㝯text}", "Shortcut")

                    save_to_csv("Shortcut:TTS", "WebShortcut")

                    speak_text(text, force_chime_off=True)

                    if end_chime and os.path.exists(END_SOUND):

                        play_sound(END_SOUND, ignore_interrupt=True)

                except Exception as e:

                    print("Shortcut TTS error:", e)

                finally:

                    relay_release("shortcut_tts")



            threading.Thread(target=_run_tts, daemon=True).start()

            return jsonify(ok=True)



        filename = data.get("filename")

        if not filename:

            return jsonify(ok=False, error="Missing filename"), 400



        # Resolve full path if just filename given (assume UPLOADS or relative)

        full_path = filename

        if not os.path.exists(full_path):

            p1 = os.path.join(UPLOAD_DIR, filename)

            if os.path.exists(p1):

                full_path = p1

            else:

                p2 = resource_path(filename)

                if os.path.exists(p2):

                    full_path = p2



        if not os.path.exists(full_path):

            return jsonify(ok=False, error="File not found"), 404



        def _run():

            # Use relay wrapper logic manually

            auto_unmute_if_needed()

            _interrupt_current_playback()

            first = relay_acquire("shortcut")

            if first:

                time.sleep(3) # Wait for amp warm up

            try:

                if start_chime and os.path.exists(START_SOUND):

                    play_sound(START_SOUND)



                play_sound(full_path)



                if end_chime and os.path.exists(END_SOUND):

                    play_sound(END_SOUND, ignore_interrupt=True)

            except Exception as e:

                print("Shortcut play error:", e)

            finally:

                relay_release("shortcut")



        threading.Thread(target=_run, daemon=True).start()

        return jsonify(ok=True)

    except Exception as e:

        return jsonify(ok=False, error=str(e)), 500



# ===== Piper HTTP 隞钅𢒰 =====

@app.get("/piper/config")

def piper_cfg_get():

    return jsonify(ok=True, config=PIPER_CFG, available=_piper_available())



@app.post("/piper/config")

def piper_cfg_set():

    try:

        j = request.get_json(force=True) or {}

        for k in ("piper_exe","model","length_scale","noise_scale","noise_w","speaker"):

            if k in j: PIPER_CFG[k] = j[k]

        _piper_save_cfg(PIPER_CFG)

        return jsonify(ok=True, saved=PIPER_CFG, available=_piper_available())

    except Exception as e:

        return jsonify(ok=False, error=str(e)), 400



@app.post("/piper/force")

def piper_force():

    global PIPER_FORCE

    on = str(request.form.get("on","1")).lower()

    PIPER_FORCE = on in ("1","true","on","yes")

    return jsonify(ok=True, force=PIPER_FORCE)



@app.post("/piper/speak")

def piper_speak():

    txt = (request.form.get("text") or "").strip()

    if not txt:

        return jsonify(ok=False, error="empty text"), 400

    def _run():

        # ?芸?甇方?瘙�麱?�撥??piper

        global PIPER_FORCE

        old = PIPER_FORCE

        PIPER_FORCE = True

        try:

            handle_msg(txt, ("Web",))

        finally:

            PIPER_FORCE = old

    threading.Thread(target=_run, daemon=True).start()

    return jsonify(ok=True, queued=True)





# ===== Taigi 蝧餉陌 / TTS 隞?? =====

# 靘苷蝙?刻��?瘙�??游??啣?敺𣬚垢嚗䔶?敶梢𣳽?Ｘ??蠘�

TAIGI_TRANSLATE_API_KEY = os.getenv("TAIGI_TRANSLATE_API_KEY", "apiKey_b1a9e2e0-7c4f-4d5a-b8c1-92b6e25a4b6e6")

TAIGI_TTS_API_KEY       = os.getenv("TAIGI_TTS_API_KEY",       "apiKey_c8f0f59f-0f83-4d6f-bb1c-f12c8c312a7a6")

TAIGI_TRANSLATE_ENDPOINT = "https://learn-language.tokyo/taigiTransBilling/model2/translate_api_limit"

TAIGI_TTS_ENDPOINT       = "https://learn-language.tokyo/taigiStripe/synth_convert_api_limit_gender"

TAIGI_AUDIO_DIR = os.path.join(DATA_DIR, "taigi_audio")

os.makedirs(TAIGI_AUDIO_DIR, exist_ok=True)





class TaigiTTSException(Exception):

    def __init__(self, error: str, status: int = 500, **extra):

        super().__init__(error)

        self.error = error

        self.status = status

        self.extra = extra or {}





def _safe_basename(name: str) -> str:

    name = re.sub(r"[\\/:*?\"<>|]+", "_", name)

    name = re.sub(r"\s+", "_", name).strip("_")

    return name or "audio"





def _now_tag(): return time.strftime("%Y%m%d-%H%M%S")





def _resolve_taigi_voice_label(mode: str | None) -> tuple[str, str]:

    val = (mode or "").strip().lower()

    if val.startswith("audrey") or val == "a":

        return ("audrey_education", "A")

    if val.startswith("m"):

        return ("normal_m2", "M")

    return ("normal_f2", "F")






class TaigiTTSClient:
    def __init__(self, api_key: str):
        self.api_url = "https://learn-language.tokyo/taigiStripe/synth_convert_api_limit_gender"
        self.headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }

    def synthesize(self, text: str, voice: str = "normal_f2", model: str = "model6", speed: float = 1.0, user_id: str = ""):
        """
        ?澆㙈?啗? TTS API ?硋??單??????
        
        Args:
            text (str): 甈脣??鞟??啗??�? (撱箄降雿輻鍂瞍Ｗ??𡝗慰蝢�毽????
            voice (str): 'normal_m2' (?? ??'normal_f2' (憟???
            model (str): ?鞱身 'model6' (擃睃?鞈???
            speed (float): 隤鮋�麄�?
            user_id (str): 雿輻鍂??ID??
        
        Returns:
            str: ?單?銝贝? URL (72撠𤩺??㗇?)??
        """
        payload = {
            "text": text,
            "model": model,
            "voice_label": voice,
            "speed": speed,
            "user": user_id
        }

        try:
            # 雿輻鍂 _post_with_fallback 靽脲??�?蝟餌絞銝�?渡?蝬脰楝隢𧢲??讛摩 (?交??�閬?
            # 雿�迨?閧??砌蝙??requests.post嚗峕??𤑳凒?乩蝙??requests.post ?喳虾嚗?
            # ?删� _post_with_fallback ?航身閮�策憭𡁜�?URL ?��?
            # ?躰ㄐ?芣?銝�??URL嚗𣬚凒?亦鍂 requests.post??
            # ?箔?靽脲??�?蝔见?蝣潛??航炊?閧?銝�?湔�改??穃�𤑳?雿𡏭矽?氬�?
            
            response = requests.post(self.api_url, headers=self.headers, data=json.dumps(payload), timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("converted_audio_url")
            elif response.status_code == 400:
                raise TaigiTTSException(f"?�彍?航炊 (400): {response.text}", status=400)
            elif response.status_code == 401:
                raise TaigiTTSException("API Key ?⊥? (401)", status=401)
            elif response.status_code == 429:
                raise TaigiTTSException("隢𧢲??餌??𡡞? (429)", status=429)
            else:
                raise TaigiTTSException(f"TTS_HTTP_{response.status_code}", status=502, detail=response.text)
                
        except TaigiTTSException:
            raise
        except Exception as e:
            raise TaigiTTSException("TTS_EXCEPTION", status=500, detail=str(e))

    def download_audio(self, url: str, save_path: str):
        """銝贝? WAV 瑼娍??唳𧋦??""
        if not url:
            return
        
        try:
            resp = requests.get(url, stream=True, timeout=30)
            if resp.status_code == 200:
                with open(save_path, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                # print(f"瑼娍?撌脣�摮䁅秐: {save_path}")
            else:
                raise TaigiTTSException(f"DOWNLOAD_HTTP_{resp.status_code}", status=502)
        except Exception as e:
             raise TaigiTTSException("DOWNLOAD_EXCEPTION", status=502, detail=str(e))


def _taigi_generate_audio_file(text: str, voice_mode: str | None, speed: float = 1.0, user_id: str = "") -> dict[str, str]:
    if not text:
        raise TaigiTTSException("EMPTY_TEXT", status=400)

    voice_label, tag = _resolve_taigi_voice_label(voice_mode)
    
    # 撖虫???Client
    client = TaigiTTSClient(api_key=TAIGI_TTS_API_KEY)
    
    # ?澆㙈?�?
    try:
        url = client.synthesize(text, voice=voice_label, speed=speed, user_id=user_id)
    except TaigiTTSException:
        raise
    except Exception as e:
        raise TaigiTTSException("SYNTHESIZE_FAIL", status=500, detail=str(e))

    if not url:
        raise TaigiTTSException("NO_AUDIO_URL", status=502)

    base = _safe_basename(text[:20])
    fname = f"{base}_{tag}_{_now_tag()}.wav"
    save_path = os.path.join(TAIGI_AUDIO_DIR, fname)

    # 銝贝?
    client.download_audio(url, save_path)

    if os.path.getsize(save_path) < 44:
        raise TaigiTTSException("AUDIO_TOO_SMALL", status=502)

    return {"url": f"/taigi/audio/{fname}", "file": fname, "voice": voice_label}





# --- endpoints with fallbacks ---

TAIGI_TRANSLATE_ENDPOINTS = [

    TAIGI_TRANSLATE_ENDPOINT,

    "https://learn-language.tokyo/taigiTransBilling/translate_api_limit",  # no model2

    "https://learn-language.tokyo/taigiTransBilling/model1/translate_api_limit",  # model1

]

TAIGI_TTS_ENDPOINTS = [

    TAIGI_TTS_ENDPOINT,

    "https://learn-language.tokyo/taigiStripe/synth_convert_api_limit_gender",  # same as default

]



def _post_with_fallback(urls, headers, json_payload, timeout):

    last = None

    for u in urls:

        try:

            r = requests.post(u, headers=headers, json=json_payload, timeout=timeout)

            if r.status_code == 404 or r.status_code == 405:

                # try next candidate

                last = r

                continue

            return r

        except Exception as e:

            last = e

            continue

    # if all failed, raise/return the last one coherently

    if hasattr(last, "status_code"):

        return last

    raise last if last else RuntimeError("No endpoint reachable")

@app.post("/taigi/translate")

def taigi_translate():

    try:

        j = request.get_json(force=True) or {}

        text = (j.get("text") or "").strip()

        direction = (j.get("direction") or "zh2nan").lower()

        if not text:

            return jsonify(ok=False, error="EMPTY_TEXT"), 400

        src, tgt = ("zhtw","tw") if direction == "zh2nan" else ("tw","zhtw")

        headers = {"x-api-key": TAIGI_TRANSLATE_API_KEY, "Content-Type":"application/json"}

        payload = {"inputText": text, "inputLan": src, "outputLan": tgt}

        r = _post_with_fallback(TAIGI_TRANSLATE_ENDPOINTS, headers, payload, timeout=20)

        if r.status_code != 200:

            try: err = r.json()

            except Exception: err = r.text

            return jsonify(ok=False, error=f"TRANSLATE_HTTP_{r.status_code}", endpoint=getattr(r, "url", None), detail=err), 502

        jr = r.json()

        if "outputText" not in jr:

            return jsonify(ok=False, error="BAD_TRANSLATE_PAYLOAD", detail=jr), 502

        return jsonify(ok=True, text=jr["outputText"])

    except Exception as e:

        return jsonify(ok=False, error="TRANSLATE_EXCEPTION", detail=str(e)), 500



@app.post("/taigi/tts")

def taigi_tts():

    try:

        j = request.get_json(force=True) or {}

        text = (j.get("text") or "").strip()
        voice_mode = j.get("voice") or j.get("gender") or "f"
        speed = float(j.get("speed") or 1.0)
        user_id = str(j.get("user") or "")

        result = _taigi_generate_audio_file(text, voice_mode, speed=speed, user_id=user_id)

        return jsonify(ok=True, **result)

    except TaigiTTSException as e:

        payload = {"ok": False, "error": e.error}

        payload.update(e.extra)

        return jsonify(payload), e.status

    except Exception as e:

        return jsonify(ok=False, error="TTS_EXCEPTION", detail=str(e)), 500



@app.get("/taigi/audio/<path:filename>")

def taigi_audio(filename):

    base = os.path.basename(filename)

    return send_from_directory(TAIGI_AUDIO_DIR, base, as_attachment=False)



@app.post("/taigi/say")

def taigi_say():

    """銝�甈∪??琜??舫�?䔶葉??>?啗?蝧餉陌?㵪? TTS嚗䔶蒂?舫�?�糓?血銁?祆??湔𦻖?剜𦆮嚗�誨?哨???

    - play=True ?𡝗𧊋?𣂷?嚗𡁜??𣂼?嚗屸�誯? taigi_play_wav_with_fx() 撱?偘?剜𦆮

    - play=False嚗𡁜蘨?Ｙ?瑼娍??�?頛厩雯?�嚗䔶??笔?撱?偘嚗�策?滨垢閰西�嚗譍?頛厩鍂嚗?

    """

    try:

        j = request.get_json(force=True) or {}

        text = (j.get("text") or "").strip()

        # direction = (j.get("direction") or "zh2nan").lower()

        direction = (j.get("direction") or "raw").lower()

        # ?芣? direction == "zh2nan" ?滚?蝧餉陌嚗𥕦�擗矋?raw嚗匧停?湔𦻖??text ??TTS



        voice_mode = j.get("voice") or j.get("gender") or "f"
        speed = float(j.get("speed") or 1.0)
        user_id = str(j.get("user") or "")



        # 閫?? play ?埈?嚗𡁻?閮?True嚗?0"/"false" 蝑㕑??粹???

        play_raw = j.get("play", True)

        if isinstance(play_raw, str):

            play = play_raw.strip().lower() in ("1", "true", "yes", "y", "on")

        else:

            play = bool(play_raw)



        if not text:

            return jsonify(ok=False, error="EMPTY_TEXT"), 400



        # ?�蕃霅荔?敹�??�?

        if direction == "zh2nan":

            r = taigi_translate()

            if getattr(r, "status_code", 200) != 200:

                # taigi_translate already returns a Response

                return r

            jr = r.get_json() if hasattr(r, "get_json") else {}

            if not jr or not jr.get("ok"):

                return jsonify(ok=False, error="TRANSLATE_FAIL", detail=jr), 502

            text = jr.get("text") or text



        # ?�?銝血?瑼䈑?瘝輻鍂 /taigi/tts ?讛摩嚗?

        try:
            result = _taigi_generate_audio_file(text, voice_mode, speed=speed, user_id=user_id)

        except TaigiTTSException as e:

            payload = {"ok": False, "error": e.error}

            payload.update(e.extra)

            return jsonify(payload), e.status

        file_url = result.get("url")

        file_name = result.get("file")



        # 閬㚚?閬�??訫誨?剜偘?橘??鮋獈憛痹?

        if play and file_name:

            def _play():

                try:

                    p = os.path.join(TAIGI_AUDIO_DIR, file_name)

                    taigi_play_wav_with_fx(p)  # 憟㛖鍂?湔𦻖?剜𦆮閬𤩺聢嚗㇌elay嚗见?撠?蝯鞉?嚗?

                except Exception as e:

                    print("[taigi] play error:", e, file=sys.stderr)

            threading.Thread(target=_play, daemon=True).start()



        return jsonify(ok=True, text=text, url=file_url, file=file_name, played=bool(play))

    except Exception as e:

        return jsonify(ok=False, error="TAIGI_SAY_EXCEPTION", detail=str(e)), 500



# ===============================

# == [ANCHOR] UDP Listener ==

# ===============================



def udp_listener():

    text_area_insert(f" UDP ??�?笔?嚗?.0.0.0:{PORT}", src="UDP")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    sock.bind(("0.0.0.0", PORT))

    while True:

        try:

            data, addr = sock.recvfrom(8192)

            try: msg = data.decode("utf-8", errors="ignore").strip()

            except Exception: msg = repr(data)

            handle_msg(msg, addr)

        except Exception as e:

            text_area_insert(f"UDP ?航炊嚗㝯e}")

            time.sleep(0.2)





# ===============================

# == [ANCHOR] UDP Discovery Responder (for student-side auto-detection) ==

# ===============================

DISCOVERY_PORT = 9999           # UDP discovery port (student clients send probe here)

DISCOVERY_TOKEN = b"SCH_ANNOUNCE_DISCOVER"  # token students send; backend replies with JSON



def _get_local_ip_for_reply():

    """Best-effort local IP used in replies (doesn't rely on GUI variables)."""

    try:

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        s.settimeout(0.5)

        # connect to public DNS just to get the outbound IP used by the OS

        s.connect(("8.8.8.8", 80))

        ip = s.getsockname()[0]

        s.close()

        return ip

    except Exception:

        try:

            return socket.gethostbyname(socket.gethostname())

        except Exception:

            return "127.0.0.1"



def discovery_responder():

    """Listen for UDP discovery probes and reply with a small JSON containing server info.

    Student clients can send DISCOVERY_TOKEN to DISCOVERY_PORT on each IP; the backend

    will reply with: b'{"ok":true,"server":"x.x.x.x","http_port":5000}' so the client can open announce.html

    """

    try:

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Allow reuse and broadcast

        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:

            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        except Exception:

            pass

        s.bind(("0.0.0.0", DISCOVERY_PORT))

    except Exception as e:

        try: text_area_insert(f" Discovery responder bind failed: {e}", src="Discovery")

        except Exception: print("Discovery bind failed:", e)

        return

    try:

        text_area_insert(f" Discovery responder listening on 0.0.0.0:{DISCOVERY_PORT}", src="Discovery")

    except Exception:

        print(f"Discovery responder listening on 0.0.0.0:{DISCOVERY_PORT}")

    while True:

        try:

            data, addr = s.recvfrom(1024)

            if not data: continue

            # Accept either plain token or JSON with token field

            ok_probe = False

            try:

                if data.strip() == DISCOVERY_TOKEN:

                    ok_probe = True

                else:

                    # also accept small JSON like {"probe":"SCH_ANNOUNCE_DISCOVER"}

                    import json as _json

                    try:

                        j = _json.loads(data.decode("utf-8", errors="ignore"))

                        if isinstance(j, dict) and j.get("probe") == DISCOVERY_TOKEN.decode():

                            ok_probe = True

                    except Exception:

                        pass

            except Exception:

                pass

            if not ok_probe:

                # ignore unrelated packets

                continue

            # build reply

            server_ip = _get_local_ip_for_reply()

            payload = {

                "ok": True,

                "server": server_ip,

                "http_port": HTTP_PORT,

                "udp_port": PORT,

                "ts": int(time.time())

            }

            import json as _json2

            reply = _json2.dumps(payload).encode("utf-8")

            try:

                s.sendto(reply, addr)

            except Exception as e:

                try: text_area_insert(f" Discovery reply failed to {addr}: {e}", src="Discovery")

                except Exception: print("Discovery reply failed:", addr, e)

        except Exception as e:

            try: text_area_insert(f" Discovery loop error: {e}", src="Discovery")

            except Exception: print("Discovery loop error:", e)

            time.sleep(0.2)



# Start the discovery responder in background if UDP is enabled

try:

    if not DISABLE_UDP:

        threading.Thread(target=discovery_responder, daemon=True).start()

except Exception:

    pass

# ===============================



# ===============================

# == [ANCHOR] ngrok (?舫�) ==

# ===============================

_ngrok_proc = None



def _healthcheck_web():

    try:

        r = requests.get(f"http://127.0.0.1:{HTTP_PORT}/health", timeout=2)

        return r.ok

    except Exception:

        return False



def start_ngrok(force=False):

    global _ngrok_proc

    if (not USE_NGROK and not force) or DISABLE_WEB: return

    if not _healthcheck_web(): return

    exe = shutil.which("ngrok")

    if not exe:

        text_area_insert("[ngrok] ?芣𪄳??ngrok嚗�虾撠?USE_NGROK=False ?硋?鋆?ngrok", src="System"); return

    try:

        _ngrok_proc = subprocess.Popen([exe, "http", str(HTTP_PORT)], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

        time.sleep(2.5)

        try:

            j = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=3).json()

            tunnels = j.get("tunnels") or []

            for t in tunnels:

                if t.get("proto") == "https":

                    STATE["ngrok_url"] = t.get("public_url")

                    break

        except Exception:

            pass

        try:

            ui_safe(ngrok_status_label.config, text=f" ngrok嚗㝯STATE.get('ngrok_url') or '?芸?敺?URL'}")

        except Exception:

            pass

    except Exception as e:

        try: ui_safe(ngrok_status_label.config, text=f" ngrok ?笔?憭望?嚗㝯e}")

        except Exception: pass

        ui_safe(lambda: update_ngrok_ui_state(False))

    

    # ?𣂼??笔?敺峕凒?唳??閧???

    if STATE.get("ngrok_url"):

         ui_safe(lambda: update_ngrok_ui_state(True))



def stop_ngrok():

    global _ngrok_proc

    try:

        if _ngrok_proc and _ngrok_proc.poll() is None:

            if os.name == "nt":

                subprocess.run(["taskkill", "/PID", str(_ngrok_proc.pid), "/T", "/F"],

                               stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

            else:

                try: os.killpg(os.getpgid(_ngrok_proc.pid), signal.SIGKILL)

                except Exception: os.kill(_ngrok_proc.pid, signal.SIGKILL)

    except Exception:

        pass

    _ngrok_proc = None

    try: ui_safe(ngrok_status_label.config, text=" ngrok嚗𡁜歇?见??𨀣迫", fg=THEME["fg_sub"])

    except: pass

    ui_safe(lambda: update_ngrok_ui_state(False))





# ===============================

# == [ANCHOR] Tkinter UI嚗? ?�?嚗?==

# ===============================

#  撠�平?�??脖蜓憿?

THEME = {

    "bg_root": "#F3F4F6",       # ?𥪜??啁蒾?峕艶

    "bg_header": "#1E293B",     # 瘛梯???Header

    "fg_header": "#F8FAFC",     # Header ?�?

    "bg_card": "#FFFFFF",       # ?∠??賢?

    "bg_status": "#FFFFFF",     # ?�?见??賢?

    "fg_text": "#1F2937",       # 瘛梁�?�?

    "fg_sub": "#6B7280",        # 瘛箇�隤芣??�?

    "accent": "#3B82F6",        # ?𣂷漁??

    "border": "#E5E7EB",        # ?𦠜?

    "btn_bg": "#FFFFFF",        # ?厰??峕艶

    "font_main": ("Microsoft JhengHei UI", 9),

    "font_bold": ("Microsoft JhengHei UI", 9, "bold"),

    "font_s": ("Microsoft JhengHei UI", 8),

}



root = None
if not DISABLE_GUI:
    try:
        root = tk.Tk()
    except Exception as e:
        print(f"[GUI] tk.Tk() initialization failed: {e}. Switching to headless mode.")
        DISABLE_GUI = True
        root = None

if not DISABLE_GUI and root:
    # [ANCHOR] 閮剖? AppUserModelID ??ICON
    try:
        myappid = 'mycompany.relaybell.client.1228v1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    try:
        icon_path = resource_path("logo.ico")
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except Exception:
        pass

    try:
        png_path = resource_path("logo.png")
        if os.path.exists(png_path):
            img = tk.PhotoImage(file=png_path)
            root.iconphoto(True, img)
    except Exception:
        pass



if not DISABLE_GUI and root:
    root.title("UDP 隤鮋𨺗?交𤣰蝡荔?撠�平?�?")
    root.geometry("1024x768")
    root.configure(bg=THEME["bg_root"])






if not DISABLE_GUI:
    # 閮剖? ttk 銝駁?
    style = ttk.Style()
    style.theme_use('clam')
    style.configure("TFrame", background=THEME["bg_root"])
    style.configure("Card.TFrame", background=THEME["bg_card"], relief="flat")
    style.configure("TLabel", background=THEME["bg_root"], foreground=THEME["fg_text"], font=THEME["font_main"])
    style.configure("Card.TLabel", background=THEME["bg_card"], foreground=THEME["fg_text"], font=THEME["font_main"])
    style.configure("Header.TLabel", background=THEME["bg_header"], foreground=THEME["fg_header"], font=("Microsoft JhengHei UI", 12, "bold"))
    style.configure("TButton", font=THEME["font_main"], padding=4)
    style.configure("TNotebook", background=THEME["bg_root"], tabposition='n')
    style.configure("TNotebook.Tab", font=THEME["font_main"], padding=[12, 6], background="#E2E8F0")
    style.map("TNotebook.Tab", background=[("selected", THEME["accent"])], foreground=[("selected", "white")])
    style.configure("Treeview", background=THEME["bg_card"], fieldbackground=THEME["bg_card"], font=THEME["font_main"], rowheight=28, borderwidth=0)
    style.configure("Treeview.Heading", font=THEME["font_bold"], background="#F1F5F9", foreground=THEME["fg_text"], padding=[8, 6])
if not DISABLE_GUI:
    main_panel = tk.Frame(root, bg=THEME["bg_root"]); main_panel.pack(expand=True, fill="both", padx=0, pady=(8,0))
    status_row = tk.Frame(main_panel, bg=THEME["bg_card"], padx=10, pady=5); status_row.pack(fill="x", pady=(0,0), padx=16)
    status_label = tk.Label(status_row, text=" 隤鮋𨺗?毺鍂銝?, fg="#059669", font=THEME["font_bold"], bg=THEME["bg_card"])
    status_label.pack(side="left", padx=0, pady=5)
    ngrok_status_label = tk.Label(status_row, text=" ngrok嚗𡁏𧊋?笔?", font=THEME["font_s"], bg=THEME["bg_card"], fg=THEME["fg_sub"])
    ngrok_status_label.pack(side="left", padx=16)
    ngrok_btn_frame = tk.Frame(status_row, bg=THEME["bg_card"]); ngrok_btn_frame.pack(side="right", padx=0)
    ngrok_start_btn = tk.Button(ngrok_btn_frame, text="?笔? ngrok", bg="#D1FAE5", relief="flat", font=THEME["font_s"], command=lambda: start_ngrok(force=True))
    ngrok_start_btn.pack(side="left", padx=(0, 4))
    ngrok_stop_btn = tk.Button(ngrok_btn_frame, text="?𨀣迫 ngrok", bg="#FEE2E2", relief="flat", font=THEME["font_s"], command=stop_ngrok)
    ngrok_stop_btn.pack(side="left", padx=(0, 6))

    def update_ngrok_ui_state(is_running):
        if is_running:
            ngrok_start_btn.config(state="disabled", text="?笔?銝?..", bg="#E5E7EB")
            ngrok_stop_btn.config(state="normal", text="?𨀣迫 ngrok", bg="#FEE2E2")
        else:
            ngrok_start_btn.config(state="normal", text="?笔? ngrok", bg="#D1FAE5")
            ngrok_stop_btn.config(state="disabled", text="撌脣?甇?, bg="#E5E7EB")
    update_ngrok_ui_state(False)

    copy_btn = tk.Button(ngrok_btn_frame, text="銴�ˊ ngrok URL", bg="#F1F5F9", relief="flat", font=THEME["font_s"])
    copy_btn.pack(side="left", padx=(0,6))
    qr_label = tk.Label(ngrok_btn_frame, bg=THEME["bg_card"]); qr_label.pack(side="left"); qr_label._visible = False

    front_btn = tk.Button(ngrok_btn_frame, text="?见??滨垢嚗㇋R 閬𣇉?嚗?, bg="#F1F5F9", relief="flat",
                          font=THEME["font_s"], command=open_frontend_and_qr_popup)
    front_btn.pack(side="left", padx=(6,6))
    front_qr_label = tk.Label(ngrok_btn_frame, bg=THEME["bg_card"])
    front_qr_label.pack(side="left")
    front_qr_label._visible = False

    def copy_ngrok_url_and_qr_popup():
        url = STATE.get("ngrok_url")
        if not url:
            ui_safe(ngrok_status_label.config, text=" ngrok嚗𡁜??芸?敺?URL", fg="#b33"); return
        try:
            if root:
                root.clipboard_clear(); root.clipboard_append(url)
            ui_safe(ngrok_status_label.config, text=f" ngrok嚗㝯url}", fg="#074")
        except Exception as e:
            ui_safe(ngrok_status_label.config, text=f" 銴�ˊ憭望?嚗㝯e}", fg="#b33")
        show_qr_popup("ngrok ?祉雯蝬脣? QR", url)
    copy_btn.configure(command=copy_ngrok_url_and_qr_popup)

    tk.Button(status_row, text=" ?滚?隡箸???, command=lambda: os.execl(sys.executable, sys.executable, *sys.argv), bg="#F1F5F9", relief="flat",
              font=THEME["font_s"]).pack(side="right", padx=(6,8), pady=4)
    tk.Label(status_row, text=" 蝑匧??交𤣰閮𦠜�銝?..", font=THEME["font_s"], bg=THEME["bg_card"], fg=THEME["fg_sub"]).pack(side="right", padx=12)

    notebook = ttk.Notebook(main_panel); notebook.pack(expand=True, fill="both", padx=16, pady=16)
    tab_main = tk.Frame(notebook, bg=THEME["bg_root"]); notebook.add(tab_main, text=" 銝餅綉??)
    tab_relay4 = tk.Frame(notebook, bg=THEME["bg_root"]); notebook.add(tab_relay4, text=" 4?駵elay")
    tab_eew = tk.Frame(notebook, bg=THEME["bg_root"]); notebook.add(tab_eew, text=" ?圈? (EEW)")




# Status label for 4?駵elay

relay4_status_var = tk.StringVar(value="Port嚗尠�䈑?Cmd嚗尠�䈑?Result嚗尠�䈑?Err嚗尠�?)
tk.Label(tab_relay4, textvariable=relay4_status_var, font=THEME["font_bold"], bg=THEME["bg_card"]).pack(fill="x", padx=16, pady=(8,4))



# Control panel

relay4_ctrl_frame = tk.Frame(tab_relay4, bg=THEME["bg_card"])

relay4_ctrl_frame.pack(fill="x", padx=16, pady=4)



tk.Label(relay4_ctrl_frame, text="雿輻鍂 COM嚗?, font=THEME["font_s"], bg=THEME["bg_card"]).grid(row=0, column=0, sticky="w")

manual_relay4_var = tk.StringVar(value=get_manual_relay4_port() or (RELAY4_INFO.get("port") or "") or "COM5")

relay4_port_combo = ttk.Combobox(relay4_ctrl_frame, textvariable=manual_relay4_var, width=8, state="readonly")

relay4_port_combo.grid(row=0, column=1, padx=4, pady=2, sticky="w")



def apply_manual_relay4_port():

    """?见??�? 4-Relay COM ?牐蒂撖怠� relay4_port.txt??""

    global RELAY4_PORT

    try:

        port = (manual_relay4_var.get() or "").strip()

        if not port:

            messagebox.showinfo("4-Relay", "隢见??豢? COM ??𦻖??)

            return

        DIAG_DIR.mkdir(exist_ok=True)

        cfg = DIAG_DIR / "relay4_port.txt"

        cfg.write_text(port, encoding="utf-8")

        with RELAY4_LOCK:

            RELAY4_PORT = port

            _relay4_set("port", port)

            _relay4_set("last_cmd", "ManualSet")

            _relay4_set("last_result", "OK")

            _relay4_set("last_error", "")

        messagebox.showinfo("4-Relay", f"撌脰身摰?4-Relay 雿輻鍂 {port}\n銝𧢲活?笔?銋�?憟㛖鍂")

    except Exception as e:

        messagebox.showerror("4-Relay", f"撖怠� relay4_port.txt 憭望?嚗䨵n{e}")

    try:

        refresh_relay4_ui()

    except Exception:

        pass



def refresh_relay4_ui():

    try:

        relay4_status_var.set(

            f"Port嚗㝯RELAY4_INFO.get('port') or RELAY4_PORT or '??'}  "

            f"Cmd嚗㝯RELAY4_INFO.get('last_cmd') or '??'}  "

            f"Result嚗㝯RELAY4_INFO.get('last_result') or '??'}  "

            f"Err嚗㝯RELAY4_INFO.get('last_error') or '??'}"

        )

        # ?湔鰵?𡁻??�?钅＊蝷?

        st = RELAY4_INFO.get("ch_state") or {}

        for ch, var in (relay4_ch_labels.items() if 'relay4_ch_labels' in globals() else []):

            state_txt = "ON" if st.get(ch) else "OFF"

            var.set(f"CH{ch}嚗㝯state_txt}")

        devs = list_4relay_candidate_ports()

        if devs:

            relay4_port_combo["values"] = devs

            preferred = get_manual_relay4_port() or RELAY4_INFO.get("port") or RELAY4_PORT or devs[0]

            current = (manual_relay4_var.get() or "").strip()

            if not current or current not in devs:

                if preferred and preferred in devs:

                    manual_relay4_var.set(preferred)

                else:

                    manual_relay4_var.set(devs[0])

    except Exception:

        pass



tk.Button(relay4_ctrl_frame, text="憟㛖鍂", command=apply_manual_relay4_port, bg="#F3F4F6", relief="flat", font=THEME["font_s"]).grid(row=0, column=2, padx=4, pady=2)



def relay4_rescan():

    list_4relay_candidate_ports()

    refresh_relay4_ui()



tk.Button(relay4_ctrl_frame, text="?齿鰵?�?", command=relay4_rescan, bg="#F1F5F9", relief="flat", font=THEME["font_s"]).grid(row=0, column=3, padx=4, pady=2)



# ?𡁻??批�嚗�極璆剝◢?鍦?嚗𡁶??页??厰?嚗?

relay4_btns_row = tk.Frame(relay4_ctrl_frame, bg=THEME["bg_card"])

relay4_btns_row.grid(row=1, column=0, columnspan=4, sticky="w", pady=6)

relay4_ch_labels = {}

for ch in range(1,5):

    cell = tk.Frame(relay4_btns_row, bg=THEME["bg_card"], padx=4)

    cell.pack(side="left")

    sv = tk.StringVar(value=f"CH{ch}嚗尠�?)

    relay4_ch_labels[ch] = sv

    tk.Label(cell, textvariable=sv, font=THEME["font_s"], bg=THEME["bg_card"], fg="#94A3B8").pack(anchor="w")

    tk.Button(cell, text="ON", command=lambda c=ch: control_usb_relay4(c, True), bg="#D1FAE5", relief="flat", font=THEME["font_s"], width=5).pack(side="left", padx=2)

    tk.Button(cell, text="OFF", command=lambda c=ch: control_usb_relay4(c, False), bg="#FEE2E2", relief="flat", font=THEME["font_s"], width=5).pack(side="left", padx=2)



# Refresh UI initially

refresh_relay4_ui()



# ---- Tab EEW: ?圈?霅血𥼚 ----

tab_eew = tk.Frame(notebook, bg=THEME["bg_root"]); notebook.add(tab_eew, text=" ?圈? (EEW)")



# Status

eew_status_var = tk.StringVar(value="頛匧�銝?..")

tk.Label(tab_eew, textvariable=eew_status_var, font=THEME["font_bold"], bg=THEME["bg_card"], fg="#DC2626").pack(fill="x", padx=16, pady=(8,4))



# Control Panel

eew_ctrl_frame = tk.Frame(tab_eew, bg=THEME["bg_card"])

eew_ctrl_frame.pack(fill="x", padx=16, pady=4)



tk.Label(eew_ctrl_frame, text="閮剖?嚗?, font=THEME["font_bold"], bg=THEME["bg_card"]).pack(side="left", padx=8, pady=8)



eew_enable_var = tk.BooleanVar(value=False)

def _auto_sync_cwa_chk(*args):

    global CWA_ENABLED

    if CWA_ENABLED != eew_enable_var.get():

        CWA_ENABLED = eew_enable_var.get()

        _save_cwa_conf()

        # If enabled, trigger poll? maybe not needed here, loop covers it or user waits

        if CWA_ENABLED: threading.Thread(target=_cwa_poll_once, args=(True,), daemon=True).start()



eew_enable_var.trace_add("write", _auto_sync_cwa_chk)

chk_eew_en = tk.Checkbutton(eew_ctrl_frame, text="?毺鍂?芸?頛芾岷", variable=eew_enable_var, bg=THEME["bg_card"], font=THEME["font_main"])

chk_eew_en.pack(side="left", padx=8)



eew_broadcast_var = tk.BooleanVar(value=True)

def _auto_sync_cwa_bc_chk(*args):

    global CWA_BROADCAST_ENABLED

    if CWA_BROADCAST_ENABLED != eew_broadcast_var.get():

        CWA_BROADCAST_ENABLED = eew_broadcast_var.get()

        _save_cwa_conf()



eew_broadcast_var.trace_add("write", _auto_sync_cwa_bc_chk)

chk_eew_bc = tk.Checkbutton(eew_ctrl_frame, text="?毺鍂霅血𥼚撱?偘", variable=eew_broadcast_var, bg=THEME["bg_card"], font=THEME["font_main"])

chk_eew_bc.pack(side="left", padx=8)



tk.Label(eew_ctrl_frame, text="?㯄?(s)嚗?, bg=THEME["bg_card"]).pack(side="left", padx=2)

eew_poll_var = tk.StringVar(value="60")

tk.Entry(eew_ctrl_frame, textvariable=eew_poll_var, width=4).pack(side="left", padx=2)



tk.Label(eew_ctrl_frame, text="Key嚗?, bg=THEME["bg_card"]).pack(side="left", padx=2)

eew_key_var = tk.StringVar(value="")

tk.Entry(eew_ctrl_frame, textvariable=eew_key_var, width=32).pack(side="left", padx=2)



tk.Label(eew_ctrl_frame, text="?𤾸?嚗?, bg=THEME["bg_card"]).pack(side="left", padx=2)

eew_city_var = tk.StringVar(value="")

_TW_CITIES = ["(?芸??菜葫)", "?粹?撣?, "?啣?撣?, "?啣?撣?, "獢�?撣?, "?啁姘撣?, "?啁姘蝮?, "?埈?蝮?, "?唬葉撣?, "敶啣?蝮?, "?埈?蝮?, "?脫?蝮?, "?厩儔撣?, "?厩儔蝮?, "?啣?撣?, "擃㗛?撣?, "撅𤩺𨭬蝮?, "摰𡏭嵰蝮?, "?梯𤧣蝮?, "?唳𨭬蝮?, "瞉擧?蝮?, "?煾?蝮?, "???蝮?]

eew_city_combo = ttk.Combobox(eew_ctrl_frame, textvariable=eew_city_var, values=_TW_CITIES, width=10, state="readonly")

eew_city_combo.pack(side="left", padx=2)



eew_auto_city_var = tk.StringVar(value="")

tk.Label(eew_ctrl_frame, text=" (?嗵征?芸??菜葫) ", font=THEME["font_s"], bg=THEME["bg_card"], fg="#64748B").pack(side="left")

tk.Label(eew_ctrl_frame, textvariable=eew_auto_city_var, font=THEME["font_s"], bg=THEME["bg_card"], fg="#3B82F6").pack(side="left", padx=(0,4))



# 蝚砌?銵諹身摰?

eew_ctrl_frame2 = tk.Frame(tab_eew, bg=THEME["bg_card"])

eew_ctrl_frame2.pack(fill="x", padx=16, pady=2)



tk.Label(eew_ctrl_frame2, text="?�漲?�瑼鳴?", bg=THEME["bg_card"]).pack(side="left", padx=2)

eew_threshold_var = tk.StringVar(value="3")

# We can use a Combobox for common values

eew_threshold_combo = ttk.Combobox(eew_ctrl_frame2, textvariable=eew_threshold_var, values=["1", "2", "3", "4", "5撘?, "5撘?, "6撘?, "6撘?, "7"], width=5)

eew_threshold_combo.pack(side="left", padx=2)



def _apply_cwa_ui():

    global CWA_ENABLED, CWA_POLL_SEC, CWA_API_KEY, CWA_LAST_ERROR, CWA_LOCAL_CITY, CWA_INTENSITY_THRESHOLD

    try:

        CWA_ENABLED = eew_enable_var.get()

        CWA_POLL_SEC = max(15, int(eew_poll_var.get() or 60))

        

        new_key = (eew_key_var.get() or "").strip()

        if new_key:

             CWA_API_KEY = new_key

             CWA_LAST_ERROR = "" # Clear error on new key apply

        

        new_city = (eew_city_var.get() or "").strip()

        if new_city == "(?芸??菜葫)":

            CWA_LOCAL_CITY = ""

        else:

            CWA_LOCAL_CITY = new_city



        new_thresh = (eew_threshold_var.get() or "").strip()

        if new_thresh:

            # Map the displayed labels to what backend expects if needed, 

            # but _int_val handles both "5撘? and "5-". 

            # However, for consistency with Web UI, let's map them to the 5-/5+ format.

            mapping = {"5撘?: "5-", "5撘?: "5+", "6撘?: "6-", "6撘?: "6+"}

            CWA_INTENSITY_THRESHOLD = mapping.get(new_thresh, new_thresh)

        

        _save_cwa_conf()

        

        if CWA_ENABLED:

             threading.Thread(target=_cwa_poll_once, daemon=True).start()

        

        messagebox.showinfo("EEW", f"撌脫凒?啗身摰䨵n?毺鍂嚗㝯CWA_ENABLED}\n?𤾸?嚗㝯CWA_LOCAL_CITY or '(?芸?)'}\n?�瑼鳴?{CWA_INTENSITY_THRESHOLD}\nKey嚗㝯CWA_API_KEY[:4]}***")

    except Exception as e:

        messagebox.showerror("EEW", str(e))



tk.Button(eew_ctrl_frame, text="憟㛖鍂", command=_apply_cwa_ui, bg="#3B82F6", fg="white", relief="flat").pack(side="left", padx=12)



# Actions

eew_act_frame = tk.Frame(tab_eew, bg=THEME["bg_root"])

eew_act_frame.pack(fill="x", padx=16, pady=8)



def _test_cwa_alarm():

    threading.Thread(target=handle_msg, args=("PlayMP3:justEarthquakeAlarm.mp3", ("System","GUI")), daemon=True).start()



tk.Button(eew_act_frame, text="[?氓 皜祈岫霅血𥼚?單?", command=_test_cwa_alarm, bg="#F59E0B", padx=8, relief="flat").pack(side="left", padx=(0,8))

tk.Button(eew_act_frame, text="[?蒸 蝡见朖瑼Ｘ䰻 CWA", command=lambda: threading.Thread(target=_cwa_poll_once, args=(True,), daemon=True).start(), bg="#10B981", relief="flat", padx=8).pack(side="left")



# Last Info

eew_info_text = tk.Text(tab_eew, height=8, font=THEME["font_s"], bg=THEME["bg_card"], relief="flat")

eew_info_text.pack(fill="both", expand=True, padx=16, pady=8)



# Updater

def _update_eew_ui_loop():

    try:

        if eew_enable_var.get() != CWA_ENABLED:

            eew_enable_var.set(CWA_ENABLED)

        if eew_broadcast_var.get() != CWA_BROADCAST_ENABLED:

            eew_broadcast_var.set(CWA_BROADCAST_ENABLED)

        

        if CWA_LOCAL_CITY:

            # Ensure value is in list or just set it

            if eew_city_var.get() != CWA_LOCAL_CITY:

                eew_city_var.set(CWA_LOCAL_CITY)

        else:

            if eew_city_var.get() != "(?芸??菜葫)":

                eew_city_var.set("(?芸??菜葫)")

        

        # Update auto-detected city display

        def _update_auto_city_task():

            global CWA_LOCAL_CITY

            try:

                loc = _get_server_location()

                city = loc.get("city") or loc.get("region") or ""

                if city:

                    # Auto-land on the city: Update variable and save

                    CWA_LOCAL_CITY = city

                    eew_city_var.set(city)

                    eew_auto_city_var.set(f" [撌脣�皜砌蒂憟㛖鍂: {city}]")

                    _save_cwa_conf()

                else:

                    eew_auto_city_var.set(" [?菜葫銝滚�?琿??𤾸?]")

            except Exception as e:

                eew_auto_city_var.set(f" [?菜葫憭望?: {e}]")

        

        # Only update if currently set to "(?芸??菜葫)"

        if not CWA_LOCAL_CITY and eew_city_var.get() == "(?芸??菜葫)":

            if not hasattr(_update_eew_ui_loop, "_polling_city"):

                _update_eew_ui_loop._polling_city = True

                threading.Thread(target=_update_auto_city_task, daemon=True).start()

        elif CWA_LOCAL_CITY:

            eew_auto_city_var.set("") # Clear hint if manually set

        

        # Reverse mapping for threshold display

        rev_mapping = {"5-": "5撘?, "5+": "5撘?, "6-": "6撘?, "6+": "6撘?}

        thresh_display = rev_mapping.get(CWA_INTENSITY_THRESHOLD, CWA_INTENSITY_THRESHOLD)

        if eew_threshold_var.get() != thresh_display:

            eew_threshold_var.set(thresh_display)

        

        status = f"頛芾岷嚗㝯'?毺鍂' if CWA_ENABLED else '?𦦵鍂'}嚚𨅯誨?哨?{'?毺鍂' if CWA_BROADCAST_ENABLED else '?𣈯𨺗'}嚚𨅯?撣�?{CWA_LOCAL_CITY or '(?芸??菜葫)'}嚚𣈯?瑼鳴?{thresh_display}嚚𨀣? {CWA_POLL_SEC} 蝘?

        eew_status_var.set(status)

        

        # Last Data

        if CWA_LAST_ERROR:

             txt = f"[!] {CWA_LAST_ERROR}"

             eew_info_text.config(fg="red")

        elif CWA_LAST_DATA:

            # Unified Format: [Time] Location M? Depth?km \n Title

            d = CWA_LAST_DATA

            txt = f"[{d.get('time')}] {d.get('location')} 閬𤩺芋{d.get('mag')} 瘛勗漲{d.get('depth')}km\n{d.get('title')}"

            eew_info_text.config(fg="black")

        else:

            txt = "(撠𡁶�?�?啣𧑐?�???..)"

            eew_info_text.config(fg="gray")

            

        current_txt = eew_info_text.get("1.0", tk.END).strip()

        if current_txt != txt:

             eew_info_text.delete("1.0", tk.END)

             eew_info_text.insert("1.0", txt)

             

    except: pass

    finally:
        if not DISABLE_GUI and root:
            root.after(2000, _update_eew_ui_loop)



# Init values

eew_enable_var.set(CWA_ENABLED)

eew_poll_var.set(str(CWA_POLL_SEC))

# Set default KEY to input if empty

if not CWA_API_KEY:

    CWA_API_KEY = "CWB-2DA9AED0-4A0D-452C-B615-EE96324133AB" 

eew_key_var.set(CWA_API_KEY)

eew_city_var.set(CWA_LOCAL_CITY if CWA_LOCAL_CITY else "(?芸??菜葫)")

rev_mapping = {"5-": "5撘?, "5+": "5撘?, "6-": "6撘?, "6+": "6撘?}

eew_threshold_var.set(rev_mapping.get(CWA_INTENSITY_THRESHOLD, CWA_INTENSITY_THRESHOLD))



# Fetch once on startup so data appears even if polling is disabled (silent=True)

threading.Thread(target=_cwa_poll_once, args=(True,), daemon=True).start()



if not DISABLE_GUI and root:
    _update_eew_ui_loop()



setting_panel = tk.Frame(tab_main, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1)

setting_panel.pack(fill="x", padx=0, pady=(0, 16))



tk.Label(setting_panel, text=" 閮剖?隤噼?嚗?, font=THEME["font_bold"], bg=THEME["bg_card"]).grid(row=0, column=0, padx=(16,0), pady=16, sticky="w")

lang_label_var = tk.StringVar(value="?芸??菜葫 (Auto)")

lang_combo = ttk.Combobox(setting_panel, textvariable=lang_label_var,

                          values=[lab for lab,_ in LANG_OPTIONS], font=THEME["font_main"], state="readonly", width=13)

lang_combo.grid(row=0, column=1, padx=6, pady=16)



tk.Label(setting_panel, text="儭??批ê̌嚗?, font=THEME["font_bold"], bg=THEME["bg_card"]).grid(row=0, column=2, padx=(24,0), pady=16, sticky="w")

gender_label_var = tk.StringVar(value="憟唾�")

gender_combo = ttk.Combobox(setting_panel, textvariable=gender_label_var,

                            values=[lab for lab,_ in GENDER_LABELS], font=THEME["font_main"], state="readonly", width=7)

gender_combo.grid(row=0, column=3, padx=6, pady=16)
# Bind events
# Events removed (sync logic is now implicit in speak_text_async)

# [Sync Logic] Strict Mapping on Speak
# We simply rely on gender_label_var in speak_text_async







# Persistence for Voice Settings

VOICE_CONFIG_PATH = Path(DATA_DIR) / "voice_config.json"



def _save_voice_config():

    """Save persistent voice settings."""

    try:

        data = {
            "lang_label": lang_label_var.get(),
            "gender_label": gender_label_var.get(),
            "rate": rate_scale.get(),
            "chime_enabled": CHIME_ENABLED,
            "melo_speaker": MELO_SPEAKER,
            "melo_enabled": USE_MELO_TTS
        }

        VOICE_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

        VOICE_CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    except Exception as e:

        print(f"[Config] Save voice config failed: {e}")



def _load_voice_config():

    """Load persistent voice settings."""

    try:

        if VOICE_CONFIG_PATH.exists():

            data = json.loads(VOICE_CONFIG_PATH.read_text(encoding="utf-8"))

            l = data.get("lang_label")

            g = data.get("gender_label")

            r = data.get("rate")

            

            if l and l in lang_label2code:

                lang_label_var.set(l)

            if g and g in gender_label2code:

                gender_label_var.set(g)

            if r is not None:

                try: rate_scale.set(int(r))

                except: pass

            

            # Sync internal state

            # update_voice() will be called by bind or manual call, but we want to trigger update without save loop

            # actually calling update_voice() is fine as long as save is efficient

            update_voice()

            _on_rate_change()

            # Load chime setting
            global CHIME_ENABLED
            CHIME_ENABLED = data.get("chime_enabled", True)
            try:
                if 'chime_var' in globals():
                    ui_safe(lambda: chime_var.set(CHIME_ENABLED))
            except: pass

            # Load Melo Speaker
            global MELO_SPEAKER, USE_MELO_TTS
            # Try new key -> default
            MELO_SPEAKER = data.get("melo_speaker", "ZH")
            STATE["melo_speaker"] = MELO_SPEAKER
            
            # Default enabled checked from new -> old -> True
            USE_MELO_TTS = data.get("melo_enabled", False)
                 
            STATE["melo_enabled"] = USE_MELO_TTS

            print(f"[Config] Loaded voice settings: {l}, {g}, {r}, Chime={CHIME_ENABLED}, MeloSpk={MELO_SPEAKER}, MeloEnabled={USE_MELO_TTS}")

    except Exception as e:

        print(f"[Config] Load voice config failed: {e}")



def update_voice(event=None):

    global voice_language, voice_gender

    try:

        voice_language = lang_label2code.get(lang_label_var.get(), "zh-TW")

        voice_gender = gender_label2code.get(gender_label_var.get(), "female")

        STATE["lang"] = voice_language; STATE["gender"] = voice_gender

        

        # Save on change

        _save_voice_config()

    except Exception:

        pass



lang_combo.bind("<<ComboboxSelected>>", update_voice)

gender_combo.bind("<<ComboboxSelected>>", update_voice)



# 隤鮋�?

# 隤鮋�?

tk.Label(setting_panel, text=" 隤鮋��?", font=THEME["font_bold"], bg=THEME["bg_card"]).grid(row=0, column=4, padx=(24,0), pady=16, sticky="w")



# [Visual] Wrap scale in frame for Slow/Fast labels

rate_frame = tk.Frame(setting_panel, bg=THEME["bg_card"])

rate_frame.grid(row=0, column=5, padx=6, pady=16, sticky="w")



tk.Label(rate_frame, text="??, font=THEME["font_s"], fg="#666", bg=THEME["bg_card"]).pack(side="left", padx=(0,2))



rate_scale = tk.Scale(rate_frame, from_=-50, to=50, orient="horizontal", length=126,

                      showvalue=False, bg=THEME["bg_card"], highlightthickness=0,

                      command=lambda v: handle_msg(f"SetRate:{int(float(v))}%", ("?祆?",)))

rate_scale.set(int(voice_rate.replace("%","") if isinstance(voice_rate, str) else voice_rate))

rate_scale.pack(side="left")



tk.Label(rate_frame, text="敹?, font=THEME["font_s"], fg="#666", bg=THEME["bg_card"]).pack(side="left", padx=(2,0))



rate_label = tk.Label(setting_panel, text=f"{rate_scale.get()}%", font=THEME["font_s"], bg=THEME["bg_card"], fg=THEME["fg_sub"])

rate_label.grid(row=0, column=6, padx=(6,16), pady=16, sticky="w")



def _on_rate_change(v=None):

    try:

        v = rate_scale.get()

        rate_label.config(text=f"{v}%")
        # [Sync]
        r_str = f"{v}%"
        STATE["voice_rate"] = r_str
        STATE["rate"] = r_str
        global voice_rate
        voice_rate = r_str

        _save_voice_config()

    except Exception:

        pass

    

rate_scale.configure(command=lambda v: (_on_rate_change(v), None))



# Load config initially

if not DISABLE_GUI and root:
    root.after(500, _load_voice_config)



# 敹急㭘?脤𨺗?�? / ?𣈯𨺗

# 敹急㭘?脤𨺗?�? / ?𣈯𨺗

if not DISABLE_GUI:
    header = tk.Frame(root, bg=THEME["bg_header"], height=50)
    header.pack(fill="x")
    tk.Label(header, text="UDP 撱?偘隤鮋𨺗?交𤣰隡箸???, fg=THEME["fg_header"], bg=THEME["bg_header"],
             font=("Microsoft JhengHei UI", 14, "bold")).pack(side="left", padx=16, pady=10)

    header_right = tk.Frame(header, bg=THEME["bg_header"]); header_right.pack(side="right", padx=10)
    header_tools = tk.Frame(header_right, bg=THEME["bg_header"]); header_tools.pack(side="right", padx=(0, 6))

    btn_cancel = tk.Button(header_tools, text="??撘瑕�?𡝗?",
                           command=lambda: handle_msg("CancelALL", ("?祆?",)),
                           bg="#EF4444", fg="white", relief="flat", font=THEME["font_s"], padx=8, pady=2)
    btn_cancel.pack(side="left", padx=(0,8), pady=4)

    btn_clear = tk.Button(header_tools, text="皜�膄閮𦠜�",
                          command=lambda: (text_area.delete("1.0", tk.END),
                                           progress_var.set(0),
                                           progress_text_var.set("0%"),
                                           set_playing_status("??蝑匧??剜𦆮銝凌�?)),
                          bg="#3B82F6", fg="white", relief="flat", font=THEME["font_s"], padx=8, pady=2)
    btn_clear.pack(side="left", padx=(0,0), pady=4)

    ip_label = tk.Label(header_right, text=f"?祆? IP嚗㝯get_local_ip()}", fg="#94A3B8", bg=THEME["bg_header"], font=THEME["font_s"])
    ip_label.pack(side="right", padx=(12,6))

    clock_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    clock_label = tk.Label(header_right, textvariable=clock_var, fg="#94A3B8", bg=THEME["bg_header"], font=THEME["font_s"])
    clock_label.pack(side="right", padx=(12, 6))

    def _tick_clock():
        try: clock_var.set(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        except Exception: pass # Ignore errors if GUI is closing
        if not DISABLE_GUI and root:
            root.after(1000, _tick_clock)
    if not DISABLE_GUI and root:
        root.after(1000, _tick_clock)
quick_panel = tk.Frame(setting_panel, bg=THEME["bg_card"])

quick_panel.grid(row=0, column=7, padx=(24,16), pady=16, sticky="e")

tk.Button(quick_panel, text="憟唾�", command=lambda: handle_msg("Girl", ("?祆?",)), bg="#F3F4F6", relief="flat", font=THEME["font_s"]).pack(side="left", padx=2)

tk.Button(quick_panel, text="?瑁�", command=lambda: handle_msg("Boy", ("?祆?",)),  bg="#F3F4F6", relief="flat", font=THEME["font_s"]).pack(side="left", padx=2)

tk.Button(quick_panel, text="?𣈯𨺗", command=lambda: handle_msg("Mute", ("?祆?",)),  bg="#FEE2E2", relief="flat", font=THEME["font_s"]).pack(side="left", padx=2)

tk.Button(quick_panel, text="閫?膄?𣈯𨺗", command=lambda: handle_msg("Unmute", ("?祆?",)), bg="#D1FAE5", relief="flat", font=THEME["font_s"]).pack(side="left", padx=2)



# ?喲?

# ?喲?

volume_panel = tk.Frame(tab_main, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1)

volume_panel.pack(fill="x", padx=0, pady=(0, 10))

volume_label = tk.Label(volume_panel, text=f"?喲?嚗㝯STATE['volume']}%", font=THEME["font_bold"], bg=THEME["bg_card"])

volume_label.pack(side="left", padx=16, pady=10)

volume_scale = tk.Scale(volume_panel, from_=0, to=100, orient="horizontal", length=252,

                        showvalue=False, bg=THEME["bg_card"], highlightthickness=0,

                        command=lambda v: set_volume(int(float(v))))

volume_scale.set(STATE["volume"])

volume_scale.pack(side="left", padx=8, pady=4)

tk.Button(volume_panel, text="嚗?", command=lambda: handle_msg("VolDown", ("?祆?",)), bg="#F3F4F6", relief="flat", font=THEME["font_s"]).pack(side="left", padx=4)

tk.Button(volume_panel, text="嚗?", command=lambda: handle_msg("VolUp", ("?祆?",)),   bg="#F3F4F6", relief="flat", font=THEME["font_s"]).pack(side="left", padx=4)



# ?剜𦆮/閮𦠜�??

# ?剜𦆮/閮𦠜�??

play_panel = tk.Frame(tab_main, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1)
play_panel.pack(fill="x", padx=0, pady=(0, 0)) # Remove bottom padding to join with preview

# [NEW] Translation Preview Frame (Initially Packed but height 0 or hidden? No, pack_forget usually shifts.
# Better strategy: Pack Main (Top), then Preview, then Second (Bottom) in order.
trans_preview_frame = tk.Frame(tab_main, bg="#EFF6FF", highlightbackground="#BFDBFE", highlightthickness=1)
# trans_preview_frame will be packed here dynamically

play_panel_extra = tk.Frame(tab_main, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1)
play_panel_extra.pack(fill="x", padx=0, pady=(0, 10))

# [NEW] Translation Preview Frame (Hidden by default, defined early for layout)
# Removed trans_preview_frame definition from here as it is moved up

tk.Label(trans_preview_frame, text="?? 蝧餉陌?鞱汗嚗?, font=THEME["font_bold"], bg="#EFF6FF", fg="#1E40AF").pack(side="top", anchor="w", padx=16, pady=(8,2))
trans_preview_text = tk.Text(trans_preview_frame, height=2, font=THEME["font_main"], bg="#F0F9FF", relief="solid", bd=1)
trans_preview_text.pack(fill="x", padx=16, pady=4)
trans_preview_text.config(state="disabled")

trans_btn_row = tk.Frame(trans_preview_frame, bg="#EFF6FF")
trans_btn_row.pack(fill="x", padx=16, pady=(2,8))

def _gui_play_trans():
    txt = trans_preview_text.get("1.0", tk.END).strip()
    if txt:
        threading.Thread(target=handle_msg, args=(txt, ("GUI",)), daemon=True).start()

tk.Button(trans_btn_row, text="?? ?剜𦆮甇斤蕃霅?, command=_gui_play_trans, bg="#3B82F6", fg="white", relief="flat", font=THEME["font_s"]).pack(side="right", padx=4)
tk.Button(trans_btn_row, text="???𣈯??鞱汗", command=lambda: trans_preview_frame.pack_forget(), bg="#94A3B8", fg="white", relief="flat", font=THEME["font_s"]).pack(side="right", padx=4)



# ?�??剖𥼚

# ?�??剖𥼚

tk.Label(play_panel, text="儭??�??剖𥼚嚗?, font=THEME["font_bold"], bg=THEME["bg_card"]).grid(row=0, column=0, padx=(16,4), pady=6, sticky="w")



speak_entry = tk.Entry(play_panel, width=43, font=THEME["font_main"], relief="solid", bd=1)

speak_entry.grid(row=0, column=1, padx=6, pady=6, sticky="w")

def _submit_tts():

    txt = speak_entry.get().strip()

    if txt:

        threading.Thread(target=handle_msg, args=(txt, ("?祆?",)), daemon=True).start()

tk.Button(play_panel, text="?剖𥼚", command=_submit_tts, bg="#D1FAE5", relief="flat", font=THEME["font_s"]).grid(row=0, column=2, padx=6, pady=6)

def _gui_translate():
    q = speak_entry.get().strip()
    if not q:
        messagebox.showinfo("?箸�蝧餉陌", "隢见?頛詨�閬�蕃霅舐??�?")
        return
    
    target_label = lang_label_var.get()
    target_code = lang_label2code.get(target_label, "zh-TW")
    
    # Show status
    trans_preview_text.config(state="normal")
    trans_preview_text.delete("1.0", tk.END)
    trans_preview_text.insert("1.0", "??蝧餉陌銝?..")
    trans_preview_text.config(state="disabled")
    trans_preview_text.config(state="disabled")
    # Pack it right AFTER the main play panel, and BEFORE the extra panel
    trans_preview_frame.pack(fill="x", padx=0, pady=(0, 0), after=play_panel)
    
    def _task():
        try:
            # Prepare request data
            from deep_translator import GoogleTranslator
            
            # Use canonized logic similar to API
            def _canon(x):
                x = x.strip().lower()
                if x in ("zh-tw","zhtw","zh_hant","zh"): return "zh-TW"
                if x in ("nan-tw","nan_tw","tw","nan"): return "nan"
                if "-" in x: return x.split("-")[0]
                return x
            
            s_code = "zh-TW" # Assume source is Chinese for manual UI mostly
            t_code = _canon(target_code)
            
            if t_code == "nan":
                # Use Taigi API
                src_lang = "zhtw"
                headers = {"x-api-key": TAIGI_TRANSLATE_API_KEY, "Content-Type":"application/json"}
                payload = {"inputText": q, "inputLan": src_lang, "outputLan": "tw"}
                r = _post_with_fallback(TAIGI_TRANSLATE_ENDPOINTS, headers, payload, timeout=20)
                if r.status_code == 200:
                    out = r.json().get("outputText")
                else: out = None
            else:
                # Use Google
                s_gt = _to_gt(s_code)
                t_gt = _to_gt(t_code)
                if s_gt == t_gt: out = q
                else:
                    out = GoogleTranslator(source=s_gt, target=t_gt).translate(q)
            
            if out:
                ui_safe(lambda: _update_trans_ui(out))
            else:
                ui_safe(lambda: messagebox.showerror("蝧餉陌憭望?", "?⊥??脣?蝧餉陌蝯鞉?"))
                ui_safe(lambda: trans_preview_frame.pack_forget())
        except Exception as e:
            ui_safe(messagebox.showinfo, "?箸�蝧餉陌", str(e))
            ui_safe(lambda: trans_preview_frame.pack_forget())

    threading.Thread(target=_task, daemon=True).start()

def _update_trans_ui(text):
    trans_preview_text.config(state="normal")
    trans_preview_text.delete("1.0", tk.END)
    trans_preview_text.insert("1.0", text)
    trans_preview_text.config(state="disabled")

def _gui_play_trans():
    txt = trans_preview_text.get("1.0", tk.END).strip()
    if txt:
        # Get current voice settings
        lang = lang_label2code.get(lang_label_var.get(), "zh-TW")
        gender = gender_label2code.get(gender_label_var.get(), "female")
        threading.Thread(target=handle_msg, args=(txt, ("GUI",)), daemon=True).start()

tk.Button(play_panel, text="?箸�蝧餉陌", command=_gui_translate, bg="#DBEAFE", relief="flat", font=THEME["font_s"]).grid(row=0, column=3, padx=6, pady=6)



# ?啗??剖𥼚

tk.Label(play_panel_extra, text="儭??啗??剖𥼚嚗?, font=THEME["font_bold"], bg=THEME["bg_card"]).grid(row=0, column=0, padx=(16,4), pady=6, sticky="w")

taigi_entry = tk.Entry(play_panel_extra, width=43, font=THEME["font_main"], relief="solid", bd=1)

taigi_entry.grid(row=0, column=1, padx=6, pady=6, sticky="w")

def _submit_taigi():

    txt = taigi_entry.get().strip()

    if txt:

        threading.Thread(target=handle_msg, args=(f"PlayTaigi:{txt}", ("?祆?",)), daemon=True).start()

tk.Button(play_panel_extra, text="?剖蝱隤?, command=_submit_taigi, bg="#FDE68A", relief="flat", font=THEME["font_s"]).grid(row=0, column=2, padx=6, pady=6)



# ?刻攟撟閗???

# ?刻攟撟閗???

tk.Label(play_panel_extra, text="儭??刻攟撟閗??荔?", font=THEME["font_bold"], bg=THEME["bg_card"]).grid(row=1, column=0, padx=(16,4), pady=6, sticky="w")

fs_entry = tk.Entry(play_panel_extra, width=43, font=THEME["font_main"], relief="solid", bd=1)

fs_entry.grid(row=1, column=1, padx=6, pady=6, sticky="w")

tk.Button(play_panel_extra, text="憿舐內嚗𧢲偘??, command=lambda: handle_msg(f"ShowMsg:{fs_entry.get().strip()}", ("?祆?",)), bg="#FEF3C7", relief="flat", font=THEME["font_s"]).grid(row=1, column=2, padx=6, pady=6)

tk.Button(play_panel_extra, text="?芷＊蝷?,   command=lambda: handle_msg(f"SilentMsg:{fs_entry.get().strip()}", ("?祆?",)), bg="#FEF3C7", relief="flat", font=THEME["font_s"]).grid(row=1, column=3, padx=6, pady=6)



# YouTube/MP3

# YouTube/MP3

tk.Label(play_panel, text=" YouTube ??MP3 ???嚗?, font=THEME["font_bold"], bg=THEME["bg_card"]).grid(row=3, column=0, padx=(16,4), pady=6, sticky="w")

yt_entry = tk.Entry(play_panel, width=43, font=THEME["font_main"], relief="solid", bd=1)

yt_entry.grid(row=3, column=1, padx=6, pady=6, sticky="w")

def _submit_media():

    url = yt_entry.get().strip()

    if not url:

        return

    if ("youtube.com/watch" in url) or ("youtu.be/" in url) or ("/shorts/" in url):

        threading.Thread(target=handle_msg, args=(url, ("?祆?",)), daemon=True).start()

    else:

        threading.Thread(target=handle_msg, args=(f"PlayMP3:{url}", ("?祆?",)), daemon=True).start()

tk.Button(play_panel, text="?剜𦆮???", command=_submit_media, bg="#DBEAFE", relief="flat", font=THEME["font_s"]).grid(row=3, column=2, padx=6, pady=12)



def _choose_mp3_local():

    p = filedialog.askopenfilename(title="?豢? MP3", filetypes=[("MP3", "*.mp3")])

    if p:

        threading.Thread(target=handle_msg, args=(f"PlayMP3:{p}", ("?祆?",)), daemon=True).start()

tk.Button(play_panel, text="?剜𦆮?祆? MP3", command=_choose_mp3_local, bg="#DBEAFE", relief="flat", font=THEME["font_s"]).grid(row=3, column=3, padx=6, pady=12)



# ?脣漲?�偘?曄???

# ?脣漲?�偘?曄???

# 摮貊?蝡舀綉??
student_ctrl_panel = tk.Frame(tab_main, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1)
student_ctrl_panel.pack(fill="x", padx=0, pady=(0, 10))

tk.Label(student_ctrl_panel, text=" 摮貊?蝡舀綉?塚?", font=THEME["font_bold"], bg=THEME["bg_card"]).pack(side="left", padx=(16,4), pady=10)

tk.Label(student_ctrl_panel, text="?格? ID (蝛??券�)嚗?, font=THEME["font_s"], bg=THEME["bg_card"]).pack(side="left", padx=2)
student_target_var = tk.StringVar()
tk.Entry(student_ctrl_panel, textvariable=student_target_var, width=12, font=THEME["font_main"]).pack(side="left", padx=2)

def _send_student_cmd_ui(cmd_key, args=""):
    target = student_target_var.get().strip() or "ALL"
    
    # Construct payload command: TARGET={id}|{cmd}
    # send_student_udp_command will wrap it in CMD|...
    # Result: CMD|TARGET={id}|{cmd}|{args}
    
    real_cmd = f"TARGET={target}|{cmd_key}"
    
    # If target is specific, try to find it in WS list for optimization
    # If target is ALL, we should broadcast.
    # send_student_udp_command logic: if client_id is passed, try WS, else UDP.
    
    # For ALL, we want UDP broadcast (255.255.255.255).
    # Also ideally send to all WS clients, but send_student_udp_command doesn't support "Broadcast to all WS".
    # We'll rely on UDP for broadcast for now, or iterate manually if needed.
    # But wait, if I pass client_id=None, it sends UDP to the IP I specify.
    
    # Let's iterate WS if ALL
    if target == "ALL":
        # 1. UDP Broadcast
        send_student_udp_command("255.255.255.255", 12345, real_cmd, args, client_id=None)
        
        # 2. WS Broadcast (Manual)
        with AGENT_WS_LOCK:
            # Copy keys to avoid runtime error if dict changes
            for cid, ws in list(AGENT_WS_CLIENTS.items()):
                try:
                    ws.send(f"CMD|{real_cmd}|{args}")
                except: pass
        
        text_area_insert(f"撌脣誨?剜?隞?({cmd_key}) ?單??匧飛??, "Student")
        
    else:
        # Targeted
        # Try to send to specific target (WS prioritized inside function)
        # We use 255.255.255.255 as fallback IP because we might not know the student's IP
        # unless we track it. But if WS fails, UDP broadcast with Target ID filter is valid too!
        success = send_student_udp_command("255.255.255.255", 12345, real_cmd, args, client_id=target)
        if success:
             text_area_insert(f"撌脩䔄?�?隞?({cmd_key}) ??{target}", "Student")
        else:
             text_area_insert(f"?潮��?隞?({cmd_key}) ??{target} 憭望?", "Student")

tk.Button(student_ctrl_panel, text="?輸�", command=lambda: _send_student_cmd_ui("Ring"), bg="#FDE68A", relief="flat", font=THEME["font_s"]).pack(side="left", padx=4)
tk.Button(student_ctrl_panel, text="?见?蝬脤?", command=lambda: _send_student_cmd_ui("OpenURL", "https://google.com"), bg="#DBEAFE", relief="flat", font=THEME["font_s"]).pack(side="left", padx=4)
tk.Button(student_ctrl_panel, text="?齿鰵?笔?", command=lambda: _send_student_cmd_ui("Reboot"), bg="#FEE2E2", relief="flat", font=THEME["font_s"]).pack(side="left", padx=4)
tk.Button(student_ctrl_panel, text="?𨀣?", command=lambda: _send_student_cmd_ui("Shutdown"), bg="#FEE2E2", relief="flat", font=THEME["font_s"]).pack(side="left", padx=4)


progress_row = tk.Frame(tab_main, bg=THEME["bg_root"])

progress_row.pack(fill="x", padx=0, pady=(4, 2))

playing_label = tk.Label(progress_row, text="??蝑匧??剜𦆮銝凌�?, bg=THEME["bg_root"], font=THEME["font_s"], fg=THEME["fg_sub"])

playing_label.pack(side="left", padx=(2, 10))



progress_var = tk.IntVar(value=0)

progress_widget = ttk.Progressbar(progress_row, orient="horizontal", mode="determinate", variable=progress_var, length=294)

progress_widget.pack(side="left", padx=(0, 10))

progress_text_var = tk.StringVar(value="0%")

progress_text_label = tk.Label(progress_row, textvariable=progress_text_var, bg=THEME["bg_root"], font=THEME["font_s"], fg=THEME["fg_sub"])

progress_text_label.pack(side="left")





# 蝜潮𤓖?典?憛?

# 蝜潮𤓖?典?憛?

relay_frame = tk.Frame(tab_main, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1)

relay_frame.pack(fill="x", padx=0, pady=(4, 6))



tk.Label(

    relay_frame,

    text=" USB 蝜潮𤓖?剁?CH340/CH341嚗?,

    font=THEME["font_bold"],

    bg=THEME["bg_card"]

).grid(row=0, column=0, padx=16, pady=(10, 2), sticky="w")



relay_status_var = tk.StringVar(value="Port嚗尠�䈑?Cmd嚗尠�䈑?Result嚗尠�䈑?Err嚗尠�?)

relay_status_label = tk.Label(relay_frame, textvariable=relay_status_var, bg=THEME["bg_card"], fg=THEME["fg_sub"], font=THEME["font_s"])

relay_status_label.grid(row=0, column=1, padx=12, pady=(10, 2), sticky="w", columnspan=2)



# 撌血�?批�?Ｘ踎嚗�???COM + ?厰?嚗?

# 撌血�?批�?Ｘ踎嚗�???COM + ?厰?嚗?

relay_ctrl_frame = tk.Frame(relay_frame, bg=THEME["bg_card"])

relay_ctrl_frame.grid(row=1, column=0, padx=(16, 6), pady=(2, 10), sticky="nw")



tk.Label(

    relay_ctrl_frame,

    text="雿輻鍂 COM嚗?,

    font=THEME["font_s"],

    bg=THEME["bg_card"]

).grid(row=0, column=0, padx=(0, 4), pady=(0, 2), sticky="w")



manual_relay_var = tk.StringVar(

    value=get_manual_relay_port() or (RELAY_INFO.get("port") or "") or "COM5"

)



relay_port_combo = ttk.Combobox(

    relay_ctrl_frame,

    textvariable=manual_relay_var,

    width=7,

    state="readonly"

)

relay_port_combo.grid(row=0, column=1, padx=(0, 6), pady=(0, 2), sticky="w")



def apply_manual_relay_port():

    """撠�??厰�?�? COM 摮䀹??鞱身銝衣??喳??具�?""

    global RELAY_PORT

    port = (manual_relay_var.get() or "").strip()

    if not port:

        messagebox.showwarning("USB 蝜潮𤓖??, "隢见??豢?閬�蝙?函? COM ?𨬭�?)

        return

    try:

        cfg = DIAG_DIR / "relay_port.txt"

        DIAG_DIR.mkdir(parents=True, exist_ok=True)

        cfg.write_text(port, encoding="utf-8")

        with RELAY_LOCK:

            RELAY_PORT = port

            _relay_set("port", port)

            _relay_set("last_cmd", "ManualSet")

            _relay_set("last_result", "OK")

            _relay_set("last_error", "")

        messagebox.showinfo("USB 蝜潮𤓖??, f"撌脫?摰𡁶匱?餃膥雿輻鍂 {port}\n銝𧢲活?笔?銋�??芸?憟㛖鍂??)

    except Exception as e:

        messagebox.showerror("USB 蝜潮𤓖??, f"撖怠� relay_port.txt 憭望?嚗䨵n{e}")



tk.Button(

    relay_ctrl_frame,

    text="憟㛖鍂",

    command=apply_manual_relay_port,

    bg="#F3F4F6",

    relief="flat",

    font=THEME["font_s"]

).grid(row=0, column=2, padx=(2, 4), pady=(0, 2), sticky="w")





def _relay_rescan():

    rescan_relay_ports()



def _relay_on():

    threading.Thread(target=test_relay_on, daemon=True).start()



def _relay_off():

    threading.Thread(target=test_relay_off, daemon=True).start()



# ?批�嚗𡁏?憿諹??厰??䔶?銵?

relay_ctrl_row = tk.Frame(relay_ctrl_frame, bg=THEME["bg_card"])

relay_ctrl_row.grid(row=2, column=0, columnspan=3, padx=0, pady=2, sticky="w")



tk.Label(

    relay_ctrl_row,

    text="?批�嚗?,

    font=THEME["font_s"],

    bg=THEME["bg_card"]

).pack(side="left", padx=(0, 6))



tk.Button(

    relay_ctrl_row,

    text="?齿鰵?�?",

    command=_relay_rescan,

    bg="#F3F4F6",

    relief="flat",

    font=THEME["font_s"]

).pack(side="left", padx=(0, 4))



tk.Button(

    relay_ctrl_row,

    text="ON",

    command=_relay_on,

    bg="#D1FAE5",

    relief="flat",

    font=THEME["font_s"]

).pack(side="left", padx=(0, 4))



tk.Button(

    relay_ctrl_row,

    text="OFF",

    command=_relay_off,

    bg="#FEE2E2",

    relief="flat",

    font=THEME["font_s"]

).pack(side="left", padx=(0, 4))

# [NEW] Checkbox for Auto Relay
def _on_relay_auto_change(*args):
    global RELAY_AUTO_ON
    RELAY_AUTO_ON = relay_auto_var.get()
    _save_relay_config()

relay_auto_var = tk.BooleanVar(value=RELAY_AUTO_ON)
relay_auto_var.trace("w", _on_relay_auto_change)
tk.Checkbutton(
    relay_ctrl_row,
    text="?芸??笔??游之璈?,
    variable=relay_auto_var,
    bg=THEME["bg_card"],
    font=THEME["font_s"]
).pack(side="left", padx=(10, 4))


# [NEW] Chime Checkbox (Moved here)
chime_var = tk.BooleanVar(value=CHIME_ENABLED)
def _on_chime_change(*args):
    global CHIME_ENABLED
    CHIME_ENABLED = chime_var.get()
    # Save to voice config (or move to relay config?) 
    # Let's keep saving to voice config as it's sound related, but displayed here.
    _save_voice_config()
chime_var.trace("w", _on_chime_change)

tk.Checkbutton(
    relay_ctrl_row,
    text="?剜𦆮?鞟內??,
    variable=chime_var,
    bg=THEME["bg_card"],
    font=THEME["font_s"]
).pack(side="left", padx=(10, 4))




# ?喳� COM ?�?蝯鞉?

relay_ports_frame = tk.Frame(relay_frame, bg=THEME["bg_card"])

relay_ports_frame.grid(row=1, column=1, padx=(0, 12), pady=(2, 10), sticky="nsew")



relay_ports_text = ScrolledText(

    relay_ports_frame,

    width=48,

    height=5,

    font=("Consolas", 8),

    bg=THEME["bg_card"],

    fg=THEME["fg_text"],

    relief="flat",

    bd=1

)

relay_ports_text.grid(row=1, column=0, padx=0, pady=2, sticky="nsew")



relay_frame.grid_columnconfigure(1, weight=1)

relay_frame.grid_rowconfigure(1, weight=1)

relay_ports_frame.grid_rowconfigure(1, weight=1)

relay_ports_frame.grid_columnconfigure(0, weight=1)



def refresh_relay_ui():

    try:

        # ?湔鰵?喳�?�?蝯鞉??�?

        relay_ports_text.delete("1.0", tk.END)

        relay_ports_text.insert(tk.END, get_ports_snapshot_text())



        # ?湔鰵銝𦠜䲮?�?见?

        relay_status_var.set(

            f"Port嚗㝯RELAY_INFO.get('port') or '??}嚚?

            f"Cmd嚗㝯RELAY_INFO.get('last_cmd') or '??}嚚?

            f"Result嚗㝯RELAY_INFO.get('last_result') or '??}嚚?

            f"Err嚗㝯RELAY_INFO.get('last_error') or '??}"

        )



        # ?湔鰵銝𧢲? COM 皜�鱓

        items = RELAY_INFO.get("ports") or []

        devs = [dev for dev, desc, hwid in items if dev]

        if devs:

            relay_port_combo["values"] = devs

            current = (manual_relay_var.get() or "").strip()

            preferred = get_manual_relay_port() or RELAY_INFO.get("port") or (devs[0] if devs else "")

            if not current or current not in devs:

                if preferred and preferred in devs:

                    manual_relay_var.set(preferred)

                else:

                    manual_relay_var.set(devs[0])

    except Exception:

        pass



# 銝餅綉?啗??臬?

console_frame = tk.Frame(tab_main, bg=THEME["bg_root"])

console_frame.pack(expand=True, fill="both", padx=0, pady=(2, 12))

text_area = ScrolledText(console_frame, height=13, font=("Consolas", 9), bg="#1E293B", fg="#F8FAFC", insertbackground="white", relief="flat")

text_area.pack(expand=True, fill="both")



def _flush_boot_logs():

    if '_BOOT_LOGS' in globals():

        for msg in _BOOT_LOGS:

            text_area_insert(msg, "BOOT")



_flush_boot_logs()

flush_text_buffer_if_any()



# ---- Tab 2:  隤脰” ----

# ---- Tab 2:  隤脰” ----

tab_tt = tk.Frame(notebook, bg=THEME["bg_root"]); notebook.add(tab_tt, text=" 隤脰”")

tt_top = tk.Frame(tab_tt, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1)

tt_top.pack(fill="x", padx=0, pady=(0, 16))

timetable_status_var = tk.StringVar(value=" 隤脰”嚗尠�?)

tk.Label(tt_top, textvariable=timetable_status_var, font=THEME["font_bold"], bg=THEME["bg_card"]).pack(side="left", padx=(16,10), pady=12)

timetable_next_var = tk.StringVar(value=" 銝衤?甈∴???)

tk.Label(tt_top, textvariable=timetable_next_var, font=THEME["font_s"], bg=THEME["bg_card"], fg=THEME["fg_sub"]).pack(side="left", padx=(6,10))

timetable_path_var = tk.StringVar(value=f"頝臬?嚗㝯TIMETABLE_PATH}")

tk.Label(tt_top, textvariable=timetable_path_var, font=THEME["font_s"], bg=THEME["bg_card"], fg=THEME["fg_sub"]).pack(side="left", padx=(6,10))



def _tt_enable():

    handle_msg("ScheduleEnable", ("?祆?",))

def _tt_disable():

    handle_msg("ScheduleDisable", ("?祆?",))

def _tt_reload():

    handle_msg("ScheduleReload", ("?祆?",))

    _load_timetable_from_disk(); update_next_label()



tk.Button(tt_top, text="?毺鍂",  command=_tt_enable,  bg="#D1FAE5", relief="flat", font=THEME["font_s"]).pack(side="right", padx=4)

tk.Button(tt_top, text="?𦦵鍂",  command=_tt_disable,  bg="#FEE2E2", relief="flat", font=THEME["font_s"]).pack(side="right", padx=4)

tk.Button(tt_top, text="?齿鰵頛匧�", command=_tt_reload, bg="#F1F5F9", relief="flat", font=THEME["font_s"]).pack(side="right", padx=(4, 16))



tt_mid = tk.Frame(tab_tt, bg=THEME["bg_root"]); tt_mid.pack(expand=True, fill="both", padx=0, pady=(0,16))

columns = ("idx","when","action","label")

tt_tree = ttk.Treeview(tt_mid, columns=columns, show="headings", height=10)

tt_tree.heading("idx", text="#")

tt_tree.heading("when", text="?�?嚗㇄OW/?交?嚗?)

tt_tree.heading("action", text="?蓥?")

tt_tree.heading("label", text="璅嗵惜")

tt_tree.column("idx", width=42, anchor="center")

tt_tree.column("when", width=154, anchor="w")

tt_tree.column("action", width=266, anchor="w")

tt_tree.column("label", width=182, anchor="w")

tt_tree.pack(side="left", expand=True, fill="both")

tt_scroll = ttk.Scrollbar(tt_mid, orient="vertical", command=tt_tree.yview); tt_tree.configure(yscroll=tt_scroll.set); tt_scroll.pack(side="left", fill="y")



def _fmt_item(it):

    if it.get("date"):

        when = f"{it['date']} {it.get('time','--:--')}"

    else:

        dow = int(it.get("dow",0))

        dowmap = {1:"Mon",2:"Tue",3:"Wed",4:"Thu",5:"Fri",6:"Sat",7:"Sun"}

        when = f"{dowmap.get(dow,'?')} {it.get('time','--:--')}"

    return when



def refresh_timetable_tree():

    for i in tt_tree.get_children():

        tt_tree.delete(i)

    items = timetable_data.get("items", [])

    for i, it in enumerate(items):

        tt_tree.insert("", "end", values=(i, _fmt_item(it), it.get("action",""), it.get("label","")))

    update_next_label()



def _tt_play_selected():

    sel = tt_tree.selection()

    if not sel:

        messagebox.showinfo("隤脰”", "隢见??豢?銝�蝑�??剜𦆮")

        return

    idx = int(tt_tree.item(sel[0])["values"][0])

    timetable_play_index(idx)



tt_bottom = tk.Frame(tab_tt, bg=THEME["bg_root"]); tt_bottom.pack(fill="x", padx=0, pady=(0,16))

tk.Button(tt_bottom, text="?剜𦆮?�??, command=_tt_play_selected, bg="#DBEAFE", relief="flat", font=THEME["font_s"]).pack(side="left", padx=4)

tk.Button(tt_bottom, text="?齿鰵?渡?", command=refresh_timetable_tree, bg="#F1F5F9", relief="flat", font=THEME["font_s"]).pack(side="left", padx=4)



# ---- Tab 3:  瑼娍?/銝𠰴� ----

# ---- Tab 3:  瑼娍?/銝𠰴� ----

tab_files = tk.Frame(notebook, bg=THEME["bg_root"]); notebook.add(tab_files, text=" 瑼娍?/銝𠰴�")

files_top = tk.Frame(tab_files, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1)

files_top.pack(fill="x", padx=0, pady=(0, 16))

tk.Label(files_top, text=" 銝𠰴�?桅?嚗?, font=THEME["font_bold"], bg=THEME["bg_card"]).pack(side="left", padx=(16,0), pady=12)

tk.Label(files_top, text=UPLOAD_DIR, font=("Consolas", 8), bg=THEME["bg_card"], fg=THEME["fg_sub"]).pack(side="left", padx=(6,10))



def _open_folder(path):

    try:

        if os.name == "nt":

            os.startfile(path)  # type: ignore

        elif sys.platform == "darwin":

            subprocess.Popen(["open", path])

        else:

            subprocess.Popen(["xdg-open", path])

    except Exception as e:

        messagebox.showerror("?见?鞈�?憭?, f"?⊥??见?嚗㝯e}")



tk.Button(files_top, text="?见?鞈�?憭?, command=lambda:_open_folder(UPLOAD_DIR), bg="#F1F5F9", relief="flat", font=THEME["font_s"]).pack(side="right", padx=(4, 16))



files_mid = tk.Frame(tab_files, bg=THEME["bg_root"]); files_mid.pack(expand=True, fill="both", padx=0, pady=(0,16))

fcols = ("name","size","mtime")

files_tree = ttk.Treeview(files_mid, columns=fcols, show="headings", height=10)

files_tree.heading("name", text="瑼𥪜?")

files_tree.heading("size", text="憭批?")

files_tree.heading("mtime", text="靽格㺿?�?")

files_tree.column("name", width=392, anchor="w")

files_tree.column("size", width=84, anchor="e")

files_tree.column("mtime", width=140, anchor="w")

files_tree.pack(side="left", expand=True, fill="both")

fscroll = ttk.Scrollbar(files_mid, orient="vertical", command=files_tree.yview); files_tree.configure(yscroll=fscroll.set); fscroll.pack(side="left", fill="y")



def _fmt_size(n):

    try:

        n = int(n)

        for unit in ["B","KB","MB","GB"]:

            if n < 1024: return f"{n} {unit}"

            n //= 1024

        return f"{n} TB"

    except:

        return str(n)



def refresh_files():

    for i in files_tree.get_children():

        files_tree.delete(i)

    try:

        items = []

        for base in os.listdir(UPLOAD_DIR):

            if not base.lower().endswith(".mp3"): continue

            p = os.path.join(UPLOAD_DIR, base)

            st = os.stat(p)

            items.append((base, st.st_size, datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")))

        items.sort(key=lambda x: x[0].lower())

        for name, size, mtime in items:

            files_tree.insert("", "end", values=(name, _fmt_size(size), mtime))

    except Exception as e:

        messagebox.showerror("瑼娍??𡑒”", str(e))



def _play_selected_file():

    sel = files_tree.selection()

    if not sel:

        messagebox.showinfo("?剜𦆮", "隢见??豢?銝�擐?MP3")

        return

    name = files_tree.item(sel[0])["values"][0]

    path = os.path.join(UPLOAD_DIR, name)

    threading.Thread(target=handle_msg, args=(f"PlayMP3:{path}", ("?祆?",)), daemon=True).start()



def _delete_selected_file():

    sel = files_tree.selection()

    if not sel:

        messagebox.showinfo("?芷膄", "隢见??豢?銝�擐?MP3")

        return

    name = files_tree.item(sel[0])["values"][0]

    path = os.path.join(UPLOAD_DIR, name)

    if not messagebox.askyesno("?芷膄", f"蝣箏??芷膄瑼娍?嚗㝯name}嚗?):

        return

    try:

        os.remove(path)

        refresh_files()

    except Exception as e:

        messagebox.showerror("?芷膄憭望?", str(e))



def _upload_from_local():

    ps = filedialog.askopenfilenames(title="?豢? MP3 銝𠰴�", filetypes=[("MP3", "*.mp3")])

    for p in ps or []:

        try:

            dst = os.path.join(UPLOAD_DIR, os.path.basename(p))

            if os.path.abspath(p) != os.path.abspath(dst):

                shutil.copy2(p, dst)

        except Exception as e:

            messagebox.showerror("銝𠰴�憭望?", f"{os.path.basename(p)}嚗㝯e}")

    refresh_files()



files_bottom = tk.Frame(tab_files, bg=THEME["bg_root"]); files_bottom.pack(fill="x", padx=0, pady=(0,16))

tk.Button(files_bottom, text="?齿鰵?渡?", command=refresh_files, bg="#F1F5F9", relief="flat", font=THEME["font_s"]).pack(side="left", padx=4)

tk.Button(files_bottom, text="?剜𦆮?�??, command=_play_selected_file, bg="#DBEAFE", relief="flat", font=THEME["font_s"]).pack(side="left", padx=4)

tk.Button(files_bottom, text="?芷膄?�??, command=_delete_selected_file, bg="#FEE2E2", relief="flat", font=THEME["font_s"]).pack(side="left", padx=4)

tk.Button(files_bottom, text="敺墧𧋦璈蠘?鋆賢� uploads", command=_upload_from_local, bg="#F1F5F9", relief="flat", font=THEME["font_s"]).pack(side="left", padx=4)



# ---- Tab 4:  ?芾??垍? ----

# ---- Tab 4:  ?芾??垍? ----

tab_sched = tk.Frame(notebook, bg=THEME["bg_root"]); notebook.add(tab_sched, text=" ?芾??垍?")

sched_top = tk.Frame(tab_sched, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1)

sched_top.pack(fill="x", padx=0, pady=(0, 16))

sched_status_var = tk.StringVar(value="銝衤?甈∴???)

tk.Label(sched_top, text="?芾??垍?嚗?schedules.json嚗?, font=THEME["font_bold"], bg=THEME["bg_card"]).pack(side="left", padx=(16,12), pady=12)

tk.Label(sched_top, textvariable=sched_status_var, font=THEME["font_s"], bg=THEME["bg_card"], fg=THEME["fg_sub"]).pack(side="left")



def _open_sched_file():

    SCHEDULES_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not SCHEDULES_PATH.exists():

        SCHEDULES_PATH.write_text("[]", encoding="utf-8")

    _open_folder(SCHEDULES_PATH.parent.as_posix())



tk.Button(sched_top, text="?见?鞈�?憭?, command=_open_sched_file, bg="#F1F5F9", relief="flat", font=THEME["font_s"]).pack(side="right", padx=(4, 16))



sched_mid = tk.Frame(tab_sched, bg=THEME["bg_root"]); sched_mid.pack(expand=True, fill="both", padx=0, pady=(0,16))

scols = ("id","title","time","days","jitter","type","payload","enabled","date")

sched_tree = ttk.Treeview(sched_mid, columns=scols, show="headings", height=9)

for c, t, w, a in [

    ("id","ID",84,"w"),

    ("title","璅䠷?",154,"w"),

    ("time","?�?",70,"center"),

    ("days","憭拇彍",70,"w"),

    ("jitter","?�榆(s)",56,"e"),

    ("type","憿𧼮?",56,"center"),

    ("payload","?批捆",252,"w"),

    ("enabled","?毺鍂",42,"center"),

    ("date","?交?",84,"center"),

]:

    sched_tree.heading(c, text=t); sched_tree.column(c, width=w, anchor=a)

sched_tree.pack(side="left", expand=True, fill="both")

sscroll = ttk.Scrollbar(sched_mid, orient="vertical", command=sched_tree.yview); sched_tree.configure(yscroll=sscroll.set); sscroll.pack(side="left", fill="y")



def _days_to_text(days):

    if not days: return ""

    m = {1:"Mon",2:"Tue",3:"Wed",4:"Thu",5:"Fri",6:"Sat",7:"Sun"}

    return ",".join(m.get(int(d), str(d)) for d in days)



def refresh_sched_tree():

    for i in sched_tree.get_children():

        sched_tree.delete(i)

    items = _load_schedules_from_disk()

    for it in (items or []):

        sched_tree.insert("", "end", values=(

            it.get("id",""), it.get("title",""), it.get("time",""),

            _days_to_text(it.get("days") or []), it.get("jitter",""),

            it.get("type",""), it.get("payload",""),

            "Yes" if it.get("enabled", True) else "No",

            it.get("date","")

        ))

    # ?湔鰵?䔶?銝�甈～�滨???

    st = _compute_next_schedule_status(items)

    if st.get("has_next"):

        nxt = st["next"]

        sched_status_var.set(f"銝衤?甈∴?{nxt.get('at')}嚚画nxt.get('title') or nxt.get('payload')}")

    else:

        sched_status_var.set("銝衤?甈∴???)



def _sched_play_selected():

    sel = sched_tree.selection()

    if not sel:

        messagebox.showinfo("?垍?", "隢见??豢?銝�蝑�?閫貊䔄")

        return

    row = sched_tree.item(sel[0])["values"]

    payload = row[6]

    typ = row[5]

    if typ == "sendmp3":

        handle_msg(f"PlayMP3:{payload}", ("?祆?",))

    else:

        handle_msg(str(payload), ("?祆?",))



sched_bottom = tk.Frame(tab_sched, bg=THEME["bg_root"]); sched_bottom.pack(fill="x", padx=0, pady=(0,16))

tk.Button(sched_bottom, text="?齿鰵?渡?", command=refresh_sched_tree, bg="#F1F5F9", relief="flat", font=THEME["font_s"]).pack(side="left", padx=4)

tk.Button(sched_bottom, text="蝡见朖閫貊䔄?�??, command=_sched_play_selected, bg="#DBEAFE", relief="flat", font=THEME["font_s"]).pack(side="left", padx=4)



# ---- Tab 5: 閮剖? ----
tab_settings = tk.Frame(notebook, bg=THEME["bg_root"]); notebook.add(tab_settings, text=" 閮剖?")

settings_frame = tk.Frame(tab_settings, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1)
settings_frame.pack(fill="x", padx=16, pady=16)

tk.Label(settings_frame, text="蝟餌絞閮剖?", font=THEME["font_bold"], bg=THEME["bg_card"]).pack(anchor="w", padx=16, pady=(12, 6))

# AI Generation Toggle
ai_gen_var = tk.BooleanVar(value=config.get("use_ai_generation", True))

def _on_ai_gen_change(*args):
    config["use_ai_generation"] = ai_gen_var.get()
    save_config(config)
    # Update global fallback if needed
    global USE_AI_GENERATION
    USE_AI_GENERATION = ai_gen_var.get()

ai_gen_var.trace_add("write", _on_ai_gen_change)

chk_ai = tk.Checkbutton(settings_frame, text="?毺鍂 AI 撱?偘蝔輻???(?�摰㕑? Ollama)", variable=ai_gen_var, bg=THEME["bg_card"], font=THEME["font_main"])
chk_ai.pack(anchor="w", padx=16, pady=(0, 12))

tk.Label(settings_frame, text="隤芣?嚗朞𥅾?𦦵鍂甇文??踝?撠�??�摰㕑? Ollama 璅∪?嚗屸�?�??滨蔭?餉�雿輻鍂??, font=THEME["font_s"], fg=THEME["fg_sub"], bg=THEME["bg_card"]).pack(anchor="w", padx=36, pady=(0, 16))



# ===== ?勗??望??湔鰵 =====

def _tick_every_5s():

    try:

        update_next_label()

        # ?湔鰵?芾??垍??䔶?銝�甈～�?

        items = _load_schedules_from_disk()

        st = _compute_next_schedule_status(items)

        if st.get("has_next"):

            nxt = st["next"]

            sched_status_var.set(f"銝衤?甈∴?{nxt.get('at')}嚚画nxt.get('title') or nxt.get('payload')}")

        else:

            sched_status_var.set("銝衤?甈∴???)

    finally:
        if not DISABLE_GUI and root:
            root.after(5000, _tick_every_5s)

if not DISABLE_GUI and root:
    root.after(5000, _tick_every_5s)



# ===============================
# [Cleaned up duplicate startup logic]


# ===============================



# [NEW ROUTES for Web UI Consistency]
# ===============================
# == [ANCHOR] Web UI Controller API (V2 Bypass) ==
# ===============================

@app.route('/controller/api/clients_v2', methods=['GET'])
def controller_api_clients_v2():
    """Return list of connected student clients (V2)."""
    try:
        # Convert students_clients dict to list
        # students_clients structure: {id: {ip, port, group, mac, hostname, last_seen}}
        client_list = {}
        online_count = 0
        now_ts = datetime.now()
        
        with students_lock:
            for cid, info in students_clients.items():
                # Check if online (e.g. seen within last 60 seconds)
                is_online = (now_ts - info['last_seen']).total_seconds() < 60
                if is_online: online_count += 1
                
                client_list[cid] = {
                    "ip": info.get("ip"),
                    "hostname": info.get("hostname"),
                    "group": info.get("group"),
                    "mac": info.get("mac"),
                    "last_seen_str": info['last_seen'].strftime("%H:%M:%S"),
                    "online": is_online
                }
                
        return jsonify(ok=True, clients=client_list, online_count=online_count)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

@app.route('/controller/api/send_v2', methods=['POST'])
def controller_api_send_v2():
    """Send command to specific targets (V2)."""
    try:
        data = request.get_json(force=True) or {}
        targets = data.get("targets", []) # List of Client IDs
        cmd = data.get("cmd", "")
        url = data.get("url", "")
        
        if not targets or not cmd:
            return jsonify(ok=False, error="Missing targets or cmd"), 400
            
        count = 0
        
        real_cmd = cmd
        real_args = url
        
        if cmd == "wol":
            # Handle WOL separately
            for cid in targets:
                mac = ""
                with students_lock:
                    if cid in students_clients:
                        mac = students_clients[cid].get("mac", "")
                
                if mac:
                    send_magic_packet(mac)
                    count += 1
            return jsonify(ok=True, count=count)

        # For other commands, use send_student_udp_command with TARGET={id}
        for cid in targets:
            ip = "255.255.255.255"
            port = STUDENT_UDP_CMD_PORT
            
            with students_lock:
                if cid in students_clients:
                    ip = students_clients[cid].get("ip", ip)
                    port = students_clients[cid].get("port", port)
            
            payload_cmd = f"TARGET={cid}|{real_cmd}"
            
            # Use client_id argument to try WS first
            if send_student_udp_command(ip, port, payload_cmd, real_args, client_id=cid):
                count += 1
                
        return jsonify(ok=True, count=count)
        
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500
# [Duplicate Routes Deleted]

def run_web_server():
    print("\n" + "[*] " + "="*50)
    print(">>> [SYSTEM] Translation Engine Updated (V2) <<<")
    print(">>> 蝟餌絞?笔??𣂼? (?�𧋦 V1214.01-FINAL) <<<")
    print(f">>> 蝬脤?隞钅𢒰嚗冴ttp://localhost:{HTTP_PORT} <<<")
    print("[*] " + "="*50 + "\n")
    
    if DISABLE_WEB:
        text_area_insert(" DISABLE_WEB=True嚗峕𧊋?笔? Flask??, "Web")
        return
    host = "0.0.0.0"; port = HTTP_PORT

    try:
        text_area_insert(f" Flask 隡箸??典???(?舀螱 WebSocket)嚗冴ttp://{host}:{port}", "Web")
        app.run(host=host, port=port, threaded=True, use_reloader=False)
    except Exception as e:
        text_area_insert(f"??Web 隡箸??典??訫仃?梹?{e}", "Web")

# [Self-Check] Edge TTS Repair Utility
def _check_and_repair_edge_tts():
    try:
        print(">>> [Self-Check] 甇?銁瑼Ｘ䰻 Edge TTS 撘閙????...")
        STATE["edge_tts_status"] = "Testing..."
        import edge_tts, asyncio, os, tempfile
        async def _test():
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name
            try:
                c = edge_tts.Communicate("Hi", "zh-TW-YunJheNeural")
                await c.save(tmp_path)
                if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                    return True
                else:
                    return False
            finally:
                try: os.remove(tmp_path)
                except: pass
        
        loop = asyncio.new_event_loop()
        ok = loop.run_until_complete(_test())
        loop.close()

        if ok:
            print(">>> [Self-Check] Edge TTS ?衤?甇?虜 (OK)")
            STATE["edge_tts_status"] = "OK"
        else:
            raise Exception("Output file empty or missing")
        
    except Exception as e:
        print(f">>> [Self-Check] Edge TTS ?啣虜 ({e})嚗峕迤?刻?隡唬耨敺拇䲮獢?..")
        STATE["edge_tts_status"] = f"Error: {str(e)[:15]}"
        
        if getattr(sys, "frozen", False):
            print(">>> [Packaged App] Edge TTS Check Failed (SSL/Network).")
            STATE["edge_tts_status"] = "Error (Frozen)"
        else:
            try:
                STATE["edge_tts_status"] = "Repairing..."
                subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "edge-tts"])
                print(">>> [Self-Repair] Edge TTS 靽桀儔摰峕?嚗�??滚??厩鍂蝔见?隞亦??��?)
                STATE["edge_tts_status"] = "Fixed"
            except Exception as e2:
                print(f">>> [Self-Repair] ?芸?靽桀儔憭望?: {e2}")
                STATE["edge_tts_status"] = "Fix Failed"

# [Monitor] Fire Alarm Hardware
class FireAlarmMonitor:
    def __init__(self, port, pin="CTS"):
        self.port = port
        self.pin = pin.upper()
        self.running = False
        self.ser = None
        self.triggered = False

    def start(self):
        if not self.port: return
        self.running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        print(f"[Fire] Monitor started on {self.port} (Pin: {self.pin})")
        from serial.tools import list_ports
        last_missing_log = 0
        while self.running:
            try:
                params = [p.device for p in list_ports.comports()]
                if self.port not in params:
                    if time.time() - last_missing_log > 60:
                        print(f"[Fire] Port {self.port} not found. Available: {params}")
                        last_missing_log = time.time()
                    time.sleep(5); continue
                import serial
                if not self.ser:
                    try:
                        self.ser = serial.Serial(self.port, 9600, timeout=1)
                        self.ser.dtr = True; self.ser.rts = True
                        print(f"[Fire] Port {self.port} opened successfully.")
                    except Exception as e:
                        print(f"[Fire] Failed to open {self.port}: {e}")
                        time.sleep(5); continue
                is_active = False
                try:
                    if self.pin == "CTS": is_active = self.ser.cts
                    elif self.pin == "DSR": is_active = self.ser.dsr
                    else: is_active = self.ser.cts
                except Exception as e:
                    print(f"[Fire] Port read error: {e}")
                    try: self.ser.close(); self.ser = None
                    except: pass
                    continue
                if is_active:
                    if not self.triggered:
                        self.triggered = True
                        print(f"[Fire] ALARM TRIGGERED!")
                        threading.Thread(target=handle_msg, args=("ShowMsg:?鞟�?質郎?晞�穃�皜砍�?怎�閮𡃏?嚗?, ("System", "Fire")), daemon=True).start()
                else:
                    if self.triggered:
                        print(f"[Fire] Alarm Reset")
                        self.triggered = False
                time.sleep(0.5)
            except Exception as e:
                print(f"[Fire] Error: {e}")
                if self.ser:
                    try: self.ser.close()
                    except: pass
                    self.ser = None
                time.sleep(5)

# Startup Sequence
try:
    if '_load_timetable_from_disk' in globals(): _load_timetable_from_disk()

    # Worker Threads
    threading.Thread(target=speech_worker, daemon=True).start()
    threading.Thread(target=youtube_worker, daemon=True).start()
    threading.Thread(target=mp3_worker, daemon=True).start()
    if '_cwa_bg_loop' in globals(): threading.Thread(target=_cwa_bg_loop, daemon=True).start()
    if 'timetable_scheduler_loop' in globals(): threading.Thread(target=timetable_scheduler_loop, daemon=True).start()
    if 'schedules_scheduler_loop' in globals(): threading.Thread(target=schedules_scheduler_loop, daemon=True).start()

    if not DISABLE_UDP:
        threading.Thread(target=udp_listener, daemon=True).start()
    else:
        text_area_insert(" UDP ?交𤣰撌脣??剁?DISABLE_UDP=True嚗?, "UDP")

    # Student Threads
    if 'student_udp_listener' in globals(): threading.Thread(target=student_udp_listener, daemon=True).start()
    if 'student_broadcast_discover' in globals(): threading.Thread(target=student_broadcast_discover, daemon=True).start()

    # GUI specific initialization
    if not DISABLE_GUI and root:
        def _init_lists_once():
            try:
                if 'refresh_timetable_tree' in globals(): refresh_timetable_tree()
                if 'refresh_files' in globals(): refresh_files()
                if 'refresh_sched_tree' in globals(): refresh_sched_tree()
            except Exception: pass

        root.after(200, _init_lists_once)
        if '_auto_watch_timetable' in globals(): root.after(30000, _auto_watch_timetable)
        if '_auto_watch_schedules' in globals(): root.after(30000, _auto_watch_schedules)
        if '_apply_button_hover' in globals(): root.after(400, lambda: _apply_button_hover(root))
        if 'start_ngrok' in globals() and USE_NGROK: root.after(2500, start_ngrok)

        def _on_close():
            try: _cleanup()
            finally: root.destroy()
        root.protocol("WM_DELETE_WINDOW", _on_close)

    # Edge TTS Self-Check
    threading.Thread(target=_check_and_repair_edge_tts, daemon=True).start()

    # Cleanup logic
    def _cleanup():
        try:
            if 'students_stop_event' in globals(): students_stop_event.set()
        except Exception: pass
        try:
            if 'stop_ngrok' in globals(): stop_ngrok()
        except Exception: pass
        try:
            with MIXER_LOCK:
                pygame.mixer.quit()
        except Exception: pass
    atexit.register(_cleanup)

    # Fire Monitor (Hardware specific, skip on Render/Linux)
    if FIRE_ALARM_PORT and FIRE_ALARM_PORT != "COM5" and not IS_LINUX:
        # Define the monitor class locally if needed or use existing one
        try:
            _fire_monitor = FireAlarmMonitor(FIRE_ALARM_PORT, FIRE_ALARM_PIN)
            _fire_monitor.start()
        except NameError: pass

    # Execution Entry
    if DISABLE_GUI:
        # Headless mode: Run web server in main thread (blocks)
        run_web_server()
    else:
        # GUI mode: Run web server in background, block on mainloop
        threading.Thread(target=run_web_server, daemon=True).start()
        root.mainloop()

except Exception as e:
    import traceback
    err_msg = "".join(traceback.format_exception(None, e, e.__traceback__))
    print(f"Startup Error: {e}")
    try:
        with open("startup_error.log", "w", encoding="utf-8") as f:
            f.write(f"Timestamp: {datetime.now()}\n")
            f.write(err_msg)
    except: pass
    if not DISABLE_GUI:
        input("Press Enter to exit...")

