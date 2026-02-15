
import json

RULE_FILE = "ziwei_rules.json"

def add_flying_rules():
    with open(RULE_FILE, 'r', encoding='utf-8') as f:
        rules = json.load(f)

    new_rules = []
    
    # helper for 4H-01
    palaces = ["life", "siblings", "spouse", "kids", "wealth", "health", 
               "travel", "friends", "career", "property", "fortune", "parents"]

    # 4H-01: Generic Self-Lu on Birth-Lu
    criterias_01 = []
    for p in palaces:
        criterias_01.append({
            "target": p,
            "has_trans": "hua_lu",
            "self_trans": "hua_lu"
        })
    
    new_rules.append({
        "id": "4H-01",
        "category": "generic",
        "description": "某宮位出現祿出 (原本就有生年化祿，該宮宮干又讓這顆星「自化祿」)。",
        "conditions": {
            "logic": "OR",
            "criteria": criterias_01
        },
        "result": {
            "text": "祿出為忌：原本的好處會因過度或自我消耗而變成壞事 (由吉轉凶)。",
            "tags": []
        }
    })

    # 4H-02: Life Self-Lu
    new_rules.append({
        "id": "4H-02",
        "category": "life",
        "description": "命宮宮干讓自己「自化祿」。",
        "conditions": {
            "target": "life",
            "self_trans": "hua_lu"
        },
        "result": {
            "text": "人生比較愜意、不辛苦，但也比較沒有積極的作為 (美賣)。",
            "tags": ["personality"]
        }
    })

    # 4H-03: Life Self-Ji
    new_rules.append({
        "id": "4H-03",
        "category": "life",
        "description": "命宮宮干讓自己「自化忌」。",
        "conditions": {
            "target": "life",
            "self_trans": "hua_ji"
        },
        "result": {
            "text": "個性較勞碌、辛苦，為人實在，不會去佔別人便宜。",
            "tags": ["personality"]
        }
    })

    # 4H-04 to 4H-07: Generic Flying from Life to ANY
    # "Any" logic requires checking if flying to ANY palace.
    # We can use OR logic across all other 11 palaces?
    # Or just generic check "flying_from": "life".
    # Implementation: My `check_condition` supports `flying_from` on a specific target.
    # So to check "Fly to Any", I need OR(Fly to Siblings, Fly to Spouse...)
    # But wait, 4H-04... are described as "Fly into *one* palace". 
    # The result says "You treat people in *that* palace well".
    # Since the result text is generic ("that palace"), this rule doesn't output "You treat spouse well".
    # It outputs "You treat that palace well".
    # This is less useful than specific rules.
    # But I will implement it as requested.
    # To avoid triggering 12 times or overlapping with specific rules 4H-08+, maybe I skip them?
    # No, user asked specific list. I add them.
    # Implementation: OR condition for all 11 targets (excluding self? Self-fly is Self-Hua).
    
    for rid, trans, txt in [
        ("4H-04", "hua_lu", "你對那個宮位的人事物很有情有義，對他們好。"),
        ("4H-05", "hua_quan", "你會把權力下放給該宮位的人，或者是你想掌控該宮位的事物。"),
        ("4H-06", "hua_ke", "你與該宮位的人是君子之交，緣分是細水長流的，比較隨緣。"),
        ("4H-07", "hua_ji", "你會特別在意、操心那個宮位，甚至會去煩那個宮位的人。")
    ]:
        # Generating OR for all non-life palaces
        crit = []
        for p in palaces:
            if p == "life": continue
            crit.append({
                "target": p,
                "flying_from": "life",
                "trans": trans
            })
        
        new_rules.append({
            "id": rid,
            "category": "life",
            "description": f"命宮宮干{TRANS_MAP[trans]} → 飛入某宮。",
            "conditions": {
                "logic": "OR",
                "criteria": crit
            },
            "result": {
                "text": txt,
                "tags": []
            }
        })

    # Specific Rules 4H-08 to 4H-20
    
    # 4H-08: Life -> Wealth (Lu)
    new_rules.append({
        "id": "4H-08",
        "category": "wealth", # Category usually target or source? Let's use target to group results.
        "description": "命宮宮干化祿 → 飛入財帛宮。",
        "conditions": {
            "target": "wealth",
            "flying_from": "life",
            "trans": "hua_lu"
        },
        "result": { "text": "靠自己能力賺得到錢，財運不錯。", "tags": ["wealth"] }
    })

    # 4H-09: Life -> Wealth (Ji)
    new_rules.append({
        "id": "4H-09",
        "category": "wealth",
        "description": "命宮宮干化忌 → 飛入財帛宮。",
        "conditions": {
            "target": "wealth",
            "flying_from": "life",
            "trans": "hua_ji"
        },
        "result": { "text": "整天為錢煩惱，覺得錢不夠用。", "tags": ["wealth"] }
    })

    # 4H-10: Life -> Spouse (Lu)
    new_rules.append({
        "id": "4H-10",
        "category": "spouse",
        "description": "命宮宮干化祿 → 飛入夫妻宮。",
        "conditions": {
            "target": "spouse",
            "flying_from": "life",
            "trans": "hua_lu"
        },
        "result": { "text": "對配偶很好，捨得在配偶身上花錢。", "tags": ["marriage"] }
    })

    # 4H-11: Life -> Spouse (Ji)
    new_rules.append({
        "id": "4H-11",
        "category": "spouse",
        "description": "命宮宮干化忌 → 飛入夫妻宮。",
        "conditions": {
            "target": "spouse",
            "flying_from": "life",
            "trans": "hua_ji"
        },
        "result": { "text": "配偶做得再好你也會嫌棄，對感情要求高，容易虧欠對方。", "tags": ["marriage"] }
    })

    # 4H-12: Life -> Spouse (Quan)
    new_rules.append({
        "id": "4H-12",
        "category": "spouse",
        "description": "命宮宮干化權 → 飛入夫妻宮。",
        "conditions": {
            "target": "spouse",
            "flying_from": "life",
            "trans": "hua_quan"
        },
        "result": { "text": "你會把家裡的權力交給配偶，讓對方作主。", "tags": ["marriage"] }
    })

    # 4H-13: Life -> Kids (Lu)
    new_rules.append({
        "id": "4H-13",
        "category": "kids",
        "description": "命宮宮干化祿 → 飛入子女宮。",
        "conditions": {
            "target": "kids",
            "flying_from": "life",
            "trans": "hua_lu"
        },
        "result": { "text": "對小孩非常好，很疼小孩。", "tags": [] }
    })

    # 4H-14: Life -> Health (Lu OR Ji)
    new_rules.append({
        "id": "4H-14",
        "category": "health",
        "description": "命宮宮干化祿 OR 化忌 → 飛入疾厄宮。",
        "conditions": {
            "logic": "OR",
            "criteria": [
                {"target": "health", "flying_from": "life", "trans": "hua_lu"},
                {"target": "health", "flying_from": "life", "trans": "hua_ji"}
            ]
        },
        "result": { "text": "很愛惜身體(惜命命)，有一點小毛病就會買藥或保健食品來吃。", "tags": ["health"] }
    })

    # 4H-15: Life -> Friends (Ji)
    new_rules.append({
        "id": "4H-15",
        "category": "friends",
        "description": "命宮宮干化忌 → 飛入奴僕宮(朋友)。",
        "conditions": {
            "target": "friends",
            "flying_from": "life",
            "trans": "hua_ji"
        },
        "result": { "text": "容易去煩朋友，或者因為朋友的事情而操心。", "tags": [] }
    })

    # 4H-16: Life -> Career (Ji)
    new_rules.append({
        "id": "4H-16",
        "category": "career",
        "description": "命宮宮干化忌 → 飛入官祿宮。",
        "conditions": {
            "target": "career",
            "flying_from": "life",
            "trans": "hua_ji"
        },
        "result": { "text": "工作狂，必躬親，不懂授權，做得累死自己 (不親眼看就不放心)。", "tags": ["career"] }
    })

    # 4H-17: Life -> Wealth (Lu) AND Wealth -> TianJi Self-Ji
    new_rules.append({
        "id": "4H-17",
        "category": "wealth",
        "description": "命宮化祿入財帛，且財帛宮(戊干)讓天機星自化忌。",
        "conditions": {
            "logic": "AND",
            "criteria": [
                {"target": "wealth", "flying_from": "life", "trans": "hua_lu"},
                {
                    "target": "wealth", 
                    "has_star": "tian_ji", 
                    "self_trans": "hua_ji" # Checks if Wealth Stem makes TianJi Ji (implies Wu Stem)
                }
            ]
        },
        "result": { "text": "為了賺錢不擇手段，甚至連父母手足的錢都會騙 (六親不認)。", "tags": ["wealth"] }
    })

    # 4H-18: Wealth -> Life (Lu)
    new_rules.append({
        "id": "4H-18",
        "category": "life",
        "description": "財帛宮宮干化祿 → 飛入命宮。",
        "conditions": {
            "target": "life",
            "flying_from": "wealth",
            "trans": "hua_lu"
        },
        "result": { "text": "賺錢容易，錢會主動來追你 (利於賺錢)。", "tags": ["wealth"] }
    })

    # 4H-19: Wealth -> Life (Ji)
    new_rules.append({
        "id": "4H-19",
        "category": "life",
        "description": "財帛宮宮干化忌 → 飛入命宮。",
        "conditions": {
            "target": "life",
            "flying_from": "wealth",
            "trans": "hua_ji"
        },
        "result": { "text": "錢來催你付帳 (例如債務、帳單)，賺得辛苦。", "tags": ["wealth"] }
    })

    # 4H-20: Siblings -> Life (Ji)
    new_rules.append({
        "id": "4H-20",
        "category": "life",
        "description": "兄弟宮宮干化忌 → 飛入命宮。",
        "conditions": {
            "target": "life",
            "flying_from": "siblings",
            "trans": "hua_ji"
        },
        "result": { "text": "兄弟姊妹平常不聯絡，有事或要借錢才會來找你。", "tags": [] }
    })

    # Append to Main File
    # Remove duplicates if referencing specific IDs?
    # Filter out old 4H-* if they exist
    rules = [r for r in rules if not r["id"].startswith("4H-")]
    rules.extend(new_rules)

    with open(RULE_FILE, 'w', encoding='utf-8') as f:
        json.dump(rules, f, ensure_ascii=False, indent=4)
    print(f"Added {len(new_rules)} new 4H rules.")

TRANS_MAP = {
    "hua_lu": "化祿",
    "hua_quan": "化權",
    "hua_ke": "化科",
    "hua_ji": "化忌"
}

if __name__ == "__main__":
    add_flying_rules()
