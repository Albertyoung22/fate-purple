
import json

RULE_FILE = "ziwei_rules.json"

def apply_fixes():
    with open(RULE_FILE, 'r', encoding='utf-8') as f:
        rules = json.load(f)

    # Dictionary of fixes
    # Key: Rule ID, Value: New Condition Dict
    fixes = {
        # C-04: Kids - Empty/Robbery + TianYao (Logic missing DiKong/DiJie)
        "C-04": {
             "logic": "AND",
             "criteria": [
                 {
                     "target": "kids",
                     "has_star": "tian_yao"
                 },
                 {
                     "logic": "OR",
                     "criteria": [
                         {"target": "kids", "has_star": "di_kong"},
                         {"target": "kids", "has_star": "di_jie"}
                     ]
                 }
             ]
        },
        # Ca-05: Career - HuaJi + Empty/Robbery (Logic missing DiKong/DiJie)
        "Ca-05": {
             "logic": "AND",
             "criteria": [
                 {"target": "career", "has_trans": "hua_ji"},
                 {
                     "logic": "OR",
                     "criteria": [
                         {"target": "career", "has_star": "di_kong"},
                         {"target": "career", "has_star": "di_jie"}
                     ]
                 }
             ]
        },
        # L-14: Life - (HuaJi/4Sha/TianXing) + No Lucky (Logic missing no_lucky check)
        "L-14": {
            "logic": "AND",
            "criteria": [
                {
                    "logic": "OR",
                    "criteria": [
                        {"target": "life", "has_trans": "hua_ji"},
                        {"target": "life", "has_star": "tian_xing"},
                        {"target": "life", "has_star": ["qing_yang", "tuo_luo", "huo_xing", "ling_xing"]}
                    ]
                },
                {"target": "life", "no_lucky_stars": True}
            ]
        },
        # S-03: Spouse - Empty/Robbery (Logic missing DiKong/DiJie, has null)
        "S-03": {
            "logic": "OR",
            "criteria": [
                {"target": "spouse", "has_star": ["di_kong"]},
                {"target": "spouse", "has_star": ["di_jie"]} # Using list or single str both supported now
            ]
        },
        # S-16: Spouse - (TianKu + Empty/Robbery)...
        # This one is complex. Updating the Ku + Kong/Jie part.
        "S-16": {
             "logic": "AND",
             "criteria": [
                 {"target": "spouse", "has_star": "tian_ku"},
                 {
                     "logic": "OR",
                     "criteria": [
                         {"target": "spouse", "has_star": "di_kong"},
                         {"target": "spouse", "has_star": "di_jie"}, 
                         # And the other parts of the rule (Male/Female specific) can be added as OR blocks if we knew gender
                         # But the rule desc says OR (Male...) OR (Female...)
                         # We can implement basic logic here, expanding if gender context available
                         # keeping original structure roughly but fixing Kong/Jie
                     ]
                 }
             ]
             # Note: The original S-16 logic was complex. We are simplifying for stability or needs careful rewrite.
             # The Audit found "Kong/Jie" missing.
             # Let's fully implement: (TianKu + (Kong OR Jie)) OR (...)
             # Wait, description says: (TianKu+Empty) OR (Male...) OR (Female...)
             # So if TianKu+KongJie is present, it triggers.
        },
        # S-17: Life JuMen-Ji + Spouse (GuaSu/Kong/Jie/TianKu)
        "S-17": {
            "logic": "AND",
            "criteria": [
                {"target": "life", "has_star": "ju_men", "has_trans": "hua_ji"},
                {
                    "target": "spouse",
                    "has_star": ["gua_su", "di_kong", "di_jie", "tian_ku"] # Any of these
                }
            ]
        },
        # W-01: Wealth - Empty/Robbery...
        "W-01": {
            "logic": "OR",
            "criteria": [
                {"target": "wealth", "has_star": "di_kong"},
                {"target": "wealth", "has_star": "di_jie"}
            ]
        },
        # X-04: Life/Fortune - LianPo(Mao/You) + HuoXing + Kong/Jie
        "X-04": {
             "logic": "AND",
             "criteria": [
                 # Lian Zhen + Po Jun only appear together in Mao/You naturally.
                 {"target": "life", "has_star": "lian_zhen"},
                 {"target": "life", "has_star": "po_jun"},
                 {"target": "life", "has_star": "huo_xing"},
                 {"target": "life", "has_star": ["di_kong", "di_jie"]}
             ]
             # Simplified to Life palace check based on risk.
        }
    }

    # Apply fixes
    count = 0
    for r in rules:
        if r["id"] in fixes:
            # For S-16 special handling or direct overwrite
            if r["id"] == "S-16":
                # Only patching the Kong/Jie check if possible, or overwriting
                # The audit said Kong/Jie missing.
                # Let's overwrite with robust logic
                r["conditions"] = {
                    "logic": "OR",
                    "criteria": [
                        {
                            "logic": "AND",
                            "criteria": [
                                {"target": "spouse", "has_star": "tian_ku"},
                                {"target": "spouse", "has_star": ["di_kong", "di_jie"]}
                            ]
                        },
                        {
                            # Male + TaiYin + Ji
                            "logic": "AND",
                            "criteria": [
                                {"target": "context", "gender": "male"},
                                {"target": "spouse", "has_star": "tai_yin", "has_trans": "hua_ji"},
                                {"target": "spouse", "has_star": "gu_chen"}
                            ]
                        },
                         {
                            # Female + TaiYang + Ji
                            "logic": "AND",
                            "criteria": [
                                {"target": "context", "gender": "female"},
                                {"target": "spouse", "has_star": "tai_yang", "has_trans": "hua_ji"},
                                {"target": "spouse", "has_star": "gua_su"}
                            ]
                        }
                    ]
                }
            else:
                r["conditions"] = fixes[r["id"]]
            
            count += 1

    with open(RULE_FILE, 'w', encoding='utf-8') as f:
        json.dump(rules, f, ensure_ascii=False, indent=4)

    print(f"Fixed {count} rules.")

if __name__ == "__main__":
    apply_fixes()
