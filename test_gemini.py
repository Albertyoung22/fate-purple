import requests
import json

api_key = "AIzaSyDHKuL1Sgj-04yNrlOookpfBaeveSZeO4E"
test_prompt = "Hello, reply with 'test success'"

combos = [
    ("v1", "gemini-1.5-flash"),
    ("v1", "gemini-1.5-flash-latest"),
    ("v1beta", "gemini-1.5-flash"),
    ("v1beta", "gemini-1.5-flash-latest"),
    ("v1beta", "gemini-1.5-flash-001"),
    ("v1beta", "gemini-1.5-flash-002"),
    ("v1beta", "gemini-2.0-flash-exp"),
]

for ver, model in combos:
    url = f"https://generativelanguage.googleapis.com/{ver}/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": test_prompt}]}]
    }
    try:
        r = requests.post(url, json=payload, timeout=5)
        print(f"Testing {ver}/{model}: Status {r.status_code}")
        if r.status_code == 200:
            print(f"SUCCESS with {ver}/{model}")
            # print(r.json())
        else:
            print(f"Error: {r.text}")
    except Exception as e:
        print(f"Failed {ver}/{model}: {e}")
