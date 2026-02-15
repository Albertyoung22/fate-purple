import json

RULE_FILE = "ziwei_rules.json"

def fix_pa02():
    with open(RULE_FILE, 'r', encoding='utf-8') as f:
        rules = json.load(f)

    for r in rules:
        if r["id"] == "Pa-02":
             print("Fixing Pa-02 (Parents - QingYang + TianXing + Fire/Bell + NO Lucky Stars)...")
             # Original was: AND(QingYang, TianXing, HuoXing, NOT(LingXing)) -> Weird logic
             # Correct: AND(QingYang, TianXing, OR(Huo, Ling), NoLucky)
             r["conditions"] = {
                 "logic": "AND",
                 "criteria": [
                     {"target": "parents", "has_star": "qing_yang"},
                     {"target": "parents", "has_star": "tian_xing"},
                     {
                         "logic": "OR",
                         "criteria": [
                             {"target": "parents", "has_star": "huo_xing"},
                             {"target": "parents", "has_star": "ling_xing"}
                         ]
                     },
                     # New logic: No Lucky Stars
                     {"target": "parents", "no_lucky_stars": True}
                 ]
             }
             # Update Text if needed
             r["result"]["text"] = "與父親關係惡劣如仇人 (且無吉星化解)。"

    with open(RULE_FILE, 'w', encoding='utf-8') as f:
        json.dump(rules, f, ensure_ascii=False, indent=4)
    print("Fixed Pa-02.")

if __name__ == "__main__":
    fix_pa02()
