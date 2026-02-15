
import json

RULE_FILE = "ziwei_rules.json"

def fix_specific_rules():
    with open(RULE_FILE, 'r', encoding='utf-8') as f:
        rules = json.load(f)

    for r in rules:
        # L-28: Only Lu Cun, No Main Stars (Iron Rooster)
        if r["id"] == "L-28":
             print("Fixing L-28 (Lu Cun Single)...")
             r["conditions"] = {
                 "logic": "AND",
                 "criteria": [
                     {"target": "life", "has_star": "lu_cun"},
                     {"target": "life", "no_main_stars": True}
                 ]
             }

        # H-03: Only Di Kong, No Other Sha
        if r["id"] == "H-03":
             print("Fixing H-03 (Di Kong Single)...")
             r["conditions"] = {
                 "logic": "AND",
                 "criteria": [
                     {"target": "health", "has_star": "di_kong"},
                     # No other sha stars
                     {"target": "health", "not_has_star": ["di_jie", "qing_yang", "tuo_luo", "huo_xing", "ling_xing"]}
                 ]
             }

    with open(RULE_FILE, 'w', encoding='utf-8') as f:
        json.dump(rules, f, ensure_ascii=False, indent=4)
    print("Fixed L-28 and H-03.")

if __name__ == "__main__":
    fix_specific_rules()
