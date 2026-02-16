
import google.generativeai as genai

KEY = "AIzaSyBf-YRUiEWx4bppTSRro4wsuccntwpq1ec"
MODEL = "gemini-2.0-flash"

print(f"Testing Key: {KEY[:10]}...")
print(f"Using Model: {MODEL}")

try:
    genai.configure(api_key=KEY)
    
    print("Attempting generation...")
    model = genai.GenerativeModel(MODEL)
    response = model.generate_content("Hello, reply with 'OK'.")
    
    if response and response.text:
         print(f"✅ SUCCESS: {response.text.strip()}")
    else:
         print("⚠️ Empty response.")
         
except Exception as e:
    print(f"❌ FAILED: {e}")
