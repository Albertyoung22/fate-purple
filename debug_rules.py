
import json

def find_rule():
    try:
        with open("ziwei_rules.json", "r", encoding="utf-8") as f:
            rules = json.load(f)
            
        found = False
        for r in rules:
            # Check description or text for Keywords
            txt = r.get("result", {}).get("text", "")
            desc = r.get("description", "")
            if "祿馬" in txt or "祿馬" in desc or "天馬" in desc:
                print(f"--- Rule ID: {r.get('id')} ---")
                print(f"Desc: {desc}")
                print(f"Text: {txt}")
                print(f"Conditions: {json.dumps(r.get('conditions'), indent=2, ensure_ascii=False)}")
                found = True
        
        if not found:
            print("No rules found matching '祿馬' or '天馬'.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_rule()
