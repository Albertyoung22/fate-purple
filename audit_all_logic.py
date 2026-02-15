
import json

RULE_FILE = "ziwei_rules.json"

def audit_and_upgrade_rules():
    with open(RULE_FILE, 'r', encoding='utf-8') as f:
        rules = json.load(f)
    
    count = 0

    for r in rules:
        desc = r.get("description", "")
        cond = r.get("conditions")
        
        # 1. B-01: Wu Qu Hua Ji -> Strict matching
        # Description: "有武曲化忌..."
        # Logic was: Has WuQu, Has WenQu, Has HuaJi -> Very loose. 
        # Correct: Has Match(WuQu, HuaJi).
        # Wait, the rule description says "Wu Qu Hua Ji". 
        # The JSON has ["wu_qu", "wen_qu"] and ["hua_ji"].
        # If user meant Wu Qu OR Wen Qu has Hua Ji, then it's ok.
        # But description says "Wu Qu Hua Ji".
        if r["id"] == "B-01":
             print("Upgrading B-01...")
             # Keep other stars (QingYang, TianXing) but fix WuQu logic.
             # Strict: WuQu must match HuaJi.
             # What about Wen Qu? Was it a mistake in JSON or intended?
             # Description: "有武曲化忌，加擎羊和天刑。" No mention of Wen Qu.
             # So 'wen_qu' in JSON seems suspicious/wrong. I will remove it and strict match WuQu.
             r["conditions"]["criteria"][0] = {
                 "target": "siblings",
                 "has_star_matching": {
                     "key": "wu_qu",
                     "trans": "hua_ji"
                 }
             }
             count += 1

        # 2. Ca-03: Ju Men (or Ju Men Hua Lu)
        # Description: "有巨門(或巨門化祿)。"
        # Logic was: Ju Men + Hua Lu.
        # Strict: Ju Men OR (Ju Men + Hua Lu) -> Actually just "Ju Men". 
        # Because if Ju Men has Hua Lu, it still "Has Ju Men".
        # So "Has Ju Men" covers both cases unless it implies "Must be Hua Lu if Ju Men is not enough?" 
        # No, "Ju Men (or Ju Men Hua Lu)" usually means "Ju Men is present, even better/worse if Hua Lu".
        # But wait, usually rules like this distinct cases.
        # Let's interpret as: "Has Ju Men". The Hua Lu part is illustrative.
        # If I change to `has_star: ju_men` it covers all.
        # However, the original JSON had `OR(has_star: ju_men, has_trans: hua_lu)`. 
        # This meant: "Has Ju Men" OR "Has ANY Hua Lu". This is definitely WRONG (Any Hua Lu).
        # Fix: Just `has_star: ju_men`. (Simplification).
        # Or maybe it meant "Ju Men sitting OR (Any star Hua Lu sitting)"? Unlikely.
        if r["id"] == "Ca-03":
            print("Upgrading Ca-03...")
            r["conditions"] = {
                "logic": "AND",
                "criteria": [
                    {"target": "career", "has_star": "ju_men"}
                ]
            }
            count += 1
            
        # 3. Ca-04: Wen Chang OR Wen Qu Hua Ke
        # Description: "有文昌或文曲化科。" -> Ambiguous.
        # (Wen Chang) OR (Wen Qu Hua Ke)?
        # OR (Wen Chang Hua Ke) OR (Wen Qu Hua Ke)?
        # Usually implies both need Ke for the effect "Academic Fame"? 
        # Or just "Chang or Qu" is good, but "Hua Ke" makes it specific for this rule?
        # Text says "Suitable for brain/writing".
        # Chang/Qu are academic stars. Transformation Hua Ke boosts them.
        # If strict: Match(WenChang, HuaKe) OR Match(WenQu, HuaKe).
        # If loose: (Has Chang OR Qu) AND (Has Hua Ke).
        # Let's go with Strict OR.
        if r["id"] == "Ca-04":
             print("Upgrading Ca-04...")
             r["conditions"] = {
                 "logic": "OR",
                 "criteria": [
                     {"target": "career", "has_star_matching": {"key": "wen_chang", "trans": "hua_ke"}},
                     {"target": "career", "has_star_matching": {"key": "wen_qu", "trans": "hua_ke"}},
                     # Some schools say just having Chang/Qu is enough. 
                     # But Description specifically says "Hua Ke".
                 ]
             }
             count += 1

        # 4. Fo-04: Tian Ji Hua Ji
        # Description: "天機化忌 (或落陷加陀羅)。"
        # Logic was: OR( (Tian Ji + Hua Ji), ...).
        # Strict: OR( Match(TianJi, HuaJi), (TianJi+TuoLuo) )?
        # Description says "Luo Xian (Trapped) + Tuo Luo".
        # Current logic doesn't check brightness.
        # I will fix the Tian Ji Hua Ji part to be strict.
        if r["id"] == "Fo-04":
             print("Upgrading Fo-04...")
             # Part A: Tian Ji Hua Ji
             part_a = {"target": "fortune", "has_star_matching": {"key": "tian_ji", "trans": "hua_ji"}}
             # Part B: Tian Ji (Trapped?) + Tuo Luo. 
             # Since I can't check Trapped yet easily without brightness calc (not fully implemented in rule engine),
             # I will keep the Tuo Luo check but ensure it's linked to Tian Ji presence.
             # Original was: AND( OR(TianJi...), TuoLuo). 
             # Let's make it: OR( Match(TianJi, HuaJi), AND(Has TianJi, Has TuoLuo) ).
             part_b = {
                 "logic": "AND",
                 "criteria": [
                     {"target": "fortune", "has_star": "tian_ji"},
                     {"target": "fortune", "has_star": "tuo_luo"}
                 ]
             }
             r["conditions"] = {
                 "logic": "OR",
                 "criteria": [part_a, part_b]
             }
             count += 1

        # 5. W-10: Tian Liang Hua Lu
        if r["id"] == "W-10":
             print("Upgrading W-10...")
             r["conditions"]["criteria"][0] = {
                 "target": "wealth",
                 "has_star_matching": {"key": "tian_liang", "trans": "hua_lu"}
             }
             count += 1

        # 6. X-01: Tai Yang Hua Ji (Night)
        if r["id"] == "X-01":
             print("Upgrading X-01...")
             # Description: "太陽在子(晚上)化忌，加擎羊和天刑。"
             # Current: Has TaiYang, Has HuaJi, ...
             # Strict: Match(TaiYang, HuaJi).
             # + Has Branch Zi (Index 0).
             # + Has QingYang, Has TianXing.
             r["conditions"]["criteria"][0]["criteria"][0] = {
                 "target": "life",
                 "has_star_matching": {"key": "tai_yang", "trans": "hua_ji"}
             }
             # Remove raw 'hua_ji' check if it was separate
             # The original had separate checks.
             # Let's rebuild X-01 cleanly.
             r["conditions"] = {
                 "logic": "AND",
                 "criteria": [
                     {"target": "life", "has_star_matching": {"key": "tai_yang", "trans": "hua_ji"}},
                     {"target": "life", "has_branch": [0]}, # Zi
                     {"target": "life", "has_star": "qing_yang"},
                     {"target": "life", "has_star": "tian_xing"}
                 ]
             }
             count += 1

        # 7. X-02: Lian Zhen Hua Ji
        if r["id"] == "X-02":
             print("Upgrading X-02...")
             r["conditions"] = {
                 "logic": "AND",
                 "criteria": [
                     {"target": "life", "has_star_matching": {"key": "lian_zhen", "trans": "hua_ji"}},
                     {"target": "life", "has_star": "qing_yang"},
                     {"target": "life", "has_star": "tian_xing"}
                 ]
             }
             count += 1

        # 8. Fo-01: Fortune Tian Tong + Life Tian Liang (or reverse)
        # Description: "(福德天同+命宮天梁) 或 (反之)。"
        # Logic check:
        # A: Fortune=TianTong AND Life=TianLiang
        # B: Fortune=TianLiang AND Life=TianTong
        if r["id"] == "Fo-01":
             print("Upgrading Fo-01...")
             r["conditions"] = {
                 "logic": "OR",
                 "criteria": [
                     {
                         "logic": "AND",
                         "criteria": [
                             {"target": "fortune", "has_star": "tian_tong"},
                             {"target": "life", "has_star": "tian_liang"}
                         ]
                     },
                     {
                         "logic": "AND",
                         "criteria": [
                             {"target": "fortune", "has_star": "tian_liang"},
                             {"target": "life", "has_star": "tian_tong"}
                         ]
                     }
                 ]
             }
             count += 1

    with open(RULE_FILE, 'w', encoding='utf-8') as f:
        json.dump(rules, f, ensure_ascii=False, indent=4)
    print(f"Upgraded {count} rules.")

if __name__ == "__main__":
    audit_and_upgrade_rules()
