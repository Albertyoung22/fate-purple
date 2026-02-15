import requests
import json

api_key = "AIzaSyDHKuL1Sgj-04yNrlOookpfBaeveSZeO4E"

def list_models():
    # Try different versions of the list endpoint
    versions = ["v1", "v1beta"]
    
    print(f"Checking available models for key ending in ...{api_key[-4:]}...")
    
    found_any = False
    
    for v in versions:
        url = f"https://generativelanguage.googleapis.com/{v}/models?key={api_key}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "models" in data:
                    print(f"\n--- Models available in {v} ---")
                    generate_models = [m for m in data["models"] if "generateContent" in m.get("supportedGenerationMethods", [])]
                    for m in generate_models:
                        print(f"Name: {m['name']}")
                        print(f"  Disp: {m.get('displayName')}")
                        print(f"  Desc: {m.get('description')}")
                        print("-" * 20)
                    if generate_models:
                        found_any = True
            else:
                print(f"Failed to list {v}: Status {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error checking {v}: {e}")

    if not found_any:
        print("\nCRITICAL: No models found with generateContent capability. The API Key might be invalid, expired, or have no enabled services.")

if __name__ == "__main__":
    list_models()
