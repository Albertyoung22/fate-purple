"""
宮干四化規則生成器 (進階版)
=================
自動生成全方位的宮干四化規則，包含：
1. 命宮自化 (祿權科忌)
2. 12宮互飛 (例如：夫妻宮飛忌入命宮)
3. 根據「宮位飛入」心法，生成對應的解釋。
"""

import json
import os

# --- 資料定義 ---

PALACE_NAMES = {
    "life": "命宮", "siblings": "兄弟宮", "spouse": "夫妻宮", "kids": "子女宮", 
    "wealth": "財帛宮", "health": "疾厄宮", "travel": "遷移宮", "friends": "奴僕宮", 
    "career": "官祿宮", "property": "田宅宮", "fortune": "福德宮", "parents": "父母宮"
}

PALACE_KEYS = [
    "life", "siblings", "spouse", "kids", "wealth", "health", 
    "travel", "friends", "career", "property", "fortune", "parents"
]

TRANSFORMATIONS = {
    "hua_lu": "化祿", "hua_quan": "化權", "hua_ke": "化科", "hua_ji": "化忌"
}

# --- 解讀模板 (Simplified for automated generation) ---
# Source -> Target : Meaning
# 這裡定義一些通用的飛伏解讀邏輯

def get_flying_meaning(source, target, trans):
    """
    根據來源宮、目標宮、化星，生成解讀。
    這是一個簡化的自動生成邏輯，盡量涵蓋大方向。
    """
    s_name = PALACE_NAMES[source]
    t_name = PALACE_NAMES[target]
    
    meaning = ""
    
    if trans == "hua_lu":
        meaning = f"{s_name}的機緣、好處、資金，流向了{t_name}。"
        if source == target: meaning = f"{s_name}自化祿：該宮位能量充足，展現樂觀、順利、自給自足之象。"
        elif target == "life": meaning = f"{s_name}對我有情，帶給我好處、財祿或快樂。"
        elif source == "life": meaning = f"我對{t_name}的人事物投入心力，樂於付出，且能獲得回饋。"
        
    elif trans == "hua_quan":
        meaning = f"{s_name}對{t_name}有控制欲、影響力，或帶來競爭與壓力。"
        if source == target: meaning = f"{s_name}自化權：該宮位展現強勢、主觀、積極爭取之象。"
        elif target == "life": meaning = f"{s_name}想管束我，給我壓力，或賦予我權力與責任。"
        elif source == "life": meaning = f"我對{t_name}展現企圖心，想要掌控局勢，或積極拓展。"

    elif trans == "hua_ke":
        meaning = f"{s_name}與{t_name}有情義相挺，關係和諧，或有貴人相助。"
        if source == target: meaning = f"{s_name}自化科：該宮位展現文雅、理性、重名聲與表面功夫。"
        elif target == "life": meaning = f"{s_name}是我的貴人，帶給我名聲或精神上的支持。"
        elif source == "life": meaning = f"我對{t_name}展現關懷，以理服人，注重名聲與形象。"

    elif trans == "hua_ji":
        meaning = f"{s_name}帶給{t_name}困擾、虧欠、壓力或變動。"
        if source == target: meaning = f"{s_name}自化忌：該宮位氣場不穩，自我消抵，容易反覆無常，甚至有損。"
        elif target == "life": meaning = f"{s_name}會來糾纏我，讓我不舒服，或我欠{s_name}債。"
        elif source == "life": meaning = f"我特別執著於{t_name}，為其操心煩惱，甚至因為{t_name}而受損。"
        elif target == "wealth": meaning = f"{s_name}會損耗我的錢財，或我因{s_name}而破財。"
        elif target == "career": meaning = f"{s_name}會干擾我的工作，或我工作上因{s_name}而有阻礙。"

    # 特定宮位組合的特殊意義 (覆蓋通用意義)
    if source == "life" and target == "kids" and trans == "hua_lu":
        meaning = "這表示你對子女極好，願意為他們付出金錢與心力，親子關係融洽；或者你桃花運不錯，異性緣佳。"
    if source == "life" and target == "wealth" and trans == "hua_ji":
        meaning = "命宮飛忌入財帛：你對錢財很執著，很想賺錢但過程辛苦，且可能不善理財，財來財去。"
    if source == "spouse" and target == "life" and trans == "hua_ji":
        meaning = "夫妻飛忌入命：配偶管你管得嚴，或者配偶依賴你，讓你感到婚姻帶來的壓力。"

    return meaning

# --- 規則生成函數 ---

def generate_all_flying_rules():
    """
    生成所有宮位之間的飛化規則 (12 x 12 x 4 = 576 條規則)
    """
    rules = []
    rule_id_base = 20000
    
    for source in PALACE_KEYS:
        for target in PALACE_KEYS:
            for trans_key, trans_name in TRANSFORMATIONS.items():
                
                # 跳過所有自化 (已有單獨處理或通用處理，這裡為了完整性可以包含，但要標記清楚)
                # 自化規則我們分開寫比較好，這裡先包含，用 logic 區分
                
                description = f"{PALACE_NAMES[source]}宮干飛{trans_name}入{PALACE_NAMES[target]}"
                meaning = get_flying_meaning(source, target, trans_key)
                
                rule = {
                    "id": f"FH-{rule_id_base}",
                    "category": target, # 歸類在目標宮位，因為影響的是目標
                    "type": "flying_hua",
                    "description": description,
                    "conditions": {
                        "target": target,
                        "flying_from": source,
                        "trans": trans_key
                    },
                    "result": {
                        "text": f"【{description}】：{meaning}",
                        "tags": ["宮干四化", "飛星", f"{PALACE_NAMES[source]}飛{PALACE_NAMES[target]}"]
                    }
                }
                
                rules.append(rule)
                rule_id_base += 1
                
    return rules

def add_rules_to_file():
    """
    將生成的規則添加到 ziwei_rules.json
    """
    rules_file = "ziwei_rules.json"
    
    # 載入現有規則
    if os.path.exists(rules_file):
        with open(rules_file, 'r', encoding='utf-8') as f:
            existing_rules = json.load(f)
    else:
        existing_rules = []
    
    print(f"現有規則數量：{len(existing_rules)}")
    
    # 生成新規則
    new_rules = generate_all_flying_rules()
    
    print(f"新增規則數量：{len(new_rules)}")
    
    # 為了避免重複，我們可以先刪除舊的 FH- 開頭的規則 (如果有)
    # 或者簡單一點，直接附加，但過濾 ID
    
    existing_ids = {rule.get("id") for rule in existing_rules}
    
    # Filter out duplicates based on ID
    final_new_rules = [r for r in new_rules if r["id"] not in existing_ids]
    
    print(f"實際寫入新規則：{len(final_new_rules)} (已扣除重複 ID)")
    
    # 合併
    all_rules = existing_rules + final_new_rules
    
    # 備份
    if os.path.exists(rules_file):
        backup = rules_file.replace(".json", "_backup_v2.json")
        with open(backup, 'w', encoding='utf-8') as f:
            json.dump(existing_rules, f, ensure_ascii=False, indent=2)
            
    # 寫入
    with open(rules_file, 'w', encoding='utf-8') as f:
        json.dump(all_rules, f, ensure_ascii=False, indent=2)
        
    print("✅ 規則庫更新完成")

if __name__ == "__main__":
    print("生成全方位飛星規則...")
    
    # Preview
    sample = generate_all_flying_rules()
    print("預覽前 5 條規則：")
    for r in sample[:5]:
        print(f"{r['id']}: {r['result']['text']}")
        
    x = input("確認寫入? (y/n): ")
    if x.lower() == 'y':
        add_rules_to_file()
