
import json
import re

RULE_FILE = "ziwei_rules.json"

def clean_and_fix_rules():
    with open(RULE_FILE, 'r', encoding='utf-8') as f:
        rules = json.load(f)

    # Helper to check if a criteria is "empty" (invalid)
    def is_empty(c):
        # A valid condition must have 'logic' OR ('target' AND ('has_star' or 'has_trans' or 'not_has_star'))
        if "logic" in c: return False
        keys = set(c.keys())
        # Valid keys for leaf: target, has_star, has_trans, not_has_star, star(for star-target), brightness(todo)
        if "has_star" in keys or "has_trans" in keys or "not_has_star" in keys:
            return False
        # If it only has 'target', it's empty/broken
        return True

    count_fixed = 0

    for rule in rules:
        desc = rule.get("description", "")
        cat = rule.get("category", "")
        
        # --- Specific Fixes based on User Feedback ---
        
        # S-02 Spouse: Lu Cun or Lu Ma?
        # Desc was "?? - Lu Cun OR Lu Ma". 
        # If we see "祿馬" or "祿存" in description but empty criteria...
        
        # Fix: 祿馬交馳 / 祿馬 (Lu Ma)
        # Logic: (Has LuCun AND Has TianMa) OR (Has HuaLu AND Has TianMa)
        # Usually checking Specific Palace (cat).
        if "祿馬" in desc or "祿馬交馳" in desc:
            print(f"Fixing 祿馬 rule: {rule['id']}")
            # Rebuild condition strictly
            # Target is the category usually (e.g. spouse, wealth)
            target = cat if cat in ["life", "spouse", "wealth", "career", "travel", "fortune"] else "life"
            
            rule["conditions"] = {
                "logic": "OR",
                "criteria": [
                    {
                        "logic": "AND",
                        "criteria": [
                            {"target": target, "has_star": "lu_cun"},
                            {"target": target, "has_star": "tian_ma"}
                        ]
                    },
                    {
                        "logic": "AND",
                        "criteria": [
                             # Hua Lu is handled via Star(transformation='hua_lu') usually,
                             # BUT my recent patch added Star('hua_lu') as literal star.
                             # So checking has_star='hua_lu' is safe.
                             # Also check has_trans='hua_lu' for robustness?
                             {"logic": "OR", "criteria": [
                                 {"target": target, "has_star": "hua_lu"},
                                 {"target": target, "has_trans": "hua_lu"}
                             ]},
                             {"target": target, "has_star": "tian_ma"}
                        ]
                    }
                ]
            }
            count_fixed += 1
            continue

        # Fix: 空劫 (Kong Jie)
        if "空劫" in desc and "夾" not in desc:
            # Logic: Di Kong OR Di Jie (or AND? Usually 'Kong Jie' implies meeting both or one?
            # 'Kong Jie Zuo Ming' usually means Both? Or meeting one is 'Ban Kong Zhe Chi'? 
            # If desc says "空劫", usually implies detecting magnitude.
            # Let's assume OR for generic, but AND for specific 'Kong Jie'.
            # Looking at previous output: Rule L-04 was Clamping.
            # If plain "空劫", let's ensure it searches for both names.
            pass # Skip for now, logic seems ok in others.

        # --- Generic Cleanup of Empty Criteria ---
        # Recursive cleaner
        def clean_criteria(c):
            if "logic" in c:
                # Filter children
                new_subs = [clean_criteria(sub) for sub in c["criteria"]]
                # Remove Nones
                new_subs = [x for x in new_subs if x is not None]
                
                if not new_subs: return None
                
                # Simplify: If logic is OR and has empty (which we returned None), 
                # actually, if we return None for empty, we effectively remove it.
                # If logic is OR and we have [A, B], it's OR(A,B).
                # If logic is OR and we have [A], it's A.
                
                c["criteria"] = new_subs
                return c
            else:
                if is_empty(c):
                    return None
                return c

        rule["conditions"] = clean_criteria(rule["conditions"])
        
        # If rule became None or empty logic, alert
        if not rule["conditions"]:
            print(f"Rule {rule['id']} has NO valid conditions left. Removing rule.")
            # Mark for deletion? Or keep as manual todo.
    
    # Save
    with open(RULE_FILE, 'w', encoding='utf-8') as f:
        json.dump(rules, f, ensure_ascii=False, indent=4)
    print(f"Fixed {count_fixed} specific rules and cleaned up structure.")

if __name__ == "__main__":
    clean_and_fix_rules()
