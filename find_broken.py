
import json

def find_broken_rules():
    with open("ziwei_rules.json", "r", encoding="utf-8") as f:
        rules = json.load(f)
    
    broken = []
    for r in rules:
        cond = r.get("conditions")
        if not cond:
            broken.append(f"{r['id']} : {r['description']}")
        elif "logic" not in cond and not cond.get("criteria"): # Empty dict check if any
             broken.append(f"{r['id']} : {r['description']} (Empty Dict)")
             
    print(f"Found {len(broken)} broken rules:")
    for b in broken:
        print(b)

if __name__ == "__main__":
    find_broken_rules()
