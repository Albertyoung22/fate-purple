
import google.generativeai as genai
KEY = "AIzaSyBf-YRUiEWx4bppTSRro4wsuccntwpq1ec"
genai.configure(api_key=KEY)
try:
    print("Listing models for key:", KEY[:5])
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print("-", m.name)
except Exception as e:
    print("Error listing models:", e)
