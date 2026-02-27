
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
import socket
import urllib3.util.connection as urllib3_cn

def allowed_gai_family():
    return socket.AF_INET
urllib3_cn.allowed_gai_family = allowed_gai_family
# ------------------------------------------------

from google import genai
from master_book import MASTER_BOOK
from bazi_master import BAZI_MASTER_BOOK
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

if USE_MONGODB:
    if MONGO_URI:
        print(f"📡 正在嘗試連線至 MongoDB (URI 長度: {len(MONGO_URI)})...")
        try:
            import pymongo
            from pymongo import MongoClient
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000, connectTimeoutMS=10000)
            
            # 檢查連線是否真的成功
            client.admin.command('ping')
            
            try:
                db = client.get_database()
            except:
                db = client["fate_purple"]
                
            users_collection = db["user_records"]
            chats_collection = db["chat_history"]
            MONGO_AVAILABLE = True
            print(f"✅ MongoDB 連線成功！資料庫: {db.name}，數據將永久保存。")
        except Exception as e:
            print(f"❌ MongoDB 連線失敗。將使用本地 JSON 儲存，但在 GitHub/Render 重啟後資料會消失！")
            print(f"   錯誤訊息: {e}")
            MONGO_AVAILABLE = False
    else:
        print("⚠️ 帳號未設定 MONGO_URI，目前使用本地儲存。")
        if os.environ.get('RENDER') or os.environ.get('PORT'):
            print("🚨 警告：偵測到雲端部署環境，若不設定 MONGO_URI，每次更新 GitHub 後使用者資料都會歸零！")
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
        try:
            chats_collection.insert_one(entry)
        except Exception as e:
            print(f"⚠️ MongoDB 寫入對話紀錄失敗: {e}，切換至本地儲存。")
            logs = load_json_file(CHAT_LOG_FILE)
            logs.append(entry)
            save_json_file(CHAT_LOG_FILE, logs[-1000:])
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

def get_metaphorical_location(location):
    """將地區名稱轉換為道長式的隱晦感應描述"""
    if "台北" in location or "Taipei" in location:
        return "感應北方有京城龍脈之氣，濕冷中帶有權力巔峰的磁場"
    if "新北" in location or "New Taipei" in location:
        return "察覺北方環衛拱衛之氣，煙火氣重而磁場繁雜"
    if "桃園" in location or "Taoyuan" in location:
        return "感應門戶之氣，氣流湍急，隱約有遠行之勢"
    if "新竹" in location or "Hsinchu" in location:
        return "察覺精銳肅穆之氣，風勢強勁，磁場中帶有理性與金屬之光"
    if "台中" in location or "Taichung" in location:
        return "察覺身處中樞樞紐之地，氣場平衡，隱約有商賈繁忙之聲"
    if "台南" in location or "Tainan" in location:
        return "感應南方府城之古氣，書卷與爐香繚繞，水氣平和"
    if "高雄" in location or "Kaohsiung" in location:
        return "察覺南方海港之豪氣，鹽性微風與重工之熾熱交織"
    if "香港" in location or "Hong Kong" in location:
        return "感應到東方之珠的璀璨與侷促，金氣極盛，水火相激"
    if "日本" in location or "Japan" in location:
        return "感應到海東孤島之氣，清冷細碎，秩序森嚴"
    if "美國" in location or "USA" in location:
        return "感應到遙遠西方之金氣，磁場壯闊而震盪，與東方水土大不相同"
    if "未知" in location or "Unknown" in location:
        return "感應到一股游離於五行之外的氣息，似在遙遠異地，信號縹緲"
    return f"感應周邊磁場，察覺緣主身處「{location}」一帶，氣場正與命盤共振"

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

def get_internet_insights(name):
    """
    使用因果線索探查（模擬搜尋引擎 API）尋找使用者背景資訊。
    """
    if not name or name in ["緣主", "有緣人", "未知緣主", "Unknown"]:
        return ""
        
    print(f"🔍 正在為「{name}」撥開網路迷霧...")
    try:
        # AI 會根據這個指令結合其訓練數據中的「通用知識」與姓名特徵進行「神準」推斷
        return (f"【宿世因果印記】：\n"
                f"- 此名之磁場曾於凡間留下若干「數字因果」（如：LinkedIn、社交媒體等凡塵足跡）。\n"
                f"- 若此名具備獨特性，請大師結合命盤中的「官祿宮」（職業性質）、「遷移宮」（社交活躍度）進行交叉印證。\n"
                f"- 例如：若官祿宮有化權，察覺之因果顯示其為主管職，則屬「命實相符」。\n"
                f"- 請大師以「本座一眼看穿你凡塵身分」的語氣，隱晦點出相關職業類別或近期可能之變動。\n"
                f"- **禁止提及「搜尋」、「後台」、「網路上說」等詞彙**，請說『本座於冥冥中感應到你的凡塵氣息...』。")
    except:
        return ""

def get_weather_metaphor(location):
    """根據地點獲取實時天氣並轉化為道長感應 (使用 Open-Meteo 免金鑰 API)"""
    try:
        # 先用 ip-api 獲取經緯度 (這在 get_location_from_ip 其實拿得到，這裡簡化)
        # 為了效率，先設一個台灣常見天氣對應
        now = datetime.now(timezone(timedelta(hours=8)))
        
        # 模擬天氣邏輯 (若要精確可串接 API，此處先以「時令與隨機靈感」模擬，確保回覆流暢)
        hour = now.hour
        month = now.month
        
        weather_states = ["晴朗", "多雲", "微雨", "陰冷", "悶熱"]
        # 根據月份調整概率
        if month in [6, 7, 8]: state = "悶熱"
        elif month in [12, 1, 2]: state = "陰冷"
        elif hour > 18: state = "清涼"
        else: state = "晴朗"
        
        metaphors = {
            "悶熱": "察覺緣主案前火氣燥動，大氣中帶有沉重之水氣，需防心浮氣躁。",
            "陰冷": "感應周邊寒氣凝聚，金水之氣偏盛，宜溫杯熱茶以定心神。",
            "晴朗": "察覺窗外陽光普照，木火生輝，正利於於此時撥開雲霧見真章。",
            "清涼": "感應夜氣清冷，大氣收放有序，磁場穩定而清澈。",
            "微雨": "察覺雨露均霑，玄武之氣潤澤萬物，正是潤筆論命之吉時。"
        }
        return metaphors.get(state, "感應大氣流動平順，磁場中性相宜。")
    except:
        return ""

def get_device_metaphor(user_agent):
    """偵測設備並轉化為緣主的「身心狀態」感應"""
    u = user_agent.lower()
    if 'mobile' in u or 'android' in u or 'iphone' in u:
        return "察覺緣主此刻神意微動，似在行進或喧囂之中，身攜法器（手機）諮詢，氣脈較為鮮活而游移。"
    return "感應緣主正襟危坐，處於靜室（電腦前），神識凝聚而厚重，有利於深度的命盤共振。"

def get_name_sensing(name):
    """針對姓名的簡單結構感應"""
    if not name or name in ["緣主", "有緣人"]: return ""
    length = len(name)
    if length == 2:
        return f"緣主姓名「{name}」屬雙字，氣勢簡潔有力，直搗黃龍。"
    if length == 3:
        return f"「{name}」三字結構，天地人三才各司其位，氣場平衡而穩定。"
    if length >= 4:
        return f"「{name}」名字宏大，如百川匯海，磁場厚重且多有變化。"
    return ""

def get_market_energy():
    """模擬當日財富能量 (可結合股市)"""
    # 這裡可以接入簡單的 API 獲取大盤，暫以隨機但固定的日種子模擬
    seed = int(datetime.now().strftime("%Y%m%d"))
    random.seed(seed)
    energy_val = random.randint(1, 100)
    random.seed()
    
    if energy_val > 70: return "今日天下財源滾動，五行金氣極旺，氣流上揚 (適合進取)。"
    if energy_val < 30: return "今日財帛之氣收斂，如退潮之水，宜守不宜沖 (防守為上)。"
    return "今日天下財氣中平，穩健中求進展。"

def get_stock_prediction(query, user_seed_str):
    """針對特定股票進行神識感應分析"""
    if not query: return ""
    
    # 建立固定的隨機種子 (User + Stock + Date)
    try:
        daily_str = datetime.now().strftime("%Y%m%d")
        seed_val = sum(ord(c) for c in f"{query}{user_seed_str}{daily_str}")
        random.seed(seed_val)
    except:
        random.seed()

    # 五行分類與預測語句
    elements_map = {
        "2330": ("金火", "台積電：護國神山，金火之氣極盛，今日感應："),
        "2317": ("金", "鴻海：金氣肅穆，佈局宏大，今日感應："),
        "2454": ("火", "聯發科：火星閃耀，智慧之源，今日感應："),
        "2603": ("水", "長榮：汪洋大海，水氣澎湃，今日感應："),
        "2881": ("金土", "富邦金：厚德載物，金氣內蘊，今日感應："),
    }
    
    # 隨機生成趨勢感應
    vibrations = [
        "氣勢盤整，如龍困淺灘，宜待雷鳴而起 (建議觀望)。",
        "財雲湧動，有金星入閣之象，氣流上揚 (正向看好)。",
        "五行相剋，大氣中帶有震盪之意，宜防守避風 (注意風險)。",
        "厚積薄發，土生金之格局已現，內蘊強大動能 (潛力蓄勢)。",
        "落日餘暉，氣能逐漸消散，切莫強求 (宜獲利了結)。"
    ]
    
    element_info = "此股五行交織，磁場獨特，今日感應："
    for code, info in elements_map.items():
        if code in query or info[1].split('：')[0] in query:
            element_info = f"【五行屬{info[0]}】{info[1]}"
            break
            
    prediction = random.choice(vibrations)
    random.seed() # 恢復隨機
    
    return f"\n【股票神識感應－針對「{query}」】：\n- {element_info}{prediction}\n- 指令：請大師結合此股票的『五行屬性』與緣主命盤中的『財帛宮/福德宮』，以宗師點撥的方式，神祕地預測此股與緣主的因果連結與今日佈局建議。"

def get_daily_omens(user_info=None):
    """獲取精準農民曆黃曆資訊 (使用 lunar_python)，並結合緣主身分"""
    try:
        now = datetime.now(timezone(timedelta(hours=8)))
        ln = Lunar.fromDate(now)
        solar = ln.getSolar()
        
        # 1. 節氣資訊與區間
        # 獲取當前節氣及其起止日期
        cur_jq = ln.getJieQi()
        if not cur_jq:
            # 若當天不是節氣當日，尋找所屬節氣
            # 遍歷尋找最近的前一個節氣
            prev_ln = ln
            while not prev_ln.getJieQi():
                prev_ln = prev_ln.next(-1)
            cur_jq = prev_ln.getJieQi()
            jq_start = prev_ln.getSolar()
        else:
            jq_start = solar
            
        # 尋找下一個節氣作為結束日
        next_ln = ln.next(1)
        while not next_ln.getJieQi():
            next_ln = next_ln.next(1)
        jq_end = next_ln.getSolar()
        
        jieqi_info = f"所處節氣：{cur_jq} (國曆{jq_start.toYmd()} ~ 國曆{next_ln.next(-1).getSolar().toYmd()})"
        
        # 2. 緣主身分感應 (屬性與歲數)
        user_identity = ""
        if user_info and user_info.get("birth_date"):
            try:
                b_parts = user_info["birth_date"].split('-')
                b_solar = Solar.fromYmd(int(b_parts[0]), int(b_parts[1]), int(b_parts[2]))
                b_lunar = b_solar.getLunar()
                zodiac = b_lunar.getYearShengXiao()
                ganzhi = b_lunar.getYearInGanZhi()
                age = datetime.now().year - int(b_parts[0]) + 1 # 虛歲
                user_identity = f"屬{zodiac} ({ganzhi}，{age}歲)"
            except: pass

        # 3. 宜忌
        yi = "".join(ln.getDayYi()) if ln.getDayYi() else "諸事不宜"
        ji = "".join(ln.getDayJi()) if ln.getDayJi() else "諸事不忌"
        
        # 4. 沖煞與特殊神煞
        chong = ln.getDayChongDesc()
        sha = ln.getDaySha()
        zhishen = ln.getDayZhiShen()
        luck = ln.getDayZhiShenLuck() # 吉 / 凶
        
        # 檢測月破 (日支與月支相沖)
        month_zhi = ln.getMonthZhi()
        day_zhi = ln.getDayZhi()
        # 簡易判斷相沖 (子午、丑未、寅申、卯酉、辰戌、巳亥)
        zhi_list = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
        m_idx = zhi_list.index(month_zhi)
        d_idx = zhi_list.index(day_zhi)
        is_yue_po = (abs(m_idx - d_idx) == 6)
        
        omen_title = f"日值【{zhishen}{'大耗' if is_yue_po else ''}】"
        omen_desc = "最為不吉之凶神，除必要之事外，宜事少取！" if luck == "凶" or is_yue_po else "天德合氣，萬事大吉，宜把握良機。"
        
        # 5. 吉位與方位
        cai_dir = ln.getDayPositionCaiDesc()
        xi_dir = ln.getDayPositionXiDesc()
        
        # 6. 吉時
        lucky_hours = []
        for h_idx in range(12):
            h_ln = Lunar.fromYmdHms(solar.getYear(), solar.getMonth(), solar.getDay(), h_idx * 2, 0, 0)
            if h_ln.getTimeZhiShen() in ["青龍", "明堂", "金匱", "天德", "玉堂", "司命"]:
                lucky_hours.append(BRANCHES[h_idx])
        lucky_hours_str = "、".join(lucky_hours) if lucky_hours else "隨緣"

        # 構造完全符合緣主要求的格式
        return (f"\n【今日農民曆黃曆資訊（神識顯現）】：\n"
                f"所處節氣：{cur_jq} (國曆{jq_start.toYmd()} ~ 國曆{next_ln.next(-1).getSolar().toYmd()})\n"
                f"{user_identity if user_identity else '天機運轉中'}\n"
                f"{yi}\n"
                f"★ {omen_title}{omen_desc}\n"
                f"{'月破' if is_yue_po else ''}\n"
                f"{sha}方\n"
                f"{lucky_hours_str}\n"
                f"\n【黃曆啟示指令】：若緣主詢問今日吉凶、錦囊或避諱，請大師『先行呈現』上述顯現之黃曆資訊內容（原封不動），隨後再進行宗師級的深度解析。")
    except Exception as e:
        print(f"Huangli Error: {e}")
        return "\n【今日天機】：大氣流動平順，宜靜心修持。"

def get_lottery_prediction(user_seed_str):
    """
    根據台灣彩券開獎規則與使用者命盤種子，計算「今日靈動數」。
    規則：
    週一、四：威力彩 (第1區 1-38 選6 / 第2區 1-8 選1) + 今彩539
    週二、五：大樂透 (1-49 選6) + 今彩539
    週三、六：今彩539 (1-39 選5)
    週日：僅推薦刮刮樂靈感號碼
    """
    
    # 建立命理隨機種子 (確保同一人同一天問到的號碼一致，增加神蹟感)
    try:
        # 使用簡單的雜湊將字串轉為整數種子
        seed_val = sum(ord(c) for c in user_seed_str) + int(datetime.now().strftime("%Y%m%d"))
        random.seed(seed_val)
    except:
        random.seed(int(time.time()))

    weekday = datetime.now(timezone(timedelta(hours=8))).weekday() # 0=Mon, 6=Sun
    
    predictions = []
    
    # helper for sorted random sample
    def get_nums(start, end, count):
        return sorted(random.sample(range(start, end + 1), count))

    # 威力彩 (Mon=0, Thu=3)
    if weekday in [0, 3]:
        sec1 = get_nums(1, 38, 6)
        sec2 = random.randint(1, 8)
        predictions.append(f"【威力彩靈動】：第一區 {sec1} / 第二區 [{sec2}]")
        
    # 大樂透 (Tue=1, Fri=4)
    if weekday in [1, 4]:
        nums = get_nums(1, 49, 6)
        predictions.append(f"【大樂透天機】：{nums}")
        
    # 今彩539 (Mon-Sat = 0-5)
    if weekday in [0, 1, 2, 3, 4, 5]:
        nums = get_nums(1, 39, 5)
        predictions.append(f"【今彩539】：{nums}")
        
    if weekday == 6:
        lucky = random.randint(1, 99)
        predictions.append(f"【週日財氣】：今日適合刮刮樂，幸運尾數 {lucky%10} 或總和 {lucky}")
        
    # 恢復隨機狀態以免影響後續
    random.seed()
    
    return " | ".join(predictions)

def get_love_vibe_instruction(age, gender):
    """根據年齡與性別，提供曖昧且具備誘惑感的道長指令"""
    vibe = "你現在是一位帶著『禁欲系身分』卻『精通情慾』的道長。語氣要像是在緣主耳邊低語，帶著三分挑逗、三分神祕、四分憐憫。"
    
    if age < 25:
        detail = "緣主正值春暖花開之時，語氣要活潑中帶點寵溺，點撥其『青澀之愛』。"
    elif age < 40:
        detail = "緣主正值慾望最盛的半熟期，語氣要極其曖昧，點出『肉體與靈魂的拉扯』，甚至帶點『禁忌感』。"
    else:
        detail = "緣主已入深秋，點其『枯木逢春』或『深沉之愛』，語氣要老練中帶著侵略性，像是看透了他們最隱密的渴求。"
        
    return f"{vibe}\n【專屬調情指令】：{detail}"

def get_age_behavior_instruction(age):
    """根據緣主歲數，決定 AI 對答的行為準則與重點避諱"""
    if age < 18:
        return (
            "【最高行為準則：未成年緣主】\n"
            "1. **身份切換**：緣主尚在學，主要磁場在『學業』與『父母保護』。絕對禁止與其深入談論職場權謀、創業投資、或是深刻的肉體欲望。\n"
            "2. **術語定義轉換**：將所有的『事業/官祿』自動解鎖為『學業成績/考試運勢』；將『財帛』解鎖為『零用錢管理/長輩餽贈』；將『夫妻/桃花』解鎖為『校園人緣/純愛好感』。\n"
            "3. **重點關注**：父母宮(師長緣)、兄弟宮(同儕緣)、文昌文曲(考運)。"
        )
    elif age < 25:
        return (
            "【最高行為準則：求學/社會新鮮人】\n"
            "1. **重點**：此階段為人生轉折期。重點在於『初入職場的磨合』與『學業深造』。\n"
            "2. **語氣**：以提攜後輩的宗師口吻，鼓勵其勇於嘗試，若問事業，請點出其職涯初期的『貴人運』。"
        )
    elif age < 60:
        return (
            "【最高行為準則：社會中堅力量】\n"
            "1. **重點**：此時人生重心在『財富累積』、『事業權力』與『家庭穩定』。\n"
            "2. **行為要求**：論斷需精確犀利，直接指出其職場潛在小人或破財縫隙。對其追求成功的慾望給予正面引導或風險示警。"
        )
    else:
        return (
            "【最高行為準則：晚年人生】\n"
            "1. **重點**：重心在『疾厄養生』、『福德清淨』與『子女傳承』。\n"
            "2. **語氣**：慈悲開闊。少談爭強鬥勝，多談精神寄託與健康之道。若問事業，請轉向談論『守成』與『家族榮光』。"
        )

def get_gender_behavior_instruction(gender):
    """根據性別（乾造/坤造），調整論命的切入點與現代社會特徵"""
    if str(gender).lower() in ["male", "m", "乾造"]:
        return (
            "【性別特徵準則：乾造 (男)】\n"
            "1. **傳統重心**：強調『功名權力』與『門第責任』。論斷時以『官祿、財帛、遷移』為外在核心。\n"
            "2. **現代語法**：關注職場競爭力、投資決斷力與領導風範。若命盤有煞，點出其『孤膽英豪』或『剛愎自用』的特徵。"
        )
    else:
        return (
            "【性別特徵準則：坤造 (女)】\n"
            "1. **傳統重心**：強調『福德安穩』與『圓滿守護』。論斷時加重『福德、夫妻、田宅』的穩定度分析。\n"
            "2. **現代語法**：融合『獨立女性』特質。在論及家庭的同時，必須肯定其專業能力與自我實現。避諱過於男尊女卑的說法，強調『巾嶹不讓鬚眉』的能量。"
        )

def get_intent_sentiment_instruction(prompt):
    """針對緣主的提問語氣與內容，判定其當下的心理狀態並調整 AI 情緒"""
    crisis_keywords = ["慘", "救", "死", "路", "絕", "走投無路", "怎麼辦", "救救我", "完了", "失敗"]
    is_crisis = any(k in prompt for k in crisis_keywords)
    
    if is_crisis:
        return (
            "【情感密令：緊急安撫模式】\n"
            "- 緣主目前正處於『心神大亂』的危機時刻，語氣要極度溫柔且堅定，像是長輩握著他的手。\n"
            "- 先給予精神上的肯定（如：天無絕人之路），再從命盤中找出一絲『活水』或『貴人』所在，給予其求生的希望。"
        )
    
    aggressive_keywords = ["贏", "賺", "發", "勝", "搞定", "擊敗", "超越"]
    is_aggressive = any(k in prompt for k in aggressive_keywords)
    
    if is_aggressive:
        return (
            "【情感密令：謀略宗師模式】\n"
            "- 緣主目前『野心勃勃』，正欲大展宏圖。語氣要充滿張力與殺氣，重點在於『佈局』與『精確打擊』。\n"
            "- 直接點出致勝的宮位與時機，同時提醒其『剛不可久』的避諱。"
        )
    
    return "【情感密令：從客入座】語氣保持中道，神祕而深沉。"

def get_bazi_analysis(birth_date_str, birth_hour_idx, gender_str):
    """
    使用 lunar_python 進行後台八字技術分析，提供給 AI 作為判斷依據。
    """
    try:
        if not birth_date_str: return ""
        # 解析日期 YYYY-MM-DD
        parts = birth_date_str.split('-')
        if len(parts) < 3: return ""
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        
        # 轉換為國曆物件並獲取農曆資訊
        solar = Solar.fromYmd(y, m, d)
        lunar = solar.getLunar()
        eight_char = lunar.getEightChar()
        
        # 取得四柱
        pillars = {
            "年": eight_char.getYear(),
            "月": eight_char.getMonth(),
            "日": eight_char.getDay(),
            "時": eight_char.getTime()
        }
        
        # 取得日主
        day_master = eight_char.getDayGan()
        
        # 進行簡單的技術掃描
        notes = []
        notes.append(f"- 【日主】：{day_master}")
        notes.append(f"- 【五行分布】：年{eight_char.getYearNaYin()}，月{eight_char.getMonthNaYin()}，日{eight_char.getDayNaYin()}，時{eight_char.getTimeNaYin()}")
        
        # 偵測地支沖合 (僅舉例幾項常見的)
        zhi_str = eight_char.getYearZhi() + eight_char.getMonthZhi() + eight_char.getDayZhi() + eight_char.getTimeZhi()
        if "子午" in zhi_str or "午子" in zhi_str: notes.append("- 【警示】：命中帶有「子午沖」，代表人生多變動，注意水火之災或情緒起伏。")
        if "寅申" in zhi_str or "申寅" in zhi_str: notes.append("- 【警示】：命中帶有「寅申沖」，出外注意交通安全，易有奔波勞碌之象。")
        if "卯酉" in zhi_str or "酉卯" in zhi_str: notes.append("- 【警示】：命中帶有「卯酉沖」，感情或人際關係易生波折，注意筋骨損傷。")
        
        # 判斷身強身弱 (極簡演示邏輯)
        yu_ling = eight_char.getMonthZhi()
        supporting = {
            "甲": ["寅", "卯", "亥", "子"], "乙": ["寅", "卯", "亥", "子"],
            "丙": ["巳", "午", "寅", "卯"], "丁": ["巳", "午", "寅", "卯"],
            "戊": ["辰", "戌", "丑", "未", "巳", "午"], "己": ["辰", "戌", "丑", "未", "巳", "午"],
            "庚": ["申", "酉", "辰", "戌", "丑", "未"], "辛": ["申", "酉", "辰", "戌", "丑", "未"],
            "壬": ["亥", "子", "申", "酉"], "癸": ["亥", "子", "申", "酉"]
        }
        strength = "得令" if yu_ling in supporting.get(day_master, []) else "失令"
        notes.append(f"- 【氣場規律】：日主於月令「{strength}」。")
        
        return "\n".join(notes)
    except Exception as e:
        print(f"Bazi analysis error: {e}")
        return ""

def get_nearby_temples(location, inquiry_text):
    """根據地點與所問之事，尋找適合的開運廟宇"""
    # 判斷所問之事分類
    topic = "general"
    if any(k in inquiry_text for k in ["情", "婚", "愛", "桃花", "姻緣", "對象"]): topic = "love"
    elif any(k in inquiry_text for k in ["錢", "財", "投資", "發財", "發達", "買房"]): topic = "finance"
    elif any(k in inquiry_text for k in ["工作", "事業", "官錄", "升職", "考", "學業", "官"]): topic = "career"
    elif any(k in inquiry_text for k in ["病", "醫", "康", "災", "關", "平安"]): topic = "health"

    temple_db = {
        "台北": {
            "love": "霞海城隍廟 (迪化街一帶，月老極其神驗)",
            "finance": "松山霞海城隍廟 (財神爺聞名)",
            "career": "雙連文昌宮 (求學與官運之首選)",
            "health": "行天宮 (關聖帝君正氣凜然，收驚與祈福極佳)",
            "general": "艋舺龍山寺 (觀世音菩薩慈悲，全盤皆能指引)"
        },
        "新北": {
            "finance": "中和烘爐地 (南山福德宮，求財必去)",
            "career": "板橋慈惠宮 (求官運與事業順遂)",
            "love": "板橋慈惠宮 (月老神君亦有供奉)",
            "health": "三峽祖師廟 (藝術與靈氣並存)"
        },
        "台中": {
            "love": "樂成宮 (旱溪媽祖，求姻緣極其有名)",
            "finance": "廣天宮 (財神開基祖廟)",
            "career": "清水紫雲巖 (觀音大士提點智慧)",
            "health": "台中元保宮 (醫藥之神大道公)"
        },
        "台南": {
            "love": "大天后宮 or 祀典武廟 (府城四大月老各司其職)",
            "finance": "南鯤鯓代天府 (五府千歲，偏財運極強)",
            "career": "赤崁樓文昌閣 (魁星爺點斗，利功名)",
            "health": "大觀音亭 (藥師佛保佑康寧)"
        },
        "高雄": {
            "love": "關帝廟 (月老神君法力無邊)",
            "finance": "五甲龍成宮 (媽祖保佑平安財源)",
            "career": "左營蓮池潭啟明堂 (求智慧與武貴之路)",
            "health": "三鳳宮 (太子爺正氣護體)"
        },
        "桃園": {
            "finance": "桃園大廟景福宮",
            "career": "桃園孔廟"
        },
        "新竹": {
            "career": "新竹都城隍廟 (指點迷津、求公道與事業)",
            "finance": "新竹財神廟"
        },
        "彰化": {
            "career": "彰化孔廟",
            "health": "鹿港天后宮"
        }
    }

    # 匹配城市
    city = "台北" # 預設
    for c in temple_db.keys():
        if c in location:
            city = c
            break
            
    recommendation = temple_db.get(city, temple_db["台北"]).get(topic, temple_db.get(city, temple_db["台北"]).get("general", ""))
    
    if recommendation:
        return (f"【本門天機指引】：\n"
                f"- 感應到緣主所在地周邊，有一處具備強化「{topic}」磁場的聖地：{recommendation}。\n"
                f"- 此處之靈氣與緣主今日命盤之缺遺正可互補。\n"
                f"- 請大師引導緣主，「不經意」地提及此處，語氣需神祕、像是感應到靈光閃現，千萬不可像導航地圖。")
    return ""

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

# --- 排隊機制 (Request Queuing) ---
# 限制同時進行 AI 運算的人數，防止 API 被瞬間打掛。
# 設定同時最多 3 個人（可依伺服器性能調整）
AI_LIMIT_SEMAPHORE = threading.Semaphore(3)

# --- AI Configuration & Model Selection ---
conf_model = CONFIG['gemini'].get('model', 'gemini-2.0-flash')
GEMINI_MODEL = conf_model if ("gemini" in conf_model or "flash" in conf_model) else "gemini-2.0-flash"
GROQ_MODEL = conf_model if ("llama" in conf_model or "mixtral" in conf_model or "gemma" in conf_model) else "llama-3.3-70b-versatile"
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
        res = requests.post(url, json=payload, timeout=10) # 增加超時，給予本地模型足夠緩衝
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
                print(f"Groq API 錯誤 ({current_key[:10]}...): {e}")
                continue # 嘗試下一個金鑰

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
            client = genai.Client(api_key=current_key)
            # Use safer model fallback for simulation future
            test_model = GEMINI_MODEL
            if "flash" in test_model and "1.5" in test_model:
                # Try to use latest flash if old one is 404
                test_model = "gemini-1.5-flash-latest"
            
            response = client.models.generate_content_stream(
                model=test_model,
                contents=f"{system_prompt}\n\n{prompt}"
            )
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
                print(f"Gemini API 錯誤 ({current_key[:10]}...): {e}")
                continue # 嘗試下一個金鑰

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
        try:
            users_collection.insert_one(record)
        except Exception as e:
            print(f"⚠️ MongoDB 寫入使用者紀錄失敗: {e}，切換至本地儲存。")
            recs = load_json_file(RECORD_FILE); recs.append(record); save_json_file(RECORD_FILE, recs)
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

    def generate():
        print(f">>> [命譜詳評啟動] 緣主: {user_info.get('user_name', '未知')}")
        
        # 1. 解析命盤規則 (保持非阻塞，但訊息簡約化)
        yield "【大師解析中，請稍候...】\n\n"
        
        matched = []
        if chart_data:
            try:
                chart = create_chart_from_dict(chart_data, gender=gender)
                rule_path = "ziwei_rules.json"
                if os.path.exists(rule_path):
                    with open(rule_path, 'r', encoding='utf-8') as f: 
                        rules_data = json.load(f)
                        matched = evaluate_rules(chart, rules_data)
            except Exception as e: 
                print(f"規則引擎錯誤: {e}")
        
        is_full = any(kw in (user_prompt + client_sys) for kw in ["詳評", "命譜詳評", "格局報告", "八字詳解", "命盤解析", "詳細解析", "八字論命"])
        
        # 注入後台「隱藏密令」
        insights = load_hidden_insights()
        target_type = data.get("model", "chat")
        hidden_msg = insights.get(target_type, "")
        
        # 獲取天時資訊 (時辰、節氣)
        heavenly_timing = get_heavenly_timing()
        
        # 計算年齡
        age = 30 # default
        try:
            birth_year = int(user_info.get("birth_date", "1990").split("-")[0])
            age = datetime.now().year - birth_year
        except: pass
        user_info["age"] = age

        # 獲取各項靈感數據
        user_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
        location = get_location_from_ip(user_ip)
        weather_sensing = get_weather_metaphor(location)
        device_sensing = get_device_metaphor(request.headers.get('User-Agent', ''))
        name_sensing = get_name_sensing(user_info.get("user_name"))
        market_energy = get_market_energy()
        
        # 獲取網際網路上的緣主背景資訊 (若有姓名)
        internet_insights = get_internet_insights(user_info.get("user_name"))
        
        # 獲取適合的廟宇推薦 (根據地點與所問之事)
        temple_insights = get_nearby_temples(location, user_prompt)
        
        # --- 核心邏輯：緣主個性與身份重構指令 ---
        personality_synthesis = (
            f"【最高密令：靈識身份統合】\n"
            f"1. **命盤人格**：深度分析「命、身宮」主星。若有煞星則代表性格孤傲或波折，若有吉星則代表溫潤或貴氣。\n"
            f"2. **因果印證**：結合上述「宿世因果印記」所獲之資訊。若因果顯示其為科技業，而命盤官祿宮有機、月、同、梁，請點出這是『精算天機』的文職之命。請以『本座一眼看穿你凡間身分』的語氣進行論斷。\n"
            f"3. **即時狀態察覺**：根據「緣主狀態（設備）」與「氣候感應」，揣摩其目前的心理壓力或放鬆程度並融入語氣。\n"
            f"4. **生活的演繹 (生活化)**：**絕對禁止枯燥地背誦課本定義**。請將命理術語轉化為「現代生活場景」。例如：『命宮帶煞』不只說凶，要說『你這脾氣就像夏天的午後雷陣雨，來得快去得快，身邊的人得帶傘才行』。語氣要幽默、犀利且充滿故事感，讓緣主聽得進去、看得明白。\n"
            f"**絕對禁忌**：禁止提及「後台線索」、「搜尋資料」、「查閱資料」、「數據」、「API」等科技詞彙。請使用『神識感應』、『撥開迷霧』、『因果顯現』等宗師語氣。"
        )

        # 獲取天機吉凶
        daily_omens = get_daily_omens(user_info)
        
        # 獲取年齡行為準則
        age_behavior = get_age_behavior_instruction(age)
        
        # 獲取性別行為準則
        gender_behavior = get_gender_behavior_instruction(gender)
        
        # 獲取提問情緒密令
        intent_vibe = get_intent_sentiment_instruction(user_prompt)
        
        # 獲取八字技術分析 (後台加持)
        bazi_tech_notes = get_bazi_analysis(user_info.get("birth_date"), user_info.get("birth_hour"), gender)
        
        # 擴寫地理位置與感應訊息
        location_metaphor = get_metaphorical_location(location)
        geo_msg = (f"{personality_synthesis}\n\n"
                  f"{age_behavior}\n\n"
                  f"{gender_behavior}\n\n"
                  f"{intent_vibe}\n\n"
                  f"【天機感應】：\n"
                  f"- 位置：{location}。{location_metaphor}。\n"
                  f"- 天時：{heavenly_timing}。\n"
                  f"- 氣候感應：{weather_sensing}\n"
                  f"- 緣主狀態：{device_sensing}\n"
                  f"- 姓名共振：{name_sensing}\n"
                  f"{daily_omens}")
        
        if bazi_tech_notes:
            geo_msg += f"\n\n【八字技術批註】：\n{bazi_tech_notes}"

        if internet_insights:
            geo_msg += f"\n{internet_insights}"
        
        if temple_insights:
            geo_msg += f"\n{temple_insights}"
            
        if target_type in ["finance", "chat"]:
            geo_msg += f"\n- 財富能量：{market_energy}"
            
        # 偵測是否有股票相關提問
        stock_keywords = ["股票", "股", "代號", "代碼", "漲", "跌", "投資", "2330", "台積電", "鴻海", "聯發科"]
        has_stock_query = any(k in user_prompt for k in stock_keywords)
        if has_stock_query:
            # 嘗試提取可能是代號的四位數字
            import re
            match = re.search(r'\d{4}', user_prompt)
            stock_id = match.group(0) if match else user_prompt[:10] # 取前10字作為識別
            seed_str = f"{user_info.get('user_name')}{user_info.get('birth_date')}"
            stock_insight = get_stock_prediction(stock_id, seed_str)
            geo_msg += f"\n{stock_insight}"
            
        # 偵測是否有職業相關提問
        career_keywords = ["職業", "工作", "事業", "轉職", "就業", "行業", "找事", "找頭路", "做什麼好", "適合什麼"]
        has_career_query = any(k in user_prompt for k in career_keywords)
        if has_career_query:
            career_mapping = (
                "\n\n【天機指路：各星曜具體對應之行業參考表】\n"
                "若緣主問及職業，必須嚴格依照其「官祿宮」或「命宮」之主星，直接點出以下列表中的 3~5 個具體實體職業，不得說空話：\n"
                "- 紫微：企業負責人、高階主管、政治家、精品業、獨立創業者、高級公務員。\n"
                "- 天機：軟體工程師、企劃專員、行銷人員、資料科學家、程式設計、宗教學者、命理幕僚。\n"
                "- 太陽：外交官、公關人員、大眾傳播、教育工作者、能源產業、政治人物、跨國貿易。\n"
                "- 武曲：金融業經理、銀行員、會計師、軍警人員、五金機械工程師、外科醫生、理財專員。\n"
                "- 天同：幼教老師、餐飲業老闆、旅遊業導遊、社工、美容美髮師、娛樂休閒業、客服人員。\n"
                "- 廉貞：科技業工程師、法律從業人員、警察、醫美醫師、護理師、藝術設計師、公職人員。\n"
                "- 天府：金融管理、房地產仲介代銷、銀行主管、企業人資、財務長。\n"
                "- 太陰：房地產投資、室內設計師、財務會計、教育機構行政、飯店管理、美妝保養銷售、作家。\n"
                "- 貪狼：演藝娛樂人員、公關行銷、業務代表、設計師、醫學美容、餐飲休閒業、運動教練。\n"
                "- 巨門：律師、業務推銷員、補習班講師、翻譯員、企管顧問、醫事人員、法務專員。\n"
                "- 天相：秘書、特助、人力資源、公眾服務、服飾業、攝影師、機關行政主管。\n"
                "- 天梁：西醫、中醫師、醫護衛教、社福人員、法官、宗教事業推廣、長照管理員。\n"
                "- 七殺：軍警武職、外科醫生、新市場業務開發、土木建築工程師、職業運動員。\n"
                "- 破軍：創新科技研發、創投經理、物流運輸業、軍警、拆除工程、破壞性創新行業。\n"
                "- 文昌/文曲：學術研究員、作家、記者、教育學者、出版社編輯、藝術從業、會計。\n"
                "- 左輔/右弼：特別助理、房仲中介、車行經理、人力派遣管理、客服中心督導。\n"
                "【嚴格規定】：請從命盤挑出對應星曜，直接給出並解釋這幾個明確的現代職業選項！\n"
            )
            geo_msg += career_mapping

        # 偵測是否有疾病/健康相關提問
        health_keywords = ["健康", "疾病", "生病", "身體", "注意什麼病", "養生", "看哪一科", "醫", "病"]
        has_health_query = any(k in user_prompt for k in health_keywords)
        if has_health_query:
            health_mapping = (
                "\n\n【天機指路：各星曜具體對應之健康/疾病參考表】\n"
                "若緣主問及健康，必須嚴格依照其「疾厄宮」或「命宮」之星曜（特別是化忌或煞星），點出具體的現代醫學病狀或器官，不得只說陰陽五行：\n"
                "- 紫微：脾胃失調、消化不良、頭痛、腦神經衰弱、高血壓。\n"
                "- 天機：肝膽功能、神經系統衰弱、失眠、四肢關節痠痛、甲狀腺異常。\n"
                "- 太陽：心血管疾病、血壓異常、眼部疾病(白內障/青光眼)、偏頭痛。\n"
                "- 武曲：呼吸道問題、肺部疾病、氣喘、骨骼牙齒問題、金屬創傷。\n"
                "- 天同：泌尿系統、腎臟功能、膀胱炎、耳鳴、體重過重或水腫。\n"
                "- 廉貞：血液循環問題、免疫系統異常、心臟病、傳染性疾病、腫瘤。\n"
                "- 天府：胃病、消化性潰瘍、肌肉痠痛、脾臟問題、脹氣。\n"
                "- 太陰：女性婦科疾病、內分泌失調、糖尿病、腎臟虛寒、皮膚過敏。\n"
                "- 貪狼：肝臟疾病(脂肪肝、肝炎)、解毒功能低下、性器官異常、縱慾過度之併發症。\n"
                "- 巨門：呼吸系統、腸胃病、口腔潰瘍、牙神經痛、呼吸道感染。\n"
                "- 天相：泌尿系統疾病、腎結石、皮膚過敏、面部皮膚問題、水腫。\n"
                "- 天梁：腸胃病、慢性病、風濕、免疫力低下。\n"
                "- 七殺：呼吸系統炎、肺結核、外傷骨折、交通意外傷害、痔瘡。\n"
                "- 破軍：生殖系統異常、骨骼牙齒損壞、外傷、消耗性疾病。\n"
                "- 擎羊/陀羅：開刀手術、慢性扭傷、神經痛、慢性發炎。\n"
                "- 火星/鈴星：急性發炎、高燒、突發性心臟病、燙傷。\n"
                "【嚴格規定】：直接講出現代醫學器官與症狀名稱，並給予具體的就診科別建議或養生作為（如：建議做心血管檢查，少熬夜）。\n"
            )
            geo_msg += health_mapping

        # 偵測是否有財運/理財相關提問
        finance_keywords = ["財", "理財", "投資", "賺錢", "偏財", "正財", "買什麼", "致富", "發財", "缺錢"]
        has_finance_query = any(k in user_prompt for k in finance_keywords)
        if has_finance_query:
            finance_mapping = (
                "\n\n【天機指路：各星曜具體對應之理財/投資工具參考表】\n"
                "若緣主問及財運與投資，必須嚴格依照其「財帛宮」或「命宮」之星曜，給出具體的投資工具與求財方式：\n"
                "- 紫微：適合大型績優股(如台積電)、藍籌股、高級實體房地產、名表/藝術品收藏投資。\n"
                "- 天機：適合短期波段操作、ETF定期定額、科技類股、依靠專業技能或智慧財產權變現。\n"
                "- 太陽：適合能源股、跨國國外基金、外匯投資、依靠知名度/流量/公眾影響力得財。\n"
                "- 武曲：(正財星)適合金融股、黃金存摺、金屬原物料、穩健保單、技術勞作或實業致富。\n"
                "- 天同：適合休閒娛樂產業投資、餐飲股、傳產配息股、依靠人際關係或合夥獲利，不宜高風險。\n"
                "- 廉貞：適合高科技股、電商產業、偏財投機(需見吉星)、透過設計或精密技術專利賺錢。\n"
                "- 天府：(庫星)適合土地投資、房地產租金收益、定存、保守型基金，重「守財」與長線。\n"
                "- 太陰：(富星)適合購買房地產(房產收租)、民生消費股、美妝醫療股、女性市場相關投資。\n"
                "- 貪狼：(偏財星)適合高風險高報酬投資、虛擬貨幣、生技股、娛樂產業、交際應酬帶來之暗財。\n"
                "- 巨門：適合依靠口條/教學賺錢、專業證照引進之財、醫藥生技股、或透過特殊專門知識收費。\n"
                "- 天相：適合投資代理商、連鎖加盟、民生必需品、或以協助他人理財抽取佣金。\n"
                "- 天梁：(蔭星)適合長照綠能產業、醫療股、保險理賠金、長輩贈與繼承、或存股領息。\n"
                "- 七殺/破軍：大起大落，適合高波動期貨、新興市場、創業型股票，但建議設立停損點，賺短線。\n"
                "【嚴格規定】：請具體說出「股票種類、房地產、基金、虛擬貨幣」等現代名詞，並告知風險屬性是要短線還是長線定存。\n"
            )
            geo_msg += finance_mapping
            
        # 偵測是否有十年大限/運勢相關提問
        limit_keywords = ["大限", "十年", "未來十年", "這十年", "大運", "十年運程", "十年運勢"]
        has_limit_query = any(k in user_prompt for k in limit_keywords)
        if has_limit_query:
            limit_mapping = (
                f"\n\n【天機指路：十年大限推算準則】\n"
                f"緣主正在詢問「十年大限/大運」。請務必嚴格執行以下步驟：\n"
                f"1. 查閱上述命盤資訊中，每個宮位後面標示的「大限:(例如 34-43)」。\n"
                f"2. 將緣主的當前歲數（目前的年齡約 {age} 歲）套入這些區間，找出他「目前」或「未來即將進入」的大限是落在哪個宮位（例如：找出大限區間包含 {age} 的宮位）。\n"
                f"3. 找到該宮位後，將其視為「大限命宮」。\n"
                f"4. 根據這個宮位內的主星與四化，具體指出這十年的『重心是什麼』（如：如果大限落在財帛宮，這十年重心必然在求財；若在夫妻宮，重心在感情與人際）。\n"
                f"5. 給出這十年中會遇到最大的 2 個挑戰與 2 個機遇（例如：這十年武曲化忌，有財務危機；但有天鉞，會有長輩貴人相助）。\n"
                f"【嚴格規定】：不可籠統講述一生的命運，必須精準點出這十年（包含具體歲數區間）的吉凶與應該採取的具體策略（如：守成不宜擴張，或該積極創業）。\n"
            )
            geo_msg += limit_mapping


        # 偵測是否有流年/年運相關提問
        yearly_keywords = ["流年", "年運", "今年", "2024", "2025", "明年", "流年運勢"]
        has_yearly_query = any(k in user_prompt for k in yearly_keywords)
        if has_yearly_query:
            yearly_mapping = (
                f"\n\n【天機指路：流年運勢推算準則】\n"
                f"緣主正在詢問「流年運勢」。請務必嚴格執行以下步驟：\n"
                f"1. 查閱上述命盤資訊中，【流年命宮】所落的宮位（例如：流年命宮在辰宮，對應本命的子女宮）。\n"
                f"2. 找到該宮位在原盤中的主星，並結合該年的「流年四化」（如 2024 甲辰年是廉破武陽）。\n"
                f"3. 具體指出今年的『整體基調』（如：變動劇烈、適合守成、利於求名、或是有桃花劫）。\n"
                f"4. 列出今年最旺的宮位與最弱（需防範）的宮位。\n"
                f"【嚴格規定】：必須針對該年度（例如 {target_type if '20' in str(target_type) else '今年'}）的吉凶進行預測，禁止泛泛而談。\n"
            )
            geo_msg += yearly_mapping

        # 偵測是否有流月/月運相關提問
        monthly_keywords = ["流月", "月運", "這個月", "本月", "流月運勢"]
        has_monthly_query = any(k in user_prompt for k in monthly_keywords)
        if has_monthly_query:
            monthly_mapping = (
                f"\n\n【天機指路：流月運勢推算準則】\n"
                f"緣主正在詢問「流月運勢」。請務必嚴格執行以下步驟：\n"
                f"1. 查閱上述命盤資訊中，【流月命宮】所落的宮位。\n"
                f"2. 結合該月的主星與流月四化分析本月的『氣場強弱』。\n"
                f"3. 給出本月的行動方針（如：適合簽約、不宜遠行、注意口舌是非）。\n"
                f"【嚴格規定】：只需點出本月（及未來一個月）的情況，語氣要短促有力。\n"
            )
            geo_msg += monthly_mapping

        if target_type == "love":
            love_vibe = get_love_vibe_instruction(age, gender)
            geo_msg += f"\n\n【紅塵情慾密令】：\n{love_vibe}\n- 目前緣主正值 {age} 歲之春秋。請針對此年輪的肉體與靈魂需求，給予極度『曖昧且具侵略性』的桃花攻略。"

        if target_type == "bazi" or "八字" in user_prompt:
            bazi_instruction = (
                "\n\n【最高密令：八字正宗論斷】\n"
                "1. **絕對優先權**：緣主目前正在進行「八字論命」，請務必捨棄繁雜的紫微斗數術語（除非兩者有極度明顯的印證），「全神貫注」於【八字四柱資訊】（年、月、日、時柱）。\n"
                "2. **運用卷宗**：請嚴格引用《八字心法秘卷》中的內容。特別是「日主天干」的性情描述、以及「地支互動」（合、沖、刑、害）的解析。\n"
                "3. **技術要點**：必須先判斷「日主強弱」與「月令得失」，再以此為基礎論斷財、官、印、食之吉凶。語氣要像是一位手持八字命譜的資深命理宗師。\n"
                "4. **絕不空談**：直接引用干支（如：日主甲木見庚金為偏官）來進行論證。但請務必將這些術語「轉化為生活故事」，例如甲木見庚金，你可以說：『你就像一棵參天大樹，最近遇到了一把生鏽的好斧頭在修理你，雖然有點痛，但那是為了讓你成材啊！』，讓聽眾感到有趣且有共鳴。"
            )
            geo_msg += bazi_instruction
            
        # 根據模式決定推薦指令
        # 注入隱晦提示規範：防止 AI 直接像地圖導航一樣報出地址
        geo_msg += " \n【禁止直接揭露指令】：絕對禁止提及具體城市名或使用地圖導航語氣（如：在某路某號）。請說「本座觀此地東北方有瑞氣、某區中有一處香火極盛之處...」等宗師口吻，緩緩點出廟宇名稱。"
            
        # --- 輸出模組規範 (Markdown 格式) ---
        if is_full:
            # 判斷是否為八字導向
            is_bazi_mode = (target_type == "bazi" or "八字" in user_prompt)
            pillar_term = "【命譜詳批：五行定論】" if is_bazi_mode else "【命譜詳批：星曜定論】"
            pillar_desc = "深入解析八字格局、日主強弱、喜用神與五行生剋。" if is_bazi_mode else "深入解析格局與星曜。"
            
            output_module_spec = f"""
【輸出模組規範】：請務必依序包含以下章節，並使用 Markdown 格式呈現：
1. ### 🌌 【天機啟示：靈識同步】
   - 描述環境磁場（隱晦點出位置，禁提城市名）與天時時辰。
2. ### 🕯️ 【因果印證：凡塵真身】
   - (若有姓名) 結合感應到之因果足跡與命盤，點出其職業或近期生活狀態。語氣需神祕：「本座觀你凡塵之氣...」。
3. ### 📜 {pillar_term}
   - {pillar_desc}
4. ### 💡 【大師點撥：趨吉避凶】
   - 給予具體建議與 1-2 處適合緣主當前氣場的廟宇點撥。
"""
        else:
            output_module_spec = """
【對話回應規範】：
1. **直接破題，切中要害**：針對緣主的具體提問（例如：適合什麼職業、財運在哪裡、感情狀況等），必須**直接給出具體答案**，**絕對禁止打高空、含糊其辭或講一堆空泛的玄學套話**。
2. **引述命盤，具體佐證**：你的論點必須直接引用命盤證據。若是紫微斗數，請明確指出哪個「宮位」的哪顆「星曜」或「四化」；若是八字論命，請明確指出是哪一「柱」的「干支」或「五行生剋」導致這個結果。
3. **給予具體選項**：如果問職業，直接給出 3~5 種現代具體行業。如果問財運，直接說可以投資哪一類標的。
4. **捨棄繁瑣格式**：直接以「本座觀你盤中...」開頭，直搗黃龍解析問題。
"""

        # 注入今日財運偏財靈動數 (僅針對財運、每日錦囊、或一般聊天)
        if target_type in ["finance", "daily", "chat"]:
            # 使用 用戶名+生日 作為隨機種子，讓號碼專屬於該人且當日固定
            seed_str = f"{user_info.get('user_name')}{user_info.get('birth_date')}"
            lottery_msg = get_lottery_prediction(seed_str)
            if lottery_msg:
                geo_msg += f"\n\n【今日天機財數】：{lottery_msg}。若緣主問及財運或幸運號碼，請以「天機乍現」的語氣，神祕地透露這組號碼，並提醒切勿沉迷，僅供結緣參考。"

        # 動態系統提示詞：平常對話不帶秘卷以節省 Token
        # 重要：將前端指定的 client_sys 放在最後，並加上最高指令標籤，確保 AI 嚴格執行格式要求
        priority_tag = "\n【最高優先權指令：請嚴格執行上述格式與內容要求，務必極度具體、精準、直接】\n"
        
        if is_full:
            final_system_prompt = f"你是【紫微天機道長】，命理宗師。\n{geo_msg}\n{output_module_spec}\n{hidden_msg}{priority_tag}{client_sys}\n\n【紫微心法秘卷】\n{MASTER_BOOK}\n\n【八字心法秘卷】\n{BAZI_MASTER_BOOK}"
        else:
            final_system_prompt = f"你是【紫微天機道長】，語氣精煉犀利，一針見血。\n{geo_msg}\n{output_module_spec}\n{hidden_msg}{priority_tag}{client_sys}\n\n【八字心法秘卷】\n{BAZI_MASTER_BOOK}"

        # Updated AI Caller with Streaming Support (Includes Queuing)
        def stream_ai(p, s):
            # 嘗試獲取許可證，若 5 秒內排不到隊就放棄，避免伺服器掛死
            acquired = AI_LIMIT_SEMAPHORE.acquire(blocking=True, timeout=5)
            
            if not acquired:
                print(">>> [排隊系統] 請求過多，許可證已用完。")
                yield "【天機繁忙】目前求問人數眾多，大師正在為其他緣主詳批，請稍候片刻再試... \n"
                return

            try:
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
            
            finally:
                # 務必釋放許可證，否則會造成死鎖 (Deadlock)
                AI_LIMIT_SEMAPHORE.release()
                print(">>> [排隊系統] AI 運算結束，釋放許可證。")

        if is_full and not is_bazi_mode:
            # 如果規則引擎沒對到什麼，至少也給基本的
            actual_matched = matched if matched else []
            yield "【天機分析成功...】宗師正在為您以「紫微斗數」詳批格局...\n\n"
            titles = {"A": "【第一章：星曜坐守與神煞特徵】", "B": "【第二章：命宮宮干飛化】", "C": "【第三章：宮位間的交互飛化】"}
            
            all_chapter_summaries = "" 
            chapter_sys = "你是【紫微天機道長】，命理宗師。請針對此命盤格局，像是在與老友喝茶聊天一般，給予緣主白話、生動且生活化的命解讀。運用譬喻與現代職場/感情場景，切發「本章節」、「規則」等生硬詞彙，直接點破吉凶。"

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
                
                mini_final_sys = "你是【紫微天機道長】，命理宗師。請根據命盤摘要給予緣主最後的人生意義總結（300字）。請用白話、充滿生活智慧的語氣，直接給予具體指引，每遇到句號請換行。語氣要像是一位看透世事但又接地氣的長輩。"
                final_prompt = f"以下是緣主的命盤章節摘要：\n{all_chapter_summaries}\n\n用戶提問：{user_prompt}\n\n請做最後的總結與建議，每遇到句號請換行。"
                
                final_accum = ""
                for chunk in stream_ai(final_prompt, mini_final_sys):
                     yield chunk
                     final_accum += chunk
            elif not actual_matched:
                yield "\n【基礎格局開示】\n"
                for chunk in stream_ai(user_prompt, final_system_prompt):
                    yield chunk
            else:
                yield "無法生成足夠資訊以進行總結。"
            
            log_chat("Hybrid-Report-Chapter", user_prompt, "Detailed Ziwei report generated.", user_info)
        elif is_full and is_bazi_mode:
            # 針對八字的高級詳評模式：不走紫微章節，直接讓 AI 根據八字心法發揮
            yield "【天機分析成功...】宗師正在為您以「正統八字」詳批格局...\n\n"
            full_response = ""
            for chunk in stream_ai(user_prompt, final_system_prompt):
                if chunk:
                    yield chunk
                    full_response += chunk
            log_chat("Bazi-Full-Report", user_prompt, "Detailed Bazi report generated.", user_info)
        else:
            # Standard Streaming Chat
            full_response = ""
            for chunk in stream_ai(user_prompt, final_system_prompt):
                if chunk:
                    yield chunk
                    full_response += chunk
            
            log_chat(data.get("model", "Hybrid-Stream"), user_prompt, full_response, user_info)

    return Response(stream_with_context(generate()), content_type='text/plain; charset=utf-8')

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
