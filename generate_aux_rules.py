"""
紫微斗數：輔助格局與長生12神規則生成器
======================================
1. 六吉星入命、財、官
2. 六煞星入命、財、官
3. 十二長生入命宮規則
"""

import json
import os

PALACE_NAMES = {
    "life": "命宮", "siblings": "兄弟宮", "spouse": "夫妻宮", "kids": "子女宮", 
    "wealth": "財帛宮", "health": "疾厄宮", "travel": "遷移宮", "friends": "奴僕宮", 
    "career": "官祿宮", "property": "田宅宮", "fortune": "福德宮", "parents": "父母宮"
}

# 12 Life Stages (match py keys in STAR_MAP)
LIFE_STAGES = [
    ("chang_sheng", "長生", "生命力強，充滿希望，長壽。"),
    ("mu_yu", "沐浴", "桃花，不穩定，易受誘惑，喜新厭舊。"),
    ("guan_dai", "冠帶", "喜慶，發展，爭取榮譽。"),
    ("ling_guan", "臨官", "獨立，有擔當，事業發展期。"),
    ("di_wang", "帝旺", "極盛之時，運勢強，但宜防盛極而衰。"),
    ("shuai", "衰", "氣勢轉弱，保守為宜。"),
    ("bing", "病", "氣虛，多病，消極。"),
    ("si", "死", "無生氣，停滯，結束。"),
    ("mu", "墓", "收藏，積蓄，保守，不開朗。"),
    ("jue", "絕", "到了谷底，也是新生的轉折點。"),
    ("tai", "胎", "懷孕，醞釀，新的希望。"),
    ("yang", "養", "培育，休養生息，等待時機。")
]

LUCKY_STARS = [
    ("zuo_fu", "左輔"), ("you_bi", "右弼"), 
    ("tian_kui", "天魁"), ("tian_yue", "天鉞"),
    ("wen_chang", "文昌"), ("wen_qu", "文曲")
]

SHA_STARS = [
    ("qing_yang", "擎羊"), ("tuo_luo", "陀羅"),
    ("huo_xing", "火星"), ("ling_xing", "鈴星"),
    ("di_kong", "地空"), ("di_jie", "地劫")
]

def generate_aux_rules():
    rules = []
    base_id = 40000
    
    # 1. 十二長生坐命
    for code, name, desc in LIFE_STAGES:
        rules.append({
            "id": f"AX-{base_id}",
            "category": "life",
            "description": f"命宮坐{name}。",
            "conditions": {
                "logic": "AND",
                "criteria": [
                    {"target": "life", "has_star": [code]} # The engine detects 'life-stage' type as star
                ]
            },
            "result": {
                "text": f"【命坐{name}】：{desc}",
                "tags": ["長生十二神"]
            }
        })
        base_id += 1
        
    # 2. 六吉星入命
    for code, name in LUCKY_STARS:
        rules.append({
            "id": f"AX-{base_id}",
            "category": "life",
            "description": f"命宮有{name}。",
            "conditions": {
                "logic": "AND",
                "criteria": [
                    {"target": "life", "has_star": [code]}
                ]
            },
            "result": {
                "text": f"【命坐{name}】：主貴人運佳，{name}入命有利於事業與人際發展。",
                "tags": ["六吉星"]
            }
        })
        base_id += 1

    # 3. 六煞星入命
    for code, name in SHA_STARS:
        rules.append({
            "id": f"AX-{base_id}",
            "category": "life",
            "description": f"命宮有{name}。",
            "conditions": {
                "logic": "AND",
                "criteria": [
                    {"target": "life", "has_star": [code]}
                ]
            },
            "result": {
                "text": f"【命坐{name}】：主性格剛毅或波折。{name}入命需防意外或小人，宜修身養性。",
                "tags": ["六煞星"]
            }
        })
        base_id += 1

    return rules

def add_aux_rules_to_file():
    rules_file = "ziwei_rules.json"
    
    if os.path.exists(rules_file):
        with open(rules_file, 'r', encoding='utf-8') as f:
            existing_rules = json.load(f)
    else:
        existing_rules = []
        
    print(f"現有規則數量：{len(existing_rules)}")
    new_rules = generate_aux_rules()
    print(f"新增輔助規則數量：{len(new_rules)}")
    
    existing_ids = {rule.get("id") for rule in existing_rules}
    final_new_rules = [r for r in new_rules if r["id"] not in existing_ids]
    
    all_rules = existing_rules + final_new_rules
    
    with open(rules_file, 'w', encoding='utf-8') as f:
        json.dump(all_rules, f, ensure_ascii=False, indent=2)
    print("✅ 輔助規則 (長生/吉煞) 更新完成")

if __name__ == "__main__":
    add_aux_rules_to_file()
