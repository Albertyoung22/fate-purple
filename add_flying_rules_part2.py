
import json

RULE_FILE = "ziwei_rules.json"

def add_flying_rules_part2():
    with open(RULE_FILE, 'r', encoding='utf-8') as f:
        rules = json.load(f)

    new_rules = []

    # 4H-21: Spouse -> Life (Lu)
    new_rules.append({
        "id": "4H-21",
        "category": "spouse",
        "description": "夫妻宮宮干化祿 → 飛入命宮。",
        "conditions": { "target": "life", "flying_from": "spouse", "trans": "hua_lu" },
        "result": { "text": "配偶對自己很好，而且願意把錢花在自己身上。", "tags": ["marriage"] }
    })

    # 4H-22: Spouse -> Life (Quan)
    new_rules.append({
        "id": "4H-22",
        "category": "spouse",
        "description": "夫妻宮宮干化權 → 飛入命宮。",
        "conditions": { "target": "life", "flying_from": "spouse", "trans": "hua_quan" },
        "result": { "text": "配偶會把家中的權力交給你掌管。", "tags": ["marriage"] }
    })

    # 4H-23: Spouse -> Life (Ji)
    # Note: Description mentions "If spouse stars are bad...", but fundamental rule is Ji->Life.
    # We implement the core flying rule.
    new_rules.append({
        "id": "4H-23",
        "category": "spouse",
        "description": "夫妻宮宮干化忌 → 飛入命宮。",
        "conditions": { "target": "life", "flying_from": "spouse", "trans": "hua_ji" },
        "result": { "text": "配偶很愛嫌棄你；若夫妻宮本身星曜又差，代表配偶對你無情無義。", "tags": ["marriage"] }
    })

    # 4H-24: Spouse has Birth Quan OR Self Quan
    new_rules.append({
        "id": "4H-24",
        "category": "spouse",
        "description": "夫妻宮有生年化權 (或自化權)。",
        "conditions": {
            "logic": "OR",
            "criteria": [
                { "target": "spouse", "has_trans": "hua_quan" },
                { "target": "spouse", "self_trans": "hua_quan" }
            ]
        },
        "result": { "text": "夫妻兩個人都想當老大，都要掌權，互不相讓。", "tags": ["marriage"] }
    })

    # 4H-25: Spouse Bad Stars + Fly Lu -> Life
    # "Bad stars" is subjective, usually Sha stars (QingYang, TuoLuo, HuoXing, LingXing, DiKong, KiJie).
    new_rules.append({
        "id": "4H-25",
        "category": "spouse",
        "description": "夫妻宮星曜差(爛)，但宮干化祿 → 飛入命宮。",
        "conditions": {
            "logic": "AND",
            "criteria": [
                {
                    "//": "Spouse has Sha stars",
                    "logic": "OR",
                    "criteria": [
                        {"target": "spouse", "has_star": "qing_yang"},
                        {"target": "spouse", "has_star": "tuo_luo"},
                        {"target": "spouse", "has_star": "huo_xing"},
                        {"target": "spouse", "has_star": "ling_xing"},
                        {"target": "spouse", "has_star": "di_kong"},
                        {"target": "spouse", "has_star": "di_jie"}
                    ]
                },
                { "target": "life", "flying_from": "spouse", "trans": "hua_lu" }
            ]
        },
        "result": { "text": "雖然配偶條件差或甚至外遇，但對正宮(你)還是有感情、有情義的 (可以平衡)。", "tags": ["marriage"] }
    })

    # 4H-26: Spouse Bad Stars + Life Fly Lu -> Spouse
    new_rules.append({
        "id": "4H-26",
        "category": "life",
        "description": "夫妻宮星曜差(爛)，且命宮宮干化祿 → 飛入夫妻宮。",
        "conditions": {
            "logic": "AND",
            "criteria": [
                 {
                    "logic": "OR",
                    "criteria": [
                        {"target": "spouse", "has_star": "qing_yang"},
                        {"target": "spouse", "has_star": "tuo_luo"},
                        {"target": "spouse", "has_star": "huo_xing"},
                        {"target": "spouse", "has_star": "ling_xing"},
                        {"target": "spouse", "has_star": "di_kong"},
                        {"target": "spouse", "has_star": "di_jie"}
                    ]
                },
                { "target": "spouse", "flying_from": "life", "trans": "hua_lu" }
            ]
        },
        "result": { "text": "即使配偶對你很狠心、很爛，你還是心甘情願為對方做牛做馬。", "tags": ["marriage"] }
    })

    # 4H-27: Female + Kids -> Health (Lu OR Ji)
    new_rules.append({
        "id": "4H-27",
        "category": "kids",
        "description": "子女宮宮干化祿 OR 化忌 → 飛入疾厄宮 (女命)。",
        "conditions": {
            "logic": "AND",
            "criteria": [
                { "target": "context", "gender": "F" },
                {
                    "logic": "OR",
                    "criteria": [
                        { "target": "health", "flying_from": "kids", "trans": "hua_lu" },
                        { "target": "health", "flying_from": "kids", "trans": "hua_ji" }
                    ]
                }
            ]
        },
        "result": { "text": "性慾強烈。", "tags": [] }
    })

    # 4H-28: Female + Flow Kids (Self Lu/Ji) + Base Peach
    # NOTE: "Flow Kids" requires dynamic engine support for flow palaces which might not be fully exposed in rules.
    # Assuming "kids" target usually refers to base unless specified.
    # BUT description says "Flow Kids" (Liu Nian). 
    # If the engine creates "flow_kids" palace, we use it. If not, this rule might only work in Flow Mode.
    # For now, I will use "kids" but add a note or assume typical usage.
    # Since "4H" refers to dynamic flying, likely applied on current chart.
    # I'll use "kids" and assume user switches context to Flow.
    # Base Peach: TianYao, HongLuan, TianXi, XianChi, MuYu, etc.
    new_rules.append({
        "id": "4H-28",
        "category": "kids",
        "description": "流年子女自化祿 OR 自化忌 + 本命有桃花星 (女命)。",
        "conditions": {
            "logic": "AND",
            "criteria": [
                { "target": "context", "gender": "F" },
                {
                    "logic": "OR",
                    "criteria": [
                        { "target": "kids", "self_trans": "hua_lu" },
                        { "target": "kids", "self_trans": "hua_ji" }
                    ]
                },
                {
                    "//": "Life has Peach Stars",
                    "logic": "OR",
                    "criteria": [
                        {"target": "life", "has_star": "tian_yao"},
                        {"target": "life", "has_star": "hong_luan"},
                        {"target": "life", "has_star": "tian_xi"},
                        {"target": "life", "has_star": "xian_chi"},
                        {"target": "life", "has_star": "mu_yu"}
                    ]
                }
            ]
        },
        "result": { "text": "該年容易跟「有家室」的男人交往。", "tags": ["marriage"] }
    })

    # 4H-29: Wealth Self Lu
    new_rules.append({
        "id": "4H-29",
        "category": "wealth",
        "description": "財帛宮宮干自化祿。",
        "conditions": { "target": "wealth", "self_trans": "hua_lu" },
        "result": { "text": "有賺錢能力，但錢左手進右手出，存不住。", "tags": ["wealth"] }
    })

    # 4H-30: Wealth Self Ji
    new_rules.append({
        "id": "4H-30",
        "category": "wealth",
        "description": "財帛宮宮干自化忌。",
        "conditions": { "target": "wealth", "self_trans": "hua_ji" },
        "result": { "text": "賺得比較少，而且錢也存不住。", "tags": ["wealth"] }
    })

    # 4H-31: Wealth -> Career (Ji)
    new_rules.append({
        "id": "4H-31",
        "category": "wealth",
        "description": "財帛宮宮干化忌 → 飛入官祿宮。",
        "conditions": { "target": "career", "flying_from": "wealth", "trans": "hua_ji" },
        "result": { "text": "敢借錢來做生意(投資事業)，而且獲利通常比利息高出好幾倍。", "tags": ["wealth", "career"] }
    })

    # 4H-32: Friends -> Life (Ji)
    new_rules.append({
        "id": "4H-32",
        "category": "friends",
        "description": "奴僕宮(交友)宮干化忌 → 飛入命宮。",
        "conditions": { "target": "life", "flying_from": "friends", "trans": "hua_ji" },
        "result": { "text": "朋友常常會來煩你，造成你的困擾。", "tags": [] }
    })

    # 4H-33: Career -> Life (Ji)
    new_rules.append({
        "id": "4H-33",
        "category": "career",
        "description": "官祿宮(事業)宮干化忌 → 飛入命宮。",
        "conditions": { "target": "life", "flying_from": "career", "trans": "hua_ji" },
        "result": { "text": "工作的事情常讓你煩心，或者工作太忙來煩你。", "tags": ["career"] }
    })

    # 4H-34: Property -> Life (Ji)
    new_rules.append({
        "id": "4H-34",
        "category": "property",
        "description": "田宅宮宮干化忌 → 飛入命宮。",
        "conditions": { "target": "life", "flying_from": "property", "trans": "hua_ji" },
        "result": { "text": "房子、家庭的問題常來煩你，讓你操心。", "tags": [] }
    })

    # 4H-35: Fortune -> Life (Lu)
    new_rules.append({
        "id": "4H-35",
        "category": "fortune",
        "description": "福德宮宮干化祿 → 飛入命宮。",
        "conditions": { "target": "life", "flying_from": "fortune", "trans": "hua_lu" },
        "result": { "text": "你對自己很好，懂得享受，通常自己先享受完了再說。", "tags": ["personality"] }
    })

    # 4H-36: Fortune -> Life (Ji)
    new_rules.append({
        "id": "4H-36",
        "category": "fortune",
        "description": "福德宮宮干化忌 → 飛入命宮。",
        "conditions": { "target": "life", "flying_from": "fortune", "trans": "hua_ji" },
        "result": { "text": "沒理性、愛計較、盧小小(台語)，容易自尋煩惱。", "tags": ["personality"] }
    })

    # 4H-37: Birth Ji in Spouse (Clashes Career)
    new_rules.append({
        "id": "4H-37",
        "category": "spouse",
        "description": "生年化忌在夫妻宮 (沖官祿宮)。",
        "conditions": { "target": "spouse", "has_trans": "hua_ji" },
        "result": { "text": "事業變動大，個性情緒化，經常換工作。", "tags": ["career", "marriage"] }
    })

    # 4H-38: Birth Ji in Career (Clashes Spouse)
    new_rules.append({
        "id": "4H-38",
        "category": "career",
        "description": "生年化忌在官祿宮 (沖夫妻宮)。",
        "conditions": { "target": "career", "has_trans": "hua_ji" },
        "result": { "text": "夫妻之間非常會吵架。", "tags": ["marriage"] }
    })

    # 4H-39: Property OR Wealth -> Kids (Ji)
    new_rules.append({
        "id": "4H-39",
        "category": "kids",
        "description": "田宅宮 OR 財帛宮宮干化忌 → 飛入子女宮。",
        "conditions": {
            "logic": "OR",
            "criteria": [
                { "target": "kids", "flying_from": "property", "trans": "hua_ji" },
                { "target": "kids", "flying_from": "wealth", "trans": "hua_ji" }
            ]
        },
        "result": { "text": "很捨得為子女花錢。", "tags": [] }
    })

    # 4H-40: Burn Ji in Property
    new_rules.append({
        "id": "4H-40",
        "category": "property",
        "description": "田宅宮有生年化忌。",
        "conditions": { "target": "property", "has_trans": "hua_ji" },
        "result": { "text": "絕對不要替人作保；女性要注意子宮方面的健康問題。", "tags": [] }
    })

    # 4H-41: Kids -> Wealth (Lu)
    new_rules.append({
        "id": "4H-41",
        "category": "wealth",
        "description": "子女宮宮干化祿 → 飛入財帛宮。",
        "conditions": { "target": "wealth", "flying_from": "kids", "trans": "hua_lu" },
        "result": { "text": "適合從事與小孩有關的生意/行業。", "tags": ["career"] }
    })

    # 4H-42: 4 Trans in One Palace
    # Any palace has AND(Lu, Quan, Ke, Ji).
    palaces = ["life", "siblings", "spouse", "kids", "wealth", "health", 
               "travel", "friends", "career", "property", "fortune", "parents"]
    
    crit_42 = []
    for p in palaces:
        crit_42.append({
            "logic": "AND",
            "criteria": [
                { "target": p, "has_trans": "hua_lu" },
                { "target": p, "has_trans": "hua_quan" },
                { "target": p, "has_trans": "hua_ke" },
                { "target": p, "has_trans": "hua_ji" }
            ]
        })

    new_rules.append({
        "id": "4H-42",
        "category": "generic",
        "description": "祿、權、科、忌 四顆星聚在同一個宮位。",
        "conditions": { "logic": "OR", "criteria": crit_42 },
        "result": { "text": "成功的過程會比較辛苦，但結局屬於好的。", "tags": [] }
    })

    # 4H-43: Friends -> Spouse (Lu)
    new_rules.append({
        "id": "4H-43",
        "category": "spouse",
        "description": "奴僕宮(朋友)宮干化祿 → 飛入夫妻宮。",
        "conditions": { "target": "spouse", "flying_from": "friends", "trans": "hua_lu" },
        "result": { "text": "朋友對你的配偶太好，婚姻容易變質 (要注意第三者)。", "tags": ["marriage"] }
    })

    # 4H-44: Life has Quan AND Ji
    new_rules.append({
        "id": "4H-44",
        "category": "life",
        "description": "命宮同時有化權、化忌。",
        "conditions": {
            "logic": "AND",
            "criteria": [
                { "target": "life", "has_trans": "hua_quan" },
                { "target": "life", "has_trans": "hua_ji" }
            ]
        },
        "result": { "text": "個性無情，翻臉跟翻書一樣快。", "tags": ["personality"] }
    })

    # Append to Main File
    rules = [r for r in rules if r["id"] not in [nr["id"] for nr in new_rules]]
    rules.extend(new_rules)

    with open(RULE_FILE, 'w', encoding='utf-8') as f:
        json.dump(rules, f, ensure_ascii=False, indent=4)
    print(f"Added {len(new_rules)} new 4H rules (Part 2).")

if __name__ == "__main__":
    add_flying_rules_part2()
