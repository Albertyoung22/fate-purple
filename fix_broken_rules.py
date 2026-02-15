
import json

RULE_FILE = "ziwei_rules.json"

def fix_remaining_rules():
    with open(RULE_FILE, 'r', encoding='utf-8') as f:
        rules = json.load(f)

    # 1. P-05 (Kids Line - Liu Nian -> Static for now: Kids or Property has Kong Jie)
    # 2140 P-05
    for r in rules:
        if r["id"] == "P-05":
            print("Fixing P-05...")
            r["conditions"] = {
                "logic": "OR",
                "criteria": [
                    {
                        "target": "kids",
                        "has_star": ["di_kong", "di_jie"] # List = Any of
                    },
                    {
                        "target": "property",
                        "has_star": ["di_kong", "di_jie"]
                    }
                ]
            }

        # 2. P-07 (Property in Si Ma Di + Self-HuaLu/Ji + Wealth has XianChi)
        if r["id"] == "P-07":
            print("Fixing P-07...")
            r["conditions"] = {
                "logic": "AND",
                "criteria": [
                    {
                        "target": "property",
                        "has_branch": [2, 5, 8, 11] # Yin Shen Si Hai
                    },
                    {
                        "logic": "OR",
                        "criteria": [
                            {"target": "property", "has_trans": "hua_lu"}, 
                            {"target": "property", "has_trans": "hua_ji"}
                        ]
                    },
                    {
                        "target": "wealth",
                        "has_star": "xian_chi"
                    }
                ]
            }

        # 3. W-05 (Wealth - Lu (Same Palace)) -> Found via ID
        if r["id"] == "W-05":
             print("Fixing W-05...")
             # "Wealth - Lu (Same Palace)"
             r["conditions"] = {
                 "logic": "OR",
                 "criteria": [
                     {"target": "wealth", "has_star": "lu_cun"},
                     {"target": "wealth", "has_trans": "hua_lu"}
                 ]
             }

        # 4. H-04 (Health - Many Peach Stars)
        if r["id"] == "H-04":
            print("Fixing H-04...")
            # Detect ANY 2 from list
            peaches = ["hong_luan", "tian_xi", "xian_chi", "tian_yao", "mu_yu"]
            # To detect ">=2", we can brute force OR(Pair A, Pair B...)
            # 5C2 = 10 pairs.
            pairs = []
            for i in range(len(peaches)):
                for j in range(i+1, len(peaches)):
                     pairs.append(
                         {"logic": "AND", "criteria": [
                             {"target": "health", "has_star": peaches[i]},
                             {"target": "health", "has_star": peaches[j]}
                         ]}
                     )
            r["conditions"] = {
                "logic": "OR",
                "criteria": pairs
            }

        # 5. B-03 (Siblings - 2+ Pairs of Double Stars)
        if r["id"] == "B-03":
            print("Fixing B-03...")
            # Pairs: (zuo_fu, you_bi), (wen_chang, wen_qu), (tian_kui, tian_yue)
            p1_c = {"logic": "AND", "criteria": [{"target": "siblings", "has_star": "zuo_fu"}, {"target": "siblings", "has_star": "you_bi"}]}
            p2_c = {"logic": "AND", "criteria": [{"target": "siblings", "has_star": "wen_chang"}, {"target": "siblings", "has_star": "wen_qu"}]}
            p3_c = {"logic": "AND", "criteria": [{"target": "siblings", "has_star": "tian_kui"}, {"target": "siblings", "has_star": "tian_yue"}]}
            
            # OR( (P1+P2), (P1+P3), (P2+P3) )
            combos = [
                {"logic": "AND", "criteria": [p1_c, p2_c]},
                {"logic": "AND", "criteria": [p1_c, p3_c]},
                {"logic": "AND", "criteria": [p2_c, p3_c]}
            ]
            r["conditions"] = {"logic": "OR", "criteria": combos}


    with open(RULE_FILE, 'w', encoding='utf-8') as f:
        json.dump(rules, f, ensure_ascii=False, indent=4)
        
    print("Fixes applied.")

if __name__ == "__main__":
    fix_remaining_rules()
