
import json

RULE_FILE = "ziwei_rules.json"

def fix_s03_logic():
    with open(RULE_FILE, 'r', encoding='utf-8') as f:
        rules = json.load(f)

    for r in rules:
        # S-03: (空劫/孤寡) + 天刑 + 煞星 -> ALL must be present
        if r["id"] == "S-03":
             print("Fixing S-03 to strict logic: (Empty/Robbery/Gu/Gua) AND TianXing AND Sha...")
             r["conditions"] = {
                 "logic": "AND",
                 "criteria": [
                     # 1. (空劫/孤寡)
                     {
                         "logic": "OR",
                         "criteria": [
                             {"target": "spouse", "has_star": "di_kong"},
                             {"target": "spouse", "has_star": "di_jie"},
                             {"target": "spouse", "has_star": "gu_chen"},
                             {"target": "spouse", "has_star": "gua_su"}
                         ]
                     },
                     # 2. 加天刑
                     {
                         "target": "spouse",
                         "has_star": "tian_xing"
                     },
                     # 3. 再遇煞星 (Assuming 4 Sha: Yang/Tuo/Huo/Ling)
                     {
                         "logic": "OR",
                         "criteria": [
                             {"target": "spouse", "has_star": "qing_yang"},
                             {"target": "spouse", "has_star": "tuo_luo"},
                             {"target": "spouse", "has_star": "huo_xing"},
                             {"target": "spouse", "has_star": "ling_xing"}
                         ]
                     }
                 ]
             }

    with open(RULE_FILE, 'w', encoding='utf-8') as f:
        json.dump(rules, f, ensure_ascii=False, indent=4)
    print("Fixed S-03.")

if __name__ == "__main__":
    fix_s03_logic()
