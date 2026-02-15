
import json

RULE_FILE = "ziwei_rules.json"

def fix_p02():
    with open(RULE_FILE, 'r', encoding='utf-8') as f:
        rules = json.load(f)

    for r in rules:
        if r["id"] == "P-02":
             # P-02: Property - Kong/Jie + QingYang + HuaJi
             print("Fixing P-02 (Missing Kong/Jie)...")
             r["conditions"] = {
                 "logic": "AND",
                 "criteria": [
                     {"target": "property", "has_star": "qing_yang"},
                     {"target": "property", "has_trans": "hua_ji"},
                     {
                         "logic": "OR",
                         "criteria": [
                             {"target": "property", "has_star": "di_kong"},
                             {"target": "property", "has_star": "di_jie"}
                         ]
                     }
                 ]
             }

    with open(RULE_FILE, 'w', encoding='utf-8') as f:
        json.dump(rules, f, ensure_ascii=False, indent=4)
        
    print("Fixed P-02.")

if __name__ == "__main__":
    fix_p02()
