
import json

RULE_FILE = "ziwei_rules.json"

def fix_4h_rules():
    with open(RULE_FILE, 'r', encoding='utf-8') as f:
        rules = json.load(f)

    # Helper maps
    palaces = ["life", "siblings", "spouse", "kids", "wealth", "health", 
               "travel", "friends", "career", "property", "fortune", "parents"]

    for r in rules:
        # 4H-01: Same Star Lu-Chu (Birth Lu + Self Lu)
        if r["id"] == "4H-01":
             print("Fixing 4H-01 to use 'has_star_matching' for same-star logic...")
             # Re-build criteria
             new_criteria = []
             for p in palaces:
                 new_criteria.append({
                     "target": p,
                     "has_star_matching": {
                         "trans": "hua_lu",       # Birth Lu
                         "self_trans": "hua_lu"   # Self Lu
                     }
                 })
             r["conditions"]["criteria"] = new_criteria

        # 4H-17: Wealth -> Tian Ji Self-Ji (Exact Tian Ji check)
        if r["id"] == "4H-17":
             print("Fixing 4H-17 to use 'has_star_matching' for specific Tian Ji Self-Ji...")
             r["conditions"]["criteria"][1] = {
                 "target": "wealth",
                 "has_star_matching": {
                     "key": "tian_ji",
                     "self_trans": "hua_ji"
                 }
             }

    with open(RULE_FILE, 'w', encoding='utf-8') as f:
        json.dump(rules, f, ensure_ascii=False, indent=4)
    print("Fixed 4H-01 and 4H-17.")

if __name__ == "__main__":
    fix_4h_rules()
