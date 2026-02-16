
import urllib.request
import urllib.error
import json
import ssl

# 直接寫死您的 Key 進行測試
KEY = "AIzaSyDHKuL1Sgj-04yNrlOookpfBaeveSZeO4E"  
MODEL = "gemini-1.5-flash"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={KEY}"

print(f"--- 測試 Google Gemini API (Urllib版) ---")
print(f"URL: {URL[:60]}...")

# 盡可能繞過所有安全檢查
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

data = json.dumps({"contents": [{"parts": [{"text": "Hello"}]}]}).encode('utf-8')
req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})

try:
    with urllib.request.urlopen(req, context=ctx, timeout=10) as f:
        print(f"✅ 狀態碼: {f.status}")
        print(f"回應: {f.read().decode('utf-8')[:100]}...")
        print("結論: Key 沒有問題，網路也沒有問題。")
except urllib.error.HTTPError as e:
    print(f"❌ HTTP 錯誤: {e.code} - {e.reason}")
    print(e.read().decode('utf-8'))
    print("結論: 連得上 Google，但 Key 被拒絕 (可能額度已滿/權限不足)。")
except urllib.error.URLError as e:
    print(f"❌ 連線失敗: {e.reason}")
    print("結論: 完全連不上 Google (網路封鎖)。")
except Exception as e:
    print(f"❌ 未知錯誤: {e}")
