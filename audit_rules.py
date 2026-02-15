
import json

def audit_rules_logic():
    with open("ziwei_rules.json", "r", encoding="utf-8") as f:
        rules = json.load(f)

    print(f"Auditing {len(rules)} rules...")

    suspicious = []

    for r in rules:
        desc = r.get("description", "")
        cond = r.get("conditions")
        
        # 1. Check for "null" conditions
        if not cond:
            suspicious.append(f"{r['id']}: Conditions are NULL")
            continue

        # 2. Check for "Empty" logic
        if "logic" not in cond and not cond.get("criteria") and not cond.get("target"):
             suspicious.append(f"{r['id']}: Empty Logic")
             continue
             
        # 3. Check specific keywords in description vs implementation
        
        # "無吉" (No Lucky)
        if "無吉" in desc:
            # Recursively check for no_lucky_stars
            if not recursive_find_key(cond, "no_lucky_stars"):
                 suspicious.append(f"{r['id']}: Described '無吉' but 'no_lucky_stars' not found in logic.")

        # "單星" (Single star) -> usually implies no_lucky or specific exclusion
        # if "單星" in desc:
        #    pass 

        # "四馬" (Four Horses)
        if "四馬" in desc or "寅申巳亥" in desc:
             if not recursive_find_key(cond, "has_branch"):
                  suspicious.append(f"{r['id']}: Described '四馬/寅申巳亥' but 'has_branch' not found.")

        # "空劫" (Empty/Robbery)
        if "空劫" in desc:
             if not recursive_find_value(cond, "has_star", ["di_kong", "di_jie"]):
                 suspicious.append(f"{r['id']}: Described '空劫' but DiKong/DiJie not found.")

        # "權" (Power)
        if "權" in desc and "權" not in r["result"]["text"]:
             if not recursive_find_value(cond, "has_trans", "hua_quan"):
                  # susp... maybe referencing just the star itself?
                  pass

    print(f"Found {len(suspicious)} potential issues:")
    for s in suspicious:
        print(s)

def recursive_find_key(d, key_to_find):
    if isinstance(d, dict):
        if key_to_find in d: return True
        for k, v in d.items():
            if recursive_find_key(v, key_to_find): return True
    elif isinstance(d, list):
        for item in d:
             if recursive_find_key(item, key_to_find): return True
    return False

def recursive_find_value(d, target_key, target_val):
    if isinstance(d, dict):
        for k, v in d.items():
            if k == target_key:
                # Check value match
                # if target_val is list, check overlap?
                # if v is list
                if isinstance(target_val, list):
                     # any match
                     vals_to_check = v if isinstance(v, list) else [v]
                     if any(t in vals_to_check for t in target_val): return True
                else: 
                     if v == target_val or (isinstance(v, list) and target_val in v): return True

            if recursive_find_value(v, target_key, target_val): return True
    elif isinstance(d, list):
        for item in d:
             if recursive_find_value(item, target_key, target_val): return True
    return False

if __name__ == "__main__":
    audit_rules_logic()
