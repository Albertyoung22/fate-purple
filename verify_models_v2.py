
import google.generativeai as genai
import time

KEY = "AIzaSyBf-YRUiEWx4bppTSRro4wsuccntwpq1ec"
MODELS = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]

for m in MODELS:
    print(f"\nTesting Model: {m} with Key: {KEY[:5]}...")
    try:
        genai.configure(api_key=KEY)
        model = genai.GenerativeModel(m)
        response = model.generate_content("Hello")
        if response and response.text:
             print(f"✅ SUCCESS on {m}!")
             break 
        else:
             print(f"⚠️ Empty response on {m}")
    except Exception as e:
        print(f"❌ FAILED on {m}: {e}")
