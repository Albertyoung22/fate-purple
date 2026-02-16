
import json
import os
import requests
import sys

# Test Gemini Connection
def test_gemini():
    print("--- 1. 檢查設定檔 (Config Check) ---")
    if not os.path.exists('config.json'):
        print("❌ 找不到 config.json")
        return

    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    gemini_key = config.get('gemini', {}).get('api_key')
    gemini_model = config.get('gemini', {}).get('model')

    if not gemini_key:
        print("❌ API Key 為空！")
    else:
        print(f"✅ API Key 已讀取 (長度: {len(gemini_key)})")
        print(f"🔑 Key 前5碼: {gemini_key[:5]}...")

    print(f"🤖 設定模型: {gemini_model}")
    if gemini_model != "gemini-1.5-flash":
        print(f"⚠️ 警告: 模型名稱不是標準的 'gemini-1.5-flash'，這可能導致錯誤。")

    print("\n--- 2. 直接連線測試 (Connection Test) ---")
    url = f"https://generativelanguage.googleapis.com/v1/models/{gemini_model}:generateContent?key={gemini_key}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{"parts": [{"text": "Hello, are you online? Respond with 'YES'."}]}]
    }

    try:
        print(f"正在連線到 Google: {url[:50]}...")
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            print("✅ 連線成功 (200 OK)！")
            print("回傳內容:", response.json().get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text'))
            print("\n結論：您的電腦可以正常連線到 Gemini。後端程式應該也要能運作。")
            return True
        else:
            print(f"❌ 連線失敗 (Status: {response.status_code})")
            print("錯誤詳情:", response.text)
            return False

    except Exception as e:
        print(f"❌ 連線異常: {e}")
        return False

if __name__ == "__main__":
    test_gemini()
