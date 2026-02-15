
import json
import os
import re

# --- Step 1: Update rule_engine.py with new stars ---

engine_path = "rule_engine.py"
with open(engine_path, "r", encoding="utf-8") as f:
    content = f.read()

# Define new entries to inject
# We look for the STAR_MAP definition and valid insertion point
new_stars = {
    "tian_ku": "天哭", 
    "tian_xu": "天虛",
    "gu_chen": "孤辰", 
    "gua_su": "寡宿",
    "xian_chi": "咸池", 
    "mu_yu": "沐浴",
    "san_tai": "三台", 
    "ba_zuo": "八座",
    "tian_cai": "天才", 
    "tian_shou": "天壽",
    "tian_wu": "天巫",
    "guan_fu": "官符", 
    "bing_fu": "病符",
    "da_hao": "大耗",
    "tian_yve_2": "天月",
    "po_sui": "破碎",
    "tian_kong": "天空",
    "tian_gwan": "天官",
    "tian_fu_2": "天福",
    "jie_shen": "解神",
    "tai_fu": "台輔",
    "feng_诰": "封誥",
    "en_guang": "恩光",
    "tian_gui": "天貴",
    "po_jun": "破軍" # Ensure it is there
}

# Construct the injection string
injection = ""
for k, v in new_stars.items():
    if f'"{k}"' not in content:
        injection += f'    "{k}": "{v}",\n'

if injection:
    # Find insertion point: inside STAR_MAP, e.g., after "li_shi"
    if '"li_shi": "力士"' in content:
        content = content.replace('"li_shi": "力士"', f'"li_shi": "力士",\n{injection}')
        with open(engine_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Updated rule_engine.py with new stars.")
    else:
        print("Could not find insertion point in rule_engine.py")

# --- Step 2: Generate ziwei_rules.json ---

rules = []

def add(id, cat, desc, conds, res_text, tags=[]):
    rules.append({
        "id": id,
        "category": cat,
        "description": desc,
        "conditions": conds,
        "result": {
            "text": res_text,
            "tags": tags
        }
    })

# Life Rules (L)
add("L-01", "life", "命有空劫或三方會", {"logic": "OR", "criteria": [
    {"target": "life", "has_star": ["di_kong"]},
    {"target": "life", "has_star": ["di_jie"]},
    {"target": "life_triangle", "has_star": ["di_kong", "di_jie"]}
]}, "需有一技之長，思想天馬行空、有創意，適合創作、命理。加化科更佳。", ["career", "personality"])

add("L-02", "life", "命有地劫", {"target": "life", "has_star": ["di_jie"]}, "一生感情或金錢至少有一次大挫敗或被騙。", ["misfortune"])

add("L-03", "life", "命有地空", {"target": "life", "has_star": ["di_kong"]}, "半空折翅，易錯失升官或成功機會。", ["career"])

add("L-04", "life", "空劫夾命", {"logic": "AND", "criteria": [
    {"target": "life_clamp", "has_star": ["di_kong"]},
    {"target": "life_clamp", "has_star": ["di_jie"]}
]}, "一生渺茫，樣樣通樣樣鬆，恆心毅力需加強。", ["personality"])

add("L-05", "life", "命有化權+化忌", {"logic": "AND", "criteria": [
    {"target": "life", "has_trans": ["hua_quan"]},
    {"target": "life", "has_trans": ["hua_ji"]}
]}, "情緒起伏大，翻臉如翻書，易離婚。", ["personality", "marriage"])

# 命 or 父母宮有龍、鳳、鸞、喜同宮
add("L-06", "life", "命或父母有吉星(龍鳳鸞喜)", {"logic": "OR", "criteria": [
    {"target": "life", "has_star": ["long_chi", "feng_ge", "hong_luan", "tian_xi"]},
    {"target": "parents", "has_star": ["long_chi", "feng_ge", "hong_luan", "tian_xi"]}
]}, "長相男帥女美，為人正派，胸襟廣闊。", ["appearance"])

add("L-07", "life", "命有龍鳳二顆", {"logic": "AND", "criteria": [
    {"target": "life", "has_star": ["long_chi"]},
    {"target": "life", "has_star": ["feng_ge"]}
]}, "就算失敗也會有遇到好的機會翻身。", ["fortune"])

add("L-08", "life", "命有紅鸞天喜", {"logic": "AND", "criteria": [
    {"target": "life", "has_star": ["hong_luan"]},
    {"target": "life", "has_star": ["tian_xi"]}
]}, "有人緣，若會昌曲則有氣質。", ["personality", "appearance"])

add("L-09", "life", "只有紅鸞在命", {"logic": "AND", "criteria": [
    {"target": "life", "has_star": ["hong_luan"]},
    {"target": "life", "not_has_star": ["tian_xi"]}
]}, "就算不美但很深緣。", ["appearance"])

add("L-10", "life", "命或福德有紫微+空劫", {"logic": "OR", "criteria": [
    {"logic": "AND", "criteria": [{"target": "life", "has_star": ["zi_wei"]}, {"target": "life", "has_star": ["di_kong", "di_jie"]}]},
    {"logic": "AND", "criteria": [{"target": "fortune", "has_star": ["zi_wei"]}, {"target": "fortune", "has_star": ["di_kong", "di_jie"]}]}
]}, "會想過隱士般的出家生活。", ["personality"])

add("L-11", "life", "命有化忌+陰煞/四煞", {"logic": "AND", "criteria": [
    {"target": "life", "has_trans": ["hua_ji"]},
    {"logic": "OR", "criteria": [
        {"target": "life", "has_star": ["yin_sha"]},
        {"target": "life", "has_star": ["qing_yang", "tuo_luo", "huo_xing", "ling_xing"]}
    ]}
]}, "心術不正。若見昌曲化忌或天姚則更奸詐。", ["personality"])

add("L-12", "life", "命有陰煞", {"target": "life", "has_star": ["yin_sha"]}, "經常被人陷害。若會四煞則會去害人。", ["misfortune"])

add("L-13", "life", "命有祿馬交馳+吉星", {"logic": "AND", "criteria": [
    {"target": "life", "has_star": ["lu_cun"]},
    {"target": "life", "has_star": ["tian_ma"]},
    {"target": "life", "has_star": ["zuo_fu", "you_bi", "tian_kui", "tian_yue"]}
]}, "好命，若主星是紫府或紫相更佳。", ["fortune"])

add("L-14", "life", "財帛三方有昌曲化忌", {"target": "life_triangle", "has_star": ["wen_chang", "wen_qu"], "has_trans": ["hua_ji"]}, "注意文書被跳票，以現金買賣為佳。", ["wealth", "career"])

add("L-15", "life", "命有天刑孤寡", {"logic": "AND", "criteria": [
    {"target": "life", "has_star": ["tian_xing"]},
    {"target": "life", "has_star": ["gu_chen", "gua_su"]}
]}, "會精神劈腿，但不敢行動。", ["marriage"])

add("L-16", "life", "命有火星", {"target": "life", "has_star": ["huo_xing"]}, "火性、性急、行動派。若逢天馬為「戰馬」，瞎忙。", ["personality"])

add("L-17", "life", "命身有孤寡", {"logic": "OR", "criteria": [
    {"target": "life", "has_star": ["gu_chen", "gua_su"]}
]}, "個性極端，若加天刑羊刃易走極端自殺或殺人。", ["personality", "danger"])

add("L-18", "life", "命有羊刃+力士", {"logic": "AND", "criteria": [
    {"target": "life", "has_star": ["qing_yang"]},
    {"target": "life", "has_star": ["li_shi"]}
]}, "講話直辣，評論是非，但很有毅力。", ["personality"])

add("L-19", "life", "命有昌曲龍鳳天才", {"target": "life", "has_star": ["wen_chang", "wen_qu", "long_chi", "feng_ge", "tian_cai"]}, "很聰明，偷吃會擦嘴。", ["personality"])

# Spouse Rules (S)
add("S-01", "spouse", "夫妻宮廉貞化忌/陷", {"logic": "AND", "criteria": [
    {"target": "spouse", "has_star": ["lian_zhen"]},
    {"logic": "OR", "criteria": [
        {"target": "spouse_star", "star": "lian_zhen", "has_trans": ["hua_ji"]},
        {"target": "spouse_star", "star": "lian_zhen", "brightness": "trap"}
    ]}
]}, "女命早婚丈夫易劈腿，易遇爛桃花。", ["marriage"])

add("S-02", "spouse", "夫妻宮祿存", {"target": "spouse", "has_star": ["lu_cun"]}, "配偶多金，但若逢破軍加煞則刻薄。", ["marriage"])

add("S-03", "spouse", "夫妻宮空劫/天刑+煞", {"logic": "AND", "criteria": [
    {"target": "spouse", "has_star": ["di_kong", "di_jie", "tian_xing"]},
    {"target": "spouse", "has_star": ["qing_yang", "tuo_luo", "huo_xing", "ling_xing"]}
]}, "相處時間少，易爭吵，易離婚。", ["marriage"])

add("S-04", "spouse", "夫妻宮天馬", {"target": "spouse", "has_star": ["tian_ma"]}, "嫁外縣市或遠方。煞多易離婚。", ["marriage"])

add("S-05", "spouse", "女命夫妻宮天鉞", {"target": "context", "gender": "F"}, "有女性貴人，丈夫易劈腿。", ["marriage"]) 

add("S-06", "spouse", "夫妻宮化祿/化權", {"target": "spouse", "has_trans": ["hua_lu", "hua_quan"]}, "性生活美滿。化權配偶喜掌權。", ["marriage"])

add("S-07", "spouse", "女命夫妻宮破軍", {"logic": "AND", "criteria": [
    {"target": "context", "gender": "F"},
    {"target": "spouse", "has_star": ["po_jun"]}
]}, "易離婚，易受夫家排擠。", ["marriage"])

add("S-08", "spouse", "女命夫妻宮太陽化祿", {"logic": "AND", "criteria": [
    {"target": "context", "gender": "F"},
    {"target": "spouse_star", "star": "tai_yang", "has_trans": ["hua_lu"]}
]}, "丈夫容易劈腿。", ["marriage"])

add("S-09", "spouse", "夫妻宮火星", {"target": "spouse", "has_star": ["huo_xing"]}, "閃電結婚閃電離婚。", ["marriage"])

add("S-10", "spouse", "夫妻宮陀羅", {"target": "spouse", "has_star": ["tuo_luo"]}, "婚事拖磨，離婚也拖磨。", ["marriage"])

add("S-11", "spouse", "夫妻宮殺破狼", {"target": "spouse", "has_star": ["qi_sha", "po_jun", "tan_lang"]}, "變動大，見煞易感情波動。", ["marriage"])

# Wealth Rules (W)
add("W-01", "wealth", "財宮火貪/鈴貪", {"logic": "AND", "criteria": [
    {"target": "wealth", "has_star": ["tan_lang"]},
    {"target": "wealth", "has_star": ["huo_xing", "ling_xing"]},
    {"target": "wealth", "not_has_star": ["di_kong", "di_jie"]}
]}, "偏財運佳，無羊陀空劫可橫發。", ["wealth"])

add("W-02", "wealth", "財宮自化祿", {"target": "wealth", "self_trans": ["hua_lu"]}, "錢左手進右手出，存不住。", ["wealth"])

add("W-03", "wealth", "財宮有化忌", {"target": "wealth", "has_trans": ["hua_ji"]}, "賺錢辛苦，存不住。", ["wealth"])

add("W-04", "wealth", "財宮雙祿", {"logic": "AND", "criteria": [
    {"target": "wealth", "has_trans": ["hua_lu"]},
    {"target": "wealth", "has_star": ["lu_cun"]}
]}, "雙祿交流，財運極佳。", ["wealth"])

add("W-05", "wealth", "財宮自化忌", {"target": "wealth", "self_trans": ["hua_ji"]}, "來源少支出多。", ["wealth"])

add("W-06", "wealth", "財宮空劫", {"target": "wealth", "has_star": ["di_kong", "di_jie"]}, "財來財去，賺少賠多。", ["wealth"])

add("W-07", "wealth", "財宮天姚", {"target": "wealth", "has_star": ["tian_yao"]}, "男命賭博贏錢開查某，女命愛買東西。", ["wealth"])

# Health (H)
add("H-01", "health", "疾厄羊刃化忌", {"logic": "AND", "criteria": [
    {"target": "health", "has_star": ["qing_yang"]},
    {"target": "health", "has_trans": ["hua_ji"]}
]}, "容易生重症，如癌症。", ["health"])

add("H-02", "health", "疾厄有羊刃", {"target": "health", "has_star": ["qing_yang"]}, "一生至少開刀一次。", ["health"])

add("H-03", "health", "疾厄桃花星多", {"target": "health", "has_star": ["tian_yao", "hong_luan", "tian_xi", "xian_chi"]}, "男命好色，女命丈夫有桃花。", ["health"])

# Migration (M)
add("M-01", "travel", "遷移巨門化忌/陀羅/天刑", {"logic": "AND", "criteria": [
    {"target": "travel", "has_star": ["ju_men", "tuo_luo", "tian_xing"]},
    {"target": "travel", "has_trans": ["hua_ji"]}
]}, "車關，出外口舌官司。", ["travel", "danger"])

add("M-02", "travel", "遷移左右", {"target": "travel", "has_star": ["zuo_fu", "you_bi"]}, "出外有貴人相助。", ["travel"])

add("M-03", "travel", "遷移文曲化忌", {"target": "travel", "has_star": ["wen_qu"], "has_trans": ["hua_ji"]}, "小心水厄。", ["travel"])

# Friends (F)
add("F-01", "friends", "交友破軍/七殺+煞", {"logic": "AND", "criteria": [
    {"target": "friends", "has_star": ["po_jun", "qi_sha"]},
    {"target": "friends", "has_star": ["qing_yang", "tuo_luo", "yin_sha"]}
]}, "易被朋友陷害。", ["relationships"])

add("F-02", "friends", "交友化忌+羊陀", {"logic": "AND", "criteria": [
    {"target": "friends", "has_trans": ["hua_ji"]},
    {"target": "friends", "has_star": ["qing_yang", "tuo_luo"]}
]}, "損友多，交友不慎。", ["relationships"])

# Career (C)
add("C-01", "career", "官祿破軍陀羅", {"logic": "AND", "criteria": [
    {"target": "career", "has_star": ["po_jun"]},
    {"target": "career", "has_star": ["tuo_luo"]}
]}, "適合流動攤販、夜市，需一技之長。", ["career"])

add("C-02", "career", "官祿巨門", {"target": "career", "has_star": ["ju_men"]}, "適合靠嘴吃飯，業務、推銷。", ["career"])

add("C-03", "career", "官祿文昌/文曲化科", {"target": "career", "has_star": ["wen_chang", "wen_qu"], "has_trans": ["hua_ke"]}, "適合老師、作家、動腦職業。", ["career"])

# Property (P)
add("P-01", "property", "田宅化權", {"target": "property", "has_trans": ["hua_quan"]}, "婚後家裡大小事都要管。", ["family"])

add("P-02", "property", "田宅空劫/羊刃/化忌", {"target": "property", "has_star": ["di_kong", "di_jie", "qing_yang"], "has_trans": ["hua_ji"]}, "錢存不住，財庫破損。", ["wealth"])

add("P-03", "property", "田宅陰煞", {"target": "property", "has_star": ["yin_sha"]}, "家裡要有宗教供奉，家運才會好。", ["family"])

# Fortune (Fd)
add("Fd-01", "fortune", "福德天同", {"target": "fortune", "has_star": ["tian_tong"]}, "變胖會很懶惰。", ["personality"])

add("Fd-02", "fortune", "福德孤寡", {"target": "fortune", "has_star": ["gu_chen", "gua_su"]}, "內心怕空虛，易有一夜情。", ["personality"])

add("Fd-03", "fortune", "福德武殺", {"target": "fortune", "has_star": ["wu_qu", "qi_sha"]}, "外柔內剛。", ["personality"])

add("Fd-04", "fortune", "福德有煞", {"target": "fortune", "has_star": ["qing_yang", "tuo_luo", "di_kong", "di_jie"]}, "思想悲觀消極，愛鑽牛角尖。", ["personality"])

# Parents (Pt)
add("Pt-01", "parents", "父母龍鳳", {"target": "parents", "has_star": ["long_chi", "feng_ge"]}, "父母外貌佳。", ["family"])

add("Pt-02", "parents", "父母化權", {"target": "parents", "has_trans": ["hua_quan"]}, "父母管教嚴格。", ["family"])

# Special (X)
add("X-01", "special", "恐怖命格-子日忌羊刑", {"logic": "AND", "criteria": [
    {"target": "context", "gender": "M"},
    {"target": "palace_zi", "has_star": ["tai_yang"]},
    {"target": "palace_zi_star", "star": "tai_yang", "has_trans": ["hua_ji"]},
    {"target": "palace_zi", "has_star": ["qing_yang", "tian_xing"]}
]}, "恐怖命格：易情殺或談判決裂。", ["danger"])

add("X-02", "special", "戰馬", {"logic": "AND", "criteria": [
    {"target": "life", "has_star": ["huo_xing", "tian_ma"]}
]}, "戰馬：瞎忙，不曉得在忙啥。", ["personality"])

add("X-03", "special", "自殺組", {"target": "fortune", "has_star": ["tian_ji"], "has_trans": ["hua_ji"]}, "福德天機化忌，易有自殺傾向。", ["danger"])

add("X-04", "special", "路上埋屍", {"logic": "AND", "criteria": [
    {"target": "travel", "has_star": ["lian_zhen", "qi_sha", "qing_yang"]}
]}, "路上埋屍：重大車關。", ["danger"])

add("X-05", "special", "女生子宮問題", {"logic": "AND", "criteria": [
    {"target": "context", "gender": "F"},
    {"target": "property", "has_star": ["qing_yang"]}
]}, "子宮易出問題，注意婦科檢查。", ["health"])

# Write to file
file_path = "ziwei_rules.json"
with open(file_path, "w", encoding="utf-8") as f:
    json.dump(rules, f, ensure_ascii=False, indent=4)

print(f"Successfully generated {len(rules)} rules to {file_path}")
