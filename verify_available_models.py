
import google.generativeai as genai
import time

KEY = "AIzaSyBf-YRUiEWx4bppTSRro4wsuccntwpq1ec"
MODELS = ["gemini-flash-latest", "gemini-2.5-flash", "gemma-3-1b-it"]

genai.configure(api_key=KEY)

for m in MODELS:
    print(f"\nTesting Model: {m}...")
    try:
        model = genai.GenerativeModel(m)
        response = model.generate_content("Hello")
        if response and response.text:
             print(f"✅ SUCCESS on {m}: {response.text.strip()}")
             break
        else:
             print(f"⚠️ Empty response on {m}")
    except Exception as e:
        print(f"❌ FAILED on {m}: {e}")
