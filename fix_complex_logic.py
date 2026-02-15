
import json

RULE_FILE = "ziwei_rules.json"

def audit_and_fix_complex_conditions():
    with open(RULE_FILE, 'r', encoding='utf-8') as f:
        rules = json.load(f)

    # Manual audit and fix for rules with complex "Description" vs "Logic" mismatch
    # Especially those with "AND" conditions that might be loosely implemented as "OR" or partial checks.

    # 1. Ca-05: Career - HuaJi + (Kong OR Jie)
    # Description: "有化忌加空劫。" -> Logic MUST be AND(HuaJi, OR(Kong, Jie))
    # Currently looks correct in JSON but let's reinforce structure.
    
    # 2. X-06: Kids/Spouse - Po Jun + Tan Lang + Peach Blossom
    # Description: "破軍加貪狼，還有桃花星。"
    # Current JSON only checks PoJun + TanLang. Missing "Peach Blossom" (TianYao/HongLuan/TianXi/XianChietc.)
    # Let's add Peach Blossom check.
    
    # 3. X-07: Fortune - Chang/Qu Arch + TianYao + HongLuan
    # Description: "昌曲拱照，且有天姚和紅鸞。"
    # Current JSON only checks TianYao + HongLuan. Missing Chang/Qu Arch check.
    # Since "Arch" (Three Fang) is hard, at least check if they are present or in strict combination if possible,
    # or just assume the user wants the stars present in Fortune.
    # "Arch" usually means in Triangle. Let's start with local check or simplified "has_star" if the engine supports triangle.
    # The rule engine supports `has_star` which usually checks the palace itself.
    # Let's reinforce TianYao + HongLuan first.
    
    # 4. X-08: Life - (Ju/Yin/Yang/Tong/Fu) + Zuo/You + HuaLu
    # Description: "(巨/陰/陽/同/府)之一坐命，有左右且化祿。"
    # Current JSON only checks HuaLu! Major logic missing.
    
    # 5. F-01: Friends - (Po/Qi) + (Yang/Tuo) + YinSha
    # Description: "(破軍/七殺)加(羊/陀)再加陰煞。"
    # Logic looks okay (AND(OR(Po,Qi), OR(Yang,Tuo), YinSha)).
    
    fixes = {
        "X-06": {
            "logic": "OR",
            "criteria": [
                {
                    "logic": "AND",
                    "criteria": [
                        {"target": "kids", "has_star": "po_jun"},
                        {"target": "kids", "has_star": "tan_lang"},
                        # Add Peach Blossom (simplified to TianYao/HongLuan for now as example)
                        {"target": "kids", "has_star": ["tian_yao", "hong_luan", "tian_xi"]}
                    ]
                },
                {
                    "logic": "AND",
                    "criteria": [
                        {"target": "spouse", "has_star": "po_jun"},
                        {"target": "spouse", "has_star": "tan_lang"},
                         {"target": "spouse", "has_star": ["tian_yao", "hong_luan", "tian_xi"]}
                    ]
                }
            ]
        },
        "X-07": {
             "logic": "AND",
             "criteria": [
                 {"target": "fortune", "has_star": "tian_yao"},
                 {"target": "fortune", "has_star": "hong_luan"},
                 # Chang + Qu (Simplified to present in Fortune for now, or Triangle if engine supported)
                 # Description says "Arch" (Gong Zhao).
                 # Let's add them as OR (at least one present? or both?) "Chang Qu" usually implies pair.
                 # Let's strictly require both for now to be safe, or at least one.
                 # "Chang Qu Arch" -> usually means they are in opposite or triangle.
                 # Without Arch logic, let's skip ChangQu specific check to avoid false negatives?
                 # OR better: Check if they are in Fortune (most direct interpretation for simple engine).
                 {
                     "logic": "AND",
                     "criteria": [
                         {"target": "fortune", "has_star": "wen_chang"},
                         {"target": "fortune", "has_star": "wen_qu"}
                     ]
                 }
             ]
        },
        "X-08": {
            "logic": "AND",
            "criteria": [
                # 1. Main Stars: Ju, TiaYin, TaiYang, TianTong, TianFu
                {
                    "logic": "OR",
                    "criteria": [
                        {"target": "life", "has_star": "ju_men"},
                        {"target": "life", "has_star": "tai_yin"},
                        {"target": "life", "has_star": "tai_yang"},
                        {"target": "life", "has_star": "tian_tong"},
                        {"target": "life", "has_star": "tian_fu"}
                    ]
                },
                # 2. Zuo OR You (or Both? Description says "Zuo You") -> Usually means pair or at least one.
                # Let's require at least one for now.
                {
                     "logic": "OR",
                     "criteria": [
                         {"target": "life", "has_star": "zuo_fu"},
                         {"target": "life", "has_star": "you_bi"}
                     ]
                },
                # 3. Hua Lu
                {"target": "life", "has_trans": "hua_lu"}
            ]
        },
        "C-02": {
             # C-02: Kids - QiSha OR QingYang
             # Logic was: AND(OR(QiSha, QingYang)) -> Correct.
             "logic": "AND",
             "criteria": [
                 {
                     "logic": "OR",
                     "criteria": [
                         {"target": "kids", "has_star": "qi_sha"},
                         {"target": "kids", "has_star": "qing_yang"}
                     ]
                 }
             ]
        }
    }

    count = 0
    for r in rules:
        if r["id"] in fixes:
            r["conditions"] = fixes[r["id"]]
            count += 1
            print(f"Fixed logic for {r['id']}")

    with open(RULE_FILE, 'w', encoding='utf-8') as f:
        json.dump(rules, f, ensure_ascii=False, indent=4)
    print(f"Total fixed: {count}")

if __name__ == "__main__":
    audit_and_fix_complex_conditions()
