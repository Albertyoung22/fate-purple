"""
紫微斗數特殊格局生成器
=================
生成常見的特殊格局規則 (Special Formations)，例如：
- 祿馬交馳
- 火貪/鈴貪
- 輔弼/昌曲拱命
- 三奇加會
- 雙祿交流
"""

import json
import os

PALACE_KEYS = [
    "life", "siblings", "spouse", "kids", "wealth", "health", 
    "travel", "friends", "career", "property", "fortune", "parents"
]

PALACE_NAMES = {
    "life": "命宮", "siblings": "兄弟宮", "spouse": "夫妻宮", "kids": "子女宮", 
    "wealth": "財帛宮", "health": "疾厄宮", "travel": "遷移宮", "friends": "奴僕宮", 
    "career": "官祿宮", "property": "田宅宮", "fortune": "福德宮", "parents": "父母宮"
}

def generate_formation_rules():
    rules = []
    base_id = 30000

    # 1. 火貪格 / 鈴貪格 (Huo Tan / Ling Tan) - 爆發格
    # 針對命宮、財帛、官祿
    for p in ["life", "wealth", "career"]:
        # 火貪
        rules.append({
            "id": f"SP-{base_id}",
            "category": p,
            "description": f"火貪格：{PALACE_NAMES[p]}有貪狼與火星同度。",
            "conditions": {
                "logic": "AND",
                "criteria": [
                    {"target": p, "has_star": ["tan_lang", "huo_xing"]}
                ]
            },
            "result": {
                "text": f"【火貪格】：{PALACE_NAMES[p]}火星與貪狼同度。主橫發，有突如其來的機運或財富，爆發力強。",
                "tags": ["富貴格", "爆發"]
            }
        })
        base_id += 1
        
        # 鈴貪
        rules.append({
            "id": f"SP-{base_id}",
            "category": p,
            "description": f"鈴貪格：{PALACE_NAMES[p]}有貪狼與鈴星同度。",
            "conditions": {
                "logic": "AND",
                "criteria": [
                    {"target": p, "has_star": ["tan_lang", "ling_xing"]}
                ]
            },
            "result": {
                "text": f"【鈴貪格】：{PALACE_NAMES[p]}鈴星與貪狼同度。主偏財，有機遇，但較火貪溫和持久。",
                "tags": ["富貴格", "爆發"]
            }
        })
        base_id += 1

    # 2. 祿馬交馳 (Lu Ma Jiao Chi) - 奔波生財
    # 命宮或財帛宮見祿存/化祿 + 天馬
    for p in ["life", "wealth", "travel"]:
        rules.append({
            "id": f"SP-{base_id}",
            "category": p,
            "description": f"祿馬交馳：{PALACE_NAMES[p]}有祿存(或化祿)與天馬同度。",
            "conditions": {
                "logic": "AND",
                "criteria": [
                    {"target": p, "has_star": ["tian_ma"]},
                    {"logic": "OR", "criteria": [
                        {"target": p, "has_star": ["lu_cun"]},
                        {"target": p, "has_trans": ["hua_lu"]}
                    ]}
                ]
            },
            "result": {
                "text": f"【祿馬交馳】：{PALACE_NAMES[p]}祿馬交馳。主奔波生財，愈動愈有錢，利於外地發展或變動中求財。",
                "tags": ["富貴格", "奔波"]
            }
        })
        base_id += 1

    # 3. 三奇加會 (San Qi Jia Hui) - 祿權科會命
    # 命宮的三方四正(命、財、官、遷) 同時見到 化祿、化權、化科
    # 這比較難用單一 condition 表達，因為不知道分佈在哪。
    # 簡化邏輯：檢查 chart wide? No, rule engine checks Palaces.
    # 其實可以寫一個針對 "命宮" 的複雜規則: (命or財or官or遷 has Lu) AND (命or財or官or遷 has Quan) AND (命or財or官or遷 has Ke)
    san_fang = ["life", "wealth", "career", "travel"]
    
    rules.append({
        "id": f"SP-{base_id}",
        "category": "life",
        "description": "三奇加會：命宮三方四正會齊化祿、化權、化科。",
        "conditions": {
            "logic": "AND",
            "criteria": [
                # Has Hua Lu in San Fang
                {"logic": "OR", "criteria": [{"target": p, "has_trans": ["hua_lu"]} for p in san_fang]},
                # Has Hua Quan in San Fang
                {"logic": "OR", "criteria": [{"target": p, "has_trans": ["hua_quan"]} for p in san_fang]},
                # Has Hua Ke in San Fang
                {"logic": "OR", "criteria": [{"target": p, "has_trans": ["hua_ke"]} for p in san_fang]}
            ]
        },
        "result": {
            "text": "【三奇加會】：命宮三方四正會齊祿權科。主名利雙收，運勢強旺，能成大器。",
            "tags": ["富貴格", "三奇"]
        }
    })
    base_id += 1

    # 4. 雙祿交流 (Double Lu)
    # 命宮三方見 祿存 與 化祿
    rules.append({
        "id": f"SP-{base_id}",
        "category": "life",
        "description": "雙祿交流：命宮三方四正見祿存與化祿。",
        "conditions": {
            "logic": "AND",
            "criteria": [
                {"logic": "OR", "criteria": [{"target": p, "has_star": ["lu_cun"]} for p in san_fang]},
                {"logic": "OR", "criteria": [{"target": p, "has_trans": ["hua_lu"]} for p in san_fang]}
            ]
        },
        "result": {
            "text": "【雙祿交流】：命宮三方見雙祿。財官雙美，資金充裕，機會多。",
            "tags": ["富貴格", "雙祿"]
        }
    })
    base_id += 1
    
    # 5. 輔弼拱命 (Fu Bi) - 左右在命宮三方
    rules.append({
        "id": f"SP-{base_id}",
        "category": "life",
        "description": "輔弼拱命：左輔右弼於命宮三方會照。",
        "conditions": {
            "logic": "AND",
            "criteria": [
                {"logic": "OR", "criteria": [{"target": p, "has_star": ["zuo_fu"]} for p in san_fang]},
                {"logic": "OR", "criteria": [{"target": p, "has_star": ["you_bi"]} for p in san_fang]}
            ]
        },
        "result": {
            "text": "【輔弼拱命】：多得貴人相助，人際關係佳，事業有助力。",
            "tags": ["貴人"]
        }
    })
    base_id += 1

     # 6. 昌曲拱命 (Chang Qu)
    rules.append({
        "id": f"SP-{base_id}",
        "category": "life",
        "description": "昌曲拱命：文昌文曲於命宮三方會照。",
        "conditions": {
            "logic": "AND",
            "criteria": [
                {"logic": "OR", "criteria": [{"target": p, "has_star": ["wen_chang"]} for p in san_fang]},
                {"logic": "OR", "criteria": [{"target": p, "has_star": ["wen_qu"]} for p in san_fang]}
            ]
        },
        "result": {
            "text": "【昌曲拱命】：主聰明才智，利於科名、學術、藝術發展。",
            "tags": ["才藝"]
        }
    })
    base_id += 1
    
    # 7. 魁鉞拱命 (Kui Yue)
    rules.append({
        "id": f"SP-{base_id}",
        "category": "life",
        "description": "魁鉞拱命：天魁天鉞於命宮三方會照。",
        "conditions": {
            "logic": "AND",
            "criteria": [
                {"logic": "OR", "criteria": [{"target": p, "has_star": ["tian_kui"]} for p in san_fang]},
                {"logic": "OR", "criteria": [{"target": p, "has_star": ["tian_yue"]} for p in san_fang]}
            ]
        },
        "result": {
            "text": "【魁鉞拱命】：主遇長輩貴人提攜，機遇佳。",
            "tags": ["貴人"]
        }
    })
    base_id += 1
    
    # 8. 陽梁昌祿 (Yang Liang Chang Lu) - 考試格
    # 太陽、天梁、文昌、祿存(或化祿) 三方會
    rules.append({
        "id": f"SP-{base_id}",
        "category": "life",
        "description": "陽梁昌祿：太陽、天梁、文昌、祿(化祿或祿存)會照。",
        "conditions": {
            "logic": "AND",
            "criteria": [
                {"logic": "OR", "criteria": [{"target": p, "has_star": ["tai_yang"]} for p in san_fang]},
                {"logic": "OR", "criteria": [{"target": p, "has_star": ["tian_liang"]} for p in san_fang]},
                {"logic": "OR", "criteria": [{"target": p, "has_star": ["wen_chang"]} for p in san_fang]},
                {"logic": "OR", "criteria": [
                    {"logic": "OR", "criteria": [{"target": p, "has_star": ["lu_cun"]} for p in san_fang]},
                    {"logic": "OR", "criteria": [{"target": p, "has_trans": ["hua_lu"]} for p in san_fang]}
                ]}
            ]
        },
        "result": {
            "text": "【陽梁昌祿】：利於考試、競爭、公職，學術成就高。",
            "tags": ["功名格"]
        }
    })
    base_id += 1
    
    return rules

def add_formation_rules_to_file():
    rules_file = "ziwei_rules.json"
    
    if os.path.exists(rules_file):
        with open(rules_file, 'r', encoding='utf-8') as f:
            existing_rules = json.load(f)
    else:
        existing_rules = []
        
    print(f"現有規則數量：{len(existing_rules)}")
    new_rules = generate_formation_rules()
    print(f"新增特殊格局數量：{len(new_rules)}")
    
    existing_ids = {rule.get("id") for rule in existing_rules}
    final_new_rules = [r for r in new_rules if r["id"] not in existing_ids]
    
    all_rules = existing_rules + final_new_rules
    
    with open(rules_file, 'w', encoding='utf-8') as f:
        json.dump(all_rules, f, ensure_ascii=False, indent=2)
    print("✅ 特殊格局規則更新完成")

if __name__ == "__main__":
    add_formation_rules_to_file()
